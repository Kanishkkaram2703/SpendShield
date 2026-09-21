"""Account repository contracts and MongoDB adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable
from bson.decimal128 import Decimal128
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.exceptions import (
    AccountPersistenceNotConfiguredError,
    DatabaseUnavailableError,
)
from app.db.manager import DatabaseManager
from app.domain.financial import Account, AccountStatus


class DuplicateAccountError(Exception):
    """Raised when an owner already has an account."""


class AccountVersionConflictError(Exception):
    """Raised when current account state changed before an update completed."""


@runtime_checkable
class AccountRepository(Protocol):
    """Persistence contract for current account state."""

    def create(self, account: Account, *, allow_duplicate_owner: bool = False) -> Account:
        """Persist and return an account."""

    def get_by_id(self, account_id: str) -> Account | None:
        """Return an account by public identifier."""

    def get_by_owner(self, owner_id: str) -> Account | None:
        """Return the owner's current account, if one exists."""

    def list_by_owner(self, owner_id: str) -> tuple[Account, ...]:
        """Return all current accounts owned by one user."""

    def update(self, account: Account, *, expected_version: int) -> Account | None:
        """Persist one version-checked current-state replacement."""


class UnavailableAccountRepository:
    """Explicit non-production adapter when MongoDB is not configured."""

    def create(self, _: Account, *, allow_duplicate_owner: bool = False) -> Account:
        raise AccountPersistenceNotConfiguredError()

    def get_by_id(self, _: str) -> Account | None:
        raise AccountPersistenceNotConfiguredError()

    def get_by_owner(self, _: str) -> Account | None:
        raise AccountPersistenceNotConfiguredError()

    def list_by_owner(self, _: str) -> tuple[Account, ...]:
        raise AccountPersistenceNotConfiguredError()

    def update(self, _: Account, *, expected_version: int) -> Account | None:
        raise AccountPersistenceNotConfiguredError()


class MongoAccountRepository:
    """Persist current account state in the existing MongoDB accounts collection."""

    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager
        self._schema_ready = False

    def _collection(self) -> Any:
        if not self._schema_ready:
            self._database_manager.ensure_mongodb_schema()
            self._schema_ready = True
        return self._database_manager.mongo_database["accounts"]

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _to_mongodb_datetime(value: datetime) -> datetime:
        """Normalize UTC datetimes to BSON's millisecond precision."""

        normalized = MongoAccountRepository._utc(value)
        return normalized.replace(microsecond=(normalized.microsecond // 1000) * 1000)

    @staticmethod
    def _to_record(document: dict[str, Any]) -> Account:
        raw_balance = document["balance"]
        balance = (
            raw_balance.to_decimal()
            if isinstance(raw_balance, Decimal128)
            else Decimal(str(raw_balance))
        )
        return Account(
            account_id=str(document["account_id"]),
            owner_id=str(document["user_id"]),
            currency=str(document["currency"]),
            balance=balance,
            status=AccountStatus(str(document["status"])),
            created_at=MongoAccountRepository._utc(document["created_at"]),
            updated_at=MongoAccountRepository._utc(document["updated_at"]),
            version=int(document.get("version", 0)),
            holder_name=document.get("holder_name"),
            demo_account_number=document.get("demo_account_number"),
            demo_bank_code=document.get("demo_bank_code"),
            demo_branch=document.get("demo_branch"),
            account_type=document.get("account_type"),
        )

    def create(self, account: Account, *, allow_duplicate_owner: bool = False) -> Account:
        created_at = self._to_mongodb_datetime(account.created_at)
        updated_at = self._to_mongodb_datetime(account.updated_at)
        document = {
            "account_id": account.account_id,
            "user_id": account.owner_id,
            "currency": account.currency,
            "balance": Decimal128(account.balance),
            "status": account.status.value,
            "created_at": created_at,
            "updated_at": updated_at,
            "version": account.version,
            "holder_name": account.holder_name,
            "demo_account_number": account.demo_account_number,
            "demo_bank_code": account.demo_bank_code,
            "demo_branch": account.demo_branch,
            "account_type": account.account_type,
        }
        try:
            if not allow_duplicate_owner and self._collection().find_one(
                {"user_id": account.owner_id}, {"_id": 1}
            ) is not None:
                raise DuplicateAccountError(account.owner_id)
            self._collection().insert_one(document)
        except DuplicateKeyError as exc:
            raise DuplicateAccountError(account.owner_id) from exc
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return Account(
            account_id=account.account_id,
            owner_id=account.owner_id,
            currency=account.currency,
            balance=account.balance,
            status=account.status,
            created_at=created_at,
            updated_at=updated_at,
            version=account.version,
            holder_name=account.holder_name,
            demo_account_number=account.demo_account_number,
            demo_bank_code=account.demo_bank_code,
            demo_branch=account.demo_branch,
            account_type=account.account_type,
        )

    def get_by_id(self, account_id: str) -> Account | None:
        try:
            document = self._collection().find_one({"account_id": account_id})
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return self._to_record(document) if document else None

    def get_by_owner(self, owner_id: str) -> Account | None:
        try:
            document = self._collection().find_one(
                {"user_id": owner_id},
                sort=[("created_at", 1), ("account_id", 1)],
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return self._to_record(document) if document else None

    def list_by_owner(self, owner_id: str) -> tuple[Account, ...]:
        try:
            documents = self._collection().find(
                {"user_id": owner_id},
                sort=[("created_at", 1), ("account_id", 1)],
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        return tuple(self._to_record(document) for document in documents)

    def update(self, account: Account, *, expected_version: int) -> Account | None:
        """Replace current account fields only when its version is unchanged."""

        document = {
            "currency": account.currency,
            "balance": Decimal128(account.balance),
            "status": account.status.value,
            "created_at": self._to_mongodb_datetime(account.created_at),
            "updated_at": self._to_mongodb_datetime(account.updated_at),
            "version": account.version,
        }
        try:
            result = self._collection().update_one(
                {
                    "account_id": account.account_id,
                    "version": expected_version,
                },
                {"$set": document},
            )
        except PyMongoError as exc:
            raise DatabaseUnavailableError() from exc
        if result.matched_count != 1:
            raise AccountVersionConflictError(account.account_id)
        return self.get_by_id(account.account_id)


__all__ = [
    "AccountRepository",
    "AccountVersionConflictError",
    "DuplicateAccountError",
    "MongoAccountRepository",
    "UnavailableAccountRepository",
]
