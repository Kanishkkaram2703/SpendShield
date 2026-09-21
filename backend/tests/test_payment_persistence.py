"""Live persistence tests for the closed payment foundation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import Settings
from app.core.exceptions import DatabaseUnavailableError
from app.db.events import CassandraEventRepository
from app.db.manager import DatabaseManager
from app.domain.financial import (
    Account,
    AccountStatus,
    IdempotencyConflictError,
    PaymentCommand,
    PaymentConcurrencyError,
    InsufficientFundsError,
    TransactionChannel,
)
from app.events.publishers import CassandraEventPublisher
from app.repositories.accounts import MongoAccountRepository
from app.repositories.audit import MongoAuditRepository
from app.repositories.payments import MongoPaymentRepository
from app.services.event_delivery_service import EventDeliveryService


def _settings(*, cassandra: bool = False) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        mongodb_uri="mongodb://127.0.0.1:27017",
        mongodb_database=f"spendshield_payment_test_{uuid4().hex}",
        cassandra_hosts="127.0.0.1" if cassandra else "",
        cassandra_keyspace="ss_test",
        mongodb_server_selection_timeout_ms=2000,
        mongodb_connect_timeout_ms=2000,
        cassandra_connect_timeout_seconds=5,
    )


def _require(settings: Settings, *, cassandra: bool = False) -> None:
    manager = DatabaseManager(settings)
    try:
        manager.connect_mongodb()
        if cassandra:
            manager.connect_cassandra()
    except DatabaseUnavailableError as exc:
        pytest.skip(f"integration dependency unavailable: {exc}")
    finally:
        manager.close()


def _cleanup(settings: Settings) -> None:
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
    try:
        try:
            client.drop_database(settings.mongodb_database)
        except PyMongoError:
            pass
    finally:
        client.close()


def _account(*, account_id: str, owner_id: str, balance: str = "1000.00") -> Account:
    now = datetime.now(timezone.utc)
    return Account(
        account_id=account_id,
        owner_id=owner_id,
        currency="INR",
        balance=Decimal(balance),
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def _command(
    *,
    account_id: str,
    owner_id: str,
    amount: str,
    key: str,
    correlation_id: str | None = None,
) -> PaymentCommand:
    return PaymentCommand(
        account_id=account_id,
        owner_id=owner_id,
        amount=Decimal(amount),
        currency="INR",
        idempotency_key=key,
        transaction_channel=TransactionChannel.QR_SIMULATED,
        merchant_id="merchant-1",
        correlation_id=correlation_id,
        causation_id="request-parent",
    )


def test_mongo_payment_is_idempotent_and_enqueues_one_historical_event() -> None:
    settings = _settings(cassandra=True)
    _require(settings, cassandra=True)
    manager = DatabaseManager(settings)
    owner_id = str(uuid4())
    account_id = str(uuid4())
    command = _command(
        account_id=account_id,
        owner_id=owner_id,
        amount="800.00",
        key="payment-once",
        correlation_id="request-correlation-1",
    )

    try:
        manager.initialize_schema()
        MongoAccountRepository(manager).create(
            _account(account_id=account_id, owner_id=owner_id)
        )
        audit = MongoAuditRepository(manager)
        repository = MongoPaymentRepository(manager, audit_repository=audit)

        first = repository.execute(
            command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
        )
        replay = repository.execute(
            command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
        )

        assert first.transaction.transaction_id == replay.transaction.transaction_id
        assert first.account.balance == Decimal("200.00")
        assert replay.account.balance == Decimal("200.00")
        assert repository.supports_multi_document_transactions is False
        assert repository.atomicity_mode == "standalone_optimistic_compare_and_set"

        with pytest.raises(IdempotencyConflictError):
            repository.execute(
                _command(
                    account_id=account_id,
                    owner_id=owner_id,
                    amount="700.00",
                    key="payment-once",
                ),
                transaction_id=str(uuid4()),
                at=datetime.now(timezone.utc),
            )

        # The audit ID is the event ID, not the transaction ID.
        record = manager.mongo_database["audit_records"].find_one(
            {"event_type": "TRANSACTION_COMPLETED", "subject_id": account_id}
        )
        assert record is None
        record = manager.mongo_database["audit_records"].find_one(
            {"event_type": "TRANSACTION_COMPLETED", "subject_id": first.transaction.transaction_id}
        )
        assert record is not None
        assert record["publication_table"] == "transaction_events_by_account_day"
        assert record["publication_partition_value"] == account_id
        assert "idempotency_key" not in record["payload"]

        delivery = EventDeliveryService(
            audit,
            CassandraEventPublisher(CassandraEventRepository(manager)),
        )
        delivery_result = delivery.publish_pending(
            now=first.transaction.updated_at + timedelta(minutes=1)
        )
        assert delivery_result.attempted == 1
        assert delivery_result.published == 1

        historical = CassandraEventRepository(manager).list_by_partition(
            "transaction_events_by_account_day",
            account_id,
            first.transaction.updated_at.date(),
        )
        matching = [
            item
            for item in historical
            if item.payload.get("subject_id") == first.transaction.transaction_id
        ]
        assert len(matching) == 1
        assert matching[0].payload["correlation_id"] == "request-correlation-1"
        assert matching[0].payload["causation_id"] == "request-parent"
    finally:
        manager.close()
        _cleanup(settings)


def test_mongo_payment_recovery_after_event_enqueue_failure_does_not_debit_twice() -> None:
    settings = _settings()
    _require(settings)
    manager = DatabaseManager(settings)
    owner_id = str(uuid4())
    account_id = str(uuid4())
    command = _command(
        account_id=account_id,
        owner_id=owner_id,
        amount="800.00",
        key="payment-retry",
    )

    class FailOnceAudit:
        def __init__(self) -> None:
            self.failed = False
            self.delegate = MongoAuditRepository(manager)

        def append(self, event, *, publication_target=None):
            if not self.failed:
                self.failed = True
                raise DatabaseUnavailableError()
            return self.delegate.append(
                event, publication_target=publication_target
            )

    try:
        MongoAccountRepository(manager).create(
            _account(account_id=account_id, owner_id=owner_id)
        )
        repository = MongoPaymentRepository(manager, audit_repository=FailOnceAudit())
        with pytest.raises(DatabaseUnavailableError):
            repository.execute(
                command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
            )

        recovered = repository.execute(
            command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
        )
        assert recovered.account.balance == Decimal("200.00")
        assert manager.mongo_database["transactions"].count_documents({}) == 1
        assert manager.mongo_database["audit_records"].count_documents({}) == 1
    finally:
        manager.close()
        _cleanup(settings)


def test_mongo_payment_compare_and_set_prevents_concurrent_overspend() -> None:
    settings = _settings()
    _require(settings)
    manager = DatabaseManager(settings)
    owner_id = str(uuid4())
    account_id = str(uuid4())

    try:
        MongoAccountRepository(manager).create(
            _account(account_id=account_id, owner_id=owner_id)
        )
        first = MongoPaymentRepository(manager)
        second = MongoPaymentRepository(manager)
        commands = (
            _command(
                account_id=account_id,
                owner_id=owner_id,
                amount="800.00",
                key="concurrent-800",
            ),
            _command(
                account_id=account_id,
                owner_id=owner_id,
                amount="700.00",
                key="concurrent-700",
            ),
        )

        def run(repository: MongoPaymentRepository, command: PaymentCommand):
            return repository.execute(
                command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run, first, commands[0]), executor.submit(run, second, commands[1])]
            results = []
            errors = []
            for future in futures:
                try:
                    results.append(future.result())
                except (InsufficientFundsError, PaymentConcurrencyError) as exc:
                    errors.append(exc)

        assert len(results) == 1
        assert len(errors) == 1
        persisted = MongoAccountRepository(manager).get_by_id(account_id)
        assert persisted is not None
        assert persisted.balance in {Decimal("200.00"), Decimal("300.00")}
        assert persisted.balance >= Decimal("0.00")
    finally:
        manager.close()
        _cleanup(settings)
