"""Unit tests for the canonical event envelope."""

from __future__ import annotations

from datetime import datetime, timezone

from app.events.models import DomainEvent
from app.events.publishers import NullEventPublisher


def test_domain_event_preserves_fact_and_provenance_fields() -> None:
    event = DomainEvent(
        event_type="ACCOUNT_CREATED",
        subject_id="account-1",
        actor_id="user-1",
        occurred_at=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        source="account-service",
        correlation_id="correlation-1",
        payload={"currency": "INR"},
        provenance={"source": "api"},
    )

    payload = event.payload_with_envelope()
    assert payload["event_id"] == str(event.event_id)
    assert payload["subject_id"] == "account-1"
    assert payload["correlation_id"] == "correlation-1"
    assert payload["payload"] == {"currency": "INR"}
    assert payload["provenance"] == {"source": "api"}


def test_null_event_publisher_is_explicit_and_side_effect_free() -> None:
    event = DomainEvent(
        event_type="TEST",
        subject_id="subject-1",
        actor_id=None,
        occurred_at=datetime.now(timezone.utc),
        source="test",
        correlation_id="correlation-1",
    )

    NullEventPublisher().publish(
        event,
        table="authentication_events_by_user_day",
        partition_value="subject-1",
    )
