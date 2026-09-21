"""Category repository contracts and MongoDB adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.exceptions import DatabaseUnavailableError
from app.db.manager import DatabaseManager
from app.domain.catalog import CategoryRecord


class DuplicateCategoryError(Exception):
    """Raised when a canonical category identity already exists."""


@runtime_checkable
class CategoryRepository(Protocol):
    """Persistence contract for the system-controlled category taxonomy."""

    def get(self, category_id: str, subcategory_id: str) -> CategoryRecord | None:
        """Return one category/subcategory pair."""

    def list(self, *, active_only: bool = True, limit: int = 100) -> tuple[CategoryRecord, ...]:
        """Return a bounded taxonomy listing."""

    def ensure(self, category: CategoryRecord) -> CategoryRecord:
        """Insert one deterministic seed record if it does not exist."""


class UnavailableCategoryRepository:
    """Explicit adapter used when MongoDB is not configured."""

    def get(self, _: str, __: str) -> CategoryRecord | None:
        raise DatabaseUnavailableError()

    def list(self, *, active_only: bool = True, limit: int = 100) -> tuple[CategoryRecord, ...]:
        raise DatabaseUnavailableError()

    def ensure(self, _: CategoryRecord) -> CategoryRecord:
        raise DatabaseUnavailableError()


class MongoCategoryRepository:
    """Store current canonical categories in MongoDB."""

    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager
        self._schema_ready = False

    def _collection(self) -> Any:
        if not self._schema_ready:
            self._database_manager.ensure_mongodb_schema()
            self._schema_ready = True
        return self._database_manager.mongo_database["categories"]

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _mongo_datetime(cls, value: datetime) -> datetime:
        normalized = cls._utc(value)
        return normalized.replace(microsecond=(normalized.microsecond // 1000) * 1000)

    @classmethod
    def _to_record(cls, document: dict[str, Any]) -> CategoryRecord:
        return CategoryRecord(
            category_id=str(document["category_id"]),
            category_name=str(document["category_name"]),
            subcategory_id=str(document["subcategory_id"]),
            subcategory_name=str(document["subcategory_name"]),
            is_active=bool(document["is_active"]),
            created_at=cls._utc(document["created_at"]),
            updated_at=cls._utc(document["updated_at"]),
        )

    def get(self, category_id: str, subcategory_id: str) -> CategoryRecord | None:
        try:
            document = self._collection().find_one(
                {"category_id": category_id, "subcategory_id": subcategory_id}
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return self._to_record(document) if document else None

    def list(
        self,
        *,
        active_only: bool = True,
        limit: int = 100,
    ) -> tuple[CategoryRecord, ...]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        query: dict[str, Any] = {"is_active": True} if active_only else {}
        try:
            documents = list(
                self._collection()
                .find(query)
                .sort([("category_id", 1), ("subcategory_id", 1)])
                .limit(limit)
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return tuple(self._to_record(document) for document in documents)

    def ensure(self, category: CategoryRecord) -> CategoryRecord:
        document = {
            "category_id": category.category_id,
            "category_name": category.category_name,
            "subcategory_id": category.subcategory_id,
            "subcategory_name": category.subcategory_name,
            "is_active": category.is_active,
            "created_at": self._mongo_datetime(category.created_at),
            "updated_at": self._mongo_datetime(category.updated_at),
        }
        try:
            self._collection().update_one(
                {
                    "category_id": category.category_id,
                    "subcategory_id": category.subcategory_id,
                },
                {"$setOnInsert": document},
                upsert=True,
            )
        except DuplicateKeyError:
            pass
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        persisted = self.get(category.category_id, category.subcategory_id)
        if persisted is None:
            raise DatabaseUnavailableError()
        return persisted


__all__ = [
    "CategoryRepository",
    "DuplicateCategoryError",
    "MongoCategoryRepository",
    "UnavailableCategoryRepository",
]
