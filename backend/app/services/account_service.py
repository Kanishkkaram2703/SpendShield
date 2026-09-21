"""Application service for backend-authoritative account operations."""

from __future__ import annotations

from uuid import uuid4

from app.core.config import Settings
from app.core.exceptions import AppError
from app.domain.financial import (
    Account,
    AccountStatus,
    InvalidAccountStatusTransitionError,
    utc_now,
)
from app.events.models import DomainEvent
from app.repositories.audit import AuditRepository, NullAuditRepository
from app.repositories.accounts import (
    AccountRepository,
    AccountVersionConflictError,
    DuplicateAccountError,
)
from app.repositories.users import UserRole


class AccountService:
    """Coordinate account rules without exposing persistence details to routes."""

    def __init__(
        self,
        repository: AccountRepository,
        settings: Settings,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._audit_repository = audit_repository or NullAuditRepository()

    def _audit(
        self,
        *,
        event_type: str,
        account: Account,
        actor_id: str,
        correlation_id: str | None,
        payload: dict[str, object],
    ) -> None:
        """Persist a structured audit event without exposing persistence details."""

        request_id = correlation_id or str(uuid4())
        self._audit_repository.append(
            DomainEvent(
                event_type=event_type,
                subject_id=account.account_id,
                actor_id=actor_id,
                occurred_at=account.updated_at,
                source="account-service",
                correlation_id=request_id,
                payload=payload,
                provenance={"channel": "api", "request_id": request_id},
            )
        )

    def create_for_owner(
        self,
        owner_id: str,
        *,
        holder_name: str | None = None,
        account_type: str = "DEMO_SAVINGS",
        allow_additional: bool = False,
        correlation_id: str | None = None,
    ) -> Account:
        """Create a fictional account with server-owned financial defaults."""

        if not allow_additional and self._repository.get_by_owner(owner_id) is not None:
            raise AppError(
                code="account_already_exists",
                message="An account already exists for this user.",
                status_code=409,
            )
        now = utc_now()
        account_id = str(uuid4())
        account_type_value = account_type.strip().upper()[:32] or "DEMO_SAVINGS"
        account = Account(
            account_id=account_id,
            owner_id=owner_id,
            currency=self._settings.account_currency,
            balance=self._settings.account_initial_balance,
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            holder_name=(holder_name or "Demo account holder").strip()[:128],
            demo_account_number=f"BJP-DEMO-{account_id.replace('-', '')[-10:].upper()}",
            demo_bank_code="BJP0DEMO0001",
            demo_branch="Virtual Demo Branch",
            account_type=account_type_value,
        )
        try:
            persisted = self._repository.create(
                account,
                allow_duplicate_owner=allow_additional,
            )
        except DuplicateAccountError as exc:
            # The unique repository constraint closes the check-then-create race.
            raise AppError(
                code="account_already_exists",
                message="An account already exists for this user.",
                status_code=409,
            ) from exc
        self._audit(
            event_type="ACCOUNT_CREATED",
            account=persisted,
            actor_id=owner_id,
            correlation_id=correlation_id,
            payload={
                "account_id": persisted.account_id,
                "currency": persisted.currency,
                "initial_balance": str(persisted.balance),
                "status": persisted.status.value,
                "account_type": persisted.account_type,
                "outcome": "succeeded",
            },
        )
        return persisted

    def change_status(
        self,
        account_id: str,
        *,
        new_status: AccountStatus,
        actor_id: str,
        actor_role: UserRole,
        expected_version: int | None = None,
        reason: str | None = None,
        correlation_id: str | None = None,
    ) -> Account:
        """Apply an admin-only status transition with optimistic concurrency."""

        if actor_role is not UserRole.ADMIN:
            raise AppError(
                code="forbidden",
                message="You do not have permission to change account status.",
                status_code=403,
            )
        account = self._repository.get_by_id(account_id)
        if account is None:
            raise AppError(
                code="account_not_found",
                message="Account was not found.",
                status_code=404,
            )
        if expected_version is not None and expected_version != account.version:
            raise AppError(
                code="account_version_conflict",
                message="Account state changed; refresh and retry the operation.",
                status_code=409,
            )
        try:
            updated = account.transition_status(new_status, at=utc_now())
        except InvalidAccountStatusTransitionError as exc:
            raise AppError(
                code="invalid_account_status_transition",
                message="The requested account status transition is not allowed.",
                status_code=409,
            ) from exc
        try:
            persisted = self._repository.update(
                updated,
                expected_version=account.version,
            )
        except AccountVersionConflictError as exc:
            raise AppError(
                code="account_version_conflict",
                message="Account state changed; refresh and retry the operation.",
                status_code=409,
            ) from exc
        if persisted is None:
            raise AppError(
                code="account_version_conflict",
                message="Account state changed; refresh and retry the operation.",
                status_code=409,
            )
        self._audit(
            event_type="ACCOUNT_STATUS_CHANGED",
            account=persisted,
            actor_id=actor_id,
            correlation_id=correlation_id,
            payload={
                "account_id": persisted.account_id,
                "previous_status": account.status.value,
                "new_status": persisted.status.value,
                "reason": reason,
                "version": persisted.version,
                "outcome": "succeeded",
            },
        )
        return persisted

    def get_for_actor(
        self,
        account_id: str,
        *,
        actor_id: str,
        actor_role: UserRole,
    ) -> Account:
        """Return an account only when the actor is its owner or an admin."""

        account = self._repository.get_by_id(account_id)
        if account is None or (
            account.owner_id != actor_id and actor_role is not UserRole.ADMIN
        ):
            # Deliberately avoid revealing whether another user's ID exists.
            raise AppError(
                code="account_not_found",
                message="Account was not found.",
                status_code=404,
            )
        return account

    def get_for_owner(self, owner_id: str) -> Account:
        """Return an owner's account or a non-sensitive not-found response."""

        account = self._repository.get_by_owner(owner_id)
        if account is None:
            raise AppError(
                code="account_not_found",
                message="Account was not found.",
                status_code=404,
            )
        return account

    def list_for_owner(self, owner_id: str) -> tuple[Account, ...]:
        """Return all current accounts owned by the authenticated user."""

        accounts = self._repository.list_by_owner(owner_id)
        if not accounts:
            raise AppError(
                code="account_not_found",
                message="Account was not found.",
                status_code=404,
            )
        return accounts

    def require_payment_owner(self, account_id: str, owner_id: str) -> Account:
        """Authorize a payment only for the authenticated account owner."""

        account = self._repository.get_by_id(account_id)
        if account is None:
            raise AppError(
                code="account_not_found",
                message="Account was not found.",
                status_code=404,
            )
        if account.owner_id != owner_id:
            raise AppError(
                code="forbidden",
                message="You do not have permission to use this account.",
                status_code=403,
            )
        return account


__all__ = ["AccountService"]
