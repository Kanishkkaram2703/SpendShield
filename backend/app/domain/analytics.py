"""Domain contracts for deterministic, read-only spending analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

MONEY_QUANTUM = Decimal("0.01")
MAX_ANALYTICS_RANGE = timedelta(days=366)


class AnalyticsInterval(str, Enum):
    """Supported calendar buckets for spending trends."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


def utc_datetime(value: datetime) -> datetime:
    """Normalize API/repository timestamps to timezone-aware UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class AnalyticsPeriod:
    """A bounded half-open UTC interval: ``start_at <= t < end_at``."""

    start_at: datetime
    end_at: datetime

    def __post_init__(self) -> None:
        start = utc_datetime(self.start_at)
        end = utc_datetime(self.end_at)
        if end <= start:
            raise ValueError("Analytics end_at must be after start_at.")
        if end - start > MAX_ANALYTICS_RANGE:
            raise ValueError("Analytics range cannot exceed 366 days.")
        object.__setattr__(self, "start_at", start)
        object.__setattr__(self, "end_at", end)

    @classmethod
    def default(cls, *, now: datetime | None = None) -> "AnalyticsPeriod":
        """Return the deterministic rolling period used when no range is sent."""

        end = utc_datetime(now or datetime.now(timezone.utc))
        return cls(start_at=end - timedelta(days=30), end_at=end)


def money(value: Decimal | int | str) -> Decimal:
    """Quantize an analytics amount without converting it to a binary float."""

    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class SpendingSummary:
    """Aggregated completed spending for one owner and period."""

    total_spending: Decimal
    transaction_count: int
    average_transaction: Decimal
    largest_payment_amount: Decimal | None
    largest_transaction_id: str | None


@dataclass(frozen=True, slots=True)
class CategorySpending:
    """Spending grouped by the category snapshot stored on a transaction."""

    category_id: str | None
    category_name: str | None
    subcategory_id: str | None
    subcategory_name: str | None
    total_spending: Decimal
    transaction_count: int


@dataclass(frozen=True, slots=True)
class MerchantSpending:
    """Spending grouped by the merchant identity captured by a payment."""

    merchant_id: str | None
    merchant_name: str | None
    total_spending: Decimal
    transaction_count: int


@dataclass(frozen=True, slots=True)
class SpendingTrend:
    """One non-empty calendar bucket of completed spending."""

    period_start: datetime
    period_end: datetime
    total_spending: Decimal
    transaction_count: int


@dataclass(frozen=True, slots=True)
class LargestPayment:
    """Safe, read-only projection of a completed payment."""

    transaction_id: str
    amount: Decimal
    currency: str
    merchant_id: str | None
    merchant_name: str | None
    category_id: str | None
    category_name: str | None
    subcategory_id: str | None
    subcategory_name: str | None
    occurred_at: datetime


__all__ = [
    "AnalyticsInterval",
    "AnalyticsPeriod",
    "CategorySpending",
    "LargestPayment",
    "MerchantSpending",
    "SpendingSummary",
    "SpendingTrend",
    "utc_datetime",
]
