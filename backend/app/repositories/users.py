"""User repository contract and the non-persistent default adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable

from app.core.exceptions import PersistenceNotConfiguredError


class UserRole(str, Enum):
    """Controlled roles defined by the SpendShield product requirements."""

    USER = "USER"
    INVESTIGATOR = "INVESTIGATOR"
    MERCHANT = "MERCHANT"
    ADMIN = "ADMIN"


@dataclass(frozen=True, slots=True)
class UserRecord:
    """Persistence-neutral user representation.

    The fields are deliberately limited to the authentication foundation and
    map cleanly to a future MongoDB document.
    """

    user_id: str
    email: str
    password_hash: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    display_name: str | None = None
    phone_number: str | None = None


class DuplicateUserError(Exception):
    """Raised by a repository when an identity already exists."""


@runtime_checkable
class UserRepository(Protocol):
    """Persistence contract required by the authentication service."""

    def get_by_email(self, email: str) -> UserRecord | None:
        """Return a user by normalized email, if present."""

    def get_by_id(self, user_id: str) -> UserRecord | None:
        """Return a user by stable identifier, if present."""

    def create(self, user: UserRecord) -> UserRecord:
        """Persist and return a new user record."""

    def update(self, user: UserRecord) -> UserRecord:
        """Persist an owner-scoped profile replacement."""


class UnavailableUserRepository:
    """Default adapter until the MongoDB repository is implemented.

    This is intentionally not an in-memory production substitute. It keeps
    the application honest by returning a clear configuration error when an
    authentication operation is attempted without persistence.
    """

    def get_by_email(self, _: str) -> UserRecord | None:
        raise PersistenceNotConfiguredError()

    def get_by_id(self, _: str) -> UserRecord | None:
        raise PersistenceNotConfiguredError()

    def create(self, _: UserRecord) -> UserRecord:
        raise PersistenceNotConfiguredError()

    def update(self, _: UserRecord) -> UserRecord:
        raise PersistenceNotConfiguredError()


__all__ = [
    "DuplicateUserError",
    "UnavailableUserRepository",
    "UserRecord",
    "UserRepository",
    "UserRole",
]
