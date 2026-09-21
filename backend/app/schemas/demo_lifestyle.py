"""Contracts for fictional mobile recharge and OTT subscription flows."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.demo_catalog import RechargePlan, SubscriptionPlan, SubscriptionPlatform
from app.domain.demo_payments import validate_demo_amount, validate_optional_note
from app.domain.financial import normalize_currency
from app.schemas.demo_payments import DemoPaymentResponse


class DemoRechargePlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    operator: str
    plan_name: str
    validity_days: int
    data_allowance: str
    calling_benefit: str
    sms_benefit: str
    price: Decimal
    demo_only: Literal[True] = True

    @classmethod
    def from_plan(cls, plan: RechargePlan) -> "DemoRechargePlanResponse":
        return cls.model_validate(asdict(plan) | {"demo_only": True})


class DemoRechargeCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operators: list[str]
    plans: list[DemoRechargePlanResponse]
    request_id: str


class DemoRechargeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: UUID
    operator: Literal["AIRTEL", "JIO", "VI", "BSNL"]
    plan_id: str = Field(min_length=1, max_length=64)
    mobile_number: str = Field(min_length=10, max_length=10)
    currency: str = Field(min_length=3, max_length=3)
    demo_mpin: str | None = Field(default=None, min_length=6, max_length=6)
    note: str | None = Field(default=None, max_length=256)

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 10 or value[0] not in "6789":
            raise ValueError("Enter a valid ten-digit Indian demo mobile number.")
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)

    @field_validator("demo_mpin")
    @classmethod
    def validate_demo_mpin(cls, value: str | None) -> str | None:
        if value is not None and not value.isdigit():
            raise ValueError("The demo MPIN must contain six digits.")
        return value

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        return validate_optional_note(value)


class DemoRechargeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: str
    mobile_number_masked: str
    plan: DemoRechargePlanResponse
    payment: DemoPaymentResponse
    demo_only: Literal[True] = True


class DemoSubscriptionPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    platform_id: str
    plan_name: str
    period: str
    duration_days: int
    price: Decimal
    demo_only: Literal[True] = True

    @classmethod
    def from_plan(cls, plan: SubscriptionPlan) -> "DemoSubscriptionPlanResponse":
        return cls.model_validate(asdict(plan) | {"demo_only": True})


class DemoSubscriptionPlatformResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform_id: str
    platform_name: str
    description: str
    plans: list[DemoSubscriptionPlanResponse]
    demo_only: Literal[True] = True

    @classmethod
    def from_platform(cls, platform: SubscriptionPlatform) -> "DemoSubscriptionPlatformResponse":
        return cls(
            platform_id=platform.platform_id,
            platform_name=platform.platform_name,
            description=platform.description,
            plans=[DemoSubscriptionPlanResponse.from_plan(plan) for plan in platform.plans],
        )


class DemoSubscriptionCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platforms: list[DemoSubscriptionPlatformResponse]
    request_id: str


class DemoSubscriptionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: UUID
    platform_id: str = Field(min_length=1, max_length=32)
    plan_id: str = Field(min_length=1, max_length=64)
    currency: str = Field(min_length=3, max_length=3)
    demo_mpin: str | None = Field(default=None, min_length=6, max_length=6)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)

    @field_validator("demo_mpin")
    @classmethod
    def validate_demo_mpin(cls, value: str | None) -> str | None:
        if value is not None and not value.isdigit():
            raise ValueError("The demo MPIN must contain six digits.")
        return value


class DemoSubscriptionStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["PAUSED", "CANCELLED"]


class DemoSubscriptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subscription_id: str
    platform_id: str
    platform_name: str
    plan_id: str
    plan_name: str
    period: str
    price: Decimal
    currency: str
    status: Literal["ACTIVE", "PAUSED", "CANCELLED"]
    next_billing_date: date
    source_transaction_id: str | None = None
    created_at: datetime
    updated_at: datetime
    demo_only: Literal[True] = True


class DemoSubscriptionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subscriptions: list[DemoSubscriptionResponse]
    request_id: str


__all__ = [
    "DemoRechargeCatalogResponse",
    "DemoRechargePlanResponse",
    "DemoRechargeRequest",
    "DemoRechargeResponse",
    "DemoSubscriptionCatalogResponse",
    "DemoSubscriptionCreateRequest",
    "DemoSubscriptionListResponse",
    "DemoSubscriptionPlanResponse",
    "DemoSubscriptionPlatformResponse",
    "DemoSubscriptionResponse",
    "DemoSubscriptionStatusRequest",
]
