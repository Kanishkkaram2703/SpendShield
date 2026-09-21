"""Integration tests for the MongoDB/Cassandra foundation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import Settings
from app.core.security import hash_password
from app.core.exceptions import DatabaseUnavailableError
from app.db.events import CassandraEventRepository
from app.db.manager import DatabaseManager
from app.db.mongo_schema import MONGO_COLLECTIONS
from app.domain.financial import Account, AccountStatus
from app.events.models import DomainEvent
from app.events.publishers import CassandraEventPublisher
from app.events.publication import EventPublicationTarget
from app.repositories.accounts import (
    AccountVersionConflictError,
    DuplicateAccountError,
    MongoAccountRepository,
)
from app.repositories.audit import MongoAuditRepository
from app.repositories.mongo_users import MongoUserRepository
from app.repositories.users import UserRecord, UserRole
from app.services.event_delivery_service import EventDeliveryService


def database_settings() -> Settings:
    """Use isolated local namespaces for each test process."""

    suffix = uuid4().hex
    return Settings(
        _env_file=None,
        environment="test",
        mongodb_uri="mongodb://127.0.0.1:27017",
        mongodb_database=f"spendshield_test_{suffix}",
        cassandra_hosts="127.0.0.1",
        # Cassandra DDL is expensive on the local single-node service.  Keep
        # one valid test keyspace and isolate test data with random Mongo
        # databases and event partition values.
        cassandra_keyspace="ss_test",
        mongodb_server_selection_timeout_ms=2000,
        mongodb_connect_timeout_ms=2000,
        cassandra_connect_timeout_seconds=5,
    )


def cleanup_database_namespaces(settings: Settings) -> None:
    """Remove the unique Mongo namespace created by one test."""

    mongo_client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
    try:
        try:
            mongo_client.drop_database(settings.mongodb_database)
        except PyMongoError:
            pass
    finally:
        mongo_client.close()

    # The shared local Cassandra test keyspace is intentionally retained so
    # repeated integration tests do not enqueue expensive schema-agreement
    # migrations.  Test rows use random partition values and event IDs.


def require_mongodb(settings: Settings) -> None:
    """Skip MongoDB integration tests when MongoDB is not running."""

    manager = DatabaseManager(settings)
    try:
        manager.connect_mongodb()
    except DatabaseUnavailableError as exc:
        pytest.skip(f"MongoDB integration service unavailable: {exc}")
    finally:
        manager.close()


def require_cassandra(settings: Settings) -> None:
    """Skip Cassandra integration tests when Cassandra is not running."""

    manager = DatabaseManager(settings)
    try:
        manager.connect_cassandra()
    except DatabaseUnavailableError as exc:
        pytest.skip(f"Cassandra integration service unavailable: {exc}")
    finally:
        manager.close()


def require_database_services(settings: Settings) -> None:
    """Skip combined integration tests when either service is unavailable."""

    require_mongodb(settings)
    require_cassandra(settings)


def test_mongodb_schema_is_initialized_idempotently() -> None:
    settings = database_settings()
    require_mongodb(settings)
    manager = DatabaseManager(settings)

    try:
        first = manager.ensure_mongodb_schema()
        second = manager.ensure_mongodb_schema()

        assert first["collections"] == len(MONGO_COLLECTIONS)
        assert second["collections"] == len(MONGO_COLLECTIONS)
        assert set(MONGO_COLLECTIONS).issubset(
            set(manager.mongo_database.list_collection_names())
        )
        assert "uq_users_email" in set(
            manager.mongo_database["users"].index_information()
        )
        assert "uq_accounts_user_id" in set(
            manager.mongo_database["accounts"].index_information()
        )
        assert "ix_transactions_user_time_id" in set(
            manager.mongo_database["transactions"].index_information()
        )
    finally:
        manager.close()
        cleanup_database_namespaces(settings)


def test_mongodb_and_cassandra_schema_and_health() -> None:
    settings = database_settings()
    require_database_services(settings)
    manager = DatabaseManager(settings)

    try:
        health = manager.health()
        assert health["status"] == "ok"
        assert health["checks"]["mongodb"]["status"] == "ok"
        assert health["checks"]["cassandra"]["status"] == "ok"

        schema = manager.initialize_schema()
        assert schema["mongodb"]["collections"] == len(MONGO_COLLECTIONS)
        assert schema["cassandra"]["tables"] == 5

        collection_names = set(manager.mongo_database.list_collection_names())
        assert set(MONGO_COLLECTIONS).issubset(collection_names)
        user_indexes = set(manager.mongo_database["users"].index_information())
        assert "uq_users_email" in user_indexes

        rows = manager.cassandra_session.execute(
            "SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s",
            (settings.cassandra_keyspace,),
        )
        table_names = {row.table_name for row in rows}
        assert "authentication_events_by_user_day" in table_names
        assert "transaction_events_by_account_day" in table_names
    finally:
        manager.close()
        cleanup_database_namespaces(settings)


def test_mongodb_user_repository_crud() -> None:
    settings = database_settings()
    require_mongodb(settings)
    manager = DatabaseManager(settings)
    repository = MongoUserRepository(manager)
    now = datetime.now(timezone.utc)
    user = UserRecord(
        user_id=str(uuid4()),
        email="database-user@example.com",
        password_hash=hash_password("database-test-password"),
        role=UserRole.USER,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    try:
        persisted = repository.create(user)
        assert persisted.user_id == user.user_id
        assert persisted.created_at.microsecond % 1000 == 0
        assert repository.get_by_id(user.user_id) == persisted
        assert repository.get_by_email(user.email) == persisted
    finally:
        manager.close()
        cleanup_database_namespaces(settings)


def test_mongodb_account_repository_crud() -> None:
    settings = database_settings()
    require_mongodb(settings)
    manager = DatabaseManager(settings)
    repository = MongoAccountRepository(manager)
    now = datetime.now(timezone.utc)
    account = Account(
        account_id=str(uuid4()),
        owner_id=str(uuid4()),
        currency="INR",
        balance="10000.00",
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    try:
        persisted = repository.create(account)
        assert persisted.account_id == account.account_id
        assert persisted.created_at.microsecond % 1000 == 0
        assert repository.get_by_id(account.account_id) == persisted
        assert repository.get_by_owner(account.owner_id) == persisted
        updated = persisted.transition_status(AccountStatus.SUSPENDED, at=now)
        status_persisted = repository.update(
            updated,
            expected_version=persisted.version,
        )
        assert status_persisted is not None
        assert status_persisted.status is AccountStatus.SUSPENDED
        assert status_persisted.version == 1
        with pytest.raises(AccountVersionConflictError):
            repository.update(updated, expected_version=0)

        duplicate_owner = Account(
            account_id=str(uuid4()),
            owner_id=account.owner_id,
            currency="INR",
            balance="10000.00",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        with pytest.raises(DuplicateAccountError):
            repository.create(duplicate_owner)
    finally:
        manager.close()
        cleanup_database_namespaces(settings)


def test_mongodb_audit_repository_is_append_only_and_replay_safe() -> None:
    settings = database_settings()
    require_mongodb(settings)
    manager = DatabaseManager(settings)
    repository = MongoAuditRepository(manager)
    event = DomainEvent(
        event_type="ACCOUNT_CREATED",
        subject_id=str(uuid4()),
        actor_id=str(uuid4()),
        occurred_at=datetime.now(timezone.utc),
        source="phase-3-test",
        correlation_id=str(uuid4()),
        payload={"synthetic": True},
    )

    try:
        repository.append(event)
        repository.append(event)
        records = list(
            manager.mongo_database["audit_records"].find(
                {"audit_id": str(event.event_id)}
            )
        )
        assert len(records) == 1
        assert records[0]["event_type"] == "ACCOUNT_CREATED"
        assert records[0]["payload"] == {"synthetic": True}
    finally:
        manager.close()
        cleanup_database_namespaces(settings)


def test_durable_publication_reaches_cassandra_and_is_replay_safe() -> None:
    settings = database_settings()
    require_database_services(settings)
    manager = DatabaseManager(settings)
    repository = MongoAuditRepository(manager)
    event_time = datetime.now(timezone.utc).replace(microsecond=0)
    publication_subject = f"publication-user-{uuid4()}"
    event = DomainEvent(
        event_type="LOGIN_SUCCESS",
        subject_id=publication_subject,
        actor_id=publication_subject,
        occurred_at=event_time,
        source="publication-integration-test",
        correlation_id=str(uuid4()),
        causation_id=None,
        payload={"synthetic": True},
        provenance={"request_id": "publication-request"},
    )
    target = EventPublicationTarget(
        table="authentication_events_by_user_day",
        partition_value=publication_subject,
    )

    try:
        manager.initialize_schema()
        repository.append(event, publication_target=target)
        repository.append(event, publication_target=target)
        delivery = EventDeliveryService(
            repository,
            CassandraEventPublisher(CassandraEventRepository(manager)),
        )

        result = delivery.publish_pending(now=event.created_at + timedelta(minutes=1))
        assert result.attempted == 1
        assert result.published == 1
        assert result.failed == 0
        assert repository.list_due(
            now=event.created_at + timedelta(minutes=1)
        ) == []

        events = CassandraEventRepository(manager).list_by_partition(
            "authentication_events_by_user_day",
            publication_subject,
            event_time.date(),
        )
        matching = [item for item in events if item.event_id == event.event_id]
        assert len(matching) == 1
        assert matching[0].payload["event_id"] == str(event.event_id)
        assert matching[0].payload["correlation_id"] == event.correlation_id
        assert matching[0].payload["provenance"] == {
            "request_id": "publication-request"
        }
    finally:
        manager.close()
        cleanup_database_namespaces(settings)


def test_cassandra_event_repository_append_and_query() -> None:
    settings = database_settings()
    require_database_services(settings)
    manager = DatabaseManager(settings)
    repository = CassandraEventRepository(manager)
    event_time = datetime.now(timezone.utc).replace(microsecond=0)
    partition_value = f"user-foundation-{uuid4()}"

    try:
        inserted = repository.append(
            "authentication_events_by_user_day",
            partition_value,
            event_type="LOGIN_SUCCESS",
            event_time=event_time,
            actor_id=partition_value,
            source="phase-2-test",
            payload={"synthetic": True},
        )
        repository.append(
            "authentication_events_by_user_day",
            partition_value,
            event_type="LOGIN_SUCCESS",
            event_time=event_time,
            actor_id=partition_value,
            source="phase-2-test",
            payload={"synthetic": True},
            event_id=inserted.event_id,
        )
        events = repository.list_by_partition(
            "authentication_events_by_user_day",
            partition_value,
            event_time.date(),
        )

        matching = [event for event in events if event.event_id == inserted.event_id]
        assert len(matching) == 1
        assert matching[0].event_type == "LOGIN_SUCCESS"
        assert matching[0].payload == {"synthetic": True}

        device_id = f"device-foundation-{uuid4()}"
        device_inserted = repository.append(
            "device_events_by_device_day",
            device_id,
            event_type="DEVICE_SEEN",
            event_time=event_time,
            actor_id="user-foundation-test",
            device_id=device_id,
            source="phase-2-test",
            payload={"synthetic": True},
        )
        device_events = repository.list_by_partition(
            "device_events_by_device_day",
            device_id,
            event_time.date(),
        )
        device_matching = [
            event for event in device_events if event.event_id == device_inserted.event_id
        ]
        assert len(device_matching) == 1
        assert device_matching[0].device_id == device_id
    finally:
        manager.close()
        cleanup_database_namespaces(settings)
