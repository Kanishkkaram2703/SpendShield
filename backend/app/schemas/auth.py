"""Authentication request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, SecretStr, Field, field_validator

from app.repositories.users import UserRecord, UserRole


class CredentialsRequest(BaseModel):
    """Shared credential validation for registration and login."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: SecretStr

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        """Apply a usable minimum password policy without leaking the value."""

        password = value.get_secret_value()
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters")
        if len(password) > 128:
            raise ValueError("Password must not exceed 128 characters")
        if not password.strip():
            raise ValueError("Password must contain a non-whitespace character")
        return value


class RegisterRequest(CredentialsRequest):
    """Public registration request; role is intentionally not client-controlled."""


class LoginRequest(CredentialsRequest):
    """Login credentials."""


class UserResponse(BaseModel):
    """Safe user representation that excludes password material."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    user_id: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    display_name: str | None = None
    phone_number: str | None = None

    @classmethod
    def from_record(cls, user: UserRecord) -> "UserResponse":
        return cls.model_validate(user)


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    display_name: str | None = Field(default=None, max_length=128)
    phone_number: str | None = Field(default=None, max_length=32)

    @field_validator("display_name", "phone_number")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if any(ord(character) < 32 for character in value):
            raise ValueError("Profile text is invalid.")
        return value or None


class TokenResponse(BaseModel):
    """Successful login response."""

    model_config = ConfigDict(extra="forbid")

    access_token: str
    token_type: Literal["bearer"]
    expires_in: int
    user: UserResponse


__all__ = [
    "CredentialsRequest",
    "LoginRequest",
    "ProfileUpdateRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
]
