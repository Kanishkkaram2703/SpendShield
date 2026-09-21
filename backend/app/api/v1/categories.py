"""Read-only access to the system-controlled category taxonomy."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.dependencies import get_current_user, get_merchant_service
from app.repositories.users import UserRecord
from app.schemas.merchants import CategoryListResponse, CategoryResponse
from app.services.merchant_service import MerchantService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=CategoryListResponse)
def list_categories(
    request: Request,
    limit: int = Query(default=100, ge=1, le=100),
    _: UserRecord = Depends(get_current_user),
    service: MerchantService = Depends(get_merchant_service),
) -> CategoryListResponse:
    """Return active canonical categories for merchant/payment selection."""

    return CategoryListResponse(
        categories=[
            CategoryResponse.from_record(category)
            for category in service.list_categories(limit=limit)
        ],
        request_id=request.state.request_id,
    )


__all__ = ["router"]
