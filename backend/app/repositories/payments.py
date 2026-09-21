"""Payment persistence boundary for current state and durable event enqueueing.

MongoDB is the source of current account/transaction state.  A replica-set
deployment uses one MongoDB transaction for the account, transaction, and
publication metadata.  The standalone fallback retains the idempotency
reservation plus optimistic account compare-and-set so existing development
data remains usable without claiming multi-document atomicity.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from threading import RLock
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from bson.decimal128 import Decimal128
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError

from app.core.exceptions import (
    DatabaseUnavailableError,
    DemoTransferRequiresReplicaSetError,
)
from app.db.manager import DatabaseManager
from app.domain.financial import (
    Account,
    AccountNotActiveError,
    AccountStatus,
    FinancialDomainError,
    IdempotencyConflictError,
    InsufficientFundsError,
    PaymentCommand,
    PaymentConcurrencyError,
    PaymentExecution,
    PaymentInProgressError,
    Transaction,
    TransactionChannel,
    TransactionDirection,
    TransactionStatus,
    TransactionType,
    authorize_payment,
    validate_idempotency_reuse,
)
from app.events.models import DomainEvent
from app.events.publication import EventPublicationTarget
from app.repositories.accounts import MongoAccountRepository
from app.repositories.audit import AuditRepository, MongoAuditRepository


class PaymentCursorError(ValueError):
    """Raised when a history cursor is absent or not owned by the requester."""


@dataclass(frozen=True, slots=True)
class PaymentPage:
    """One bounded, stable payment-history page."""

    items: tuple[PaymentExecution, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class PaymentHistoryWindow:
    """A bounded prior-only window for read-only behavioral feature building."""

    items: tuple[PaymentExecution, ...]
    truncated: bool


@runtime_checkable
class PaymentRepository(Protocol):
    """Repository contract that must make payment effects idempotent and atomic."""

    def execute(
        self,
        command: PaymentCommand,
        *,
        transaction_id: str,
        at: datetime,
    ) -> PaymentExecution:
        """Execute or replay one logical payment operation."""

    def get_by_id(self, transaction_id: str, *, owner_id: str) -> PaymentExecution | None:
        """Return one transaction only within the owner's current state."""

    def get_completed_by_idempotency(
        self,
        owner_id: str,
        idempotency_key: str,
    ) -> PaymentExecution | None:
        """Return an already-completed operation for replay handling."""

    def list_for_owner(
        self,
        owner_id: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: TransactionStatus | None = None,
        merchant_id: str | None = None,
    ) -> PaymentPage:
        """Return one bounded, stable page of owner-scoped transactions."""

    def list_for_owner_before(
        self,
        owner_id: str,
        *,
        before: datetime,
        before_transaction_id: str,
        limit: int = 1000,
    ) -> PaymentHistoryWindow:
        """Return only completed transactions strictly before a target row."""


@runtime_checkable
class TransferPaymentRepository(Protocol):
    """Optional repository capability for atomic two-account demo transfers."""

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
        """Debit one account, credit another, and return the debit plus credit ID."""


