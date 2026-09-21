"""Service tests for payment invariants before production persistence wiring."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.exceptions import AppError
from app.domain.financial import Account, AccountStatus, PaymentCommand, TransactionChannel
from app.repositories.fakes import InMemoryPaymentRepository
from app.repositories.demo_resources import DuplicateDemoResourceError
from app.services.payment_service import PaymentService


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_account(status: AccountStatus = AccountStatus.ACTIVE) -> Account:
    return Account(
        account_id="account-1",
        owner_id="user-1",
        currency="INR",
        balance=Decimal("100.00"),
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


def make_command(amount: str = "25.00", key: str = "key-1") -> PaymentCommand:
    return PaymentCommand(
        account_id="account-1",
        owner_id="user-1",
        amount=Decimal(amount),
        currency="INR",
        idempotency_key=key,
        transaction_channel=TransactionChannel.QR_SIMULATED,
    )


def test_duplicate_payment_request_has_one_financial_effect() -> None:
    repository = InMemoryPaymentRepository([make_account()])
    service = PaymentService(repository)

    first = service.execute(make_command(), at=NOW)
    replay = service.execute(make_command(), at=NOW)

    assert replay.transaction.transaction_id == first.transaction.transaction_id
    assert replay.account.balance == Decimal("75.00")


def test_conflicting_idempotency_request_is_rejected() -> None:
    service = PaymentService(InMemoryPaymentRepository([make_account()]))
    service.execute(make_command(), at=NOW)

    with pytest.raises(AppError) as error:
        service.execute(make_command(amount="26.00"), at=NOW)

    assert error.value.code == "idempotency_conflict"
    assert error.value.status_code == 409


def test_failed_payment_does_not_change_balance() -> None:
    repository = InMemoryPaymentRepository([make_account(status=AccountStatus.SUSPENDED)])
    service = PaymentService(repository)

    with pytest.raises(AppError) as error:
        service.execute(make_command(), at=NOW)

    assert error.value.code == "account_not_active"
    assert repository._accounts["account-1"].balance == Decimal("100.00")


def test_failed_payment_creates_one_safe_owner_notification() -> None:
    repository = InMemoryPaymentRepository([make_account(status=AccountStatus.SUSPENDED)])

    class NotificationRepository:
        def __init__(self) -> None:
            self.items: list[tuple[str, dict[str, object]]] = []

        def create(self, owner_id: str, values: dict[str, object]) -> dict[str, object]:
            if any(item[1]["notification_id"] == values["notification_id"] for item in self.items):
                raise DuplicateDemoResourceError(str(values["notification_id"]))
            self.items.append((owner_id, values))
            return values

    notifications = NotificationRepository()
    service = PaymentService(repository, notification_repository=notifications)  # type: ignore[arg-type]

    with pytest.raises(AppError):
        service.execute(make_command(), at=NOW)
    with pytest.raises(AppError):
        service.execute(make_command(), at=NOW)

    assert len(notifications.items) == 1
    assert notifications.items[0][0] == "user-1"
    payload = notifications.items[0][1]
    assert payload["category"] == "PAYMENT_FAILED"
    assert payload["message"] == "Your fictional payment could not be completed (account_not_active)."
    assert "25.00" not in str(payload)
    assert "key-1" not in str(payload)
