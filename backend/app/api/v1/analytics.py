"""Authenticated, read-only spending analytics API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.dependencies import get_analytics_service, get_current_user
from app.core.exceptions import AppError
from app.domain.analytics import AnalyticsInterval, AnalyticsPeriod
from app.repositories.users import UserRecord
from app.schemas.analytics import (
    CategorySpendingItem,
    CategorySpendingResponse,
    LargestPaymentItem,
    LargestPaymentsResponse,
    MerchantSpendingItem,
    MerchantSpendingResponse,
    SpendingSummaryResponse,
    SpendingTrendItem,
    SpendingTrendResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _period(
    start_at: datetime | None,
    end_at: datetime | None,
) -> AnalyticsPeriod:
    """Resolve an optional half-open UTC range with bounded defaults."""

    if start_at is None and end_at is None:
        return AnalyticsPeriod.default()
    end = end_at or datetime.now().astimezone()
    start = start_at or AnalyticsPeriod.default(now=end).start_at
    try:
        return AnalyticsPeriod(start_at=start, end_at=end)
    except ValueError as exc:
        raise AppError(
            code="invalid_analytics_period",
            message="The analytics time range is invalid or exceeds 366 days.",
            status_code=422,
        ) from exc


StartAt = Annotated[
    datetime | None,
    Query(
        description="Inclusive UTC range start. Naive timestamps are interpreted as UTC.",
    ),
]
EndAt = Annotated[
    datetime | None,
    Query(
        description="Exclusive UTC range end. Naive timestamps are interpreted as UTC.",
    ),
]


@router.get("/spending/summary", response_model=SpendingSummaryResponse)
def spending_summary(
    request: Request,
    start_at: StartAt = None,
    end_at: EndAt = None,
    user: UserRecord = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> SpendingSummaryResponse:
    """Return current balance and completed spending totals for the owner."""

    period = _period(start_at, end_at)
    account, summary = service.spending_summary(user.user_id, period=period)
    return SpendingSummaryResponse.from_values(
        account=account,
        period=period,
        summary=summary,
        request_id=request.state.request_id,
    )


@router.get("/spending/categories", response_model=CategorySpendingResponse)
def category_spending(
    request: Request,
    start_at: StartAt = None,
    end_at: EndAt = None,
    limit: int = Query(default=100, ge=1, le=100),
    user: UserRecord = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> CategorySpendingResponse:
    """Return spending grouped by payment-time category snapshots."""

    period = _period(start_at, end_at)
    account, total, items = service.category_breakdown(
        user.user_id,
        period=period,
        limit=limit,
    )
    return CategorySpendingResponse(
        currency=account.currency,
        period={"start_at": period.start_at, "end_at": period.end_at},
        total_spending=total,
        categories=[
            CategorySpendingItem.from_value(
                item,
                share_percent=service.share_percent(item.total_spending, total),
            )
            for item in items
        ],
        request_id=request.state.request_id,
    )


@router.get("/spending/merchants", response_model=MerchantSpendingResponse)
def merchant_spending(
    request: Request,
    start_at: StartAt = None,
    end_at: EndAt = None,
    limit: int = Query(default=100, ge=1, le=100),
    user: UserRecord = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> MerchantSpendingResponse:
    """Return spending grouped by persisted merchant identity."""

    period = _period(start_at, end_at)
    account, total, items = service.merchant_breakdown(
        user.user_id,
        period=period,
        limit=limit,
    )
    return MerchantSpendingResponse(
        currency=account.currency,
        period={"start_at": period.start_at, "end_at": period.end_at},
        total_spending=total,
        merchants=[
            MerchantSpendingItem.from_value(
                item,
                share_percent=service.share_percent(item.total_spending, total),
            )
            for item in items
        ],
        request_id=request.state.request_id,
    )


@router.get("/spending/trends", response_model=SpendingTrendResponse)
def spending_trends(
    request: Request,
    start_at: StartAt = None,
    end_at: EndAt = None,
    interval: AnalyticsInterval = Query(default=AnalyticsInterval.DAILY),
    user: UserRecord = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> SpendingTrendResponse:
    """Return completed spending grouped into UTC daily/weekly/monthly buckets."""

    period = _period(start_at, end_at)
    account, items = service.trends(
        user.user_id,
        period=period,
        interval=interval,
    )
    return SpendingTrendResponse(
        currency=account.currency,
        period={"start_at": period.start_at, "end_at": period.end_at},
        interval=interval.value,
        trends=[SpendingTrendItem.from_value(item) for item in items],
        request_id=request.state.request_id,
    )


@router.get("/spending/largest", response_model=LargestPaymentsResponse)
def largest_payments(
    request: Request,
    start_at: StartAt = None,
    end_at: EndAt = None,
    limit: int = Query(default=10, ge=1, le=100),
    user: UserRecord = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> LargestPaymentsResponse:
    """Return a bounded largest-payment projection for the owner."""

    period = _period(start_at, end_at)
    account, items = service.largest_payments(
        user.user_id,
        period=period,
        limit=limit,
    )
    return LargestPaymentsResponse(
        currency=account.currency,
        period={"start_at": period.start_at, "end_at": period.end_at},
        payments=[LargestPaymentItem.from_value(item) for item in items],
        request_id=request.state.request_id,
    )


__all__ = ["router"]