class MongoPaymentRepository:
    """Persist fictional payments with replica-set and standalone boundaries.

    Replica-set deployments commit the account, transaction, and MongoDB audit
    publication record together.  Standalone deployments insert a reservation
    before the account CAS; if the process stops after the account update, a
    retry sees the expected post-debit version and finalizes the same
    transaction.
    """

    TRANSACTION_EVENT_TABLE = "transaction_events_by_account_day"

    def __init__(
        self,
        database_manager: DatabaseManager,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self._database_manager = database_manager
        self._audit_repository = audit_repository or MongoAuditRepository(
            database_manager
        )
        self._schema_ready = False
        self._lock = RLock()

    @property
    def supports_multi_document_transactions(self) -> bool:
        """Report whether MongoDB advertises replica-set transaction support."""

        try:
            hello = self._database_manager.mongo_database.client.admin.command(
                "hello"
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return bool(hello.get("setName") or hello.get("isreplicaset"))

    @property
    def atomicity_mode(self) -> str:
        """Describe the actual deployment capability without overstating it."""

        if self.supports_multi_document_transactions:
            return "replica_set_mongo_transaction"
        return "standalone_optimistic_compare_and_set"

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _mongo_datetime(cls, value: datetime) -> datetime:
        normalized = cls._utc(value)
        return normalized.replace(microsecond=(normalized.microsecond // 1000) * 1000)

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal128):
            return value.to_decimal()
        return Decimal(str(value))

    def _transaction_collection(self) -> Any:
        if not self._schema_ready:
            self._database_manager.ensure_mongodb_schema()
            self._schema_ready = True
        return self._database_manager.mongo_database["transactions"]

    def _account_collection(self) -> Any:
        return self._transaction_collection().database["accounts"]

    def _find_account_document(
        self,
        *,
        account_id: str,
        owner_id: str,
        session: Any | None = None,
    ) -> dict[str, Any] | None:
        try:
            find_options = {"session": session} if session is not None else {}
            return self._account_collection().find_one(
                {"account_id": account_id, "user_id": owner_id},
                **find_options,
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def _find_any_account_document(
        self,
        account_id: str,
        *,
        session: Any | None = None,
    ) -> dict[str, Any] | None:
        """Read one destination account without weakening source authorization."""

        try:
            find_options = {"session": session} if session is not None else {}
            return self._account_collection().find_one(
                {"account_id": account_id},
                **find_options,
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    @staticmethod
    def _account_from_document(document: dict[str, Any]) -> Account:
        return MongoAccountRepository._to_record(document)

    def _find_existing(
        self,
        command: PaymentCommand,
        *,
        session: Any | None = None,
    ) -> dict[str, Any] | None:
        try:
            find_options = {"session": session} if session is not None else {}
            return self._transaction_collection().find_one(
                {
                    "user_id": command.owner_id,
                    "idempotency_key": command.idempotency_key,
                },
                **find_options,
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    @staticmethod
    def _history_values(transaction: Transaction) -> list[str]:
        return [status.value for status in transaction.status_history]

    def _transaction_document(
        self,
        execution: PaymentExecution,
        *,
        event_id: UUID,
        account_version_before: int,
        operation_state: str,
        failure_code: str | None = None,
    ) -> dict[str, Any]:
        transaction = execution.transaction
        is_reservation = operation_state == "RESERVED"
        return {
            "transaction_id": transaction.transaction_id,
            "user_id": transaction.owner_id,
            "account_id": transaction.account_id,
            "timestamp": self._mongo_datetime(transaction.created_at),
            "created_at": self._mongo_datetime(transaction.created_at),
            "updated_at": self._mongo_datetime(transaction.updated_at),
            "currency": transaction.currency,
            "amount": Decimal128(transaction.amount),
            "status": (
                TransactionStatus.INITIATED.value
                if is_reservation
                else transaction.status.value
            ),
            "idempotency_key": transaction.idempotency_key,
            "request_fingerprint": transaction.request_fingerprint,
            "transaction_channel": (
                transaction.transaction_channel.value
                if transaction.transaction_channel is not None
                else None
            ),
            "note": transaction.note,
            "transaction_type": transaction.transaction_type.value,
            "direction": transaction.direction.value,
            "counterparty_account_id": transaction.counterparty_account_id,
            "counterparty_name": transaction.counterparty_name,
            "beneficiary_name": transaction.beneficiary_name,
            "demo_bank_account_number": transaction.demo_bank_account_number,
            "demo_bank_code": transaction.demo_bank_code,
            "transfer_reference": transaction.transfer_reference,
            "demo_mode": transaction.demo_mode,
            "balance_before": Decimal128(transaction.balance_before),
            "balance_after": (
                Decimal128(transaction.balance_after)
                if transaction.balance_after is not None
                else None
            ),
            "merchant_id": transaction.merchant_id,
            "merchant_name": transaction.merchant_name,
            # These are immutable historical classification snapshots.  The
            # merchant/category collections remain the current-state source;
            # this copy prevents later reclassification from rewriting old
            # transaction meaning.
            "category_id": transaction.category_id,
            "category_name": transaction.category_name,
            "subcategory_id": transaction.subcategory_id,
            "subcategory_name": transaction.subcategory_name,
            "failure_reason": transaction.failure_reason,
            "failure_code": failure_code,
            "status_history": (
                [TransactionStatus.INITIATED.value]
                if is_reservation
                else self._history_values(transaction)
            ),
            "planned_status_history": self._history_values(transaction),
            "actor_id": transaction.actor_id,
            "correlation_id": transaction.correlation_id,
            "causation_id": transaction.causation_id,
            "event_id": str(event_id),
            "account_version_before": account_version_before,
            "account_version_after": execution.account.version,
            "operation_state": operation_state,
        }

    def _insert_transaction(
        self,
        document: dict[str, Any],
        *,
        session: Any | None = None,
    ) -> dict[str, Any]:
        try:
            insert_options = {"session": session} if session is not None else {}
            self._transaction_collection().insert_one(document, **insert_options)
            return document
        except DuplicateKeyError:
            if session is not None:
                raise
            try:
                existing = self._transaction_collection().find_one(
                    {
                        "user_id": document["user_id"],
                        "idempotency_key": document["idempotency_key"],
                    }
                )
            except PyMongoError as exc:
                raise DatabaseUnavailableError() from exc
            if existing is not None:
                return existing
            raise DatabaseUnavailableError()
        except OperationFailure as exc:
            if session is not None and (
                exc.code == 112 or exc.has_error_label("TransientTransactionError")
            ):
                raise
            raise DatabaseUnavailableError() from exc
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def _execution_from_document(self, document: dict[str, Any]) -> PaymentExecution:
        account_document = self._find_account_document(
            account_id=str(document["account_id"]),
            owner_id=str(document["user_id"]),
        )
        if account_document is None:
            raise PaymentInProgressError("Payment account state is unavailable.")
        history = tuple(TransactionStatus(value) for value in document["status_history"])
        transaction = Transaction(
            transaction_id=str(document["transaction_id"]),
            account_id=str(document["account_id"]),
            owner_id=str(document["user_id"]),
            currency=str(document["currency"]),
            amount=self._decimal(document["amount"]),
            status=TransactionStatus(str(document["status"])),
            idempotency_key=str(document["idempotency_key"]),
            request_fingerprint=str(document["request_fingerprint"]),
            transaction_channel=(
                TransactionChannel(str(document["transaction_channel"]))
                if document.get("transaction_channel")
                else None
            ),
            note=document.get("note"),
            transaction_type=TransactionType(
                str(document.get("transaction_type", TransactionType.MERCHANT_PAYMENT.value))
            ),
            direction=TransactionDirection(
                str(document.get("direction", TransactionDirection.DEBIT.value))
            ),
            created_at=self._utc(document["created_at"]),
            updated_at=self._utc(document["updated_at"]),
            balance_before=self._decimal(document["balance_before"]),
            balance_after=(
                self._decimal(document["balance_after"])
                if document.get("balance_after") is not None
                else None
            ),
            merchant_id=document.get("merchant_id"),
            merchant_name=document.get("merchant_name"),
            category_id=document.get("category_id"),
            category_name=document.get("category_name"),
            subcategory_id=document.get("subcategory_id"),
            subcategory_name=document.get("subcategory_name"),
            failure_reason=document.get("failure_reason"),
            status_history=history,
            actor_id=document.get("actor_id"),
            correlation_id=document.get("correlation_id"),
            causation_id=document.get("causation_id"),
            counterparty_account_id=document.get("counterparty_account_id"),
            counterparty_name=document.get("counterparty_name"),
            beneficiary_name=document.get("beneficiary_name"),
            demo_bank_account_number=document.get("demo_bank_account_number"),
            demo_bank_code=document.get("demo_bank_code"),
            transfer_reference=document.get("transfer_reference"),
            demo_mode=bool(document.get("demo_mode", True)),
        )
        return PaymentExecution(
            account=self._account_from_document(account_document),
            transaction=transaction,
        )

    def get_by_id(
        self,
        transaction_id: str,
        *,
        owner_id: str,
    ) -> PaymentExecution | None:
        """Read authoritative current transaction state for one owner."""

        try:
            document = self._transaction_collection().find_one(
                {"transaction_id": transaction_id, "user_id": owner_id}
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return self._execution_from_document(document) if document else None

    def get_completed_by_idempotency(
        self,
        owner_id: str,
        idempotency_key: str,
    ) -> PaymentExecution | None:
        """Read only terminal successful state for idempotent replay."""

        try:
            document = self._transaction_collection().find_one(
                {
                    "user_id": owner_id,
                    "idempotency_key": idempotency_key,
                    "status": TransactionStatus.COMPLETED.value,
                }
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return self._execution_from_document(document) if document else None

    def list_for_owner(
        self,
        owner_id: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: TransactionStatus | None = None,
        merchant_id: str | None = None,
    ) -> PaymentPage:
        """List current MongoDB transactions with bounded stable pagination."""

        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        query: dict[str, Any] = {"user_id": owner_id}
        if status is not None:
            query["status"] = status.value
        if merchant_id is not None:
            query["merchant_id"] = merchant_id

        try:
            if cursor is not None:
                cursor_document = self._transaction_collection().find_one(
                    {"transaction_id": cursor, "user_id": owner_id},
                    {"timestamp": 1, "transaction_id": 1},
                )
                if cursor_document is None:
                    raise PaymentCursorError()
                cursor_timestamp = cursor_document["timestamp"]
                query["$or"] = [
                    {"timestamp": {"$lt": cursor_timestamp}},
                    {
                        "timestamp": cursor_timestamp,
                        "transaction_id": {"$lt": cursor},
                    },
                ]
            documents = list(
                self._transaction_collection()
                .find(query)
                .sort([("timestamp", DESCENDING), ("transaction_id", DESCENDING)])
                .limit(limit + 1)
            )
        except PaymentCursorError:
            raise
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

        has_more = len(documents) > limit
        page_documents = documents[:limit]
        return PaymentPage(
            items=tuple(self._execution_from_document(document) for document in page_documents),
            next_cursor=(
                str(page_documents[-1]["transaction_id"])
                if has_more and page_documents
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
        """Read a bounded prior-only completed history window."""

        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")
        before_utc = self._utc(before)
        query: dict[str, Any] = {
            "user_id": owner_id,
            "status": TransactionStatus.COMPLETED.value,
            "$or": [
                {"timestamp": {"$lt": before_utc}},
                {
                    "timestamp": before_utc,
                    "transaction_id": {"$lt": before_transaction_id},
                },
            ],
        }
        try:
            documents = list(
                self._transaction_collection()
                .find(query)
                .sort([("timestamp", ASCENDING), ("transaction_id", ASCENDING)])
                .limit(limit + 1)
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return PaymentHistoryWindow(
            items=tuple(
                self._execution_from_document(document) for document in documents[:limit]
            ),
            truncated=len(documents) > limit,
        )

    def _event_for_transaction(self, document: dict[str, Any]) -> DomainEvent:
        correlation_id = str(document.get("correlation_id") or document["transaction_id"])
        status = str(document["status"])
        return DomainEvent(
            event_id=UUID(str(document["event_id"])),
            event_type=f"TRANSACTION_{status}",
            subject_id=str(document["transaction_id"]),
            actor_id=str(document.get("actor_id") or document["user_id"]),
            occurred_at=self._utc(document["updated_at"]),
            source="payment-repository",
            correlation_id=correlation_id,
            causation_id=document.get("causation_id"),
            schema_version=1,
            payload={
                "transaction_id": str(document["transaction_id"]),
                "account_id": str(document["account_id"]),
                "amount": str(self._decimal(document["amount"])),
                "currency": str(document["currency"]),
                "transaction_channel": document.get("transaction_channel"),
                "transaction_type": document.get(
                    "transaction_type", TransactionType.MERCHANT_PAYMENT.value
                ),
                "direction": document.get("direction", TransactionDirection.DEBIT.value),
                "note": document.get("note"),
                "merchant_id": document.get("merchant_id"),
                "merchant_name": document.get("merchant_name"),
                "category_id": document.get("category_id"),
                "category_name": document.get("category_name"),
                "subcategory_id": document.get("subcategory_id"),
                "subcategory_name": document.get("subcategory_name"),
                "status": status,
                "status_history": list(document["status_history"]),
                "balance_before": str(self._decimal(document["balance_before"])),
                "balance_after": (
                    str(self._decimal(document["balance_after"]))
                    if document.get("balance_after") is not None
                    else None
                ),
                "outcome": "succeeded" if status == "COMPLETED" else "rejected",
                "failure_reason": document.get("failure_reason"),
                "counterparty_account_id": document.get("counterparty_account_id"),
                "counterparty_name": document.get("counterparty_name"),
                "beneficiary_name": document.get("beneficiary_name"),
                "demo_bank_account_number": document.get("demo_bank_account_number"),
                "demo_bank_code": document.get("demo_bank_code"),
                "transfer_reference": document.get("transfer_reference"),
                "demo_mode": bool(document.get("demo_mode", True)),
            },
            provenance={
                "channel": "application",
                "operation": "fictional_payment",
                "account_id": str(document["account_id"]),
            },
            created_at=self._utc(document["created_at"]),
        )

    def _credit_transaction(
        self,
        *,
        destination: Account,
        command: PaymentCommand,
        transaction_id: str,
        idempotency_key: str,
        at: datetime,
        transfer_reference: str,
        transaction_type: TransactionType,
        counterparty_name: str | None,
    ) -> PaymentExecution:
        """Build the receiver-side history record for an atomic demo transfer."""

        transaction = Transaction(
            transaction_id=transaction_id,
            account_id=destination.account_id,
            owner_id=destination.owner_id,
            currency=destination.currency,
            amount=command.amount,
            status=TransactionStatus.INITIATED,
            idempotency_key=idempotency_key,
            request_fingerprint=command.fingerprint,
            transaction_channel=command.transaction_channel,
            note=command.note,
            transaction_type=transaction_type,
            direction=TransactionDirection.CREDIT,
            counterparty_account_id=command.account_id,
            counterparty_name=counterparty_name,
            actor_id=command.owner_id,
            correlation_id=command.correlation_id,
            causation_id=command.causation_id,
            transfer_reference=transfer_reference,
            created_at=at,
            updated_at=at,
            balance_before=destination.balance,
            balance_after=destination.balance + command.amount,
            demo_mode=True,
        )
        for status in (
            TransactionStatus.AUTHORIZED,
            TransactionStatus.PROCESSING,
            TransactionStatus.COMPLETED,
        ):
            transaction = transaction.transition(status, at=at)
        return PaymentExecution(
            account=destination.credit(command.amount, at=at),
            transaction=transaction,
        )

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
        """Atomically debit/credit two current accounts on MongoDB rs0.

        The source transaction remains the returned API result.  The credit
        transaction is separately persisted for the destination owner's
        history and is linked by ``transfer_reference``.
        """

        if not self.supports_multi_document_transactions:
            raise DemoTransferRequiresReplicaSetError()

        timestamp = self._utc(at)
        with self._lock:
            existing = self._find_existing(command)
            if existing is not None:
                validate_idempotency_reuse(
                    str(existing["request_fingerprint"]), command.fingerprint
                )
                credit = self._transaction_collection().find_one(
                    {
                        "transfer_reference": existing.get("transfer_reference"),
                        "direction": TransactionDirection.CREDIT.value,
                    }
                )
                return self._execution_from_document(existing), str(
                    credit["transaction_id"] if credit else ""
                )

            self._transaction_collection()
            if isinstance(self._audit_repository, MongoAuditRepository):
                self._audit_repository._collection()
            client = self._database_manager.mongo_database.client
            source_document: dict[str, Any] | None = None
            credit_document: dict[str, Any] | None = None
            operation_command = replace(command, transfer_reference=transaction_id)

            try:
                with client.start_session() as session:
                    with session.start_transaction():
                        source_document_raw = self._find_account_document(
                            account_id=command.account_id,
                            owner_id=command.owner_id,
                            session=session,
                        )
                        if source_document_raw is None:
                            raise FinancialDomainError("Source account was not found.")
                        destination_document = self._find_any_account_document(
                            destination_account_id,
                            session=session,
                        )
                        if destination_document is None:
                            raise FinancialDomainError("Destination account was not found.")
                        if destination_owner_id is not None and str(
                            destination_document["user_id"]
                        ) != destination_owner_id:
                            raise FinancialDomainError(
                                "Destination account is not owned by the current user."
                            )
                        if destination_account_id == command.account_id:
                            raise FinancialDomainError(
                                "Source and destination accounts must be different."
                            )

                        source = self._account_from_document(source_document_raw)
                        destination = self._account_from_document(destination_document)
                        if source.currency != command.currency or destination.currency != command.currency:
                            raise FinancialDomainError(
                                "Transfer currency must match both demo accounts."
                            )
                        source_execution = authorize_payment(
                            source,
                            operation_command,
                            transaction_id=transaction_id,
                            at=timestamp,
                        )
                        credit_type = (
                            TransactionType.SELF_TRANSFER_CREDIT
                            if command.transaction_type is TransactionType.SELF_TRANSFER_DEBIT
                            else TransactionType.SEND_MONEY_CREDIT
                        )
                        credit_execution = self._credit_transaction(
                            destination=destination,
                            command=operation_command,
                            transaction_id=str(uuid4()),
                            idempotency_key=f"credit-{transaction_id}",
                            at=timestamp,
                            transfer_reference=transaction_id,
                            transaction_type=credit_type,
                            counterparty_name=source_execution.transaction.counterparty_name,
                        )
                        source_document = self._transaction_document(
                            source_execution,
                            event_id=uuid4(),
                            account_version_before=source.version,
                            operation_state="COMPLETED",
                        )
                        credit_document = self._transaction_document(
                            credit_execution,
                            event_id=uuid4(),
                            account_version_before=destination.version,
                            operation_state="COMPLETED",
                        )
                        self._insert_transaction(source_document, session=session)
                        self._insert_transaction(credit_document, session=session)
                        source_update = self._account_collection().update_one(
                            {
                                "account_id": source.account_id,
                                "user_id": source.owner_id,
                                "version": source.version,
                                "balance": Decimal128(source.balance),
                            },
                            {
                                "$set": {
                                    "balance": Decimal128(source_execution.account.balance),
                                    "updated_at": self._mongo_datetime(timestamp),
                                    "version": source_execution.account.version,
                                }
                            },
                            session=session,
                        )
                        destination_update = self._account_collection().update_one(
                            {
                                "account_id": destination.account_id,
                                "user_id": destination.owner_id,
                                "version": destination.version,
                                "balance": Decimal128(destination.balance),
                            },
                            {
                                "$set": {
                                    "balance": Decimal128(credit_execution.account.balance),
                                    "updated_at": self._mongo_datetime(timestamp),
                                    "version": credit_execution.account.version,
                                }
                            },
                            session=session,
                        )
                        if source_update.matched_count != 1 or destination_update.matched_count != 1:
                            raise PaymentConcurrencyError(
                                "An account changed while the demo transfer was running."
                            )
                        self._ensure_event(source_document, session=session)
                        self._ensure_event(credit_document, session=session)
            except DuplicateKeyError:
                winner = self._find_existing(command)
                if winner is not None:
                    validate_idempotency_reuse(
                        str(winner["request_fingerprint"]), command.fingerprint
                    )
                    credit = self._transaction_collection().find_one(
                        {"transfer_reference": winner.get("transfer_reference"), "direction": TransactionDirection.CREDIT.value}
                    )
                    return self._execution_from_document(winner), str(
                        credit["transaction_id"] if credit else ""
                    )
                raise DatabaseUnavailableError()
            except OperationFailure as exc:
                if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
                    raise PaymentConcurrencyError(
                        "The demo transfer lost a concurrent write race."
                    ) from exc
                raise DatabaseUnavailableError() from exc
            except PyMongoError as exc:
                raise DatabaseUnavailableError() from exc

            if source_document is None or credit_document is None:
                raise PaymentInProgressError("The demo transfer did not commit.")
            return self._execution_from_document(source_document), str(
                credit_document["transaction_id"]
            )

    def _ensure_event(
        self,
        document: dict[str, Any],
        *,
        session: Any | None = None,
    ) -> None:
        append_options = {"session": session} if session is not None else {}
        self._audit_repository.append(
            self._event_for_transaction(document),
            publication_target=EventPublicationTarget(
                table=self.TRANSACTION_EVENT_TABLE,
                partition_value=str(document["account_id"]),
            ),
            **append_options,
        )

    def _finalize_transaction(self, document: dict[str, Any]) -> PaymentExecution:
        now = self._utc(document["updated_at"])
        try:
            result = self._transaction_collection().update_one(
                {
                    "transaction_id": document["transaction_id"],
                    "status": {
                        "$in": [
                            TransactionStatus.INITIATED.value,
                            TransactionStatus.AUTHORIZED.value,
                            TransactionStatus.PROCESSING.value,
                        ]
                    },
                },
                {
                    "$set": {
                        "status": TransactionStatus.COMPLETED.value,
                        "status_history": [
                            TransactionStatus.INITIATED.value,
                            TransactionStatus.AUTHORIZED.value,
                            TransactionStatus.PROCESSING.value,
                            TransactionStatus.COMPLETED.value,
                        ],
                        "updated_at": self._mongo_datetime(now),
                        "operation_state": "COMPLETED",
                    }
                },
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        if result.matched_count != 1:
            current = self._transaction_collection().find_one(
                {"transaction_id": document["transaction_id"]}
            )
            if current is None or current["status"] != TransactionStatus.COMPLETED.value:
                raise PaymentInProgressError(
                    "Payment state needs recovery before it can be replayed."
                )
            document = current
        else:
            document = self._transaction_collection().find_one(
                {"transaction_id": document["transaction_id"]}
            ) or document
        self._ensure_event(document)
        return self._execution_from_document(document)

    def _mark_rejected(
        self,
        document: dict[str, Any],
        *,
        failure_code: str,
        reason: str,
    ) -> dict[str, Any]:
        now = self._mongo_datetime(datetime.now(timezone.utc))
        try:
            self._transaction_collection().update_one(
                {
                    "transaction_id": document["transaction_id"],
                    "status": {
                        "$in": [
                            TransactionStatus.INITIATED.value,
                            TransactionStatus.AUTHORIZED.value,
                            TransactionStatus.PROCESSING.value,
                        ]
                    },
                },
                {
                    "$set": {
                        "status": TransactionStatus.REJECTED.value,
                        "status_history": [
                            TransactionStatus.INITIATED.value,
                            TransactionStatus.REJECTED.value,
                        ],
                        "failure_code": failure_code,
                        "failure_reason": reason,
                        "updated_at": now,
                        "operation_state": "REJECTED",
                    }
                },
            )
            current = self._transaction_collection().find_one(
                {"transaction_id": document["transaction_id"]}
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        if current is None:
            raise PaymentInProgressError("Payment rejection state is unavailable.")
        self._ensure_event(current)
        return current

    @staticmethod
    def _raise_rejection(document: dict[str, Any]) -> None:
        code = document.get("failure_code")
        reason = str(document.get("failure_reason") or "Payment was rejected.")
        if code == "account_not_active":
            raise AccountNotActiveError(reason)
        if code == "insufficient_funds":
            raise InsufficientFundsError(reason)
        if code == "concurrency_conflict":
            raise PaymentConcurrencyError(reason)
        raise FinancialDomainError(reason)

    def _complete_reserved(self, document: dict[str, Any]) -> PaymentExecution:
        account_document = self._find_account_document(
            account_id=str(document["account_id"]),
            owner_id=str(document["user_id"]),
        )
        if account_document is None:
            raise PaymentInProgressError("Payment account state is unavailable.")
        current_version = int(account_document.get("version", 0))
        current_balance = self._decimal(account_document["balance"])
        expected_before = self._decimal(document["balance_before"])
        expected_after = self._decimal(document["balance_after"])
        expected_version_before = int(document["account_version_before"])
        expected_version_after = int(document["account_version_after"])

        if current_version == expected_version_after and current_balance == expected_after:
            return self._finalize_transaction(document)

        if current_version != expected_version_before or current_balance != expected_before:
            rejected = self._mark_rejected(
                document,
                failure_code="concurrency_conflict",
                reason="Account state changed before the payment reservation was applied.",
            )
            self._raise_rejection(rejected)

        try:
            result = self._account_collection().update_one(
                {
                    "account_id": document["account_id"],
                    "user_id": document["user_id"],
                    "currency": document["currency"],
                    "status": AccountStatus.ACTIVE.value,
                    "version": expected_version_before,
                    "balance": Decimal128(expected_before),
                },
                {
                    "$set": {
                        "balance": Decimal128(expected_after),
                        "updated_at": self._mongo_datetime(document["updated_at"]),
                        "version": expected_version_after,
                    }
                },
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

        if result.matched_count != 1:
            # Re-read once to distinguish a successful update observed late from
            # a competing writer.  An ambiguous result is never debited again.
            refreshed = self._find_account_document(
                account_id=str(document["account_id"]),
                owner_id=str(document["user_id"]),
            )
            if refreshed is not None:
                refreshed_version = int(refreshed.get("version", 0))
                refreshed_balance = self._decimal(refreshed["balance"])
                if (
                    refreshed_version == expected_version_after
                    and refreshed_balance == expected_after
                ):
                    return self._finalize_transaction(document)
            rejected = self._mark_rejected(
                document,
                failure_code="concurrency_conflict",
                reason="Account state changed while applying the payment reservation.",
            )
            self._raise_rejection(rejected)

        return self._finalize_transaction(document)

    def _rejected_execution(
        self,
        account: Account,
        command: PaymentCommand,
        *,
        transaction_id: str,
        at: datetime,
        reason: str,
    ) -> PaymentExecution:
        transaction = Transaction(
            transaction_id=transaction_id,
            account_id=account.account_id,
            owner_id=account.owner_id,
            currency=account.currency,
            amount=command.amount,
            status=TransactionStatus.INITIATED,
            idempotency_key=command.idempotency_key,
            request_fingerprint=command.fingerprint,
            transaction_channel=command.transaction_channel,
            created_at=at,
            updated_at=at,
            balance_before=account.balance,
            merchant_id=command.merchant_id,
            merchant_name=command.merchant_name,
            category_id=command.category_id,
            category_name=command.category_name,
            subcategory_id=command.subcategory_id,
            subcategory_name=command.subcategory_name,
            actor_id=command.owner_id,
            correlation_id=command.correlation_id,
            causation_id=command.causation_id,
            transaction_type=command.transaction_type,
            direction=command.direction,
            counterparty_account_id=command.counterparty_account_id,
            counterparty_name=command.counterparty_name,
            beneficiary_name=command.beneficiary_name,
            demo_bank_account_number=command.demo_bank_account_number,
            demo_bank_code=command.demo_bank_code,
            transfer_reference=command.transfer_reference,
            demo_mode=True,
        ).transition(TransactionStatus.REJECTED, at=at, reason=reason)
        return PaymentExecution(account=account, transaction=transaction)

    def _resume_or_replay(
        self,
        document: dict[str, Any],
        command: PaymentCommand,
    ) -> PaymentExecution:
        validate_idempotency_reuse(
            str(document["request_fingerprint"]), command.fingerprint
        )
        status = TransactionStatus(str(document["status"]))
        if status is TransactionStatus.COMPLETED:
            self._ensure_event(document)
            return self._execution_from_document(document)
        if status in {TransactionStatus.REJECTED, TransactionStatus.FAILED}:
            self._ensure_event(document)
            self._raise_rejection(document)
        if status in {
            TransactionStatus.INITIATED,
            TransactionStatus.AUTHORIZED,
            TransactionStatus.PROCESSING,
        }:
            return self._complete_reserved(document)
        raise PaymentInProgressError("Payment state cannot be safely replayed.")

    def _execute_replica_set_transaction(
        self,
        command: PaymentCommand,
        *,
        transaction_id: str,
        at: datetime,
        attempt: int = 0,
    ) -> PaymentExecution:
        """Commit account, transaction, and publication metadata together."""

        existing = self._find_existing(command)
        if existing is not None:
            return self._resume_or_replay(existing, command)

        # Schema/index work must never run inside the MongoDB transaction.
        self._transaction_collection()
        if isinstance(self._audit_repository, MongoAuditRepository):
            self._audit_repository._collection()

        timestamp = self._utc(at)
        client = self._database_manager.mongo_database.client
        committed_document: dict[str, Any] | None = None
        rejected_document: dict[str, Any] | None = None
        rejection: FinancialDomainError | None = None

        try:
            with client.start_session() as session:
                with session.start_transaction():
                    account_document = self._find_account_document(
                        account_id=command.account_id,
                        owner_id=command.owner_id,
                        session=session,
                    )
                    if account_document is None:
                        raise FinancialDomainError("Account was not found.")
                    account = self._account_from_document(account_document)

                    try:
                        execution = authorize_payment(
                            account,
                            command,
                            transaction_id=transaction_id,
                            at=timestamp,
                        )
                    except FinancialDomainError as exc:
                        rejection = exc
                        rejected_execution = self._rejected_execution(
                            account,
                            command,
                            transaction_id=transaction_id,
                            at=timestamp,
                            reason=str(exc),
                        )
                        failure_code = (
                            "account_not_active"
                            if isinstance(exc, AccountNotActiveError)
                            else "insufficient_funds"
                            if isinstance(exc, InsufficientFundsError)
                            else "financial_rule_violation"
                        )
                        rejected_document = self._insert_transaction(
                            self._transaction_document(
                                rejected_execution,
                                event_id=uuid4(),
                                account_version_before=account.version,
                                operation_state="REJECTED",
                                failure_code=failure_code,
                            ),
                            session=session,
                        )
                        self._ensure_event(rejected_document, session=session)
                    else:
                        committed_document = self._transaction_document(
                            execution,
                            event_id=uuid4(),
                            account_version_before=account.version,
                            operation_state="COMPLETED",
                        )
                        self._insert_transaction(
                            committed_document,
                            session=session,
                        )
                        update_result = self._account_collection().update_one(
                            {
                                "account_id": command.account_id,
                                "user_id": command.owner_id,
                                "currency": command.currency,
                                "status": AccountStatus.ACTIVE.value,
                                "version": account.version,
                                "balance": Decimal128(account.balance),
                            },
                            {
                                "$set": {
                                    "balance": Decimal128(execution.account.balance),
                                    "updated_at": self._mongo_datetime(
                                        execution.account.updated_at
                                    ),
                                    "version": execution.account.version,
                                }
                            },
                            session=session,
                        )
                        if update_result.matched_count != 1:
                            raise PaymentConcurrencyError(
                                "Account state changed while the payment transaction was running."
                            )
                        self._ensure_event(committed_document, session=session)
        except DuplicateKeyError:
            # A concurrent request may have committed the same idempotency key
            # first.  The transaction is aborted; replay only the winner.
            existing = self._find_existing(command)
            if existing is not None:
                return self._resume_or_replay(existing, command)
            raise DatabaseUnavailableError()
        except OperationFailure as exc:
            if (
                exc.code == 112 or exc.has_error_label("TransientTransactionError")
            ) and attempt < 3:
                return self._execute_replica_set_transaction(
                    command,
                    transaction_id=transaction_id,
                    at=at,
                    attempt=attempt + 1,
                )
            if exc.code == 112 or exc.has_error_label("TransientTransactionError"):
                raise PaymentConcurrencyError(
                    "The payment transaction lost a concurrent write race."
                ) from exc
            raise DatabaseUnavailableError() from exc
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

        if rejection is not None and rejected_document is not None:
            self._raise_rejection(rejected_document)
        if committed_document is None:
            raise PaymentInProgressError("Payment transaction did not commit.")
        return self._execution_from_document(committed_document)

    def execute(
        self,
        command: PaymentCommand,
        *,
        transaction_id: str,
        at: datetime,
    ) -> PaymentExecution:
        """Execute or replay one payment without duplicating its financial effect."""

        timestamp = self._utc(at)
        with self._lock:
            if self.supports_multi_document_transactions:
                return self._execute_replica_set_transaction(
                    command,
                    transaction_id=transaction_id,
                    at=timestamp,
                )
            existing = self._find_existing(command)
            if existing is not None:
                return self._resume_or_replay(existing, command)

            account_document = self._find_account_document(
                account_id=command.account_id,
                owner_id=command.owner_id,
            )
            if account_document is None:
                raise FinancialDomainError("Account was not found.")
            account = self._account_from_document(account_document)

            try:
                execution = authorize_payment(
                    account,
                    command,
                    transaction_id=transaction_id,
                    at=timestamp,
                )
            except FinancialDomainError as exc:
                if isinstance(exc, IdempotencyConflictError):
                    raise
                failure_code = (
                    "account_not_active"
                    if isinstance(exc, AccountNotActiveError)
                    else "insufficient_funds"
                    if isinstance(exc, InsufficientFundsError)
                    else "financial_rule_violation"
                )
                rejected_execution = self._rejected_execution(
                    account,
                    command,
                    transaction_id=transaction_id,
                    at=timestamp,
                    reason=str(exc),
                )
                rejected_document = self._insert_transaction(
                    self._transaction_document(
                        rejected_execution,
                        event_id=uuid4(),
                        account_version_before=account.version,
                        operation_state="REJECTED",
                        failure_code=failure_code,
                    )
                )
                if rejected_document["status"] != TransactionStatus.REJECTED.value:
                    return self._resume_or_replay(rejected_document, command)
                self._ensure_event(rejected_document)
                raise

            document = self._transaction_document(
                execution,
                event_id=uuid4(),
                account_version_before=account.version,
                operation_state="RESERVED",
            )
            reserved = self._insert_transaction(document)
            return self._resume_or_replay(reserved, command)


__all__ = [
    "MongoPaymentRepository",
    "PaymentHistoryWindow",
    "PaymentCursorError",
    "PaymentPage",
    "PaymentRepository",
]
