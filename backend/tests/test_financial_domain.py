"""Unit tests for money, account, transaction, and idempotency rules."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.financial import (
    Account,
    AccountNotActiveError,
    AccountStatus,
    FinancialDomainError,
    IdempotencyConflictError,
    InsufficientFundsError,
    InvalidAccountStatusTransitionError,
    InvalidTransactionTransitionError,
    PaymentCommand,
    TransactionChannel,
    TransactionStatus,
    authorize_payment,
    normalize_money,
    validate_idempotency_reuse,
)


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def account(*, balance: str = "100.00", status: AccountStatus = AccountStatus.ACTIVE) -> Account:
    return Account(
        account_id="account-1",
        owner_id="user-1",
        currency="INR",
        balance=Decimal(balance),
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


def command(
    *,
    amount: str = "25.00",
    key: str = "request-1",
    correlation_id: str | None = None,
) -> PaymentCommand:
    return PaymentCommand(
        account_id="account-1",
        owner_id="user-1",
        amount=Decimal(amount),
        currency="INR",
        idempotency_key=key,
        transaction_channel=TransactionChannel.QR_SIMULATED,
        merchant_id="merchant-1",
        correlation_id=correlation_id,
        causation_id="parent-request",
    )


def test_money_is_exact_and_normalized() -> None:
    assert normalize_money("10.005") == Decimal("10.01")
    assert normalize_money("0") == Decimal("0.00")

    with pytest.raises(FinancialDomainError):
        normalize_money("-1")
    with pytest.raises(FinancialDomainError):
        normalize_money("NaN")
    with pytest.raises(FinancialDomainError):
        normalize_money("0", allow_zero=False)


def test_account_debit_enforces_status_and_balance() -> None:
    updated = account().debit("25.00", at=NOW)
    assert updated.balance == Decimal("75.00")
    assert updated.version == 1

    with pytest.raises(InsufficientFundsError):
        account(balance="10.00").debit("10.01", at=NOW)
    with pytest.raises(AccountNotActiveError):
        account(status=AccountStatus.SUSPENDED).debit("1.00", at=NOW)


def test_account_status_transitions_are_explicit_and_closed_is_terminal() -> None:
    suspended = account().transition_status(AccountStatus.SUSPENDED, at=NOW)
    active = suspended.transition_status(AccountStatus.ACTIVE, at=NOW)
    closed = active.transition_status(AccountStatus.CLOSED, at=NOW)

    assert suspended.status is AccountStatus.SUSPENDED
    assert active.status is AccountStatus.ACTIVE
    assert closed.status is AccountStatus.CLOSED
    with pytest.raises(InvalidAccountStatusTransitionError):
        closed.transition_status(AccountStatus.ACTIVE, at=NOW)


def test_payment_lifecycle_and_balance_are_deterministic() -> None:
    result = authorize_payment(
        account(),
        command(),
        transaction_id="transaction-1",
        at=NOW,
    )

    assert result.account.balance == Decimal("75.00")
    assert result.transaction.balance_before == Decimal("100.00")
    assert result.transaction.balance_after == Decimal("75.00")
    assert result.transaction.status is TransactionStatus.COMPLETED
    assert result.transaction.status_history == (
        TransactionStatus.INITIATED,
        TransactionStatus.AUTHORIZED,
        TransactionStatus.PROCESSING,
        TransactionStatus.COMPLETED,
    )


def test_payment_trace_context_is_preserved_without_changing_idempotency() -> None:
    result = authorize_payment(
        account(), command(correlation_id="request-correlation"), transaction_id="transaction-1", at=NOW
    )

    assert result.transaction.actor_id == "user-1"
    assert result.transaction.correlation_id == "request-correlation"
    assert result.transaction.causation_id == "parent-request"
    assert command().fingerprint == command(correlation_id="another-request").fingerprint


def test_invalid_transaction_transition_is_rejected() -> None:
    result = authorize_payment(
        account(), command(), transaction_id="transaction-1", at=NOW
    )

    with pytest.raises(InvalidTransactionTransitionError):
        result.transaction.transition(TransactionStatus.AUTHORIZED, at=NOW)


def test_idempotency_fingerprint_changes_when_logical_request_changes() -> None:
    assert command().fingerprint == command().fingerprint
    assert command().fingerprint != command(amount="26.00").fingerprint
    assert command().fingerprint == command(key="request-2").fingerprint
    validate_idempotency_reuse(command().fingerprint, command().fingerprint)
    with pytest.raises(IdempotencyConflictError):
        validate_idempotency_reuse(
            command().fingerprint, command(amount="26.00").fingerprint
        )
