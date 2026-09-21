"""Focused tests for the additive fictional banking foundation."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.domain.financial import (
    Account,
    AccountStatus,
    PaymentCommand,
    TransactionChannel,
    TransactionDirection,
    TransactionType,
)
from app.repositories.fakes import InMemoryAccountRepository, InMemoryPaymentRepository
from app.services.account_service import AccountService
from app.schemas.demo_payments import DemoAccountOperationRequest


def make_account(owner_id: str) -> Account:
    now = datetime.now(timezone.utc)
    return Account(
        account_id=str(uuid4()),
        owner_id=owner_id,
        currency="INR",
        balance=Decimal("100.00"),
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def make_command(account: Account, key: str, operation: TransactionType, direction: TransactionDirection, amount: str) -> PaymentCommand:
    return PaymentCommand(
        account_id=account.account_id,
        owner_id=account.owner_id,
        amount=Decimal(amount),
        currency=account.currency,
        idempotency_key=key,
        transaction_channel=TransactionChannel.BANK_SIMULATED,
        transaction_type=operation,
        direction=direction,
    )


def test_demo_deposit_credits_and_replays_without_duplicate_effect() -> None:
    account = make_account("owner")
    repository = InMemoryPaymentRepository([account])
    command = make_command(account, "deposit-once", TransactionType.DEMO_DEPOSIT, TransactionDirection.CREDIT, "25.00")

    first = repository.execute(command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc))
    replay = repository.execute(command, transaction_id=str(uuid4()), at=datetime.now(timezone.utc))

    assert first.transaction.transaction_type is TransactionType.DEMO_DEPOSIT
    assert first.transaction.direction is TransactionDirection.CREDIT
    assert first.account.balance == Decimal("125.00")
    assert replay.transaction.transaction_id == first.transaction.transaction_id
    assert repository._accounts[account.account_id].balance == Decimal("125.00")


def test_additional_account_requires_explicit_profile_request_but_keeps_separate_state() -> None:
    repository = InMemoryAccountRepository()
    service = AccountService(
        repository,
        Settings(_env_file=None, environment="test", account_initial_balance="100.00"),
    )

    first = service.create_for_owner("owner")
    second = service.create_for_owner("owner", account_type="DEMO_WALLET", allow_additional=True)

    assert first.account_id != second.account_id
    assert len(repository.list_by_owner("owner")) == 2
    assert first.balance == second.balance == Decimal("100.00")
    with pytest.raises(AppError) as error:
        service.create_for_owner("owner")
    assert error.value.code == "account_already_exists"


def test_demo_operation_schema_rejects_zero_and_unknown_fields() -> None:
    valid = DemoAccountOperationRequest(account_id=uuid4(), amount="1.00", currency="INR", reason="seed")
    assert valid.amount == Decimal("1.00")
    with pytest.raises(ValueError):
        DemoAccountOperationRequest(account_id=uuid4(), amount="0.00", currency="INR")
    with pytest.raises(ValueError):
        DemoAccountOperationRequest(account_id=uuid4(), amount="1.00", currency="INR", owner_id="attacker")
