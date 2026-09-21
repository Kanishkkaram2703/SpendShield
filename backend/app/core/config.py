"""Typed environment-backed configuration for the backend foundation."""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings shared by the backend process.

    Database settings are kept in the application configuration layer so the
    connection manager can initialize external systems without leaking driver
    details into routes or services.
    """

    app_name: str = Field(default="SpendShield Backend")
    app_version: str = Field(default="0.1.0")
    environment: Literal["development", "test", "staging", "production"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    api_prefix: str = Field(default="/api/v1")
    log_level: str = Field(default="INFO")
    # ALLOWED_HOSTS is the current name. TRUSTED_HOSTS remains supported for
    # existing deployments and test callers.
    allowed_hosts: str | None = Field(default=None)
    trusted_hosts: str | None = Field(default=None)

    mongodb_uri: str | None = Field(default=None)
    mongodb_database: str = Field(default="spendshield")
    mongodb_replica_set: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z][A-Za-z0-9_-]*$",
    )
    mongodb_server_selection_timeout_ms: int = Field(
        default=2000, ge=250, le=30000
    )
    mongodb_connect_timeout_ms: int = Field(default=2000, ge=250, le=30000)
    cassandra_hosts: str | None = Field(default=None)
    cassandra_port: int = Field(default=9042)
    cassandra_keyspace: str = Field(
        default="spendshield_events",
        min_length=1,
        max_length=48,
        pattern=r"^[A-Za-z][A-Za-z0-9_]*$",
    )
    cassandra_username: str | None = Field(default=None)
    cassandra_password: str | None = Field(default=None)
    cassandra_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    cassandra_replication_factor: int = Field(default=1, ge=1, le=10)

    auth_secret_key: str | None = Field(default=None)
    auth_algorithm: Literal["HS256"] = Field(default="HS256")
    auth_access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    auth_issuer: str = Field(default="spendshield-api", min_length=1, max_length=128)
    auth_audience: str = Field(
        default="spendshield-client", min_length=1, max_length=128
    )
    account_initial_balance: Decimal = Field(default=Decimal("10000.00"), ge=0)
    account_currency: str = Field(default="INR", min_length=3, max_length=3)
    evidence_storage_path: str | None = Field(default=None)
    research_anomaly_artifact_path: str = Field(
        default="data/synthetic/anomaly_detection/v2",
        min_length=1,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SPENDSHIELD_",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        """Require an absolute path and normalize a trailing slash."""

        prefix = value.strip()
        if not prefix.startswith("/"):
            raise ValueError("API_PREFIX must start with '/'")
        if len(prefix) > 1 and prefix.endswith("/"):
            prefix = prefix.rstrip("/")
        return prefix

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Accept only standard-library logging levels."""

        level = value.strip().upper()
        allowed_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if level not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed_levels)}")
        return level

    @field_validator("account_currency")
    @classmethod
    def validate_account_currency(cls, value: str) -> str:
        """Normalize the fictional account currency to an ISO-style code."""

        currency = value.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("ACCOUNT_CURRENCY must be a three-letter code")
        return currency

    @field_validator("auth_secret_key")
    @classmethod
    def validate_auth_secret_key(cls, value: str | None) -> str | None:
        """Normalize optional secrets and reject weak configured values."""

        if value is None:
            return None
        secret = value.strip()
        if not secret:
            return None
        if len(secret) < 32:
            raise ValueError("AUTH_SECRET_KEY must contain at least 32 characters")
        return secret

    @model_validator(mode="after")
    def validate_runtime_security(self) -> "Settings":
        """Reject unsafe production defaults before the app can start."""

        if self.environment in {"staging", "production"}:
            if self.debug:
                raise ValueError("DEBUG must be false outside development and tests")
            if not self.auth_secret_key or self.auth_secret_key.startswith(
                "change-this-"
            ):
                raise ValueError(
                    "AUTH_SECRET_KEY must be a real secret outside development and tests"
                )
            if not self.trusted_host_list:
                raise ValueError(
                    "ALLOWED_HOSTS (or legacy TRUSTED_HOSTS) must be configured "
                    "outside development and tests"
                )
            if "*" in self.trusted_host_list:
                raise ValueError(
                    "Wildcard allowed hosts are not permitted outside development"
                )
        return self

    @property
    def trusted_host_list(self) -> list[str]:
        """Return normalized host allowlist entries."""

        configured_hosts = (
            self.allowed_hosts
            if (self.allowed_hosts or "").strip()
            else self.trusted_hosts
        )
        return [
            host.strip()
            for host in (configured_hosts or "").split(",")
            if host.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache process settings."""

    return Settings()


__all__ = ["Settings", "get_settings"]
