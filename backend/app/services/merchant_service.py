"""Merchant/category application workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from app.core.exceptions import AppError
from app.domain.catalog import (
    CategoryRecord,
    MerchantDomainError,
    MerchantRecord,
    MerchantResolution,
    MerchantStatus,
    normalize_catalog_id,
    normalize_display_name,
)
from app.events.models import DomainEvent
from app.repositories.audit import AuditRepository
from app.repositories.categories import CategoryRepository
from app.repositories.merchants import (
    DuplicateMerchantError,
    MerchantCursorError,
    MerchantPage,
    MerchantRepository,
    MerchantVersionConflictError,
)


@dataclass(frozen=True, slots=True)
class MerchantViewPage:
    """Resolved merchant page for safe API responses."""

    items: tuple[MerchantResolution, ...]
    next_cursor: str | None


class MerchantService:
    """Coordinate current merchant state and canonical category validation."""

    def __init__(
        self,
        merchant_repository: MerchantRepository,
        category_repository: CategoryRepository,
        audit_repository: AuditRepository,
    ) -> None:
        self._merchants = merchant_repository
        self._categories = category_repository
        self._audit = audit_repository

    def _resolve_category(
        self,
        merchant: MerchantRecord,
        *,
        require_active: bool = True,
    ) -> CategoryRecord:
        category = self._categories.get(
            merchant.category_id,
            merchant.subcategory_id,
        )
        if category is None:
            raise AppError(
                code="merchant_category_not_found",
                message="The merchant category is not available.",
                status_code=409,
            )
        if require_active and not category.is_active:
            raise AppError(
                code="merchant_category_inactive",
                message="The merchant category is inactive.",
                status_code=409,
            )
        return category

    def resolve_for_payment(self, merchant_id: str | None) -> MerchantResolution:
        """Validate an active merchant and resolve its active category."""

        if merchant_id is None or not merchant_id.strip():
            raise AppError(
                code="merchant_required",
                message="A valid merchant is required for a payment.",
                status_code=422,
            )
        merchant = self._merchants.get_by_id(merchant_id)
        if merchant is None:
            raise AppError(
                code="merchant_not_found",
                message="Merchant was not found.",
                status_code=404,
            )
        if merchant.status is not MerchantStatus.ACTIVE:
            raise AppError(
                code="merchant_inactive",
                message="The merchant cannot accept payments.",
                status_code=409,
            )
        return MerchantResolution(
            merchant=merchant,
            category=self._resolve_category(merchant),
        )

    def get(self, merchant_id: str) -> MerchantResolution:
        """Return one merchant with its current category semantics."""

        merchant = self._merchants.get_by_id(merchant_id)
        if merchant is None:
            raise AppError(
                code="merchant_not_found",
                message="Merchant was not found.",
                status_code=404,
            )
        return MerchantResolution(
            merchant=merchant,
            category=self._resolve_category(merchant, require_active=False),
        )

    def list(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        status: MerchantStatus | None = None,
        category_id: str | None = None,
        subcategory_id: str | None = None,
    ) -> MerchantViewPage:
        """Return a bounded page of merchants with category resolution."""

        try:
            page: MerchantPage = self._merchants.list(
                limit=limit,
                cursor=cursor,
                status=status,
                category_id=category_id,
                subcategory_id=subcategory_id,
            )
        except MerchantCursorError as exc:
            raise AppError(
                code="invalid_merchant_cursor",
                message="The merchant listing cursor is invalid or unavailable.",
                status_code=422,
            ) from exc
        return MerchantViewPage(
            items=tuple(self.get(item.merchant_id) for item in page.items),
            next_cursor=page.next_cursor,
        )

    def list_categories(
        self,
        *,
        active_only: bool = True,
        limit: int = 100,
    ) -> tuple[CategoryRecord, ...]:
        """Return the controlled taxonomy without exposing persistence details."""

        return self._categories.list(active_only=active_only, limit=limit)

    def create(
        self,
        *,
        merchant_name: str,
        category_id: str,
        subcategory_id: str,
        actor_id: str,
        correlation_id: str,
        at: datetime,
    ) -> MerchantResolution:
        """Create one active merchant after validating its category pair."""

        try:
            normalized_name = normalize_display_name(
                merchant_name, field_name="Merchant name"
            )
            normalized_category = normalize_catalog_id(
                category_id, field_name="Category ID"
            )
            normalized_subcategory = normalize_catalog_id(
                subcategory_id, field_name="Subcategory ID"
            )
        except MerchantDomainError as exc:
            raise AppError(
                code="invalid_merchant_request",
                message="Merchant details are invalid.",
                status_code=422,
            ) from exc

        category = self._categories.get(normalized_category, normalized_subcategory)
        if category is None:
            raise AppError(
                code="merchant_category_not_found",
                message="The selected category is not available.",
                status_code=422,
            )
        if not category.is_active:
            raise AppError(
                code="merchant_category_inactive",
                message="The selected category is inactive.",
                status_code=409,
            )

        merchant = MerchantRecord(
            merchant_id=str(uuid4()),
            merchant_name=normalized_name,
            category_id=category.category_id,
            subcategory_id=category.subcategory_id,
            status=MerchantStatus.ACTIVE,
            created_at=at,
            updated_at=at,
        )
        try:
            persisted = self._merchants.create(merchant)
        except DuplicateMerchantError as exc:
            raise AppError(
                code="merchant_conflict",
                message="The merchant could not be created because it already exists.",
                status_code=409,
            ) from exc
        self._write_audit(
            event_type="MERCHANT_CREATED",
            merchant=persisted,
            actor_id=actor_id,
            correlation_id=correlation_id,
            payload={"outcome": "succeeded"},
        )
        return MerchantResolution(merchant=persisted, category=category)

    def update(
        self,
        merchant_id: str,
        *,
        merchant_name: str | None,
        category_id: str | None,
        subcategory_id: str | None,
        status: MerchantStatus | None,
        expected_version: int,
        actor_id: str,
        correlation_id: str,
        at: datetime,
    ) -> MerchantResolution:
        """Apply one administrator-controlled, version-checked update."""

        current = self._merchants.get_by_id(merchant_id)
        if current is None:
            raise AppError(
                code="merchant_not_found",
                message="Merchant was not found.",
                status_code=404,
            )
        if expected_version != current.version:
            raise AppError(
                code="merchant_version_conflict",
                message="Merchant state changed; refresh and retry the update.",
                status_code=409,
            )

        next_category_id = current.category_id if category_id is None else category_id
        next_subcategory_id = (
            current.subcategory_id
            if subcategory_id is None
            else subcategory_id
        )
        try:
            next_name = (
                current.merchant_name
                if merchant_name is None
                else normalize_display_name(merchant_name, field_name="Merchant name")
            )
            next_category_id = normalize_catalog_id(
                next_category_id, field_name="Category ID"
            )
            next_subcategory_id = normalize_catalog_id(
                next_subcategory_id, field_name="Subcategory ID"
            )
            if status is not None and status is not current.status:
                current.transition_status(status, at=at)
        except MerchantDomainError as exc:
            raise AppError(
                code="invalid_merchant_request",
                message="Merchant update violates a domain rule.",
                status_code=409,
            ) from exc

        category = self._categories.get(next_category_id, next_subcategory_id)
        if category is None:
            raise AppError(
                code="merchant_category_not_found",
                message="The selected category is not available.",
                status_code=422,
            )
        if not category.is_active:
            raise AppError(
                code="merchant_category_inactive",
                message="The selected category is inactive.",
                status_code=409,
            )

        next_merchant = MerchantRecord(
            merchant_id=current.merchant_id,
            merchant_name=next_name,
            category_id=next_category_id,
            subcategory_id=next_subcategory_id,
            status=current.status if status is None else status,
            created_at=current.created_at,
            updated_at=at,
            version=current.version + 1,
        )
        try:
            persisted = self._merchants.update(
                next_merchant,
                expected_version=expected_version,
            )
        except MerchantVersionConflictError as exc:
            raise AppError(
                code="merchant_version_conflict",
                message="Merchant state changed; refresh and retry the update.",
                status_code=409,
            ) from exc
        if persisted is None:
            raise AppError(
                code="merchant_not_found",
                message="Merchant was not found.",
                status_code=404,
            )
        self._write_audit(
            event_type=(
                "MERCHANT_DEACTIVATED"
                if current.status is MerchantStatus.ACTIVE
                and persisted.status is MerchantStatus.INACTIVE
                else "MERCHANT_UPDATED"
            ),
            merchant=persisted,
            actor_id=actor_id,
            correlation_id=correlation_id,
            payload={
                "outcome": "succeeded",
                "previous_status": current.status.value,
                "new_status": persisted.status.value,
                "previous_category_id": current.category_id,
                "previous_subcategory_id": current.subcategory_id,
            },
        )
        return MerchantResolution(merchant=persisted, category=category)

    def _write_audit(
        self,
        *,
        event_type: str,
        merchant: MerchantRecord,
        actor_id: str,
        correlation_id: str,
        payload: dict[str, object],
    ) -> None:
        """Record merchant lifecycle facts in MongoDB audit storage only."""

        self._audit.append(
            DomainEvent(
                event_type=event_type,
                subject_id=merchant.merchant_id,
                actor_id=actor_id,
                occurred_at=merchant.updated_at,
                source="merchant-service",
                correlation_id=correlation_id,
                payload={
                    "merchant_id": merchant.merchant_id,
                    "merchant_name": merchant.merchant_name,
                    "category_id": merchant.category_id,
                    "subcategory_id": merchant.subcategory_id,
                    "status": merchant.status.value,
                    **payload,
                },
                provenance={"channel": "application", "operation": "merchant_management"},
                created_at=merchant.updated_at,
            )
        )


__all__ = ["MerchantService", "MerchantViewPage"]
