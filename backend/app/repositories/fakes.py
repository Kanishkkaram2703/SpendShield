"""Explicit non-production repositories used by isolated tests only."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from app.domain.catalog import CategoryRecord, MerchantRecord, MerchantStatus
from app.domain.financial import (
    Account,
    FinancialDomainError,
    PaymentCommand,
    PaymentExecution,
    Transaction,
    TransactionDirection,
    TransactionType,
    TransactionStatus,
    authorize_payment,
    validate_idempotency_reuse,
)
from app.events.models import DomainEvent
from app.events.publication import (
    EventPublicationTarget,
    PendingEventPublication,
)
from app.repositories.accounts import AccountVersionConflictError, DuplicateAccountError
from app.repositories.merchants import (
    DuplicateMerchantError,
    MerchantCursorError,
    MerchantPage,
    MerchantVersionConflictError,
)
from app.repositories.payments import (
    PaymentCursorError,
    PaymentHistoryWindow,
    PaymentPage,
)
from app.repositories.users import DuplicateUserError, UserRecord


class InMemoryUserRepository:
    """Volatile test fake; it is never selected by the production app."""

    def __init__(self) -> None:
        self._by_id: dict[str, UserRecord] = {}
        self._by_email: dict[str, UserRecord] = {}

    def get_by_email(self, email: str) -> UserRecord | None:
        return self._by_email.get(email)

    def get_by_id(self, user_id: str) -> UserRecord | None:
        return self._by_id.get(user_id)

    def create(self, user: UserRecord) -> UserRecord:
        if user.email in self._by_email or user.user_id in self._by_id:
            raise DuplicateUserError(user.email)
        self._by_id[user.user_id] = user
        self._by_email[user.email] = user
        return user

    def update(self, user: UserRecord) -> UserRecord:
        if user.user_id not in self._by_id:
            raise KeyError(user.user_id)
        existing = self._by_email.get(user.email)
        if existing is not None and existing.user_id != user.user_id:
            raise DuplicateUserError(user.email)
        old = self._by_id[user.user_id]
        self._by_id[user.user_id] = user
        if old.email != user.email:
            self._by_email.pop(old.email, None)
        self._by_email[user.email] = user
        return user

    def set_active(self, user_id: str, is_active: bool) -> UserRecord:
        """Update active status for tests that exercise disabled accounts."""

        user = self._by_id[user_id]
        updated = replace(user, is_active=is_active)
        self._by_id[user.user_id] = updated
        self._by_email[user.email] = updated
        return updated


class InMemoryAccountRepository:
    """Thread-safe volatile account fake for service/API tests only."""

    def __init__(self) -> None:
        self._by_id: dict[str, Account] = {}
        self._by_owner: dict[str, list[Account]] = {}
        self._lock = RLock()

    def create(self, account: Account, *, allow_duplicate_owner: bool = False) -> Account:
        with self._lock:
            if account.account_id in self._by_id or (
                not allow_duplicate_owner and account.owner_id in self._by_owner
            ):
                raise DuplicateAccountError(account.owner_id)
            self._by_id[account.account_id] = account
            self._by_owner.setdefault(account.owner_id, []).append(account)
            return account

    def get_by_id(self, account_id: str) -> Account | None:
        with self._lock:
            return self._by_id.get(account_id)

    def get_by_owner(self, owner_id: str) -> Account | None:
        with self._lock:
            accounts = self._by_owner.get(owner_id, [])
            return accounts[0] if accounts else None

    def list_by_owner(self, owner_id: str) -> tuple[Account, ...]:
        with self._lock:
            return tuple(self._by_owner.get(owner_id, []))

    def update(self, account: Account, *, expected_version: int) -> Account | None:
        with self._lock:
            current = self._by_id.get(account.account_id)
            if current is None:
                return None
            if current.version != expected_version:
                raise AccountVersionConflictError(account.account_id)
            self._by_id[account.account_id] = account
            accounts = self._by_owner.get(account.owner_id, [])
            self._by_owner[account.owner_id] = [
                account if item.account_id == account.account_id else item
                for item in accounts
            ]
            return account


class InMemoryAuditRepository:
    """Volatile audit fake for service/API tests only."""

    def __init__(self) -> None:
        self.events: list[DomainEvent] = []
        self._event_ids: set[str] = set()
        self._publications: dict[str, PendingEventPublication] = {}
        self._lock = RLock()

    def append(
        self,
        event: DomainEvent,
        *,
        publication_target: EventPublicationTarget | None = None,
        session: object | None = None,
    ) -> None:
        with self._lock:
            event_id = str(event.event_id)
            if event_id in self._event_ids:
                return None
            self._event_ids.add(event_id)
            self.events.append(event)
            if publication_target is not None:
                self._publications[event_id] = PendingEventPublication(
                    event=event,
                    target=publication_target,
                    attempt_count=0,
                    next_attempt_at=event.created_at,
                )

    def list_due(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[PendingEventPublication]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        current = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        current = current.astimezone(timezone.utc)
        with self._lock:
            return sorted(
                (
                    publication
                    for publication in self._publications.values()
                    if publication.next_attempt_at <= current
                ),
                key=lambda publication: (
                    publication.next_attempt_at,
                    publication.event.created_at,
                    str(publication.event.event_id),
                ),
            )[:limit]

    def mark_published(self, event_id: str, *, published_at: datetime) -> None:
        with self._lock:
            self._publications.pop(event_id, None)

    def mark_failed(
        self,
        event_id: str,
        *,
        failed_at: datetime,
        next_attempt_at: datetime,
        error_code: str,
    ) -> None:
        with self._lock:
            publication = self._publications.get(event_id)
            if publication is None:
                return None
            self._publications[event_id] = PendingEventPublication(
                event=publication.event,
                target=publication.target,
                attempt_count=publication.attempt_count + 1,
                next_attempt_at=next_attempt_at,
                last_error=error_code[:128],
            )


class InMemoryCategoryRepository:
    """Thread-safe canonical taxonomy fake used by service/API tests."""

    def __init__(self, categories: list[CategoryRecord] | None = None) -> None:
        self._categories = {
            (category.category_id, category.subcategory_id): category
            for category in categories or []
        }
        self._lock = RLock()

    def get(self, category_id: str, subcategory_id: str) -> CategoryRecord | None:
        with self._lock:
            return self._categories.get((category_id, subcategory_id))

    def list(
        self,
        *,
        active_only: bool = True,
        limit: int = 100,
    ) -> tuple[CategoryRecord, ...]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self._lock:
            categories = [
                category
                for category in self._categories.values()
                if not active_only or category.is_active
            ]
            categories.sort(key=lambda item: (item.category_id, item.subcategory_id))
            return tuple(categories[:limit])

    def ensure(self, category: CategoryRecord) -> CategoryRecord:
        with self._lock:
            return self._categories.setdefault(
                (category.category_id, category.subcategory_id), category
            )


class InMemoryMerchantRepository:
    """Thread-safe current-state merchant fake used by service/API tests."""

    def __init__(self, merchants: list[MerchantRecord] | None = None) -> None:
        self._merchants = {
            merchant.merchant_id: merchant for merchant in merchants or []
        }
        self._lock = RLock()

    def create(self, merchant: MerchantRecord) -> MerchantRecord:
        with self._lock:
            if merchant.merchant_id in self._merchants:
                raise DuplicateMerchantError(merchant.merchant_id)
            self._merchants[merchant.merchant_id] = merchant
            return merchant

    def get_by_id(self, merchant_id: str) -> MerchantRecord | None:
        with self._lock:
            return self._merchants.get(merchant_id)

    def update(
        self,
        merchant: MerchantRecord,
        *,
        expected_version: int,
    ) -> MerchantRecord | None:
        with self._lock:
            current = self._merchants.get(merchant.merchant_id)
            if current is None:
                return None
            if current.version != expected_version:
                raise MerchantVersionConflictError(merchant.merchant_id)
            self._merchants[merchant.merchant_id] = merchant
            return merchant

    def list(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: MerchantStatus | None = None,
        category_id: str | None = None,
        subcategory_id: str | None = None,
    ) -> MerchantPage:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        with self._lock:
            merchants = [
                merchant
                for merchant in self._merchants.values()
                if (status is None or merchant.status is status)
                and (category_id is None or merchant.category_id == category_id)
                and (
                    subcategory_id is None
                    or merchant.subcategory_id == subcategory_id
                )
            ]
            merchants.sort(
                key=lambda item: (item.merchant_name.casefold(), item.merchant_id)
            )
            if cursor is not None:
                cursor_index = next(
                    (
                        index
                        for index, merchant in enumerate(merchants)
                        if merchant.merchant_id == cursor
                    ),
                    None,
                )
                if cursor_index is None:
                    raise MerchantCursorError()
                merchants = merchants[cursor_index + 1 :]
            page = merchants[: limit + 1]
            has_more = len(page) > limit
            items = tuple(page[:limit])
            return MerchantPage(
                items=items,
                next_cursor=(
                    items[-1].merchant_id if has_more and items else None
                ),
            )


class InMemoryPaymentRepository:
    """Atomic volatile payment fake used only for service/domain tests."""

    def __init__(self, accounts: list[Account] | None = None) -> None:
        self._accounts = {account.account_id: account for account in accounts or []}
        self._executions: dict[tuple[str, str], PaymentExecution] = {}
        self._lock = RLock()

    def execute(
        self,
        command: PaymentCommand,
        *,
        transaction_id: str,
        at: datetime,
    ) -> PaymentExecution:
        with self._lock:
            key = (command.owner_id, command.idempotency_key)
            existing = self._executions.get(key)
            if existing is not None:
                validate_idempotency_reuse(
                    existing.transaction.request_fingerprint,
                    command.fingerprint,
                )
                return existing
            account = self._accounts.get(command.account_id)
            if account is None:
                raise FinancialDomainError("Account was not found.")
            execution = authorize_payment(
                account,
                command,
                transaction_id=transaction_id,
                at=at,
            )
            self._accounts[account.account_id] = execution.account
            self._executions[key] = execution
            return execution

    def execute_transfer(
        self,
        command: PaymentCommand,
        *,
        destination_account_id: str,
        destination_owner_id: str | None,
        destination_name: str | None,
        transaction_id: str,
        at: datetime,
    ) -> tuple[PaymentExecution, str]:
        with self._lock:
            key = (command.owner_id, command.idempotency_key)
            existing = self._executions.get(key)
            if existing is not None:
                validate_idempotency_reuse(
                    existing.transaction.request_fingerprint,
                    command.fingerprint,
                )
                related = next(
                    (
                        item.transaction.transaction_id
                        for item in self._executions.values()
                        if item.transaction.transfer_reference
                        == existing.transaction.transfer_reference
                        and item.transaction.direction is TransactionDirection.CREDIT
                    ),
                    "",
                )
                return existing, related
            source = self._accounts.get(command.account_id)
            destination = self._accounts.get(destination_account_id)
            if source is None:
                raise FinancialDomainError("Source account was not found.")
            if destination is None:
                raise FinancialDomainError("Destination account was not found.")
            if destination_owner_id is not None and destination.owner_id != destination_owner_id:
                raise FinancialDomainError("Destination account is not owned by the current user.")
            if source.account_id == destination.account_id:
                raise FinancialDomainError("Source and destination accounts must be different.")
            operation_command = replace(command, transfer_reference=transaction_id)
            source_execution = authorize_payment(
                source,
                operation_command,
                transaction_id=transaction_id,
                at=at,
            )
            credited_account = destination.credit(command.amount, at=at)
            credit_transaction = Transaction(
                transaction_id=str(uuid4()),
                account_id=destination.account_id,
                owner_id=destination.owner_id,
                currency=destination.currency,
                amount=command.amount,
                status=TransactionStatus.INITIATED,
                idempotency_key=f"credit-{transaction_id}",
                request_fingerprint=command.fingerprint,
                transaction_channel=command.transaction_channel,
                note=command.note,
                transaction_type=(
                    TransactionType.SELF_TRANSFER_CREDIT
                    if command.transaction_type is TransactionType.SELF_TRANSFER_DEBIT
                    else TransactionType.SEND_MONEY_CREDIT
                ),
                direction=TransactionDirection.CREDIT,
                counterparty_account_id=source.account_id,
                counterparty_name=destination_name,
                transfer_reference=transaction_id,
                actor_id=command.owner_id,
                correlation_id=command.correlation_id,
                causation_id=command.causation_id,
                created_at=at,
                updated_at=at,
                balance_before=destination.balance,
                balance_after=credited_account.balance,
            )
            for status in (TransactionStatus.AUTHORIZED, TransactionStatus.PROCESSING, TransactionStatus.COMPLETED):
                credit_transaction = credit_transaction.transition(status, at=at)
            credit_execution = PaymentExecution(account=credited_account, transaction=credit_transaction)
            self._accounts[source.account_id] = source_execution.account
            self._accounts[destination.account_id] = credited_account
            self._executions[key] = source_execution
            self._executions[(destination.owner_id, credit_transaction.idempotency_key)] = credit_execution
            return source_execution, credit_transaction.transaction_id

    def get_by_id(
        self,
        transaction_id: str,
        *,
        owner_id: str,
    ) -> PaymentExecution | None:
        with self._lock:
            return next(
                (
                    execution
                    for execution in self._executions.values()
                    if execution.transaction.transaction_id == transaction_id
                    and execution.transaction.owner_id == owner_id
                ),
                None,
            )

    def get_completed_by_idempotency(
        self,
        owner_id: str,
        idempotency_key: str,
    ) -> PaymentExecution | None:
        with self._lock:
            execution = self._executions.get((owner_id, idempotency_key))
            if execution is None or execution.transaction.status is not TransactionStatus.COMPLETED:
                return None
            return execution

    def list_for_owner(
        self,
        owner_id: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: TransactionStatus | None = None,
        merchant_id: str | None = None,
    ) -> PaymentPage:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        with self._lock:
            executions = [
                execution
                for execution in self._executions.values()
                if execution.transaction.owner_id == owner_id
                and (status is None or execution.transaction.status is status)
                and (
                    merchant_id is None
                    or execution.transaction.merchant_id == merchant_id
                )
            ]
            executions.sort(
                key=lambda item: (
                    item.transaction.created_at,
                    item.transaction.transaction_id,
                ),
                reverse=True,
            )
            if cursor is not None:
                cursor_index = next(
                    (
                        index
                        for index, execution in enumerate(executions)
                        if execution.transaction.transaction_id == cursor
                    ),
                    None,
                )
                if cursor_index is None:
                    raise PaymentCursorError()
                executions = executions[cursor_index + 1 :]
            page = executions[: limit + 1]
            has_more = len(page) > limit
            items = tuple(page[:limit])
            return PaymentPage(
                items=items,
                next_cursor=(
                    items[-1].transaction.transaction_id
                    if has_more and items
                    else None
                ),
            )

    def list_for_owner_before(
        self,
        owner_id: str,
        *,
        before: datetime,
        before_transaction_id: str,
        limit: int = 1000,
    ) -> PaymentHistoryWindow:
        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")
        with self._lock:
            executions = [
                execution
                for execution in self._executions.values()
                if execution.transaction.owner_id == owner_id
                and execution.transaction.status is TransactionStatus.COMPLETED
                and (
                    execution.transaction.created_at < before
                    or (
                        execution.transaction.created_at == before
                        and execution.transaction.transaction_id < before_transaction_id
                    )
                )
            ]
            executions.sort(
                key=lambda item: (
                    item.transaction.created_at,
                    item.transaction.transaction_id,
                )
            )
            return PaymentHistoryWindow(
                items=tuple(executions[:limit]),
                truncated=len(executions) > limit,
            )


__all__ = [
    "InMemoryAccountRepository",
    "InMemoryAuditRepository",
    "InMemoryCategoryRepository",
    "InMemoryMerchantRepository",
    "InMemoryPaymentRepository",
    "InMemoryUserRepository",
]
