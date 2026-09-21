"""Demo-only MPIN management; unrelated to bearer-token authentication."""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_current_user, get_demo_security_repository
from app.core.exceptions import AppError
from app.core.security import verify_password_or_dummy
from app.repositories.demo_resources import DemoResourceRepository
from app.repositories.users import UserRecord
from app.schemas.demo_security import DemoMpinRequest, DemoMpinResetRequest, DemoSecurityStatusResponse
from app.services.demo_security_service import reset_demo_mpin, security_status, set_demo_mpin

router = APIRouter(prefix="/demo-security", tags=["demo-security"])


@router.get("", response_model=DemoSecurityStatusResponse)
def get_security_status(
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_demo_security_repository),
) -> DemoSecurityStatusResponse:
    return DemoSecurityStatusResponse(**security_status(repository, user.user_id))


@router.put("/mpin", response_model=DemoSecurityStatusResponse)
def update_mpin(
    payload: DemoMpinRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_demo_security_repository),
) -> DemoSecurityStatusResponse:
    if payload.pin != payload.confirm_pin:
        raise AppError(code="demo_mpin_mismatch", message="The demo MPIN entries do not match.", status_code=422)
    set_demo_mpin(repository, user.user_id, pin=payload.pin, current_pin=payload.current_pin)
    return DemoSecurityStatusResponse(**security_status(repository, user.user_id))


@router.post("/mpin/reset", response_model=DemoSecurityStatusResponse)
def reset_mpin(
    payload: DemoMpinResetRequest,
    user: UserRecord = Depends(get_current_user),
    repository: DemoResourceRepository = Depends(get_demo_security_repository),
) -> DemoSecurityStatusResponse:
    if not verify_password_or_dummy(payload.password, user.password_hash):
        raise AppError(code="demo_mpin_reset_invalid", message="The account password is incorrect.", status_code=401)
    reset_demo_mpin(repository, user.user_id)
    return DemoSecurityStatusResponse(**security_status(repository, user.user_id))


__all__ = ["router"]
