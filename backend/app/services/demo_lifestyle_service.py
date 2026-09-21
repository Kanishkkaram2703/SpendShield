"""Application helpers for fictional recharge and subscription catalogs."""

from __future__ import annotations

from datetime import date

from app.domain.demo_catalog import (
    RechargePlan,
    SubscriptionPlan,
    SubscriptionPlatform,
    get_recharge_plan,
    get_subscription_plan,
    list_recharge_plans,
    list_subscription_platforms,
    next_billing_date,
)
from app.domain.financial import FinancialDomainError


class DemoLifestyleService:
    """Validate immutable demo catalogs without embedding catalog rules in routes."""

    @staticmethod
    def recharge_plans(operator: str | None = None) -> tuple[RechargePlan, ...]:
        return list_recharge_plans(operator)

    @staticmethod
    def recharge_plan(plan_id: str, operator: str) -> RechargePlan:
        return get_recharge_plan(plan_id, operator)

    @staticmethod
    def subscription_platforms() -> tuple[SubscriptionPlatform, ...]:
        return list_subscription_platforms()

    @staticmethod
    def subscription_plan(platform_id: str, plan_id: str) -> tuple[SubscriptionPlatform, SubscriptionPlan]:
        return get_subscription_plan(platform_id, plan_id)

    @staticmethod
    def next_billing_date(*, from_date: date, duration_days: int) -> date:
        return next_billing_date(from_date=from_date, duration_days=duration_days)

    @staticmethod
    def mask_mobile_number(value: str) -> str:
        if len(value) != 10 or not value.isdigit():
            raise FinancialDomainError("The demo mobile number is invalid.")
        return f"******{value[-4:]}"


__all__ = ["DemoLifestyleService"]
