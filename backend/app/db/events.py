"""Cassandra event repository for Phase 2 chronological workloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.db.cassandra_schema import EVENT_TABLES
from app.db.manager import DatabaseManager


@dataclass(frozen=True, slots=True)
class EventRecord:
    """Common event record stored in a query-specific Cassandra table."""

    table: str
    partition_value: str
    event_date: date
    event_time: datetime
    event_id: UUID
    event_type: str
    actor_id: str | None
    device_id: str | None
    session_id: str | None
    source: str | None
    payload: dict[str, Any]


class CassandraEventRepository:
    """Append/query events using the table's documented partition key."""

    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def append(
        self,
        table: str,
        partition_value: str,
        *,
        event_type: str,
        event_time: datetime,
        actor_id: str | None = None,
        device_id: str | None = None,
        session_id: str | None = None,
        source: str | None = None,
        payload: dict[str, Any] | None = None,
        event_id: UUID | None = None,
    ) -> EventRecord:
        if table not in EVENT_TABLES:
            raise ValueError(f"Unsupported event table: {table}")
        definition = EVENT_TABLES[table]
        normalized_time = self._utc(event_time)
        identifier = event_id or uuid4()
        event_date = normalized_time.date()
        columns = [
            definition.partition_column,
            "event_date",
            "event_time",
            "event_id",
            "event_type",
            "actor_id",
        ]
        parameters: list[Any] = [
            partition_value,
            event_date,
            normalized_time,
            identifier,
            event_type,
            actor_id,
        ]
        if definition.partition_column != "device_id":
            columns.append("device_id")
            parameters.append(device_id)
        columns.extend(["session_id", "source", "payload"])
        parameters.extend(
            [
                session_id,
                source,
                json.dumps(payload or {}, separators=(",", ":")),
            ]
        )
        statement = self._database_manager.cassandra_session.prepare(
            f"INSERT INTO {definition.name} ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)})"
        )
        self._database_manager.cassandra_session.execute(
            statement,
            tuple(parameters),
        )
        return EventRecord(
            table=table,
            partition_value=partition_value,
            event_date=event_date,
            event_time=normalized_time,
            event_id=identifier,
            event_type=event_type,
            actor_id=actor_id,
            device_id=(
                partition_value if definition.partition_column == "device_id" else device_id
            ),
            session_id=session_id,
            source=source,
            payload=payload or {},
        )

    def list_by_partition(
        self,
        table: str,
        partition_value: str,
        event_date: date,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[EventRecord]:
        if table not in EVENT_TABLES:
            raise ValueError(f"Unsupported event table: {table}")
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        definition = EVENT_TABLES[table]
        conditions = [
            f"{definition.partition_column} = %s",
            "event_date = %s",
        ]
        parameters: list[Any] = [partition_value, event_date]
        if start_time is not None:
            conditions.append("event_time >= %s")
            parameters.append(self._utc(start_time))
        if end_time is not None:
            conditions.append("event_time <= %s")
            parameters.append(self._utc(end_time))
        selected_columns = [
            definition.partition_column,
            "event_date",
            "event_time",
            "event_id",
            "event_type",
            "actor_id",
        ]
        if definition.partition_column != "device_id":
            selected_columns.append("device_id")
        selected_columns.extend(["session_id", "source", "payload"])
        query = (
            f"SELECT {', '.join(selected_columns)} FROM {definition.name} WHERE "
            + " AND ".join(conditions)
            + " LIMIT %s"
        )
        parameters.append(limit)
        rows = self._database_manager.cassandra_session.execute(query, parameters)
        records: list[EventRecord] = []
        for row in rows:
            raw_payload = row.payload or "{}"
            records.append(
                EventRecord(
                    table=table,
                    partition_value=getattr(row, definition.partition_column),
                    event_date=row.event_date,
                    event_time=self._utc(row.event_time),
                    event_id=row.event_id,
                    event_type=row.event_type,
                    actor_id=row.actor_id,
                    device_id=getattr(row, "device_id", None),
                    session_id=row.session_id,
                    source=row.source,
                    payload=json.loads(raw_payload),
                )
            )
        return records


__all__ = ["CassandraEventRepository", "EventRecord"]
