"""Account routes with ownership enforced through the authenticated user."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request, status
from uuid import UUID

from app.api.v1.dependencies import (
    get_account_service,
    get_current_user,
    get_optional_demo_security_repository,
)
from app.core.exceptions import AppError
from app.repositories.demo_resources import DemoResourceRepository
from app.repositories.users import UserRecord
from app.schemas.accounts import (
    AccountCreateRequest,
    AccountListResponse,
    AccountReferenceListResponse,
    AccountReferenceResponse,
    AccountResponse,
    AccountStatusUpdateRequest,
    ProtectedAccountAccessRequest,
)
from app.services.account_service import AccountService
from app.services.demo_security_service import require_demo_mpin

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    request: Request,
    request_body: AccountCreateRequest | None = Body(default=None),
    user: UserRecord = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """Create one fictional account with server-owned financial values."""

    return AccountResponse.from_record(
        service.create_for_owner(
            user.user_id,
            holder_name=user.email.split("@", 1)[0],
            account_type=request_body.account_type if request_body else "DEMO_SAVINGS",
            allow_additional=bool(
                request_body is not None
                and "account_type" in request_body.model_fields_set
            ),
            correlation_id=request.state.request_id,
        )
    )


@router.get("/me", response_model=AccountResponse)
def get_my_account(
    user: UserRecord = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """Return the authenticated user's current account state."""

    return AccountResponse.from_record(service.get_for_owner(user.user_id))


@router.get("", response_model=AccountListResponse)
def list_my_accounts(
    user: UserRecord = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
) -> AccountListResponse:
    """Return all current fictional accounts owned by the authenticated user."""

    return AccountListResponse(
        accounts=[
            AccountResponse.from_record(account)
            for account in service.list_for_owner(user.user_id)
        ]
    )


@router.get("/me/references", response_model=AccountReferenceListResponse)
def list_account_references(
    user: UserRecord = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
) -> AccountReferenceListResponse:
    """Return account selectors without exposing balances before MPIN unlock."""

    return AccountReferenceListResponse(
        accounts=[
            AccountReferenceResponse(
                account_id=account.account_id,
                currency=account.currency,
                status=account.status,
                account_type=account.account_type,
                demo_account_number=(
                    f"****{account.demo_account_number[-4:]}"
                    if account.demo_account_number
                    else None
                ),
            )
            for account in service.list_for_owner(user.user_id)
        ]
    )


@router.post("/{account_id}/protected", response_model=AccountResponse)
def unlock_account_details(
    account_id: UUID,
    payload: ProtectedAccountAccessRequest,
    user: UserRecord = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> AccountResponse:
    """Return sensitive current account details only after demo MPIN verification."""

    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    return AccountResponse.from_record(
        service.get_for_actor(
            str(account_id),
            actor_id=user.user_id,
            actor_role=user.role,
        )
    )


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: UUID,
    user: UserRecord = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """Return an owned account or an admin-authorized account."""

    return AccountResponse.from_record(
        service.get_for_actor(
            str(account_id),
            actor_id=user.user_id,
            actor_role=user.role,
        )
    )


@router.patch(
    "/{account_id}/status",
    response_model=AccountResponse,
)
def update_account_status(
    account_id: UUID,
    request_body: AccountStatusUpdateRequest,
    request: Request,
    user: UserRecord = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
) -> AccountResponse:
    """Apply an admin-authorized account status transition."""

    return AccountResponse.from_record(
        service.change_status(
            str(account_id),
            new_status=request_body.status,
            actor_id=user.user_id,
            actor_role=user.role,
            expected_version=request_body.expected_version,
            reason=request_body.reason,
            correlation_id=request.state.request_id,
        )
    )


__all__ = ["router"]
