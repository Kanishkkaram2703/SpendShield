"""Event publisher boundary with a Cassandra-backed adapter."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.db.events import CassandraEventRepository
from app.events.models import DomainEvent


@runtime_checkable
class EventPublisher(Protocol):
    """Application boundary for historical event publication."""

    def publish(
        self,
        event: DomainEvent,
        *,
        table: str,
        partition_value: str,
    ) -> None:
        """Publish one immutable domain event."""


class NullEventPublisher:
    """Explicit no-op publisher for tests and non-event workflows."""

    def publish(
        self,
        event: DomainEvent,
        *,
        table: str,
        partition_value: str,
    ) -> None:
        return None


class CassandraEventPublisher:
    """Adapt the canonical envelope to the existing Cassandra event repository."""

    def __init__(self, repository: CassandraEventRepository) -> None:
        self._repository = repository

    def publish(
        self,
        event: DomainEvent,
        *,
        table: str,
        partition_value: str,
    ) -> None:
        self._repository.append(
            table,
            partition_value,
            event_type=event.event_type,
            event_time=event.occurred_at,
            actor_id=event.actor_id,
            source=event.source,
            payload=event.payload_with_envelope(),
            event_id=event.event_id,
        )


__all__ = ["CassandraEventPublisher", "EventPublisher", "NullEventPublisher"]
