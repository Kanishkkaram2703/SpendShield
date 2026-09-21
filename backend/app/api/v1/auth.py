"""Authentication endpoints."""

from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies import (
    get_auth_service,
    require_authenticated_user,
)
from app.repositories.users import UserRecord
from app.schemas.auth import (
    LoginRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Register a normal financial user."""

    return UserResponse.from_record(
        service.register(
            email=str(payload.email),
            password=payload.password.get_secret_value(),
        )
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate credentials and return a bearer access token."""

    result = service.login(
        email=str(payload.email),
        password=payload.password.get_secret_value(),
    )
    return TokenResponse(
        access_token=result.access_token,
        token_type="bearer",
        expires_in=result.expires_in,
        user=UserResponse.from_record(result.user),
    )


@router.get("/me", response_model=UserResponse)
def current_user(
    user: UserRecord = Depends(require_authenticated_user),
) -> UserResponse:
    """Return safe details for the authenticated active user."""

    return UserResponse.from_record(user)


@router.patch("/me", response_model=UserResponse)
def update_current_user(
    payload: ProfileUpdateRequest,
    user: UserRecord = Depends(require_authenticated_user),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    updated = service.update_profile(
        user,
        email=str(payload.email) if payload.email is not None else None,
        display_name=payload.display_name,
        phone_number=payload.phone_number,
    )
    return UserResponse.from_record(updated)


__all__ = ["router"]
