"""Merchant repository contracts and MongoDB adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.exceptions import DatabaseUnavailableError
from app.db.manager import DatabaseManager
from app.domain.catalog import MerchantRecord, MerchantStatus


class DuplicateMerchantError(Exception):
    """Raised when a merchant identifier already exists."""


class MerchantVersionConflictError(Exception):
    """Raised when a concurrent merchant update wins the compare-and-set race."""


class MerchantCursorError(ValueError):
    """Raised when a merchant listing cursor is not available."""


@dataclass(frozen=True, slots=True)
class MerchantPage:
    """One bounded, stable merchant listing page."""

    items: tuple[MerchantRecord, ...]
    next_cursor: str | None


@runtime_checkable
class MerchantRepository(Protocol):
    """Persistence contract for current merchant state."""

    def create(self, merchant: MerchantRecord) -> MerchantRecord:
        """Create one merchant."""

    def get_by_id(self, merchant_id: str) -> MerchantRecord | None:
        """Return one current merchant."""

    def update(
        self,
        merchant: MerchantRecord,
        *,
        expected_version: int,
    ) -> MerchantRecord | None:
        """Persist one version-checked current-state replacement."""

    def list(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: MerchantStatus | None = None,
        category_id: str | None = None,
        subcategory_id: str | None = None,
    ) -> MerchantPage:
        """Return one bounded stable page of merchants."""


class UnavailableMerchantRepository:
    """Explicit adapter used when MongoDB is not configured."""

    def create(self, _: MerchantRecord) -> MerchantRecord:
        raise DatabaseUnavailableError()

    def get_by_id(self, _: str) -> MerchantRecord | None:
        raise DatabaseUnavailableError()

    def update(
        self,
        _: MerchantRecord,
        *,
        expected_version: int,
    ) -> MerchantRecord | None:
        raise DatabaseUnavailableError()

    def list(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: MerchantStatus | None = None,
        category_id: str | None = None,
        subcategory_id: str | None = None,
    ) -> MerchantPage:
        raise DatabaseUnavailableError()


class MongoMerchantRepository:
    """Store current merchant state in the existing MongoDB operational store."""

    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager
        self._schema_ready = False

    def _collection(self) -> Any:
        if not self._schema_ready:
            self._database_manager.ensure_mongodb_schema()
            self._schema_ready = True
        return self._database_manager.mongo_database["merchants"]

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _mongo_datetime(cls, value: datetime) -> datetime:
        normalized = cls._utc(value)
        return normalized.replace(microsecond=(normalized.microsecond // 1000) * 1000)

    @staticmethod
    def _name_key(value: str) -> str:
        return " ".join(value.casefold().split())

    @classmethod
    def _to_record(cls, document: dict[str, Any]) -> MerchantRecord:
        return MerchantRecord(
            merchant_id=str(document["merchant_id"]),
            merchant_name=str(document["merchant_name"]),
            category_id=str(document["category_id"]),
            subcategory_id=str(document["subcategory_id"]),
            status=MerchantStatus(str(document["status"])),
            created_at=cls._utc(document["created_at"]),
            updated_at=cls._utc(document["updated_at"]),
            version=int(document.get("version", 0)),
        )

    @classmethod
    def _document(cls, merchant: MerchantRecord) -> dict[str, Any]:
        return {
            "merchant_id": merchant.merchant_id,
            "merchant_name": merchant.merchant_name,
            "merchant_name_key": cls._name_key(merchant.merchant_name),
            "category_id": merchant.category_id,
            "subcategory_id": merchant.subcategory_id,
            "status": merchant.status.value,
            "created_at": cls._mongo_datetime(merchant.created_at),
            "updated_at": cls._mongo_datetime(merchant.updated_at),
            "version": merchant.version,
        }

    def create(self, merchant: MerchantRecord) -> MerchantRecord:
        try:
            self._collection().insert_one(self._document(merchant))
        except DuplicateKeyError as exc:
            raise DuplicateMerchantError(merchant.merchant_id) from exc
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return self.get_by_id(merchant.merchant_id) or merchant

    def get_by_id(self, merchant_id: str) -> MerchantRecord | None:
        try:
            document = self._collection().find_one({"merchant_id": merchant_id})
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return self._to_record(document) if document else None

    def update(
        self,
        merchant: MerchantRecord,
        *,
        expected_version: int,
    ) -> MerchantRecord | None:
        document = self._document(merchant)
        document.pop("merchant_id", None)
        try:
            result = self._collection().update_one(
                {
                    "merchant_id": merchant.merchant_id,
                    "version": expected_version,
                },
                {"$set": document},
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        if result.matched_count != 1:
            current = self.get_by_id(merchant.merchant_id)
            if current is not None:
                raise MerchantVersionConflictError(merchant.merchant_id)
            return None
        return self.get_by_id(merchant.merchant_id)

    def list(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: MerchantStatus | None = None,
        category_id: str | None = None,
        subcategory_id: str | None = None,
    ) -> MerchantPage:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        query: dict[str, Any] = {}
        if status is not None:
            query["status"] = status.value
        if category_id is not None:
            query["category_id"] = category_id
        if subcategory_id is not None:
            query["subcategory_id"] = subcategory_id

        try:
            if cursor is not None:
                cursor_document = self._collection().find_one(
                    {"merchant_id": cursor},
                    {"merchant_id": 1, "merchant_name_key": 1},
                )
                if cursor_document is None:
                    raise MerchantCursorError()
                cursor_name_key = str(cursor_document.get("merchant_name_key", ""))
                query["$or"] = [
                    {"merchant_name_key": {"$gt": cursor_name_key}},
                    {
                        "merchant_name_key": cursor_name_key,
                        "merchant_id": {"$gt": cursor},
                    },
                ]
            documents = list(
                self._collection()
                .find(query)
                .sort([("merchant_name_key", ASCENDING), ("merchant_id", ASCENDING)])
                .limit(limit + 1)
            )
        except MerchantCursorError:
            raise
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc

        has_more = len(documents) > limit
        page_documents = documents[:limit]
        return MerchantPage(
            items=tuple(self._to_record(document) for document in page_documents),
            next_cursor=(
                str(page_documents[-1]["merchant_id"])
                if has_more and page_documents
                else None
            ),
        )


__all__ = [
    "DuplicateMerchantError",
    "MerchantCursorError",
    "MerchantPage",
    "MerchantRepository",
    "MerchantVersionConflictError",
    "MongoMerchantRepository",
    "UnavailableMerchantRepository",
]
