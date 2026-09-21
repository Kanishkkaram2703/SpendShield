"""Demo-only MPIN contracts; never used as production authentication."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DemoSecurityStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    locked: bool
    failed_attempts: int
    demo_only: bool = True


class DemoMpinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pin: str = Field(min_length=6, max_length=6)
    confirm_pin: str = Field(min_length=6, max_length=6)
    current_pin: str | None = Field(default=None, min_length=6, max_length=6)

    @field_validator("pin", "confirm_pin", "current_pin")
    @classmethod
    def validate_pin(cls, value: str | None) -> str | None:
        if value is not None and not value.isdigit():
            raise ValueError("The demo MPIN must contain six digits.")
        return value


class DemoMpinVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pin: str = Field(min_length=6, max_length=6)

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("The demo MPIN must contain six digits.")
        return value


class DemoMpinResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=256)


__all__ = ["DemoMpinRequest", "DemoMpinResetRequest", "DemoMpinVerifyRequest", "DemoSecurityStatusResponse"]
