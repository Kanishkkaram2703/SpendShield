"""Canonical event envelope shared by domain services and history adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Immutable description of something that happened in the domain."""

    event_type: str
    subject_id: str
    actor_id: str | None
    occurred_at: datetime
    source: str
    correlation_id: str
    causation_id: str | None = None
    schema_version: int = 1
    payload: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    event_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.event_type.strip() or not self.subject_id.strip():
            raise ValueError("Event type and subject identifier are required.")
        if not self.source.strip() or not self.correlation_id.strip():
            raise ValueError("Event source and correlation identifier are required.")
        if self.schema_version < 1:
            raise ValueError("Event schema version must be positive.")
        object.__setattr__(self, "occurred_at", _utc(self.occurred_at))
        object.__setattr__(self, "created_at", _utc(self.created_at))

    def payload_with_envelope(self) -> dict[str, Any]:
        """Return a JSON-safe payload for Cassandra's event record."""

        return {
            "event_id": str(self.event_id),
            "subject_id": self.subject_id,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "schema_version": self.schema_version,
            "payload": self.payload,
            "provenance": self.provenance,
            "created_at": self.created_at.isoformat(),
        }


__all__ = ["DomainEvent"]
