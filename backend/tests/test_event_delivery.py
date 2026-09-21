"""Unit tests for the durable event-publication boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.exceptions import DatabaseUnavailableError
from app.events.models import DomainEvent
from app.events.publication import EventPublicationTarget
from app.repositories.fakes import InMemoryAuditRepository
from app.services.event_delivery_service import EventDeliveryService


class RecordingPublisher:
    """Small publisher fake that can model a transient Cassandra outage."""

    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.calls: list[tuple[DomainEvent, str, str]] = []

    def publish(
        self,
        event: DomainEvent,
        *,
        table: str,
        partition_value: str,
    ) -> None:
        if self.failures:
            self.failures -= 1
            raise DatabaseUnavailableError()
        self.calls.append((event, table, partition_value))


def make_event() -> DomainEvent:
    return DomainEvent(
        event_type="TRANSACTION_COMPLETED",
        subject_id="account-1",
        actor_id="user-1",
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source="event-delivery-test",
        correlation_id="request-1",
        causation_id="transaction-initiated-1",
        payload={"amount": "850.00"},
        provenance={"request_id": "request-1", "source_record": "test"},
    )


def target() -> EventPublicationTarget:
    return EventPublicationTarget(
        table="transaction_events_by_account_day",
        partition_value="account-1",
    )


def test_normal_delivery_preserves_identity_and_trace_fields() -> None:
    store = InMemoryAuditRepository()
    publisher = RecordingPublisher()
    event = make_event()
    store.append(event, publication_target=target())

    result = EventDeliveryService(store, publisher).publish_pending(
        now=event.created_at + timedelta(minutes=1)
    )

    assert result.attempted == 1
    assert result.published == 1
    assert result.failed == 0
    assert len(publisher.calls) == 1
    delivered, table, partition = publisher.calls[0]
    assert delivered.event_id == event.event_id
    assert delivered.correlation_id == "request-1"
    assert delivered.causation_id == "transaction-initiated-1"
    assert table == "transaction_events_by_account_day"
    assert partition == "account-1"
    assert store.list_due(now=event.created_at + timedelta(minutes=1)) == []


def test_duplicate_event_append_and_delivery_are_idempotent() -> None:
    store = InMemoryAuditRepository()
    publisher = RecordingPublisher()
    event = make_event()
    store.append(event, publication_target=target())
    store.append(event, publication_target=target())

    first = EventDeliveryService(store, publisher).publish_pending(
        now=event.created_at + timedelta(minutes=1)
    )
    second = EventDeliveryService(store, publisher).publish_pending(
        now=event.created_at + timedelta(minutes=2)
    )

    assert first.published == 1
    assert second.attempted == 0
    assert len(publisher.calls) == 1


def test_failed_publication_is_retryable_without_reexecuting_the_event() -> None:
    store = InMemoryAuditRepository()
    publisher = RecordingPublisher(failures=1)
    event = make_event()
    store.append(event, publication_target=target())
    service = EventDeliveryService(
        store,
        publisher,
        retry_base_seconds=5,
        retry_max_seconds=30,
    )

    failed = service.publish_pending(now=event.created_at + timedelta(minutes=1))
    retried = service.publish_pending(
        now=event.created_at + timedelta(minutes=1, seconds=5)
    )

    assert failed.attempted == 1
    assert failed.published == 0
    assert failed.failed == 1
    assert retried.attempted == 1
    assert retried.published == 1
    assert retried.failed == 0
    assert len(publisher.calls) == 1


def test_cassandra_failure_leaves_a_pending_record() -> None:
    store = InMemoryAuditRepository()
    publisher = RecordingPublisher(failures=99)
    event = make_event()
    store.append(event, publication_target=target())
    service = EventDeliveryService(store, publisher)

    result = service.publish_pending(now=event.created_at + timedelta(minutes=1))
    pending = store.list_due(
        now=event.created_at + timedelta(minutes=1, seconds=4)
    )

    assert result.failed == 1
    assert len(pending) == 0  # exponential backoff has not elapsed
    assert publisher.calls == []
