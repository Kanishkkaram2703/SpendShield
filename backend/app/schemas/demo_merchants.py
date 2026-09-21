"""Contracts for the fictional persisted merchant and QR registry."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DemoMerchantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchant_id: str
    merchant_name: str
    category: str
    demo_bank: str
    merchant_account_id: str
    status: Literal["ACTIVE", "INACTIVE"]
    qr_payload: str
    created_at: datetime
    updated_at: datetime


class DemoMerchantListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merchants: list[DemoMerchantResponse]
    request_id: str


class DemoMerchantStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ACTIVE", "INACTIVE"]


__all__ = ["DemoMerchantListResponse", "DemoMerchantResponse", "DemoMerchantStatusRequest"]
