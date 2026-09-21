"""FastAPI application entry point for the SpendShield backend foundation."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import health_check, router as v1_router
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.db.events import CassandraEventRepository
from app.db.manager import DatabaseManager
from app.events.publishers import CassandraEventPublisher
from app.events.publication import EventPublicationStore
from app.repositories.accounts import (
    AccountRepository,
    MongoAccountRepository,
    UnavailableAccountRepository,
)
from app.repositories.analytics import (
    AnalyticsRepository,
    MongoAnalyticsRepository,
    UnavailableAnalyticsRepository,
)
from app.repositories.audit import (
    AuditRepository,
    MongoAuditRepository,
    NullAuditRepository,
)
from app.repositories.categories import (
    CategoryRepository,
    MongoCategoryRepository,
    UnavailableCategoryRepository,
)
from app.repositories.merchants import (
    MerchantRepository,
    MongoMerchantRepository,
    UnavailableMerchantRepository,
)
from app.repositories.mongo_users import MongoUserRepository
from app.repositories.payments import MongoPaymentRepository, PaymentRepository
from app.repositories.demo_resources import DemoResourceRepository
from app.repositories.demo_merchants import DemoMerchantRepository
from app.repositories.users import UnavailableUserRepository, UserRepository
from app.schemas.common import ErrorDetail, ErrorResponse, HealthResponse
from app.services.event_delivery_service import EventDeliveryService

LOGGER = get_logger(__name__)


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Release database clients owned by the application on shutdown."""

    try:
        yield
    finally:
        application.state.database_manager.close()


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the single error envelope used by the API."""

    body = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details)
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
        headers=headers,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Return safe details for an expected application error."""

    LOGGER.warning(
        "application_error code=%s request_id=%s",
        exc.code,
        getattr(request.state, "request_id", "unknown"),
    )
    return _error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        headers=exc.headers,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return validation locations without echoing potentially sensitive input."""

    fields = [
        {
            "location": list(error.get("loc", ())),
            "type": error.get("type", "validation_error"),
        }
        for error in exc.errors()
    ]
    LOGGER.warning(
        "request_validation_failed method=%s path=%s request_id=%s fields=%s",
        request.method,
        request.url.path,
        getattr(request.state, "request_id", "unknown"),
        fields,
    )
    return _error_response(
        status_code=422,
        code="validation_error",
        message="Request validation failed.",
        details={"fields": fields},
    )


async def http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Normalize framework HTTP errors into the API error envelope."""

    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    LOGGER.warning(
        "http_error status_code=%s method=%s path=%s request_id=%s",
        exc.status_code,
        request.method,
        request.url.path,
        getattr(request.state, "request_id", "unknown"),
    )
    return _error_response(
        status_code=exc.status_code,
        code="http_error",
        message=message,
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected failures while keeping internal details out of responses."""

    LOGGER.exception(
        "unhandled_exception method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return _error_response(
        status_code=500,
        code="internal_error",
        message="An unexpected error occurred.",
    )


def create_app(
    settings: Settings | None = None,
    user_repository: UserRepository | None = None,
    database_manager: DatabaseManager | None = None,
    account_repository: AccountRepository | None = None,
    audit_repository: AuditRepository | None = None,
    payment_repository: PaymentRepository | None = None,
    category_repository: CategoryRepository | None = None,
    merchant_repository: MerchantRepository | None = None,
    analytics_repository: AnalyticsRepository | None = None,
    contacts_repository: DemoResourceRepository | None = None,
    beneficiaries_repository: DemoResourceRepository | None = None,
    billers_repository: DemoResourceRepository | None = None,
    cards_repository: DemoResourceRepository | None = None,
    notifications_repository: DemoResourceRepository | None = None,
    subscriptions_repository: DemoResourceRepository | None = None,
    demo_merchant_repository: Any | None = None,
    demo_security_repository: DemoResourceRepository | None = None,
) -> FastAPI:
    """Create and configure a SpendShield FastAPI application."""

    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description=(
            "Backend foundation for the SpendShield fictional financial and "
            "digital-forensics platform."
        ),
        debug=app_settings.debug,
        docs_url=None
        if app_settings.environment in {"staging", "production"}
        else "/docs",
        redoc_url=None
        if app_settings.environment in {"staging", "production"}
        else "/redoc",
        openapi_url=None
        if app_settings.environment in {"staging", "production"}
        else "/openapi.json",
        lifespan=application_lifespan,
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    if app_settings.trusted_host_list:
        application.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=app_settings.trusted_host_list,
        )
    application.state.settings = app_settings
    manager = (
        database_manager
        if database_manager is not None
        else DatabaseManager(app_settings)
    )
    application.state.database_manager = manager
    if user_repository is not None:
        application.state.user_repository = user_repository
    elif (app_settings.mongodb_uri or "").strip():
        application.state.user_repository = MongoUserRepository(manager)
    else:
        application.state.user_repository = UnavailableUserRepository()
    if account_repository is not None:
        application.state.account_repository = account_repository
    elif (app_settings.mongodb_uri or "").strip():
        application.state.account_repository = MongoAccountRepository(manager)
    else:
        application.state.account_repository = UnavailableAccountRepository()
    if audit_repository is not None:
        application.state.audit_repository = audit_repository
    elif (app_settings.mongodb_uri or "").strip():
        application.state.audit_repository = MongoAuditRepository(manager)
    else:
        application.state.audit_repository = NullAuditRepository()
    if payment_repository is not None:
        application.state.payment_repository = payment_repository
    elif (app_settings.mongodb_uri or "").strip():
        application.state.payment_repository = MongoPaymentRepository(
            manager,
            audit_repository=application.state.audit_repository,
        )
    else:
        application.state.payment_repository = None
    if category_repository is not None:
        application.state.category_repository = category_repository
    elif (app_settings.mongodb_uri or "").strip():
        application.state.category_repository = MongoCategoryRepository(manager)
    else:
        application.state.category_repository = UnavailableCategoryRepository()
    if merchant_repository is not None:
        application.state.merchant_repository = merchant_repository
    elif (app_settings.mongodb_uri or "").strip():
        application.state.merchant_repository = MongoMerchantRepository(manager)
    else:
        application.state.merchant_repository = UnavailableMerchantRepository()
    if analytics_repository is not None:
        application.state.analytics_repository = analytics_repository
    elif (app_settings.mongodb_uri or "").strip():
        application.state.analytics_repository = MongoAnalyticsRepository(manager)
    else:
        application.state.analytics_repository = UnavailableAnalyticsRepository()

    for name, collection, identifier, supplied in (
        ("contacts", "contacts", "contact_id", contacts_repository),
        ("beneficiaries", "beneficiaries", "beneficiary_id", beneficiaries_repository),
        ("billers", "billers", "biller_id", billers_repository),
        ("cards", "cards", "card_id", cards_repository),
        ("notifications", "notifications", "notification_id", notifications_repository),
        ("subscriptions", "subscriptions", "subscription_id", subscriptions_repository),
        ("demo_security", "demo_security", "user_id", demo_security_repository),
    ):
        if supplied is not None:
            setattr(application.state, f"{name}_repository", supplied)
        elif (app_settings.mongodb_uri or "").strip():
            setattr(
                application.state,
                f"{name}_repository",
                DemoResourceRepository(manager, collection, identifier),
            )
        else:
            setattr(application.state, f"{name}_repository", None)

    if demo_merchant_repository is not None:
        application.state.demo_merchant_repository = demo_merchant_repository
    elif (app_settings.mongodb_uri or "").strip():
        application.state.demo_merchant_repository = DemoMerchantRepository(manager)
    else:
        application.state.demo_merchant_repository = None

    # Construct the explicit delivery boundary without opening a background
    # worker or a broker.  A future scheduler/application service can invoke
    # publish_pending; app startup remains free of external side effects.
    if (
        (app_settings.cassandra_hosts or "").strip()
        and isinstance(application.state.audit_repository, EventPublicationStore)
    ):
        application.state.event_delivery_service = EventDeliveryService(
            application.state.audit_repository,
            CassandraEventPublisher(CassandraEventRepository(manager)),
        )
    else:
        application.state.event_delivery_service = None

    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)

    application.include_router(v1_router, prefix=app_settings.api_prefix)
    application.add_api_route(
        "/health",
        health_check,
        methods=["GET"],
        response_model=HealthResponse,
        tags=["system"],
        include_in_schema=False,
    )

    logging.getLogger(__name__).debug("FastAPI application created")
    return application


app = create_app()

__all__ = ["app", "create_app"]
