"""Immutable fictional catalogs for recharge and subscription demos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Final

from app.domain.financial import FinancialDomainError


@dataclass(frozen=True, slots=True)
class RechargePlan:
    plan_id: str
    operator: str
    plan_name: str
    validity_days: int
    data_allowance: str
    calling_benefit: str
    sms_benefit: str
    price: Decimal


@dataclass(frozen=True, slots=True)
class SubscriptionPlan:
    plan_id: str
    platform_id: str
    plan_name: str
    period: str
    duration_days: int
    price: Decimal


@dataclass(frozen=True, slots=True)
class SubscriptionPlatform:
    platform_id: str
    platform_name: str
    description: str
    plans: tuple[SubscriptionPlan, ...]


DEMO_OPERATORS: Final[tuple[str, ...]] = ("AIRTEL", "JIO", "VI", "BSNL")

DEMO_RECHARGE_PLANS: Final[tuple[RechargePlan, ...]] = (
    RechargePlan("AIRTEL-199", "AIRTEL", "Demo 1.5 GB/day", 28, "1.5 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("199.00")),
    RechargePlan("AIRTEL-299", "AIRTEL", "Demo 2 GB/day", 28, "2 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("299.00")),
    RechargePlan("AIRTEL-399", "AIRTEL", "Demo 2.5 GB/day", 56, "2.5 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("399.00")),
    RechargePlan("JIO-199", "JIO", "Demo 1.5 GB/day", 28, "1.5 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("199.00")),
    RechargePlan("JIO-299", "JIO", "Demo 2 GB/day", 28, "2 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("299.00")),
    RechargePlan("JIO-399", "JIO", "Demo 2.5 GB/day", 56, "2.5 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("399.00")),
    RechargePlan("VI-199", "VI", "Demo 1.5 GB/day", 28, "1.5 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("199.00")),
    RechargePlan("VI-299", "VI", "Demo 2 GB/day", 28, "2 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("299.00")),
    RechargePlan("VI-399", "VI", "Demo 2.5 GB/day", 56, "2.5 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("399.00")),
    RechargePlan("BSNL-199", "BSNL", "Demo 1.5 GB/day", 28, "1.5 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("199.00")),
    RechargePlan("BSNL-299", "BSNL", "Demo 2 GB/day", 28, "2 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("299.00")),
    RechargePlan("BSNL-399", "BSNL", "Demo 2.5 GB/day", 56, "2.5 GB/day", "Unlimited demo calls", "100 SMS/day", Decimal("399.00")),
)


def _platform(platform_id: str, name: str, description: str) -> SubscriptionPlatform:
    return SubscriptionPlatform(
        platform_id=platform_id,
        platform_name=name,
        description=description,
        plans=(
            SubscriptionPlan(f"{platform_id}-MONTHLY", platform_id, "Monthly", "MONTHLY", 30, Decimal("149.00")),
            SubscriptionPlan(f"{platform_id}-QUARTERLY", platform_id, "Quarterly", "QUARTERLY", 90, Decimal("399.00")),
            SubscriptionPlan(f"{platform_id}-YEARLY", platform_id, "Yearly", "YEARLY", 365, Decimal("1299.00")),
        ),
    )


DEMO_SUBSCRIPTION_PLATFORMS: Final[tuple[SubscriptionPlatform, ...]] = (
    _platform("BJPPRIME", "BJPPrime", "Movies, Series and Entertainment"),
    _platform("BJPENTERTAINMENTS", "BJP Entertainments", "Shows, Movies and Originals"),
)


def list_recharge_plans(operator: str | None = None) -> tuple[RechargePlan, ...]:
    normalized = operator.strip().upper() if operator else None
    if normalized is not None and normalized not in DEMO_OPERATORS:
        raise FinancialDomainError("Only the fictional demo operators are supported.")
    return tuple(item for item in DEMO_RECHARGE_PLANS if normalized is None or item.operator == normalized)


def get_recharge_plan(plan_id: str, operator: str) -> RechargePlan:
    normalized_operator = operator.strip().upper()
    for plan in list_recharge_plans(normalized_operator):
        if plan.plan_id == plan_id:
            return plan
    raise FinancialDomainError("The selected demo recharge plan is not available.")


def list_subscription_platforms() -> tuple[SubscriptionPlatform, ...]:
    return DEMO_SUBSCRIPTION_PLATFORMS


def get_subscription_plan(platform_id: str, plan_id: str) -> tuple[SubscriptionPlatform, SubscriptionPlan]:
    for platform in DEMO_SUBSCRIPTION_PLATFORMS:
        if platform.platform_id == platform_id:
            for plan in platform.plans:
                if plan.plan_id == plan_id:
                    return platform, plan
    raise FinancialDomainError("The selected demo subscription plan is not available.")


def next_billing_date(*, from_date: date, duration_days: int) -> date:
    return from_date + timedelta(days=duration_days)


__all__ = [
    "DEMO_OPERATORS",
    "DEMO_RECHARGE_PLANS",
    "DEMO_SUBSCRIPTION_PLATFORMS",
    "RechargePlan",
    "SubscriptionPlan",
    "SubscriptionPlatform",
    "get_recharge_plan",
    "get_subscription_plan",
    "list_recharge_plans",
    "list_subscription_platforms",
    "next_billing_date",
]
