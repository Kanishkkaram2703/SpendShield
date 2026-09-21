"""Authentication business logic independent of persistence technology."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.core.security import (
    TokenManager,
    hash_password,
    verify_password_or_dummy,
)
from app.repositories.users import (
    DuplicateUserError,
    UserRecord,
    UserRepository,
    UserRole,
)

LOGGER = get_logger(__name__)
AUTH_HEADERS = {"WWW-Authenticate": "Bearer"}


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    """Internal result passed from the service to the login route."""

    access_token: str
    expires_in: int
    user: UserRecord


class AuthService:
    """Coordinate registration, login, and access-token issuance."""

    def __init__(self, repository: UserRepository, settings: Settings) -> None:
        self._repository = repository
        self._token_manager = TokenManager(settings)

    @staticmethod
    def normalize_email(email: str) -> str:
        """Normalize the supported identity before repository access."""

        return email.strip().lower()

    def register(self, email: str, password: str) -> UserRecord:
        """Register a normal USER without accepting a client-provided role."""

        normalized_email = self.normalize_email(email)
        LOGGER.info("registration_attempt")
        if self._repository.get_by_email(normalized_email) is not None:
            LOGGER.warning("registration_result result=duplicate_identity")
            raise AppError(
                code="duplicate_identity",
                message="An account with this email already exists.",
                status_code=409,
            )

        now = datetime.now(timezone.utc)
        user = UserRecord(
            user_id=str(uuid4()),
            email=normalized_email,
            password_hash=hash_password(password),
            role=UserRole.USER,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        try:
            created = self._repository.create(user)
        except DuplicateUserError as exc:
            LOGGER.warning("registration_result result=duplicate_identity")
            raise AppError(
                code="duplicate_identity",
                message="An account with this email already exists.",
                status_code=409,
            ) from exc
        LOGGER.info("registration_result result=success")
        return created

    def login(self, email: str, password: str) -> AuthenticationResult:
        """Verify credentials and issue a short-lived access token."""

        normalized_email = self.normalize_email(email)
        user = self._repository.get_by_email(normalized_email)
        password_valid = verify_password_or_dummy(
            password,
            user.password_hash if user is not None else None,
        )
        if user is None or not password_valid or not user.is_active:
            LOGGER.warning("login_result result=failure")
            raise AppError(
                code="invalid_credentials",
                message="Invalid email or password.",
                status_code=401,
                headers=AUTH_HEADERS,
            )

        access_token = self._token_manager.create_access_token(user.user_id)
        LOGGER.info("login_result result=success")
        return AuthenticationResult(
            access_token=access_token,
            expires_in=self._token_manager.expires_in_seconds,
            user=user,
        )

    def update_profile(
        self,
        user: UserRecord,
        *,
        email: str | None = None,
        display_name: str | None = None,
        phone_number: str | None = None,
    ) -> UserRecord:
        next_email = self.normalize_email(email) if email is not None else user.email
        if next_email != user.email:
            existing = self._repository.get_by_email(next_email)
            if existing is not None and existing.user_id != user.user_id:
                raise AppError(code="duplicate_identity", message="An account with this email already exists.", status_code=409)
        updated = replace(
            user,
            email=next_email,
            display_name=display_name,
            phone_number=phone_number,
            updated_at=datetime.now(timezone.utc),
        )
        try:
            return self._repository.update(updated)
        except DuplicateUserError as exc:
            raise AppError(code="duplicate_identity", message="An account with this email already exists.", status_code=409) from exc


__all__ = ["AuthService", "AuthenticationResult"]
