"""Reusable authentication and authorization dependencies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.core.security import TokenManager
from app.db.manager import DatabaseManager
from app.repositories.accounts import AccountRepository
from app.repositories.analytics import AnalyticsRepository
from app.repositories.audit import AuditRepository
from app.repositories.categories import CategoryRepository
from app.repositories.merchants import MerchantRepository
from app.repositories.payments import PaymentRepository
from app.repositories.demo_resources import DemoResourceRepository
from app.repositories.demo_merchants import DemoMerchantRepositoryProtocol
from app.repositories.users import UserRecord, UserRepository, UserRole
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.services.event_delivery_service import EventDeliveryService
from app.services.payment_service import PaymentService
from app.services.merchant_service import MerchantService
from app.services.analytics_service import AnalyticsService
from app.services.research_anomaly_service import ResearchAnomalyService

LOGGER = get_logger(__name__)
BEARER_SCHEME = HTTPBearer(auto_error=False)
AUTH_HEADERS = {"WWW-Authenticate": "Bearer"}


def get_settings(request: Request) -> Settings:
    """Resolve settings from the application created by the factory."""

    return request.app.state.settings


def get_user_repository(request: Request) -> UserRepository:
    """Resolve the configured repository adapter."""

    return request.app.state.user_repository


def get_database_manager(request: Request) -> DatabaseManager:
    """Resolve the application database manager."""

    return request.app.state.database_manager


def get_auth_service(
    repository: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    """Build the authentication service for one request."""

    return AuthService(repository, settings)


def get_account_repository(request: Request) -> AccountRepository:
    """Resolve the configured account persistence adapter."""

    return request.app.state.account_repository


def get_demo_resource_repository(
    request: Request,
    collection_name: str,
    identifier_field: str,
) -> DemoResourceRepository:
    """Resolve one configured Mongo-backed demo current-state collection."""

    repository = getattr(request.app.state, f"{collection_name}_repository", None)
    if repository is None:
        raise AppError(
            code="demo_module_persistence_not_configured",
            message="This demo module is not configured for the current environment.",
            status_code=503,
        )
    return repository


def get_contacts_repository(request: Request) -> DemoResourceRepository:
    return get_demo_resource_repository(request, "contacts", "contact_id")


def get_beneficiaries_repository(request: Request) -> DemoResourceRepository:
    return get_demo_resource_repository(request, "beneficiaries", "beneficiary_id")


def get_billers_repository(request: Request) -> DemoResourceRepository:
    return get_demo_resource_repository(request, "billers", "biller_id")


def get_cards_repository(request: Request) -> DemoResourceRepository:
    return get_demo_resource_repository(request, "cards", "card_id")


def get_notifications_repository(request: Request) -> DemoResourceRepository:
    return get_demo_resource_repository(request, "notifications", "notification_id")


def get_subscriptions_repository(request: Request) -> DemoResourceRepository:
    return get_demo_resource_repository(request, "subscriptions", "subscription_id")


def get_demo_security_repository(request: Request) -> DemoResourceRepository:
    return get_demo_resource_repository(request, "demo_security", "user_id")


def get_optional_demo_security_repository(request: Request) -> DemoResourceRepository | None:
    return getattr(request.app.state, "demo_security_repository", None)


def get_optional_notifications_repository(request: Request) -> DemoResourceRepository | None:
    return getattr(request.app.state, "notifications_repository", None)


def get_demo_merchant_repository(request: Request) -> DemoMerchantRepositoryProtocol:
    repository = getattr(request.app.state, "demo_merchant_repository", None)
    if repository is None:
        raise AppError(
            code="demo_merchant_persistence_not_configured",
            message="The demo merchant registry is not configured for this environment.",
            status_code=503,
        )
    return repository


def get_optional_demo_merchant_repository(request: Request) -> DemoMerchantRepositoryProtocol | None:
    return getattr(request.app.state, "demo_merchant_repository", None)


def get_audit_repository(request: Request) -> AuditRepository:
    """Resolve the configured audit persistence adapter."""

    return request.app.state.audit_repository


def get_payment_repository(request: Request) -> PaymentRepository:
    """Resolve the configured payment persistence boundary."""

    repository = getattr(request.app.state, "payment_repository", None)
    if repository is None:
        raise AppError(
            code="payment_persistence_not_configured",
            message="Payment persistence is not configured for this environment.",
            status_code=503,
        )
    return repository


def get_category_repository(request: Request) -> CategoryRepository:
    """Resolve the current canonical category repository."""

    repository = getattr(request.app.state, "category_repository", None)
    if repository is None:
        raise AppError(
            code="catalog_persistence_not_configured",
            message="Category persistence is not configured for this environment.",
            status_code=503,
        )
    return repository


def get_merchant_repository(request: Request) -> MerchantRepository:
    """Resolve the current merchant repository."""

    repository = getattr(request.app.state, "merchant_repository", None)
    if repository is None:
        raise AppError(
            code="catalog_persistence_not_configured",
            message="Merchant persistence is not configured for this environment.",
            status_code=503,
        )
    return repository


def get_analytics_repository(request: Request) -> AnalyticsRepository:
    """Resolve the read-only analytics persistence adapter."""

    repository = getattr(request.app.state, "analytics_repository", None)
    if repository is None:
        raise AppError(
            code="analytics_persistence_not_configured",
            message="Analytics persistence is not configured for this environment.",
            status_code=503,
        )
    return repository


def get_analytics_service(
    repository: AnalyticsRepository = Depends(get_analytics_repository),
    account_repository: AccountRepository = Depends(get_account_repository),
) -> AnalyticsService:
    """Build the owner-scoped analytics service for one request."""

    return AnalyticsService(repository, account_repository)


def get_research_anomaly_service(
    repository: PaymentRepository = Depends(get_payment_repository),
    settings: Settings = Depends(get_settings),
) -> ResearchAnomalyService:
    """Build the read-only research anomaly service for one request."""

    return ResearchAnomalyService(repository, settings)


def get_event_delivery_service(request: Request) -> EventDeliveryService | None:
    """Resolve optional post-commit historical event delivery."""

    return getattr(request.app.state, "event_delivery_service", None)


def get_merchant_service(
    merchant_repository: MerchantRepository = Depends(get_merchant_repository),
    category_repository: CategoryRepository = Depends(get_category_repository),
    audit_repository: AuditRepository = Depends(get_audit_repository),
) -> MerchantService:
    """Build the merchant/category application service for one request."""

    return MerchantService(
        merchant_repository,
        category_repository,
        audit_repository,
    )


def get_payment_service(
    repository: PaymentRepository = Depends(get_payment_repository),
    event_delivery_service: EventDeliveryService | None = Depends(
        get_event_delivery_service
    ),
    merchant_service: MerchantService = Depends(get_merchant_service),
    notification_repository: DemoResourceRepository | None = Depends(get_optional_notifications_repository),
) -> PaymentService:
    """Build the payment application service for one request."""

    return PaymentService(repository, event_delivery_service, merchant_service, notification_repository)


def get_account_service(
    repository: AccountRepository = Depends(get_account_repository),
    audit_repository: AuditRepository = Depends(get_audit_repository),
    settings: Settings = Depends(get_settings),
) -> AccountService:
    """Build the account service for one request."""

    return AccountService(repository, settings, audit_repository)


def _authentication_error() -> AppError:
    return AppError(
        code="authentication_required",
        message="Authentication is required.",
        status_code=401,
        headers=AUTH_HEADERS,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(BEARER_SCHEME),
    repository: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> UserRecord:
    """Validate a bearer token and load the current active user server-side."""

    if credentials is None:
        LOGGER.warning("protected_access_denied reason=missing_credentials")
        raise _authentication_error()

    try:
        payload = TokenManager(settings).decode_access_token(credentials.credentials)
    except AppError as exc:
        if exc.status_code == 503:
            raise
        LOGGER.warning("protected_access_denied reason=invalid_token")
        raise _authentication_error() from exc

    user_id = payload["sub"]
    user = repository.get_by_id(user_id)
    if user is None or not user.is_active:
        LOGGER.warning("protected_access_denied reason=unknown_or_inactive_user")
        raise _authentication_error()
    return user


require_authenticated_user = get_current_user


def require_role(*roles: UserRole) -> Callable[..., Any]:
    """Create a dependency that permits only the supplied server-side roles."""

    allowed_roles = frozenset(roles)

    def role_dependency(
        user: UserRecord = Depends(get_current_user),
    ) -> UserRecord:
        if user.role not in allowed_roles:
            LOGGER.warning("protected_access_denied reason=insufficient_role")
            raise AppError(
                code="forbidden",
                message="You do not have permission to access this resource.",
                status_code=403,
            )
        return user

    return role_dependency


__all__ = [
    "get_auth_service",
    "get_account_repository",
    "get_account_service",
    "get_beneficiaries_repository",
    "get_billers_repository",
    "get_cards_repository",
    "get_contacts_repository",
    "get_analytics_repository",
    "get_analytics_service",
    "get_audit_repository",
    "get_category_repository",
    "get_database_manager",
    "get_demo_merchant_repository",
    "get_demo_security_repository",
    "get_optional_demo_security_repository",
    "get_optional_demo_merchant_repository",
    "get_current_user",
    "get_event_delivery_service",
    "get_payment_repository",
    "get_payment_service",
    "get_merchant_repository",
    "get_merchant_service",
    "get_notifications_repository",
    "get_subscriptions_repository",
    "get_optional_notifications_repository",
    "get_settings",
    "get_user_repository",
    "require_authenticated_user",
    "require_role",
]
