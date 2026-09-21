"""Retryable delivery of durable event records to Cassandra."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.logging import get_logger
from app.events.publishers import EventPublisher
from app.events.publication import EventPublicationStore

LOGGER = get_logger(__name__)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class EventDeliveryResult:
    """Counters from one explicit delivery pass."""

    attempted: int
    published: int
    failed: int


class EventDeliveryService:
    """Deliver persisted events without coupling retries to financial effects.

    This is intentionally an explicit application service rather than a
    background-worker framework.  A future scheduler or process entry point
    may call ``publish_pending``; no broker is required for the current
    modular-monolith workload.
    """

    def __init__(
        self,
        store: EventPublicationStore,
        publisher: EventPublisher,
        *,
        retry_base_seconds: int = 5,
        retry_max_seconds: int = 3600,
    ) -> None:
        if retry_base_seconds < 1 or retry_max_seconds < retry_base_seconds:
            raise ValueError("Retry delay bounds are invalid.")
        self._store = store
        self._publisher = publisher
        self._retry_base_seconds = retry_base_seconds
        self._retry_max_seconds = retry_max_seconds

    def _retry_delay(self, attempt_count: int) -> timedelta:
        seconds = min(
            self._retry_max_seconds,
            self._retry_base_seconds * (2**min(attempt_count, 10)),
        )
        return timedelta(seconds=seconds)

    def publish_pending(
        self,
        *,
        now: datetime | None = None,
        limit: int = 100,
    ) -> EventDeliveryResult:
        """Attempt due events once and persist the result of each attempt."""

        current_time = _utc(now or datetime.now(timezone.utc))
        pending = self._store.list_due(now=current_time, limit=limit)
        published = 0
        failed = 0

        for item in pending:
            event_id = str(item.event.event_id)
            try:
                # Parse before calling an adapter so malformed persisted IDs
                # fail closed and are represented as a delivery failure.
                UUID(event_id)
                self._publisher.publish(
                    item.event,
                    table=item.target.table,
                    partition_value=item.target.partition_value,
                )
                self._store.mark_published(
                    event_id,
                    published_at=current_time,
                )
                published += 1
            except Exception as exc:  # noqa: BLE001 - delivery must be retryable
                failed += 1
                error_code = type(exc).__name__[:128]
                next_attempt_at = current_time + self._retry_delay(
                    item.attempt_count
                )
                self._store.mark_failed(
                    event_id,
                    failed_at=current_time,
                    next_attempt_at=next_attempt_at,
                    error_code=error_code,
                )
                LOGGER.warning(
                    "event_delivery_failed event_id=%s error_type=%s attempt=%s",
                    event_id,
                    error_code,
                    item.attempt_count + 1,
                )

        return EventDeliveryResult(
            attempted=len(pending),
            published=published,
            failed=failed,
        )


__all__ = ["EventDeliveryResult", "EventDeliveryService"]
