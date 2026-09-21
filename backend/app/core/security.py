"""Password and access-token security primitives."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings
from app.core.exceptions import AppError

PASSWORD_HASHER = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash("SpendShield dummy password")


def hash_password(password: str) -> str:
    """Hash a password using the recommended Argon2 configuration."""

    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a password hash without exposing details."""

    try:
        return PASSWORD_HASHER.verify(password, password_hash)
    except (TypeError, ValueError):
        return False


def verify_password_or_dummy(password: str, password_hash: str | None) -> bool:
    """Perform a password-hash verification even when the user is unknown."""

    return verify_password(password, password_hash or _DUMMY_PASSWORD_HASH)


class TokenManager:
    """Create and validate short-lived signed access tokens."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def expires_in_seconds(self) -> int:
        """Return the configured access-token lifetime in seconds."""

        return self._settings.auth_access_token_expire_minutes * 60

    def _secret(self) -> str:
        secret = self._settings.auth_secret_key
        if not secret or len(secret) < 32:
            raise AppError(
                code="authentication_not_configured",
                message="Authentication is not configured for this environment.",
                status_code=503,
            )
        return secret

    def create_access_token(
        self,
        user_id: str,
        *,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create an access token containing only non-sensitive identifiers."""

        now = datetime.now(timezone.utc)
        expires_at = now + (
            expires_delta
            if expires_delta is not None
            else timedelta(seconds=self.expires_in_seconds)
        )
        payload = {
            "sub": user_id,
            "jti": str(uuid4()),
            "iat": now,
            "exp": expires_at,
            "token_type": "access",
            "iss": self._settings.auth_issuer,
            "aud": self._settings.auth_audience,
        }
        return jwt.encode(
            payload,
            self._secret(),
            algorithm=self._settings.auth_algorithm,
        )

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """Validate signature, expiry, required claims, and token purpose."""

        try:
            payload = jwt.decode(
                token,
                self._secret(),
                algorithms=[self._settings.auth_algorithm],
                audience=self._settings.auth_audience,
                issuer=self._settings.auth_issuer,
                options={
                    "require": ["sub", "jti", "iat", "exp", "token_type"]
                },
            )
        except jwt.PyJWTError as exc:
            raise AppError(
                code="invalid_token",
                message="The authentication token is invalid or expired.",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if payload.get("token_type") != "access":
            raise AppError(
                code="invalid_token",
                message="The authentication token is invalid or expired.",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            raise AppError(
                code="invalid_token",
                message="The authentication token is invalid or expired.",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload


__all__ = [
    "PASSWORD_HASHER",
    "TokenManager",
    "hash_password",
    "verify_password",
    "verify_password_or_dummy",
]
