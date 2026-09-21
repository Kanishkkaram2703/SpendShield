"""Application exception types used by API error handling."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """An expected, client-safe application error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.headers = headers or {}


class PersistenceNotConfiguredError(AppError):
    """Signal that a real persistence adapter has not been configured yet."""

    def __init__(self) -> None:
        super().__init__(
            code="persistence_not_configured",
            message="User persistence is not configured for this environment.",
            status_code=503,
        )


class AccountPersistenceNotConfiguredError(AppError):
    """Signal that account persistence has not been configured."""

    def __init__(self) -> None:
        super().__init__(
            code="account_persistence_not_configured",
            message="Account persistence is not configured for this environment.",
            status_code=503,
        )


class DatabaseNotConfiguredError(AppError):
    """Signal that a requested database has no configured connection."""

    def __init__(self) -> None:
        super().__init__(
            code="database_not_configured",
            message="Database configuration is not available for this environment.",
            status_code=503,
        )


class DatabaseUnavailableError(AppError):
    """Signal that a configured database cannot currently be reached."""

    def __init__(self) -> None:
        super().__init__(
            code="database_unavailable",
            message="The requested database is temporarily unavailable.",
            status_code=503,
        )


class DemoTransferRequiresReplicaSetError(AppError):
    """Signal that a two-account demo transfer needs MongoDB transactions."""

    def __init__(self) -> None:
        super().__init__(
            code="demo_transfer_requires_replica_set",
            message="Two-account demo transfers require the configured MongoDB replica set.",
            status_code=503,
        )


__all__ = [
    "AccountPersistenceNotConfiguredError",
    "AppError",
    "DatabaseNotConfiguredError",
    "DatabaseUnavailableError",
    "DemoTransferRequiresReplicaSetError",
    "PersistenceNotConfiguredError",
]
