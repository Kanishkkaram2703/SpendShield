"""Application service for owner-scoped, read-only spending analytics."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.core.exceptions import AppError
from app.domain.analytics import (
    AnalyticsInterval,
    AnalyticsPeriod,
    CategorySpending,
    LargestPayment,
    MerchantSpending,
    SpendingSummary,
    SpendingTrend,
)
from app.domain.financial import Account
from app.repositories.accounts import AccountRepository
from app.repositories.analytics import AnalyticsRepository


class AnalyticsService:
    """Keep account authorization and analytics semantics out of HTTP routes."""

    def __init__(
        self,
        repository: AnalyticsRepository,
        account_repository: AccountRepository,
    ) -> None:
        self._repository = repository
        self._accounts = account_repository

    def _account(self, owner_id: str) -> Account:
        account = self._accounts.get_by_owner(owner_id)
        if account is None:
            raise AppError(
                code="account_not_found",
                message="Account was not found.",
                status_code=404,
            )
        return account

    def spending_summary(
        self,
        owner_id: str,
        *,
        period: AnalyticsPeriod,
    ) -> tuple[Account, SpendingSummary]:
        account = self._account(owner_id)
        return account, self._repository.spending_summary(
            owner_id,
            currency=account.currency,
            period=period,
        )

    def category_breakdown(
        self,
        owner_id: str,
        *,
        period: AnalyticsPeriod,
        limit: int,
    ) -> tuple[Account, Decimal, tuple[CategorySpending, ...]]:
        account = self._account(owner_id)
        summary = self._repository.spending_summary(
            owner_id,
            currency=account.currency,
            period=period,
        )
        items = self._repository.category_breakdown(
            owner_id,
            currency=account.currency,
            period=period,
            limit=limit,
        )
        return account, summary.total_spending, items

    def merchant_breakdown(
        self,
        owner_id: str,
        *,
        period: AnalyticsPeriod,
        limit: int,
    ) -> tuple[Account, Decimal, tuple[MerchantSpending, ...]]:
        account = self._account(owner_id)
        summary = self._repository.spending_summary(
            owner_id,
            currency=account.currency,
            period=period,
        )
        items = self._repository.merchant_breakdown(
            owner_id,
            currency=account.currency,
            period=period,
            limit=limit,
        )
        return account, summary.total_spending, items

    def trends(
        self,
        owner_id: str,
        *,
        period: AnalyticsPeriod,
        interval: AnalyticsInterval,
    ) -> tuple[Account, tuple[SpendingTrend, ...]]:
        account = self._account(owner_id)
        return account, self._repository.trends(
            owner_id,
            currency=account.currency,
            period=period,
            interval=interval,
        )

    def largest_payments(
        self,
        owner_id: str,
        *,
        period: AnalyticsPeriod,
        limit: int,
    ) -> tuple[Account, tuple[LargestPayment, ...]]:
        account = self._account(owner_id)
        return account, self._repository.largest_payments(
            owner_id,
            currency=account.currency,
            period=period,
            limit=limit,
        )

    @staticmethod
    def share_percent(amount: Decimal, total: Decimal) -> Decimal:
        """Calculate a display percentage using exact Decimal arithmetic."""

        if total == 0:
            return Decimal("0.00")
        return (amount / total * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )


__all__ = ["AnalyticsService"]
