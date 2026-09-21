"""Authenticated fictional recharge and subscription APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.api.v1.dependencies import (
    get_account_service,
    get_current_user,
    get_optional_demo_security_repository,
    get_optional_notifications_repository,
    get_payment_service,
    get_subscriptions_repository,
)
from app.api.v1.payments import _demo_command, _demo_response
from app.core.exceptions import AppError
from app.domain.demo_catalog import RechargePlan, SubscriptionPlan, SubscriptionPlatform
from app.domain.financial import TransactionChannel, TransactionType
from app.repositories.demo_resources import DemoResourceRepository, DuplicateDemoResourceError
from app.repositories.users import UserRecord
from app.schemas.demo_lifestyle import (
    DemoRechargeCatalogResponse,
    DemoRechargePlanResponse,
    DemoRechargeRequest,
    DemoRechargeResponse,
    DemoSubscriptionCatalogResponse,
    DemoSubscriptionCreateRequest,
    DemoSubscriptionListResponse,
    DemoSubscriptionPlatformResponse,
    DemoSubscriptionResponse,
    DemoSubscriptionStatusRequest,
)
from app.services.account_service import AccountService
from app.services.demo_lifestyle_service import DemoLifestyleService
from app.services.demo_security_service import require_demo_mpin
from app.services.payment_service import PaymentService

router = APIRouter(tags=["demo-lifestyle"])
catalog = DemoLifestyleService()


def _invalid_catalog_error(exc: Exception) -> AppError:
    return AppError(
        code="invalid_demo_catalog_selection",
        message="The selected fictional demo option is not available.",
        status_code=422,
    )


def _subscription(document: dict) -> DemoSubscriptionResponse:
    return DemoSubscriptionResponse(
        subscription_id=str(document["subscription_id"]),
        platform_id=str(document["platform_id"]),
        platform_name=str(document["platform_name"]),
        plan_id=str(document["plan_id"]),
        plan_name=str(document["plan_name"]),
        period=str(document["period"]),
        price=document["price"],
        currency=str(document["currency"]),
        status=str(document.get("status", "ACTIVE")),
        next_billing_date=document["next_billing_date"],
        source_transaction_id=document.get("source_transaction_id"),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def _create_notification(
    repository: DemoResourceRepository | None,
    owner_id: str,
    notification_id: str,
    title: str,
    message: str,
) -> None:
    if repository is None:
        return
    try:
        repository.create(
            owner_id,
            {
                "notification_id": notification_id,
                "category": "DEMO_LIFESTYLE",
                "title": title,
                "message": message,
                "is_read": False,
            },
        )
    except DuplicateDemoResourceError:
        return


@router.get("/recharge/operators", response_model=DemoRechargeCatalogResponse)
def recharge_catalog(
    request: Request,
    operator: str | None = Query(default=None, max_length=16),
    _: UserRecord = Depends(get_current_user),
) -> DemoRechargeCatalogResponse:
    try:
        plans = catalog.recharge_plans(operator)
    except Exception as exc:
        raise _invalid_catalog_error(exc) from exc
    return DemoRechargeCatalogResponse(
        operators=["AIRTEL", "JIO", "VI", "BSNL"],
        plans=[DemoRechargePlanResponse.from_plan(plan) for plan in plans],
        request_id=request.state.request_id,
    )


@router.post("/recharge", response_model=DemoRechargeResponse, status_code=status.HTTP_201_CREATED)
def recharge(
    payload: DemoRechargeRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    payment_service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoRechargeResponse:
    account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    try:
        plan = catalog.recharge_plan(payload.plan_id, payload.operator)
    except Exception as exc:
        raise _invalid_catalog_error(exc) from exc
    command = _demo_command(
        account_id=str(payload.account_id),
        owner_id=user.user_id,
        amount=plan.price,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.WALLET_SIMULATED,
        transaction_type=TransactionType.MOBILE_RECHARGE_DEMO,
        request=request,
        causation_id=causation_id,
        note=payload.note or f"{plan.plan_name} demo recharge for {payload.mobile_number}",
        counterparty_name=plan.operator,
        beneficiary_name=catalog.mask_mobile_number(payload.mobile_number),
        category_id="mobile_recharge_demo",
        category_name="Mobile recharge",
        subcategory_id=plan.operator.lower(),
        subcategory_name="Recharge plan",
    )
    execution = payment_service.execute_demo(command)
    return DemoRechargeResponse(
        operator=plan.operator,
        mobile_number_masked=catalog.mask_mobile_number(payload.mobile_number),
        plan=DemoRechargePlanResponse.from_plan(plan),
        payment=_demo_response(execution, request=request),
    )


@router.get("/subscriptions/platforms", response_model=DemoSubscriptionCatalogResponse)
def subscription_catalog(
    request: Request,
    _: UserRecord = Depends(get_current_user),
) -> DemoSubscriptionCatalogResponse:
    return DemoSubscriptionCatalogResponse(
        platforms=[
            DemoSubscriptionPlatformResponse.from_platform(platform)
            for platform in catalog.subscription_platforms()
        ],
        request_id=request.state.request_id,
    )


@router.get("/subscriptions", response_model=DemoSubscriptionListResponse)
def list_subscriptions(
    request: Request,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_subscriptions_repository),
) -> DemoSubscriptionListResponse:
    return DemoSubscriptionListResponse(
        subscriptions=[_subscription(item) for item in repository.list(user.user_id)],
        request_id=request.state.request_id,
    )


@router.post("/subscriptions", response_model=DemoSubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: DemoSubscriptionCreateRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    payment_service: PaymentService = Depends(get_payment_service),
    repository: DemoResourceRepository = Depends(get_subscriptions_repository),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
    notifications: DemoResourceRepository | None = Depends(get_optional_notifications_repository),
) -> DemoSubscriptionResponse:
    account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    existing = next(
        (item for item in repository.list(user.user_id) if item.get("idempotency_key") == idempotency_key),
        None,
    )
    if existing is not None:
        return _subscription(existing)
    try:
        platform, plan = catalog.subscription_plan(payload.platform_id, payload.plan_id)
    except Exception as exc:
        raise _invalid_catalog_error(exc) from exc
    command = _demo_command(
        account_id=str(payload.account_id),
        owner_id=user.user_id,
        amount=plan.price,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.WALLET_SIMULATED,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT_DEMO,
        request=request,
        causation_id=causation_id,
        note=f"{platform.platform_name} {plan.plan_name} demo subscription",
        counterparty_name=platform.platform_name,
        category_id="entertainment_demo",
        category_name="BJP Entertainments",
        subcategory_id=platform.platform_id.lower(),
        subcategory_name=plan.period.title(),
    )
    payment = payment_service.execute_demo(command)
    now = datetime.now(timezone.utc)
    document = {
        "subscription_id": str(uuid4()),
        "user_id": user.user_id,
        "account_id": str(payload.account_id),
        "platform_id": platform.platform_id,
        "platform_name": platform.platform_name,
        "plan_id": plan.plan_id,
        "plan_name": plan.plan_name,
        "period": plan.period,
        "price": str(plan.price),
        "currency": payload.currency,
        "status": "ACTIVE",
        "next_billing_date": datetime.combine(
            catalog.next_billing_date(from_date=now.date(), duration_days=plan.duration_days),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ),
        "source_transaction_id": payment.transaction.transaction_id,
        "idempotency_key": idempotency_key,
        "created_at": now,
        "updated_at": now,
    }
    try:
        created = repository.create(user.user_id, document)
    except DuplicateDemoResourceError:
        existing = next(
            (item for item in repository.list(user.user_id) if item.get("idempotency_key") == idempotency_key),
            None,
        )
        if existing is None:
            raise AppError(code="subscription_conflict", message="The demo subscription could not be created safely.", status_code=409)
        return _subscription(existing)
    _create_notification(
        notifications,
        user.user_id,
        f"subscription-{created['subscription_id']}",
        "Demo subscription started",
        f"{platform.platform_name} {plan.plan_name} is active in the fictional demo environment.",
    )
    return _subscription(created)


@router.patch("/subscriptions/{subscription_id}/status", response_model=DemoSubscriptionResponse)
def update_subscription_status(
    subscription_id: UUID,
    payload: DemoSubscriptionStatusRequest,
    request: Request,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_subscriptions_repository),
    notifications: DemoResourceRepository | None = Depends(get_optional_notifications_repository),
) -> DemoSubscriptionResponse:
    current = repository.get(user.user_id, str(subscription_id))
    if current is None:
        raise AppError(code="subscription_not_found", message="The demo subscription was not found.", status_code=404)
    if current.get("status") == "CANCELLED":
        raise AppError(code="subscription_already_cancelled", message="The demo subscription is already cancelled.", status_code=409)
    updated = repository.update(user.user_id, str(subscription_id), {"status": payload.status})
    assert updated is not None
    _create_notification(
        notifications,
        user.user_id,
        f"subscription-status-{subscription_id}-{payload.status}",
        "Demo subscription updated",
        f"{updated['platform_name']} is now {payload.status.lower()} in the fictional demo environment.",
    )
    return _subscription(updated)


__all__ = ["router"]
