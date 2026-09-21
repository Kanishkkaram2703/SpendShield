"""Public merchant and controlled-category API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.catalog import CategoryRecord, MerchantResolution, MerchantStatus


class CategoryResponse(BaseModel):
    """Safe canonical category representation."""

    model_config = ConfigDict(extra="forbid")

    category_id: str
    category_name: str
    subcategory_id: str
    subcategory_name: str
    is_active: bool

    @classmethod
    def from_record(cls, category: CategoryRecord) -> "CategoryResponse":
        return cls(
            category_id=category.category_id,
            category_name=category.category_name,
            subcategory_id=category.subcategory_id,
            subcategory_name=category.subcategory_name,
            is_active=category.is_active,
        )


class CategoryListResponse(BaseModel):
    """Bounded canonical taxonomy response."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    categories: list[CategoryResponse]
    request_id: str


class MerchantCreateRequest(BaseModel):
    """Administrator-controlled merchant creation fields."""

    model_config = ConfigDict(extra="forbid")

    merchant_name: str = Field(min_length=1, max_length=160)
    category_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    subcategory_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
    )


class MerchantUpdateRequest(BaseModel):
    """Administrator-controlled, version-checked merchant update."""

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=0)
    merchant_name: str | None = Field(default=None, min_length=1, max_length=160)
    category_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    subcategory_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    status: MerchantStatus | None = None

    @model_validator(mode="after")
    def require_update_field(self) -> "MerchantUpdateRequest":
        if all(
            value is None
            for value in (
                self.merchant_name,
                self.category_id,
                self.subcategory_id,
                self.status,
            )
        ):
            raise ValueError("At least one merchant field must be updated.")
        if (self.category_id is None) != (self.subcategory_id is None):
            raise ValueError(
                "Category ID and subcategory ID must be updated together."
            )
        return self


class MerchantResponse(BaseModel):
    """Safe current merchant representation."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    merchant_id: UUID
    merchant_name: str
    status: MerchantStatus
    category: CategoryResponse
    version: int
    created_at: datetime
    updated_at: datetime
    request_id: str

    @classmethod
    def from_resolution(
        cls,
        resolution: MerchantResolution,
        *,
        request_id: str,
    ) -> "MerchantResponse":
        merchant = resolution.merchant
        return cls(
            merchant_id=UUID(merchant.merchant_id),
            merchant_name=merchant.merchant_name,
            status=merchant.status,
            category=CategoryResponse.from_record(resolution.category),
            version=merchant.version,
            created_at=merchant.created_at,
            updated_at=merchant.updated_at,
            request_id=request_id,
        )


class MerchantListItem(BaseModel):
    """Safe merchant representation inside a list response."""

    model_config = ConfigDict(extra="forbid")

    merchant_id: UUID
    merchant_name: str
    status: MerchantStatus
    category: CategoryResponse
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_resolution(cls, resolution: MerchantResolution) -> "MerchantListItem":
        merchant = resolution.merchant
        return cls(
            merchant_id=UUID(merchant.merchant_id),
            merchant_name=merchant.merchant_name,
            status=merchant.status,
            category=CategoryResponse.from_record(resolution.category),
            version=merchant.version,
            created_at=merchant.created_at,
            updated_at=merchant.updated_at,
        )


class MerchantListResponse(BaseModel):
    """Bounded, stable merchant listing response."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    merchants: list[MerchantListItem]
    next_cursor: str | None
    request_id: str


__all__ = [
    "CategoryListResponse",
    "CategoryResponse",
    "MerchantCreateRequest",
    "MerchantListItem",
    "MerchantListResponse",
    "MerchantResponse",
    "MerchantUpdateRequest",
]
