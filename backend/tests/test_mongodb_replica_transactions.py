"""Integration tests for the optional local single-node MongoDB replica set."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import DatabaseUnavailableError
from app.db.events import CassandraEventRepository
from app.db.manager import DatabaseManager
from app.domain.financial import (
    Account,
    AccountStatus,
    IdempotencyConflictError,
    InsufficientFundsError,
    PaymentCommand,
    TransactionChannel,
    PaymentConcurrencyError,
)
from app.events.publishers import CassandraEventPublisher
from app.main import create_app
from app.repositories.accounts import MongoAccountRepository
from app.repositories.audit import MongoAuditRepository
from app.repositories.payments import MongoPaymentRepository
from app.services.event_delivery_service import EventDeliveryService


def replica_settings(*, cassandra: bool = False) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        mongodb_uri="mongodb://127.0.0.1:27018",
        mongodb_database=f"spendshield_replica_test_{uuid4().hex}",
        mongodb_replica_set="rs0",
        cassandra_hosts="127.0.0.1" if cassandra else "",
        cassandra_keyspace="ss_test",
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        cassandra_connect_timeout_seconds=5,
    )


def require_replica(settings: Settings, *, cassandra: bool = False) -> None:
    manager = DatabaseManager(settings)
    try:
        manager.connect_mongodb()
        hello = manager.mongo_database.client.admin.command("hello")
        if hello.get("setName") != "rs0" or not hello.get("isWritablePrimary"):
            pytest.skip("MongoDB replica set is not initialized as rs0 primary")
        if cassandra:
            manager.connect_cassandra()
    except DatabaseUnavailableError as exc:
        pytest.skip(f"replica integration service unavailable: {exc}")
    finally:
        manager.close()


def cleanup(settings: Settings) -> None:
    client = MongoClient(
        settings.mongodb_uri,
        replicaSet=settings.mongodb_replica_set,
        serverSelectionTimeoutMS=3000,
    )
    try:
        try:
            client.drop_database(settings.mongodb_database)
        except PyMongoError:
            pass
    finally:
        client.close()


def make_account(account_id: str, owner_id: str, balance: str = "1000.00") -> Account:
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


def make_command(
    account_id: str,
    owner_id: str,
    amount: str,
    key: str,
    *,
    correlation_id: str = "replica-request",
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
        causation_id="replica-parent",
    )


def test_replica_set_commit_and_rollback_are_real() -> None:
    settings = replica_settings()
    require_replica(settings)
    manager = DatabaseManager(settings)
    marker = uuid4().hex

    try:
        manager.ensure_mongodb_schema()
        client = manager.mongo_database.client
        database = manager.mongo_database
        with client.start_session() as session:
            with session.start_transaction():
                database["atomic_commit_a"].insert_one(
                    {"marker": marker}, session=session
                )
                database["atomic_commit_b"].insert_one(
                    {"marker": marker}, session=session
                )

        assert database["atomic_commit_a"].count_documents({"marker": marker}) == 1
        assert database["atomic_commit_b"].count_documents({"marker": marker}) == 1

        rollback_marker = uuid4().hex
        with pytest.raises(RuntimeError):
            with client.start_session() as session:
                with session.start_transaction():
                    database["atomic_rollback_a"].insert_one(
                        {"marker": rollback_marker}, session=session
                    )
                    database["atomic_rollback_b"].insert_one(
                        {"marker": rollback_marker}, session=session
                    )
                    raise RuntimeError("injected transaction failure")

        assert database["atomic_rollback_a"].count_documents(
            {"marker": rollback_marker}
        ) == 0
        assert database["atomic_rollback_b"].count_documents(
            {"marker": rollback_marker}
        ) == 0
    finally:
        manager.close()
        cleanup(settings)


def test_real_application_dependency_health_identifies_rs0_primary() -> None:
    settings = replica_settings()
    require_replica(settings)
    manager = DatabaseManager(settings)

    try:
        application = create_app(settings, database_manager=manager)
        with TestClient(application) as client:
            response = client.get("/api/v1/health/dependencies")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "degraded"
        assert body["checks"]["mongodb"] == {
            "status": "ok",
            "detail": "MongoDB is reachable.",
            "endpoint": "127.0.0.1:27018",
            "replica_set": "rs0",
            "is_writable_primary": True,
        }
        assert body["checks"]["cassandra"]["status"] == "not_configured"
    finally:
        manager.close()
        cleanup(settings)


def test_replica_payment_commits_state_and_publication_metadata_atomically() -> None:
    settings = replica_settings(cassandra=True)
    require_replica(settings, cassandra=True)
    manager = DatabaseManager(settings)
    owner_id = str(uuid4())
    account_id = str(uuid4())
    command = make_command(
        account_id, owner_id, "800.00", "replica-payment-once"
    )

    try:
        manager.initialize_schema()
        MongoAccountRepository(manager).create(make_account(account_id, owner_id))
        audit = MongoAuditRepository(manager)
        repository = MongoPaymentRepository(manager, audit_repository=audit)

        first = repository.execute(
            command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
        )
        replay = repository.execute(
            command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
        )

        assert repository.supports_multi_document_transactions is True
        assert repository.atomicity_mode == "replica_set_mongo_transaction"
        assert first.transaction.transaction_id == replay.transaction.transaction_id
        assert first.account.balance == Decimal("200.00")
        assert manager.mongo_database["transactions"].count_documents({}) == 1
        assert manager.mongo_database["audit_records"].count_documents({}) == 1
        assert manager.mongo_database["audit_records"].find_one(
            {"publication_status": "PENDING"}
        ) is not None

        with pytest.raises(IdempotencyConflictError):
            repository.execute(
                make_command(account_id, owner_id, "700.00", "replica-payment-once"),
                transaction_id=str(uuid4()),
                at=datetime.now(timezone.utc),
            )

        delivery = EventDeliveryService(
            audit,
            CassandraEventPublisher(CassandraEventRepository(manager)),
        )
        delivered = delivery.publish_pending(
            now=first.transaction.updated_at + timedelta(minutes=1)
        )
        assert delivered.attempted == 1
        assert delivered.published == 1
    finally:
        manager.close()
        cleanup(settings)


def test_replica_transaction_rolls_back_account_and_transaction_on_event_failure() -> None:
    settings = replica_settings()
    require_replica(settings)
    manager = DatabaseManager(settings)
    owner_id = str(uuid4())
    account_id = str(uuid4())
    command = make_command(account_id, owner_id, "800.00", "replica-rollback")

    class FailingAudit:
        def append(self, event, *, publication_target=None, session=None):
            raise DatabaseUnavailableError()

    try:
        MongoAccountRepository(manager).create(make_account(account_id, owner_id))
        failing_repository = MongoPaymentRepository(
            manager, audit_repository=FailingAudit()
        )
        with pytest.raises(DatabaseUnavailableError):
            failing_repository.execute(
                command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
            )

        account = MongoAccountRepository(manager).get_by_id(account_id)
        assert account is not None
        assert account.balance == Decimal("1000.00")
        assert manager.mongo_database["transactions"].count_documents({}) == 0
        assert manager.mongo_database["audit_records"].count_documents({}) == 0

        recovered = MongoPaymentRepository(
            manager, audit_repository=MongoAuditRepository(manager)
        ).execute(
            command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
        )
        assert recovered.account.balance == Decimal("200.00")
    finally:
        manager.close()
        cleanup(settings)


def test_replica_concurrency_and_same_key_retry_preserve_one_effect() -> None:
    settings = replica_settings()
    require_replica(settings)
    manager = DatabaseManager(settings)
    owner_id = str(uuid4())
    account_id = str(uuid4())

    try:
        MongoAccountRepository(manager).create(make_account(account_id, owner_id))
        first = MongoPaymentRepository(manager)
        second = MongoPaymentRepository(manager)
        same_key = make_command(account_id, owner_id, "500.00", "replica-same-key")

        def execute_same(repository: MongoPaymentRepository):
            return repository.execute(
                same_key, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            same_results = list(
                executor.map(execute_same, (first, second))
            )
        assert same_results[0].transaction.transaction_id == same_results[1].transaction.transaction_id
        assert MongoAccountRepository(manager).get_by_id(account_id).balance == Decimal("500.00")

        # Use a fresh account for the overspend race.
        race_account_id = str(uuid4())
        race_owner_id = str(uuid4())
        MongoAccountRepository(manager).create(
            make_account(race_account_id, race_owner_id)
        )
        commands = (
            make_command(race_account_id, race_owner_id, "800.00", "replica-race-800"),
            make_command(race_account_id, race_owner_id, "700.00", "replica-race-700"),
        )

        def execute_race(item):
            repository, command = item
            return repository.execute(
                command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc)
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(execute_race, (first, commands[0])),
                executor.submit(execute_race, (second, commands[1])),
            ]
            results = []
            failures = []
            for future in futures:
                try:
                    results.append(future.result())
                except (InsufficientFundsError, PaymentConcurrencyError, DatabaseUnavailableError) as exc:
                    failures.append(exc)

        assert len(results) == 1
        assert len(failures) == 1
        final_account = MongoAccountRepository(manager).get_by_id(race_account_id)
        assert final_account is not None
        assert final_account.balance in {Decimal("200.00"), Decimal("300.00")}
        assert final_account.balance >= Decimal("0.00")
    finally:
        manager.close()
        cleanup(settings)
