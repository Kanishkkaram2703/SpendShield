"""Authenticated merchant discovery and administrator management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.v1.dependencies import (
    get_current_user,
    get_merchant_service,
    require_role,
)
from app.repositories.users import UserRecord, UserRole
from app.schemas.merchants import (
    MerchantCreateRequest,
    MerchantListItem,
    MerchantListResponse,
    MerchantResponse,
    MerchantUpdateRequest,
)
from app.domain.catalog import MerchantStatus
from app.domain.financial import utc_now
from app.services.merchant_service import MerchantService

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("", response_model=MerchantListResponse)
def list_merchants(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: UUID | None = Query(default=None),
    status_filter: MerchantStatus | None = Query(
        default=MerchantStatus.ACTIVE,
        alias="status",
    ),
    category_id: str | None = Query(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
    ),
    subcategory_id: str | None = Query(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
    ),
    _: UserRecord = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service),
) -> MerchantListResponse:
    """List current merchants with bounded stable pagination."""

    page = service.list(
        limit=limit,
        cursor=str(cursor) if cursor is not None else None,
        status=status_filter,
        category_id=category_id,
        subcategory_id=subcategory_id,
    )
    return MerchantListResponse(
        merchants=[
            MerchantListItem.from_resolution(item) for item in page.items
        ],
        next_cursor=page.next_cursor,
        request_id=request.state.request_id,
    )


@router.get("/{merchant_id}", response_model=MerchantResponse)
def get_merchant(
    merchant_id: UUID,
    request: Request,
    _: UserRecord = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service),
) -> MerchantResponse:
    """Return safe current merchant and category information."""

    return MerchantResponse.from_resolution(
        service.get(str(merchant_id)),
        request_id=request.state.request_id,
    )


@router.post(
    "",
    response_model=MerchantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_merchant(
    payload: MerchantCreateRequest,
    request: Request,
    user: UserRecord = Depends(require_role(UserRole.ADMIN)),
    service: MerchantService = Depends(get_merchant_service),
) -> MerchantResponse:
    """Create one canonical merchant; administrator authorization is required."""

    return MerchantResponse.from_resolution(
        service.create(
            merchant_name=payload.merchant_name,
            category_id=payload.category_id,
            subcategory_id=payload.subcategory_id,
            actor_id=user.user_id,
            correlation_id=request.state.request_id,
            at=utc_now(),
        ),
        request_id=request.state.request_id,
    )


@router.patch("/{merchant_id}", response_model=MerchantResponse)
def update_merchant(
    merchant_id: UUID,
    payload: MerchantUpdateRequest,
    request: Request,
    user: UserRecord = Depends(require_role(UserRole.ADMIN)),
    service: MerchantService = Depends(get_merchant_service),
) -> MerchantResponse:
    """Apply one administrator-controlled, version-checked update."""

    return MerchantResponse.from_resolution(
        service.update(
            str(merchant_id),
            merchant_name=payload.merchant_name,
            category_id=payload.category_id,
            subcategory_id=payload.subcategory_id,
            status=payload.status,
            expected_version=payload.expected_version,
            actor_id=user.user_id,
            correlation_id=request.state.request_id,
            at=utc_now(),
        ),
        request_id=request.state.request_id,
    )


__all__ = ["router"]
