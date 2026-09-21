"""Small MongoDB current-state repository for fictional user-owned modules.

These records are operational state only. Historical financial effects remain
transactions in the existing payment repository and events in Cassandra.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.exceptions import DatabaseUnavailableError
from app.db.manager import DatabaseManager


class DuplicateDemoResourceError(Exception):
    """Raised when one owner attempts to create a duplicate demo resource."""


class DemoResourceRepository:
    """Owner-scoped CRUD adapter for cards, billers, contacts, and alerts."""

    def __init__(
        self,
        database_manager: DatabaseManager,
        collection_name: str,
        identifier_field: str = "resource_id",
    ) -> None:
        self._database_manager = database_manager
        self._collection_name = collection_name
        self._identifier_field = identifier_field
        self._schema_ready = False

    def _collection(self) -> Any:
        if not self._schema_ready:
            self._database_manager.ensure_mongodb_schema()
            self._schema_ready = True
        return self._database_manager.mongo_database[self._collection_name]

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def create(self, owner_id: str, values: dict[str, Any]) -> dict[str, Any]:
        now = self._utc(datetime.now(timezone.utc))
        resource_id = values.get(self._identifier_field) or str(uuid4())
        document = {
            **values,
            self._identifier_field: resource_id,
            "user_id": owner_id,
            "created_at": now,
            "updated_at": now,
        }
        try:
            self._collection().insert_one(document)
        except DuplicateKeyError as exc:
            raise DuplicateDemoResourceError(resource_id) from exc
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return document

    def list(self, owner_id: str, *, limit: int = 100) -> tuple[dict[str, Any], ...]:
        try:
            documents = self._collection().find(
                {"user_id": owner_id},
                sort=[("created_at", -1), (self._identifier_field, 1)],
                limit=limit,
            )
            return tuple(documents)
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def get(self, owner_id: str, resource_id: str) -> dict[str, Any] | None:
        try:
            return self._collection().find_one(
                {"user_id": owner_id, self._identifier_field: resource_id}
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def update(
        self,
        owner_id: str,
        resource_id: str,
        values: dict[str, Any],
    ) -> dict[str, Any] | None:
        try:
            result = self._collection().update_one(
                {"user_id": owner_id, self._identifier_field: resource_id},
                {"$set": {**values, "updated_at": datetime.now(timezone.utc)}},
            )
            if result.matched_count != 1:
                return None
            return self.get(owner_id, resource_id)
        except DuplicateKeyError as exc:
            raise DuplicateDemoResourceError(resource_id) from exc
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def delete(self, owner_id: str, resource_id: str) -> bool:
        try:
            result = self._collection().delete_one(
                {"user_id": owner_id, self._identifier_field: resource_id}
            )
            return result.deleted_count == 1
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

    def update_many(self, owner_id: str, values: dict[str, Any]) -> int:
        try:
            result = self._collection().update_many(
                {"user_id": owner_id},
                {"$set": {**values, "updated_at": datetime.now(timezone.utc)}},
            )
            return int(result.modified_count)
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc


__all__ = ["DemoResourceRepository", "DuplicateDemoResourceError"]
