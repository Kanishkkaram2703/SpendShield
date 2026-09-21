"""Append-only audit record contracts for security-sensitive domain changes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.exceptions import DatabaseUnavailableError
from app.db.manager import DatabaseManager
from app.events.models import DomainEvent
from app.events.publication import (
    EventPublicationStore,
    EventPublicationTarget,
    PendingEventPublication,
)


@runtime_checkable
class AuditRepository(Protocol):
    """Persistence boundary for meaningful application audit events."""

    def append(
        self,
        event: DomainEvent,
        *,
        publication_target: EventPublicationTarget | None = None,
        session: Any | None = None,
    ) -> None:
        """Append one immutable audit event and optional delivery record."""


class NullAuditRepository:
    """Explicit no-op adapter for isolated tests without real persistence."""

    def append(
        self,
        event: DomainEvent,
        *,
        publication_target: EventPublicationTarget | None = None,
        session: Any | None = None,
    ) -> None:
        return None

    def list_due(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[PendingEventPublication]:
        return []

    def mark_published(self, event_id: str, *, published_at: datetime) -> None:
        return None

    def mark_failed(
        self,
        event_id: str,
        *,
        failed_at: datetime,
        next_attempt_at: datetime,
        error_code: str,
    ) -> None:
        return None


class MongoAuditRepository:
    """Store immutable audit facts and optional publication metadata.

    The event envelope is never changed after insertion.  Publication fields
    are operational delivery metadata in the same MongoDB document, allowing
    a future retry pass to replay the exact stored event without re-running a
    financial operation.
    """

    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager
        self._schema_ready = False

    def _collection(self) -> Any:
        if not self._schema_ready:
            self._database_manager.ensure_mongodb_schema()
            self._schema_ready = True
        return self._database_manager.mongo_database["audit_records"]

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _to_mongodb_datetime(value: datetime) -> datetime:
        normalized = MongoAuditRepository._utc(value)
        return normalized.replace(microsecond=(normalized.microsecond // 1000) * 1000)

    def append(
        self,
        event: DomainEvent,
        *,
        publication_target: EventPublicationTarget | None = None,
        session: Any | None = None,
    ) -> None:
        """Insert an audit record; replaying the same event ID is idempotent."""

        created_at = self._to_mongodb_datetime(event.created_at)
        publication_status = "PENDING" if publication_target is not None else "NOT_ROUTED"

        document = {
            "audit_id": str(event.event_id),
            "event_type": event.event_type,
            "subject_id": event.subject_id,
            "actor_id": event.actor_id,
            "timestamp": self._to_mongodb_datetime(event.occurred_at),
            "source": event.source,
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id,
            "schema_version": event.schema_version,
            "payload": event.payload,
            "provenance": event.provenance,
            "created_at": created_at,
            "publication_status": publication_status,
            "publication_attempts": 0,
            "publication_next_attempt_at": (
                created_at if publication_target is not None else None
            ),
            "publication_last_error": None,
            "published_at": None,
            "publication_table": (
                publication_target.table if publication_target is not None else None
            ),
            "publication_partition_value": (
                publication_target.partition_value
                if publication_target is not None
                else None
            ),
        }
        try:
            insert_options = {"session": session} if session is not None else {}
            self._collection().insert_one(document, **insert_options)
        except DuplicateKeyError:
            # The unique audit ID makes retries safe without duplicating records.
            return None
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def list_due(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[PendingEventPublication]:
        """Return pending/failed routed events whose retry time has arrived."""

        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        query = {
            "publication_status": {"$in": ["PENDING", "FAILED"]},
            "publication_next_attempt_at": {
                "$lte": self._to_mongodb_datetime(now)
            },
        }
        try:
            documents = self._collection().find(query).sort(
                [
                    ("publication_next_attempt_at", 1),
                    ("created_at", 1),
                    ("audit_id", 1),
                ]
            ).limit(limit)
            return [self._pending_from_document(document) for document in documents]
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def mark_published(self, event_id: str, *, published_at: datetime) -> None:
        """Acknowledge delivery without modifying the canonical event fields."""

        try:
            self._collection().update_one(
                {
                    "audit_id": event_id,
                    "publication_status": {"$in": ["PENDING", "FAILED"]},
                },
                {
                    "$set": {
                        "publication_status": "PUBLISHED",
                        "published_at": self._to_mongodb_datetime(published_at),
                        "publication_next_attempt_at": None,
                        "publication_last_error": None,
                    }
                },
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def mark_failed(
        self,
        event_id: str,
        *,
        failed_at: datetime,
        next_attempt_at: datetime,
        error_code: str,
    ) -> None:
        """Record a bounded error classification for a later retry."""

        try:
            self._collection().update_one(
                {
                    "audit_id": event_id,
                    "publication_status": {"$in": ["PENDING", "FAILED"]},
                },
                {
                    "$set": {
                        "publication_status": "FAILED",
                        "publication_last_error": error_code[:128],
                        "publication_next_attempt_at": self._to_mongodb_datetime(
                            next_attempt_at
                        ),
                        "publication_failed_at": self._to_mongodb_datetime(failed_at),
                    },
                    "$inc": {"publication_attempts": 1},
                },
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    @classmethod
    def _pending_from_document(cls, document: dict[str, Any]) -> PendingEventPublication:
        event = DomainEvent(
            event_type=document["event_type"],
            subject_id=document["subject_id"],
            actor_id=document.get("actor_id"),
            occurred_at=document["timestamp"],
            source=document["source"],
            correlation_id=document["correlation_id"],
            causation_id=document.get("causation_id"),
            schema_version=int(document.get("schema_version", 1)),
            payload=dict(document.get("payload") or {}),
            provenance=dict(document.get("provenance") or {}),
            event_id=UUID(document["audit_id"]),
            created_at=document["created_at"],
        )
        target = EventPublicationTarget(
            table=document["publication_table"],
            partition_value=document["publication_partition_value"],
        )
        next_attempt_at = document.get("publication_next_attempt_at")
        if next_attempt_at is None:
            next_attempt_at = document["created_at"]
        return PendingEventPublication(
            event=event,
            target=target,
            attempt_count=int(document.get("publication_attempts", 0)),
            next_attempt_at=next_attempt_at,
            last_error=document.get("publication_last_error"),
        )


__all__ = [
    "AuditRepository",
    "EventPublicationStore",
    "MongoAuditRepository",
    "NullAuditRepository",
]
