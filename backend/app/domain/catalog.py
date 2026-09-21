"""Merchant and controlled-category domain objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from app.domain.financial import FinancialDomainError

CATALOG_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
MAX_DISPLAY_NAME_LENGTH = 160


class MerchantStatus(str, Enum):
    """Current merchant lifecycle states owned by MongoDB."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class MerchantDomainError(FinancialDomainError):
    """Base class for merchant/category rule failures."""


class InvalidMerchantStatusTransitionError(MerchantDomainError):
    """Raised when a merchant lifecycle transition is not allowed."""


VALID_MERCHANT_STATUS_TRANSITIONS: dict[
    MerchantStatus, frozenset[MerchantStatus]
] = {
    MerchantStatus.ACTIVE: frozenset({MerchantStatus.INACTIVE}),
    MerchantStatus.INACTIVE: frozenset({MerchantStatus.ACTIVE}),
}


def normalize_catalog_id(value: str, *, field_name: str) -> str:
    """Normalize one stable taxonomy identifier without accepting free text."""

    normalized = value.strip().lower()
    if not CATALOG_ID_PATTERN.fullmatch(normalized):
        raise MerchantDomainError(
            f"{field_name} must use a lowercase stable catalog identifier."
        )
    return normalized


def normalize_display_name(value: str, *, field_name: str) -> str:
    """Normalize a human-readable catalog or merchant name."""

    normalized = " ".join(value.split())
    if not normalized or len(normalized) > MAX_DISPLAY_NAME_LENGTH:
        raise MerchantDomainError(
            f"{field_name} must contain 1 to {MAX_DISPLAY_NAME_LENGTH} characters."
        )
    return normalized


@dataclass(frozen=True, slots=True)
class CategoryRecord:
    """One canonical category/subcategory pair."""

    category_id: str
    category_name: str
    subcategory_id: str
    subcategory_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "category_id",
            normalize_catalog_id(self.category_id, field_name="Category ID"),
        )
        object.__setattr__(
            self,
            "subcategory_id",
            normalize_catalog_id(
                self.subcategory_id, field_name="Subcategory ID"
            ),
        )
        object.__setattr__(
            self,
            "category_name",
            normalize_display_name(self.category_name, field_name="Category name"),
        )
        object.__setattr__(
            self,
            "subcategory_name",
            normalize_display_name(
                self.subcategory_name, field_name="Subcategory name"
            ),
        )


@dataclass(frozen=True, slots=True)
class MerchantRecord:
    """Current authoritative merchant state."""

    merchant_id: str
    merchant_name: str
    category_id: str
    subcategory_id: str
    status: MerchantStatus
    created_at: datetime
    updated_at: datetime
    version: int = 0

    def __post_init__(self) -> None:
        if not self.merchant_id.strip():
            raise MerchantDomainError("Merchant identifier is required.")
        object.__setattr__(
            self,
            "merchant_name",
            normalize_display_name(self.merchant_name, field_name="Merchant name"),
        )
        object.__setattr__(
            self,
            "category_id",
            normalize_catalog_id(self.category_id, field_name="Category ID"),
        )
        object.__setattr__(
            self,
            "subcategory_id",
            normalize_catalog_id(
                self.subcategory_id, field_name="Subcategory ID"
            ),
        )
        if self.version < 0:
            raise MerchantDomainError("Merchant version cannot be negative.")

    def transition_status(
        self,
        new_status: MerchantStatus,
        *,
        at: datetime,
    ) -> "MerchantRecord":
        """Return the next merchant state after a valid lifecycle transition."""

        if new_status is self.status:
            return self
        if new_status not in VALID_MERCHANT_STATUS_TRANSITIONS[self.status]:
            raise InvalidMerchantStatusTransitionError(
                f"Cannot transition {self.status} to {new_status}."
            )
        return replace(
            self,
            status=new_status,
            updated_at=at,
            version=self.version + 1,
        )

    def update_details(
        self,
        *,
        merchant_name: str | None = None,
        category_id: str | None = None,
        subcategory_id: str | None = None,
        at: datetime,
    ) -> "MerchantRecord":
        """Return a versioned current-state update."""

        return replace(
            self,
            merchant_name=(
                self.merchant_name if merchant_name is None else merchant_name
            ),
            category_id=self.category_id if category_id is None else category_id,
            subcategory_id=(
                self.subcategory_id
                if subcategory_id is None
                else subcategory_id
            ),
            updated_at=at,
            version=self.version + 1,
        )


@dataclass(frozen=True, slots=True)
class MerchantResolution:
    """Validated merchant plus the category snapshot used by a payment."""

    merchant: MerchantRecord
    category: CategoryRecord


__all__ = [
    "CATALOG_ID_PATTERN",
    "CategoryRecord",
    "InvalidMerchantStatusTransitionError",
    "MerchantDomainError",
    "MerchantRecord",
    "MerchantResolution",
    "MerchantStatus",
    "VALID_MERCHANT_STATUS_TRANSITIONS",
    "normalize_catalog_id",
    "normalize_display_name",
]
