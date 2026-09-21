"""MongoDB implementation of the Phase 3 user repository contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.exceptions import DatabaseUnavailableError
from app.db.manager import DatabaseManager
from app.repositories.users import DuplicateUserError, UserRecord, UserRole


class MongoUserRepository:
    """Persist authentication users in MongoDB without leaking driver details."""

    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager
        self._schema_ready = False

    def _collection(self) -> Any:
        if not self._schema_ready:
            self._database_manager.ensure_mongodb_schema()
            self._schema_ready = True
        return self._database_manager.mongo_database["users"]

    @staticmethod
    def _to_mongodb_datetime(value: datetime) -> datetime:
        """Normalize UTC datetimes to BSON's millisecond precision."""

        normalized = (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )
        return normalized.replace(
            microsecond=(normalized.microsecond // 1000) * 1000
        )

    @staticmethod
    def _to_record(document: dict[str, Any]) -> UserRecord:
        def normalized_datetime(value: datetime) -> datetime:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        return UserRecord(
            user_id=str(document["user_id"]),
            email=str(document["email"]),
            password_hash=str(document["password_hash"]),
            role=UserRole(str(document["role"])),
            is_active=bool(document["is_active"]),
            created_at=normalized_datetime(document["created_at"]),
            updated_at=normalized_datetime(document["updated_at"]),
            display_name=document.get("display_name"),
            phone_number=document.get("phone_number"),
        )

    def get_by_email(self, email: str) -> UserRecord | None:
        try:
            document = self._collection().find_one({"email": email})
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return self._to_record(document) if document else None

    def get_by_id(self, user_id: str) -> UserRecord | None:
        try:
            document = self._collection().find_one({"user_id": user_id})
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return self._to_record(document) if document else None

    def create(self, user: UserRecord) -> UserRecord:
        created_at = self._to_mongodb_datetime(user.created_at)
        updated_at = self._to_mongodb_datetime(user.updated_at)
        document = {
            "user_id": user.user_id,
            "email": user.email,
            "password_hash": user.password_hash,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": created_at,
            "updated_at": updated_at,
            "display_name": user.display_name,
            "phone_number": user.phone_number,
        }
        try:
            self._collection().insert_one(document)
        except DuplicateKeyError as exc:
            raise DuplicateUserError(user.email) from exc
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return UserRecord(
            user_id=user.user_id,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            is_active=user.is_active,
            created_at=created_at,
            updated_at=updated_at,
            display_name=user.display_name,
            phone_number=user.phone_number,
        )

    def update(self, user: UserRecord) -> UserRecord:
        try:
            result = self._collection().replace_one(
                {"user_id": user.user_id},
                {
                    "user_id": user.user_id,
                    "email": user.email,
                    "password_hash": user.password_hash,
                    "role": user.role.value,
                    "is_active": user.is_active,
                    "created_at": self._to_mongodb_datetime(user.created_at),
                    "updated_at": self._to_mongodb_datetime(user.updated_at),
                    "display_name": user.display_name,
                    "phone_number": user.phone_number,
                },
            )
            if result.matched_count != 1:
                raise DatabaseUnavailableError()
        except DuplicateKeyError as exc:
            raise DuplicateUserError(user.email) from exc
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return self.get_by_id(user.user_id) or user


__all__ = ["MongoUserRepository"]
