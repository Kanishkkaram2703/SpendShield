"""Query-first Cassandra keyspace and event-table definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EventTableDefinition:
    """Definition for one chronological event access pattern."""

    name: str
    partition_column: str
    query: str


EVENT_TABLES: dict[str, EventTableDefinition] = {
    "authentication_events_by_user_day": EventTableDefinition(
        name="authentication_events_by_user_day",
        partition_column="user_id",
        query="user_id + event_date + time range",
    ),
    "session_events_by_user_day": EventTableDefinition(
        name="session_events_by_user_day",
        partition_column="user_id",
        query="user_id + event_date + time range",
    ),
    "device_events_by_device_day": EventTableDefinition(
        name="device_events_by_device_day",
        partition_column="device_id",
        query="device_id + event_date + time range",
    ),
    "transaction_events_by_account_day": EventTableDefinition(
        name="transaction_events_by_account_day",
        partition_column="account_id",
        query="account_id + event_date + time range",
    ),
    "audit_events_by_case_day": EventTableDefinition(
        name="audit_events_by_case_day",
        partition_column="case_id",
        query="case_id + event_date + time range",
    ),
}


def _event_table_cql(definition: EventTableDefinition) -> str:
    partition_column = definition.partition_column
    columns = [
        f"{partition_column} text",
        "event_date date",
        "event_time timestamp",
        "event_id uuid",
        "event_type text",
        "actor_id text",
    ]
    # device_id is already the partition column for the device workload.
    # Declaring it again produces an invalid schema on a real Cassandra node.
    if partition_column != "device_id":
        columns.append("device_id text")
    columns.extend(
        [
            "session_id text",
            "source text",
            "payload text",
        ]
    )
    return f"""
    CREATE TABLE IF NOT EXISTS {definition.name} (
        {", ".join(columns)},
        PRIMARY KEY (({partition_column}, event_date), event_time, event_id)
    ) WITH CLUSTERING ORDER BY (event_time DESC, event_id ASC)
    """


def ensure_cassandra_schema(
    session: Any,
    keyspace: str,
    replication_factor: int,
) -> dict[str, int]:
    """Create the keyspace and event tables for documented query patterns."""

    session.execute(
        f"CREATE KEYSPACE IF NOT EXISTS {keyspace} "
        "WITH replication = "
        f"{{'class': 'SimpleStrategy', 'replication_factor': '{replication_factor}'}}"
    )
    session.set_keyspace(keyspace)
    for definition in EVENT_TABLES.values():
        session.execute(_event_table_cql(definition))
    return {"tables": len(EVENT_TABLES)}


__all__ = ["EVENT_TABLES", "EventTableDefinition", "ensure_cassandra_schema"]
