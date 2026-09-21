"""Version 1 API routes."""

from fastapi import APIRouter, Depends

from app.api.v1.auth import router as auth_router
from app.api.v1.accounts import router as accounts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.categories import router as categories_router
from app.api.v1.merchants import router as merchants_router
from app.api.v1.payments import router as payments_router
from app.api.v1.research import router as research_router
from app.api.v1.demo_modules import router as demo_modules_router
from app.api.v1.demo_merchants import router as demo_merchants_router
from app.api.v1.demo_security import router as demo_security_router
from app.api.v1.demo_lifestyle import router as demo_lifestyle_router
from app.api.v1.dependencies import get_database_manager
from app.db.manager import DatabaseManager
from app.schemas.common import DependenciesHealthResponse, HealthResponse

SERVICE_NAME = "spendshield-backend"

router = APIRouter()
router.include_router(auth_router)
router.include_router(accounts_router)
router.include_router(analytics_router)
router.include_router(categories_router)
router.include_router(merchants_router)
router.include_router(payments_router)
router.include_router(research_router)
router.include_router(demo_modules_router)
router.include_router(demo_merchants_router)
router.include_router(demo_security_router)
router.include_router(demo_lifestyle_router)


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    """Report only that the backend process is running."""

    return HealthResponse(status="ok", service=SERVICE_NAME)


@router.get(
    "/health/dependencies",
    response_model=DependenciesHealthResponse,
    response_model_exclude_none=True,
    tags=["system"],
)
def dependency_health_check(
    database_manager: DatabaseManager = Depends(get_database_manager),
) -> DependenciesHealthResponse:
    """Report MongoDB/Cassandra readiness without affecting process liveness."""

    return DependenciesHealthResponse.model_validate(database_manager.health())


__all__ = ["health_check", "router"]
