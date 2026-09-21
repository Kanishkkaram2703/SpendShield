"""Public account API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.financial import Account, AccountStatus


class AccountResponse(BaseModel):
    """Safe current account representation."""

    model_config = ConfigDict(extra="forbid")

    account_id: str
    currency: str
    balance: Decimal = Field(ge=0)
    status: AccountStatus
    created_at: datetime
    updated_at: datetime
    version: int = Field(ge=0)
    holder_name: str | None = None
    demo_account_number: str | None = None
    demo_bank_code: str | None = None
    demo_branch: str | None = None
    account_type: str | None = None

    @classmethod
    def from_record(cls, account: Account) -> "AccountResponse":
        return cls(
            account_id=account.account_id,
            currency=account.currency,
            balance=account.balance,
            status=account.status,
            created_at=account.created_at,
            updated_at=account.updated_at,
            version=account.version,
            holder_name=account.holder_name,
            demo_account_number=account.demo_account_number,
            demo_bank_code=account.demo_bank_code,
            demo_branch=account.demo_branch,
            account_type=account.account_type,
        )


class AccountCreateRequest(BaseModel):
    """Optional profile hint for an additional fictional account.

    Balance, owner, currency, identifiers, and status remain server-owned.
    An omitted body is retained as the backwards-compatible first-account
    onboarding request.
    """

    # Older clients accidentally sent client-owned balance/owner fields. They
    # are ignored rather than accepted as authoritative input, preserving the
    # original onboarding contract while keeping those values server-owned.
    model_config = ConfigDict(extra="ignore")

    account_type: str = Field(default="DEMO_SAVINGS", min_length=1, max_length=32)


class AccountListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accounts: list[AccountResponse]


class AccountReferenceResponse(BaseModel):
    """Non-balance account reference used before protected unlock."""

    model_config = ConfigDict(extra="forbid")

    account_id: str
    currency: str
    status: AccountStatus
    account_type: str | None = None
    demo_account_number: str | None = None


class AccountReferenceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accounts: list[AccountReferenceResponse]


class ProtectedAccountAccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    demo_mpin: str = Field(min_length=6, max_length=6)

    @field_validator("demo_mpin")
    @classmethod
    def validate_demo_mpin(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("The demo MPIN must contain six digits.")
        return value


class AccountStatusUpdateRequest(BaseModel):
    """Validated administrator request for an account status transition."""

    model_config = ConfigDict(extra="forbid")

    status: AccountStatus
    expected_version: int | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=256)


__all__ = [
    "AccountCreateRequest",
    "AccountListResponse",
    "AccountReferenceListResponse",
    "AccountReferenceResponse",
    "AccountResponse",
    "AccountStatusUpdateRequest",
    "ProtectedAccountAccessRequest",
]
