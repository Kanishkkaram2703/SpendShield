"""Authenticated fictional merchant registry and QR generation API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.v1.dependencies import get_demo_merchant_repository, get_current_user, require_role
from app.core.exceptions import AppError
from app.repositories.demo_merchants import DemoMerchantRepositoryProtocol
from app.repositories.users import UserRecord, UserRole
from app.schemas.demo_merchants import (
    DemoMerchantListResponse,
    DemoMerchantResponse,
    DemoMerchantStatusRequest,
)

router = APIRouter(prefix="/demo-merchants", tags=["demo-merchants"])


def _response(document: dict, request_id: str) -> DemoMerchantResponse:
    return DemoMerchantResponse(
        merchant_id=str(document["merchant_id"]),
        merchant_name=str(document["merchant_name"]),
        category=str(document["category"]),
        demo_bank=str(document["demo_bank"]),
        merchant_account_id=str(document["merchant_account_id"]),
        status=str(document.get("status", "ACTIVE")),
        qr_payload=str(document["qr_payload"]),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


@router.get("", response_model=DemoMerchantListResponse)
def list_demo_merchants(
    request: Request,
    _: UserRecord = Depends(get_current_user),
    repository: DemoMerchantRepositoryProtocol = Depends(get_demo_merchant_repository),
) -> DemoMerchantListResponse:
    return DemoMerchantListResponse(
        merchants=[_response(item, request.state.request_id) for item in repository.list()],
        request_id=request.state.request_id,
    )


@router.get("/{merchant_id}", response_model=DemoMerchantResponse)
def get_demo_merchant(
    merchant_id: str,
    request: Request,
    _: UserRecord = Depends(get_current_user),
    repository: DemoMerchantRepositoryProtocol = Depends(get_demo_merchant_repository),
) -> DemoMerchantResponse:
    merchant = repository.get(merchant_id)
    if merchant is None:
        raise AppError(code="demo_merchant_not_found", message="Demo merchant was not found.", status_code=404)
    return _response(merchant, request.state.request_id)


@router.patch("/{merchant_id}/status", response_model=DemoMerchantResponse)
def update_demo_merchant_status(
    merchant_id: str,
    payload: DemoMerchantStatusRequest,
    request: Request,
    _: UserRecord = Depends(require_role(UserRole.ADMIN)),
    repository: DemoMerchantRepositoryProtocol = Depends(get_demo_merchant_repository),
) -> DemoMerchantResponse:
    merchant = repository.update_status(merchant_id, payload.status)
    if merchant is None:
        raise AppError(code="demo_merchant_not_found", message="Demo merchant was not found.", status_code=404)
    return _response(merchant, request.state.request_id)


__all__ = ["router"]
