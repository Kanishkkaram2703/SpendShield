"""Payment application boundary with explicit domain-error mapping."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime
from uuid import uuid4

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.domain.financial import (
    AccountNotActiveError,
    FinancialDomainError,
    IdempotencyConflictError,
    InsufficientFundsError,
    PaymentCommand,
    PaymentConcurrencyError,
    PaymentExecution,
    PaymentInProgressError,
    validate_idempotency_reuse,
    utc_now,
)
from app.repositories.payments import (
    PaymentCursorError,
    PaymentPage,
    PaymentRepository,
    TransferPaymentRepository,
)
from app.repositories.demo_resources import DemoResourceRepository, DuplicateDemoResourceError
from app.services.event_delivery_service import EventDeliveryService
from app.services.merchant_service import MerchantService

LOGGER = get_logger(__name__)


class PaymentService:
    """Keep HTTP concerns out of payment validation and persistence orchestration."""

    def __init__(
        self,
        repository: PaymentRepository,
        event_delivery_service: EventDeliveryService | None = None,
        merchant_service: MerchantService | None = None,
        notification_repository: DemoResourceRepository | None = None,
    ) -> None:
        self._repository = repository
        self._event_delivery_service = event_delivery_service
        self._merchant_service = merchant_service
        self._notification_repository = notification_repository

    def execute(
        self,
        command: PaymentCommand,
        *,
        at: datetime | None = None,
    ) -> PaymentExecution:
        """Execute a payment through a repository that owns atomicity."""

        try:
            execution = None
            if self._merchant_service is not None:
                # A committed successful replay must remain idempotent even if
                # current merchant state changed after the original payment.
                existing = self._repository.get_completed_by_idempotency(
                    command.owner_id,
                    command.idempotency_key,
                )
                if existing is not None:
                    validate_idempotency_reuse(
                        existing.transaction.request_fingerprint,
                        command.fingerprint,
                    )
                    execution = existing
            if execution is None and self._merchant_service is not None:
                resolution = self._merchant_service.resolve_for_payment(
                    command.merchant_id
                )
                command = replace(
                    command,
                    merchant_id=resolution.merchant.merchant_id,
                    merchant_name=resolution.merchant.merchant_name,
                    category_id=resolution.category.category_id,
                    category_name=resolution.category.category_name,
                    subcategory_id=resolution.category.subcategory_id,
                    subcategory_name=resolution.category.subcategory_name,
                )
            if execution is None:
                execution = self._repository.execute(
                    command,
                    transaction_id=str(uuid4()),
                    at=at or utc_now(),
                )
            if self._event_delivery_service is not None:
                try:
                    # Historical delivery is post-commit and must never cause
                    # a committed fictional debit to be repeated or rolled back.
                    self._event_delivery_service.publish_pending(
                        now=execution.transaction.updated_at
                    )
                except Exception:  # noqa: BLE001 - persistence remains committed
                    LOGGER.warning(
                        "payment_event_delivery_deferred transaction_id=%s",
                        execution.transaction.transaction_id,
                    )
            self._notify(execution)
            return execution
        except IdempotencyConflictError as exc:
            self._notify_failure(command, "idempotency_conflict")
            raise AppError(
                code="idempotency_conflict",
                message="The idempotency key was already used for another request.",
                status_code=409,
            ) from exc
        except AccountNotActiveError as exc:
            self._notify_failure(command, "account_not_active")
            raise AppError(
                code="account_not_active",
                message="The account cannot perform this operation.",
                status_code=409,
            ) from exc
        except InsufficientFundsError as exc:
            self._notify_failure(command, "insufficient_funds")
            raise AppError(
                code="insufficient_funds",
                message="The account balance is insufficient.",
                status_code=409,
            ) from exc
        except PaymentConcurrencyError as exc:
            self._notify_failure(command, "payment_concurrency_conflict")
            raise AppError(
                code="payment_concurrency_conflict",
                message="The account changed while the payment was being applied; retry with a new request key.",
                status_code=409,
            ) from exc
        except PaymentInProgressError as exc:
            self._notify_failure(command, "payment_in_progress")
            raise AppError(
                code="payment_in_progress",
                message="The payment is still being recovered; retry the same request later.",
                status_code=409,
            ) from exc
        except FinancialDomainError as exc:
            self._notify_failure(command, "financial_rule_violation")
            raise AppError(
                code="financial_rule_violation",
                message="The financial operation violates a domain rule.",
                status_code=422,
            ) from exc

    def execute_demo(self, command: PaymentCommand, *, at: datetime | None = None) -> PaymentExecution:
        """Execute a non-merchant demo operation without catalog resolution."""

        try:
            execution = self._repository.execute(
                command,
                transaction_id=str(uuid4()),
                at=at or utc_now(),
            )
            self._publish_pending(execution)
            self._notify(execution)
            return execution
        except IdempotencyConflictError as exc:
            self._notify_failure(command, "idempotency_conflict")
            raise AppError(
                code="idempotency_conflict",
                message="The idempotency key was already used for another request.",
                status_code=409,
            ) from exc
        except AccountNotActiveError as exc:
            self._notify_failure(command, "account_not_active")
            raise AppError(
                code="account_not_active",
                message="The account cannot perform this operation.",
                status_code=409,
            ) from exc
        except InsufficientFundsError as exc:
            self._notify_failure(command, "insufficient_funds")
            raise AppError(
                code="insufficient_funds",
                message="The account balance is insufficient.",
                status_code=409,
            ) from exc
        except PaymentConcurrencyError as exc:
            self._notify_failure(command, "payment_concurrency_conflict")
            raise AppError(
                code="payment_concurrency_conflict",
                message="The account changed while the operation was being applied; retry with a new request key.",
                status_code=409,
            ) from exc
        except PaymentInProgressError as exc:
            self._notify_failure(command, "payment_in_progress")
            raise AppError(
                code="payment_in_progress",
                message="The operation is still being recovered; retry the same request later.",
                status_code=409,
            ) from exc
        except FinancialDomainError as exc:
            self._notify_failure(command, "financial_rule_violation")
            raise AppError(
                code="financial_rule_violation",
                message="The demo operation violates a domain rule.",
                status_code=422,
            ) from exc

    def execute_transfer(
        self,
        command: PaymentCommand,
        *,
        destination_account_id: str,
        destination_owner_id: str | None,
        destination_name: str | None,
        at: datetime | None = None,
    ) -> tuple[PaymentExecution, str]:
        """Execute a two-account demo transfer through the repository boundary."""

        repository = self._repository
        if not isinstance(repository, TransferPaymentRepository):
            raise AppError(
                code="demo_transfer_not_configured",
                message="Two-account demo transfers are not configured for this environment.",
                status_code=503,
            )
        try:
            execution, related_id = repository.execute_transfer(
                command,
                destination_account_id=destination_account_id,
                destination_owner_id=destination_owner_id,
                destination_name=destination_name,
                transaction_id=str(uuid4()),
                at=at or utc_now(),
            )
            self._publish_pending(execution)
            self._notify(execution)
            return execution, related_id
        except IdempotencyConflictError as exc:
            self._notify_failure(command, "idempotency_conflict")
            raise AppError(
                code="idempotency_conflict",
                message="The idempotency key was already used for another request.",
                status_code=409,
            ) from exc
        except AccountNotActiveError as exc:
            self._notify_failure(command, "account_not_active")
            raise AppError(
                code="account_not_active",
                message="The account cannot perform this operation.",
                status_code=409,
            ) from exc
        except InsufficientFundsError as exc:
            self._notify_failure(command, "insufficient_funds")
            raise AppError(
                code="insufficient_funds",
                message="The account balance is insufficient.",
                status_code=409,
            ) from exc
        except PaymentConcurrencyError as exc:
            self._notify_failure(command, "payment_concurrency_conflict")
            raise AppError(
                code="payment_concurrency_conflict",
                message="An account changed while the demo transfer was being applied; retry with a new request key.",
                status_code=409,
            ) from exc
        except PaymentInProgressError as exc:
            self._notify_failure(command, "payment_in_progress")
            raise AppError(
                code="payment_in_progress",
                message="The demo transfer is still being recovered; retry the same request later.",
                status_code=409,
            ) from exc
        except FinancialDomainError as exc:
            self._notify_failure(command, "financial_rule_violation")
            raise AppError(
                code="financial_rule_violation",
                message="The demo transfer violates a domain rule.",
                status_code=422,
            ) from exc

    def _publish_pending(self, execution: PaymentExecution) -> None:
        if self._event_delivery_service is None:
            return
        try:
            self._event_delivery_service.publish_pending(
                now=execution.transaction.updated_at
            )
        except Exception:  # noqa: BLE001 - delivery remains retryable
            LOGGER.warning(
                "payment_event_delivery_deferred transaction_id=%s",
                execution.transaction.transaction_id,
            )

    def _notify(self, execution: PaymentExecution) -> None:
        """Create one owner-scoped in-app notification after commit.

        The deterministic source transaction key makes a replay safe even when
        a client retries after the financial operation has already committed.
        """

        repository = self._notification_repository
        if repository is None:
            return
        transaction = execution.transaction
        title = "Demo payment successful" if transaction.status.value == "COMPLETED" else "Demo payment update"
        counterparty = transaction.merchant_name or transaction.counterparty_name or "demo operation"
        try:
            repository.create(
                transaction.owner_id,
                {
                    "notification_id": f"payment-{transaction.transaction_id}",
                    "source_transaction_id": transaction.transaction_id,
                    "category": "PAYMENT",
                    "title": title,
                    "message": f"{transaction.amount} {transaction.currency} recorded for {counterparty}.",
                    "is_read": False,
                },
            )
        except DuplicateDemoResourceError:
            return
        except Exception:  # noqa: BLE001 - notifications cannot roll back money
            LOGGER.warning(
                "demo_notification_deferred transaction_id=%s",
                transaction.transaction_id,
            )

    def _notify_failure(self, command: PaymentCommand, reason: str) -> None:
        """Record one safe owner-scoped notification for a failed operation.

        The identifier is derived from the owner, idempotency key, and safe
        domain error code.  The raw key and financial request details are not
        persisted in the notification, so retries remain idempotent without
        leaking request data into the UI.
        """

        repository = self._notification_repository
        if repository is None:
            return
        digest = hashlib.sha256(
            f"{command.owner_id}|{command.idempotency_key}|{reason}".encode("utf-8")
        ).hexdigest()[:32]
        try:
            repository.create(
                command.owner_id,
                {
                    "notification_id": f"payment-failed-{digest}",
                    "category": "PAYMENT_FAILED",
                    "title": "Demo payment failed",
                    "message": f"Your fictional payment could not be completed ({reason}).",
                    "is_read": False,
                },
            )
        except DuplicateDemoResourceError:
            return
        except Exception:  # noqa: BLE001 - notifications cannot alter failure semantics
            LOGGER.warning("demo_failure_notification_deferred reason=%s", reason)

    def get_for_owner(
        self,
        transaction_id: str,
        *,
        owner_id: str,
    ):
        """Return one current transaction or a safe owner-scoped 404."""

        execution = self._repository.get_by_id(transaction_id, owner_id=owner_id)
        if execution is None:
            raise AppError(
                code="payment_not_found",
                message="Payment was not found.",
                status_code=404,
            )
        return execution

    def list_for_owner(
        self,
        owner_id: str,
        *,
        limit: int,
        cursor: str | None = None,
        status=None,
        merchant_id: str | None = None,
    ) -> PaymentPage:
        """Return one bounded page of current owner-scoped transactions."""

        try:
            return self._repository.list_for_owner(
                owner_id,
                limit=limit,
                cursor=cursor,
                status=status,
                merchant_id=merchant_id,
            )
        except PaymentCursorError as exc:
            raise AppError(
                code="invalid_payment_cursor",
                message="The payment history cursor is invalid or unavailable.",
                status_code=422,
            ) from exc


__all__ = ["PaymentService"]
