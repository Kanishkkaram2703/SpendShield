"""Contracts for durable historical-event publication.

The publication target is deliberately kept outside :class:`DomainEvent`.
The event describes what happened; the target describes which existing
Cassandra query model can store that event.  This prevents routing metadata
from becoming part of the canonical domain fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from app.events.models import DomainEvent


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class EventPublicationTarget:
    """Route an event to one already-defined chronological query table."""

    table: str
    partition_value: str

    def __post_init__(self) -> None:
        if not self.table.strip() or not self.partition_value.strip():
            raise ValueError("Event publication target values are required.")


@dataclass(frozen=True, slots=True)
class PendingEventPublication:
    """An immutable event plus mutable delivery metadata."""

    event: DomainEvent
    target: EventPublicationTarget
    attempt_count: int
    next_attempt_at: datetime
    last_error: str | None = None

    def __post_init__(self) -> None:
        if self.attempt_count < 0:
            raise ValueError("Publication attempt count cannot be negative.")
        object.__setattr__(self, "next_attempt_at", _utc(self.next_attempt_at))


@runtime_checkable
class EventPublicationStore(Protocol):
    """Persistence boundary for pending Cassandra publication attempts."""

    def list_due(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[PendingEventPublication]:
        """Return due records without changing their delivery state."""

    def mark_published(
        self,
        event_id: str,
        *,
        published_at: datetime,
    ) -> None:
        """Mark one event as historically published."""

    def mark_failed(
        self,
        event_id: str,
        *,
        failed_at: datetime,
        next_attempt_at: datetime,
        error_code: str,
    ) -> None:
        """Record a retryable delivery failure without changing the event."""


__all__ = [
    "EventPublicationStore",
    "EventPublicationTarget",
    "PendingEventPublication",
]
