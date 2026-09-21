"""Strict response schemas for read-only spending analytics."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.analytics import (
    AnalyticsPeriod,
    CategorySpending,
    LargestPayment,
    MerchantSpending,
    SpendingSummary,
    SpendingTrend,
)
from app.domain.financial import Account, AccountStatus


class AnalyticsPeriodResponse(BaseModel):
    """Half-open UTC range used for one analytics response."""

    model_config = ConfigDict(extra="forbid")

    start_at: datetime
    end_at: datetime
    timezone: Literal["UTC"] = "UTC"

    @classmethod
    def from_period(cls, period: AnalyticsPeriod) -> "AnalyticsPeriodResponse":
        return cls(start_at=period.start_at, end_at=period.end_at)


class SpendingSummaryResponse(BaseModel):
    """Owner-scoped aggregate of completed transaction spending."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    currency: str
    period: AnalyticsPeriodResponse
    total_spending: Decimal
    transaction_count: int
    average_transaction: Decimal
    largest_payment_amount: Decimal | None
    largest_transaction_id: str | None
    current_balance: Decimal
    account_status: AccountStatus
    calculation_basis: Literal["completed_mongodb_transactions"] = (
        "completed_mongodb_transactions"
    )
    request_id: str

    @classmethod
    def from_values(
        cls,
        *,
        account: Account,
        period: AnalyticsPeriod,
        summary: SpendingSummary,
        request_id: str,
    ) -> "SpendingSummaryResponse":
        return cls(
            currency=account.currency,
            period=AnalyticsPeriodResponse.from_period(period),
            total_spending=summary.total_spending,
            transaction_count=summary.transaction_count,
            average_transaction=summary.average_transaction,
            largest_payment_amount=summary.largest_payment_amount,
            largest_transaction_id=summary.largest_transaction_id,
            current_balance=account.balance,
            account_status=account.status,
            request_id=request_id,
        )


class CategorySpendingItem(BaseModel):
    """One immutable category/subcategory spending group."""

    model_config = ConfigDict(extra="forbid")

    category_id: str | None
    category_name: str | None
    subcategory_id: str | None
    subcategory_name: str | None
    total_spending: Decimal
    transaction_count: int
    share_percent: Decimal

    @classmethod
    def from_value(
        cls, item: CategorySpending, *, share_percent: Decimal
    ) -> "CategorySpendingItem":
        return cls(
            category_id=item.category_id,
            category_name=item.category_name,
            subcategory_id=item.subcategory_id,
            subcategory_name=item.subcategory_name,
            total_spending=item.total_spending,
            transaction_count=item.transaction_count,
            share_percent=share_percent,
        )


class CategorySpendingResponse(BaseModel):
    """Category spending breakdown for one owner and period."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    currency: str
    period: AnalyticsPeriodResponse
    total_spending: Decimal
    categories: list[CategorySpendingItem]
    calculation_basis: Literal["completed_mongodb_transactions"] = (
        "completed_mongodb_transactions"
    )
    request_id: str


class MerchantSpendingItem(BaseModel):
    """One merchant spending group identified by persisted merchant ID."""

    model_config = ConfigDict(extra="forbid")

    merchant_id: str | None
    merchant_name: str | None
    total_spending: Decimal
    transaction_count: int
    share_percent: Decimal

    @classmethod
    def from_value(
        cls, item: MerchantSpending, *, share_percent: Decimal
    ) -> "MerchantSpendingItem":
        return cls(
            merchant_id=item.merchant_id,
            merchant_name=item.merchant_name,
            total_spending=item.total_spending,
            transaction_count=item.transaction_count,
            share_percent=share_percent,
        )


class MerchantSpendingResponse(BaseModel):
    """Merchant spending breakdown for one owner and period."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    currency: str
    period: AnalyticsPeriodResponse
    total_spending: Decimal
    merchants: list[MerchantSpendingItem]
    calculation_basis: Literal["completed_mongodb_transactions"] = (
        "completed_mongodb_transactions"
    )
    request_id: str


class SpendingTrendItem(BaseModel):
    """One UTC calendar bucket of completed spending."""

    model_config = ConfigDict(extra="forbid")

    period_start: datetime
    period_end: datetime
    total_spending: Decimal
    transaction_count: int

    @classmethod
    def from_value(cls, item: SpendingTrend) -> "SpendingTrendItem":
        return cls(
            period_start=item.period_start,
            period_end=item.period_end,
            total_spending=item.total_spending,
            transaction_count=item.transaction_count,
        )


class SpendingTrendResponse(BaseModel):
    """Daily, weekly, or monthly spending trend."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    currency: str
    period: AnalyticsPeriodResponse
    interval: Literal["daily", "weekly", "monthly"]
    trends: list[SpendingTrendItem]
    calculation_basis: Literal["completed_mongodb_transactions"] = (
        "completed_mongodb_transactions"
    )
    request_id: str


class LargestPaymentItem(BaseModel):
    """Safe projection of one completed payment in the requested period."""

    model_config = ConfigDict(extra="forbid")

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

    @classmethod
    def from_value(cls, item: LargestPayment) -> "LargestPaymentItem":
        return cls(
            transaction_id=item.transaction_id,
            amount=item.amount,
            currency=item.currency,
            merchant_id=item.merchant_id,
            merchant_name=item.merchant_name,
            category_id=item.category_id,
            category_name=item.category_name,
            subcategory_id=item.subcategory_id,
            subcategory_name=item.subcategory_name,
            occurred_at=item.occurred_at,
        )


class LargestPaymentsResponse(BaseModel):
    """Bounded largest completed payments response."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    currency: str
    period: AnalyticsPeriodResponse
    payments: list[LargestPaymentItem]
    calculation_basis: Literal["completed_mongodb_transactions"] = (
        "completed_mongodb_transactions"
    )
    request_id: str


__all__ = [
    "AnalyticsPeriodResponse",
    "CategorySpendingItem",
    "CategorySpendingResponse",
    "LargestPaymentItem",
    "LargestPaymentsResponse",
    "MerchantSpendingItem",
    "MerchantSpendingResponse",
    "SpendingSummaryResponse",
    "SpendingTrendItem",
    "SpendingTrendResponse",
]
