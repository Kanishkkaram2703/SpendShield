"""API contracts for the fictional, owner-scoped demo modules."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.demo_payments import validate_demo_amount, validate_demo_text
from app.domain.financial import normalize_currency


class ContactCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    phone: str = Field(min_length=7, max_length=32)
    email: str | None = Field(default=None, max_length=256)
    favorite: bool = False
    contact_type: Literal["PERSON", "BUSINESS"] = "PERSON"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return validate_demo_text(value, field_name="Contact name")

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise ValueError("Phone number is invalid.")
        return normalized


class ContactUpdateRequest(ContactCreateRequest):
    pass


class ContactResponse(ContactCreateRequest):
    contact_id: str
    created_at: datetime
    updated_at: datetime


class ContactListResponse(BaseModel):
    contacts: list[ContactResponse]


class BeneficiaryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    account_number: str = Field(min_length=6, max_length=32)
    bank_name: str = Field(default="BJP Bank", min_length=1, max_length=64)
    bank_code: str = Field(default="BJP0DEMO0001", min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=256)
    favorite: bool = False

    @field_validator("name", "bank_name", "bank_code")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return validate_demo_text(value, field_name="Beneficiary field")

    @field_validator("account_number")
    @classmethod
    def clean_account_number(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized.startswith("DEMO-"):
            raise ValueError("Only demo beneficiary accounts are supported.")
        return normalized


class BeneficiaryUpdateRequest(BeneficiaryCreateRequest):
    pass


class BeneficiaryResponse(BeneficiaryCreateRequest):
    beneficiary_id: str
    created_at: datetime
    updated_at: datetime


class BeneficiaryListResponse(BaseModel):
    beneficiaries: list[BeneficiaryResponse]


class BillerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "MOBILE_RECHARGE", "ELECTRICITY", "WATER", "GAS", "INTERNET", "DTH", "POSTPAID", "LOAN_EMI"
    ]
    provider: str = Field(min_length=1, max_length=128)
    identifier: str = Field(min_length=4, max_length=64)
    nickname: str | None = Field(default=None, max_length=64)

    @field_validator("provider", "identifier")
    @classmethod
    def clean_demo_text(cls, value: str) -> str:
        normalized = validate_demo_text(value, field_name="Demo biller field")
        if not normalized.upper().startswith("DEMO"):
            raise ValueError("Only demo billers are supported.")
        return normalized


class BillerUpdateRequest(BillerCreateRequest):
    pass


class BillerResponse(BillerCreateRequest):
    biller_id: str
    created_at: datetime
    updated_at: datetime


class BillerListResponse(BaseModel):
    billers: list[BillerResponse]


class BillPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: UUID
    category: Literal[
        "MOBILE_RECHARGE", "ELECTRICITY", "WATER", "GAS", "INTERNET", "DTH", "POSTPAID", "LOAN_EMI"
    ]
    provider: str = Field(min_length=1, max_length=128)
    identifier: str = Field(min_length=4, max_length=64)
    amount: Decimal = Field(gt=0, max_digits=34, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    note: str | None = Field(default=None, max_length=256)

    @field_validator("provider", "identifier")
    @classmethod
    def clean_bill_text(cls, value: str) -> str:
        normalized = validate_demo_text(value, field_name="Demo bill field")
        if not normalized.upper().startswith("DEMO"):
            raise ValueError("Only demo billers are supported.")
        return normalized

    @field_validator("amount")
    @classmethod
    def clean_amount(cls, value: Decimal) -> Decimal:
        return validate_demo_amount(value)

    @field_validator("currency")
    @classmethod
    def clean_currency(cls, value: str) -> str:
        return normalize_currency(value)


class NotificationResponse(BaseModel):
    notification_id: str
    category: str
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]


class CardResponse(BaseModel):
    card_id: str
    holder_name: str
    masked_card_number: str
    expiry: str
    masked_cvv: str
    status: Literal["ACTIVE", "FROZEN", "BLOCKED"]
    spending_limit: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime


class CardListResponse(BaseModel):
    cards: list[CardResponse]


class CardStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["freeze", "unfreeze", "block"]
    demo_mpin: str = Field(pattern=r"^\d{6}$")


class CardPinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pin: str = Field(min_length=4, max_length=6)
    confirm_pin: str = Field(min_length=4, max_length=6)
    demo_mpin: str = Field(pattern=r"^\d{6}$")

    @field_validator("pin", "confirm_pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not value.isdigit() or len(set(value)) == 1:
            raise ValueError("Demo PIN must contain varied digits.")
        return value


class CardLimitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spending_limit: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    demo_mpin: str = Field(pattern=r"^\d{6}$")

    @field_validator("spending_limit")
    @classmethod
    def validate_limit(cls, value: Decimal) -> Decimal:
        return validate_demo_amount(value)


__all__ = [
    "BeneficiaryCreateRequest", "BeneficiaryListResponse", "BeneficiaryResponse", "BeneficiaryUpdateRequest",
    "BillerCreateRequest", "BillerListResponse", "BillerResponse", "BillerUpdateRequest",
    "BillPaymentRequest",
    "CardListResponse", "CardLimitRequest", "CardPinRequest", "CardResponse", "CardStatusRequest",
    "ContactCreateRequest", "ContactListResponse", "ContactResponse", "ContactUpdateRequest",
    "NotificationListResponse", "NotificationResponse",
]
