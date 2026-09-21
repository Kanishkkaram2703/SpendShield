"""Common API response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Deterministic process health response."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: str


class ErrorDetail(BaseModel):
    """Safe, structured error details returned to API clients."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Consistent API error envelope."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


class DependencyCheck(BaseModel):
    """Safe health status for one configured external dependency."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "not_configured", "unavailable"]
    detail: str
    endpoint: str | None = None
    replica_set: str | None = None
    is_writable_primary: bool | None = None


class DependenciesHealthResponse(BaseModel):
    """Dependency readiness status; separate from process liveness."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded"]
    checks: dict[str, DependencyCheck]


__all__ = [
    "DependenciesHealthResponse",
    "DependencyCheck",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
]
