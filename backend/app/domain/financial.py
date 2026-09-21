"""Financial value objects and invariants independent of HTTP or databases."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Any

MONEY_QUANTUM = Decimal("0.01")


class FinancialDomainError(ValueError):
    """Base class for expected financial-domain rule failures."""


class InvalidMoneyError(FinancialDomainError):
    """Raised when a money value is malformed or outside the allowed range."""


class AccountNotActiveError(FinancialDomainError):
    """Raised when a financial operation targets a non-active account."""


class InsufficientFundsError(FinancialDomainError):
    """Raised when an account cannot cover a debit."""


class InvalidTransactionTransitionError(FinancialDomainError):
    """Raised when a transaction lifecycle transition is not allowed."""


class InvalidAccountStatusTransitionError(FinancialDomainError):
    """Raised when an account status change is not allowed."""


class IdempotencyConflictError(FinancialDomainError):
    """Raised when one key is reused for a different logical request."""


class PaymentInProgressError(FinancialDomainError):
    """Raised when a prior payment attempt needs recovery or completion."""


class PaymentConcurrencyError(FinancialDomainError):
    """Raised when a compare-and-set payment reservation loses a race."""


class AccountStatus(str, Enum):
    """Current account states owned by MongoDB."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


VALID_ACCOUNT_STATUS_TRANSITIONS: dict[
    AccountStatus, frozenset[AccountStatus]
] = {
    AccountStatus.ACTIVE: frozenset(
        {AccountStatus.SUSPENDED, AccountStatus.CLOSED}
    ),
    AccountStatus.SUSPENDED: frozenset(
        {AccountStatus.ACTIVE, AccountStatus.CLOSED}
    ),
    AccountStatus.CLOSED: frozenset(),
}


class TransactionStatus(str, Enum):
    """Explicit transaction lifecycle states."""

    INITIATED = "INITIATED"
    AUTHORIZED = "AUTHORIZED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class TransactionChannel(str, Enum):
    """Explicit channel vocabulary for simulated operational payments."""

    QR_SIMULATED = "QR_SIMULATED"
    CARD_SIMULATED = "CARD_SIMULATED"
    WALLET_SIMULATED = "WALLET_SIMULATED"
    BANK_SIMULATED = "BANK_SIMULATED"


class TransactionType(str, Enum):
    """Explicit fictional operation vocabulary used in transaction history."""

    MERCHANT_PAYMENT = "MERCHANT_PAYMENT"
    SEND_MONEY = "SEND_MONEY"
    SEND_MONEY_CREDIT = "SEND_MONEY_CREDIT"
    QR_PAYMENT = "QR_PAYMENT"
    MANUAL_PAYMENT = "MANUAL_PAYMENT"
    BANK_TRANSFER_DEMO = "BANK_TRANSFER_DEMO"
    SELF_TRANSFER_DEBIT = "SELF_TRANSFER_DEBIT"
    SELF_TRANSFER_CREDIT = "SELF_TRANSFER_CREDIT"
    DEMO_DEPOSIT = "DEMO_DEPOSIT"
    DEMO_WITHDRAWAL = "DEMO_WITHDRAWAL"
    MOBILE_RECHARGE_DEMO = "MOBILE_RECHARGE_DEMO"
    ELECTRICITY_BILL_DEMO = "ELECTRICITY_BILL_DEMO"
    WATER_BILL_DEMO = "WATER_BILL_DEMO"
    GAS_BILL_DEMO = "GAS_BILL_DEMO"
    INTERNET_BILL_DEMO = "INTERNET_BILL_DEMO"
    DTH_RECHARGE_DEMO = "DTH_RECHARGE_DEMO"
    POSTPAID_BILL_DEMO = "POSTPAID_BILL_DEMO"
    LOAN_EMI_DEMO = "LOAN_EMI_DEMO"
    CARD_PAYMENT_DEMO = "CARD_PAYMENT_DEMO"
    SUBSCRIPTION_PAYMENT_DEMO = "SUBSCRIPTION_PAYMENT_DEMO"


class TransactionDirection(str, Enum):
    """Whether a history record debits or credits the represented account."""

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


VALID_TRANSACTION_TRANSITIONS: dict[
    TransactionStatus, frozenset[TransactionStatus]
] = {
    TransactionStatus.INITIATED: frozenset(
        {TransactionStatus.AUTHORIZED, TransactionStatus.REJECTED}
    ),
    TransactionStatus.AUTHORIZED: frozenset(
        {TransactionStatus.PROCESSING, TransactionStatus.FAILED}
    ),
    TransactionStatus.PROCESSING: frozenset(
        {TransactionStatus.COMPLETED, TransactionStatus.FAILED}
    ),
    TransactionStatus.COMPLETED: frozenset({TransactionStatus.REVERSED}),
    TransactionStatus.REJECTED: frozenset(),
    TransactionStatus.FAILED: frozenset(),
    TransactionStatus.REVERSED: frozenset(),
}


def utc_now() -> datetime:
    """Return an explicit timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def normalize_money(value: Decimal | int | str, *, allow_zero: bool = True) -> Decimal:
    """Normalize exact monetary input to two decimal places."""

    if isinstance(value, bool):
        raise InvalidMoneyError("Money values must be numeric.")
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidMoneyError("Money values must be numeric.") from exc
    if not decimal_value.is_finite():
        raise InvalidMoneyError("Money values must be finite.")
    normalized = decimal_value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    if normalized < 0 or (not allow_zero and normalized <= 0):
        raise InvalidMoneyError("Money values must satisfy the domain range.")
    return normalized


def normalize_currency(value: str) -> str:
    """Normalize and validate a three-letter currency code."""

    currency = value.strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise FinancialDomainError("Currency must be a three-letter code.")
    return currency


def normalize_idempotency_key(value: str) -> str:
    """Normalize a bounded idempotency key without accepting blank values."""

    key = value.strip()
    if not 1 <= len(key) <= 128:
        raise FinancialDomainError("Idempotency key must contain 1 to 128 characters.")
    return key


@dataclass(frozen=True, slots=True)
class Account:
    """Authoritative current account state."""

    account_id: str
    owner_id: str
    currency: str
    balance: Decimal
    status: AccountStatus
    created_at: datetime
    updated_at: datetime
    version: int = 0
    holder_name: str | None = None
    demo_account_number: str | None = None
    demo_bank_code: str | None = None
    demo_branch: str | None = None
    account_type: str | None = None

    def __post_init__(self) -> None:
        if not self.account_id.strip() or not self.owner_id.strip():
            raise FinancialDomainError("Account and owner identifiers are required.")
        object.__setattr__(self, "currency", normalize_currency(self.currency))
        object.__setattr__(self, "balance", normalize_money(self.balance))
        if self.version < 0:
            raise FinancialDomainError("Account version cannot be negative.")

    def debit(self, amount: Decimal | int | str, *, at: datetime) -> "Account":
        """Return the next account state after a valid debit."""

        if self.status is not AccountStatus.ACTIVE:
            raise AccountNotActiveError("Only active accounts can be debited.")
        normalized_amount = normalize_money(amount, allow_zero=False)
        if normalized_amount > self.balance:
            raise InsufficientFundsError("Account balance is insufficient.")
        return replace(
            self,
            balance=normalize_money(self.balance - normalized_amount),
            updated_at=at,
            version=self.version + 1,
        )

    def credit(self, amount: Decimal | int | str, *, at: datetime) -> "Account":
        """Return the next account state after a valid simulated credit."""

        if self.status is not AccountStatus.ACTIVE:
            raise AccountNotActiveError("Only active accounts can be credited.")
        normalized_amount = normalize_money(amount, allow_zero=False)
        return replace(
            self,
            balance=normalize_money(self.balance + normalized_amount),
            updated_at=at,
            version=self.version + 1,
        )

    def transition_status(
        self,
        new_status: AccountStatus,
        *,
        at: datetime,
    ) -> "Account":
        """Return the next account state after a valid status transition."""

        if new_status not in VALID_ACCOUNT_STATUS_TRANSITIONS[self.status]:
            raise InvalidAccountStatusTransitionError(
                f"Cannot transition {self.status} to {new_status}."
            )
        return replace(
            self,
            status=new_status,
            updated_at=at,
            version=self.version + 1,
        )


@dataclass(frozen=True, slots=True)
class Transaction:
    """Current transaction state plus its in-memory lifecycle history."""

    transaction_id: str
    account_id: str
    owner_id: str
    currency: str
    amount: Decimal
    status: TransactionStatus
    idempotency_key: str
    request_fingerprint: str
    created_at: datetime
    updated_at: datetime
    balance_before: Decimal
    balance_after: Decimal | None = None
    merchant_id: str | None = None
    merchant_name: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    subcategory_id: str | None = None
    subcategory_name: str | None = None
    failure_reason: str | None = None
    status_history: tuple[TransactionStatus, ...] = field(
        default=(TransactionStatus.INITIATED,)
    )
    actor_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    transaction_channel: TransactionChannel | None = None
    note: str | None = None
    transaction_type: TransactionType = TransactionType.MERCHANT_PAYMENT
    direction: TransactionDirection = TransactionDirection.DEBIT
    counterparty_account_id: str | None = None
    counterparty_name: str | None = None
    beneficiary_name: str | None = None
    demo_bank_account_number: str | None = None
    demo_bank_code: str | None = None
    transfer_reference: str | None = None
    demo_mode: bool = True

    def __post_init__(self) -> None:
        if not self.transaction_id.strip() or not self.account_id.strip():
            raise FinancialDomainError("Transaction and account identifiers are required.")
        if not self.owner_id.strip():
            raise FinancialDomainError("Transaction owner is required.")
        object.__setattr__(self, "currency", normalize_currency(self.currency))
        object.__setattr__(
            self, "amount", normalize_money(self.amount, allow_zero=False)
        )
        object.__setattr__(self, "balance_before", normalize_money(self.balance_before))
        if self.balance_after is not None:
            object.__setattr__(
                self, "balance_after", normalize_money(self.balance_after)
            )
        object.__setattr__(self, "idempotency_key", normalize_idempotency_key(self.idempotency_key))
        if len(self.request_fingerprint) != 64:
            raise FinancialDomainError("Transaction request fingerprint is invalid.")
        category_values = (
            self.category_id,
            self.category_name,
            self.subcategory_id,
            self.subcategory_name,
        )
        if any(value is not None for value in category_values) and not all(
            value is not None and value.strip() for value in category_values
        ):
            raise FinancialDomainError(
                "Transaction category snapshot must be complete when present."
            )
        if not self.status_history or self.status_history[-1] is not self.status:
            raise FinancialDomainError("Transaction history must end at current status.")
        if not isinstance(self.transaction_type, TransactionType):
            try:
                object.__setattr__(self, "transaction_type", TransactionType(self.transaction_type))
            except (TypeError, ValueError) as exc:
                raise FinancialDomainError("Transaction type is invalid.") from exc
        if not isinstance(self.direction, TransactionDirection):
            try:
                object.__setattr__(self, "direction", TransactionDirection(self.direction))
            except (TypeError, ValueError) as exc:
                raise FinancialDomainError("Transaction direction is invalid.") from exc

    def transition(
        self,
        new_status: TransactionStatus,
        *,
        at: datetime,
        reason: str | None = None,
    ) -> "Transaction":
        """Apply one documented lifecycle transition."""

        if new_status not in VALID_TRANSACTION_TRANSITIONS[self.status]:
            raise InvalidTransactionTransitionError(
                f"Cannot transition {self.status} to {new_status}."
            )
        return replace(
            self,
            status=new_status,
            updated_at=at,
            failure_reason=reason if new_status in {
                TransactionStatus.REJECTED,
                TransactionStatus.FAILED,
            } else self.failure_reason,
            status_history=self.status_history + (new_status,),
        )


@dataclass(frozen=True, slots=True)
class PaymentCommand:
    """Validated input required to authorize a future payment operation."""

    account_id: str
    owner_id: str
    amount: Decimal
    currency: str
    idempotency_key: str
    transaction_channel: TransactionChannel
    merchant_id: str | None = None
    merchant_name: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    subcategory_id: str | None = None
    subcategory_name: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    note: str | None = None
    transaction_type: TransactionType = TransactionType.MERCHANT_PAYMENT
    direction: TransactionDirection = TransactionDirection.DEBIT
    counterparty_account_id: str | None = None
    counterparty_name: str | None = None
    beneficiary_name: str | None = None
    demo_bank_account_number: str | None = None
    demo_bank_code: str | None = None
    transfer_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.account_id.strip() or not self.owner_id.strip():
            raise FinancialDomainError("Payment account and owner are required.")
        object.__setattr__(
            self, "amount", normalize_money(self.amount, allow_zero=False)
        )
        object.__setattr__(self, "currency", normalize_currency(self.currency))
        object.__setattr__(
            self, "idempotency_key", normalize_idempotency_key(self.idempotency_key)
        )
        if not isinstance(self.transaction_channel, TransactionChannel):
            try:
                object.__setattr__(
                    self, "transaction_channel", TransactionChannel(self.transaction_channel)
                )
            except (TypeError, ValueError) as exc:
                raise FinancialDomainError("Transaction channel is invalid.") from exc
        if not isinstance(self.transaction_type, TransactionType):
            try:
                object.__setattr__(self, "transaction_type", TransactionType(self.transaction_type))
            except (TypeError, ValueError) as exc:
                raise FinancialDomainError("Transaction type is invalid.") from exc
        if not isinstance(self.direction, TransactionDirection):
            try:
                object.__setattr__(self, "direction", TransactionDirection(self.direction))
            except (TypeError, ValueError) as exc:
                raise FinancialDomainError("Transaction direction is invalid.") from exc
        if self.note is not None:
            normalized_note = self.note.strip()
            if len(normalized_note) > 256:
                raise FinancialDomainError("Payment note cannot exceed 256 characters.")
            object.__setattr__(self, "note", normalized_note or None)
        category_values = (
            self.category_id,
            self.category_name,
            self.subcategory_id,
            self.subcategory_name,
        )
        if any(value is not None for value in category_values) and not all(
            value is not None and value.strip() for value in category_values
        ):
            raise FinancialDomainError(
                "Payment category snapshot must be complete when present."
            )

    @property
    def fingerprint(self) -> str:
        """Return a stable hash for same-key/same-request comparisons."""

        value = {
            "account_id": self.account_id,
            "owner_id": self.owner_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "merchant_id": self.merchant_id,
            "transaction_channel": self.transaction_channel.value,
            # Notes are non-authoritative display metadata. A retry with the
            # same operation key must replay the committed financial effect
            # even if an older client omitted its note on retry.
            "transaction_type": self.transaction_type.value,
            "direction": self.direction.value,
            "counterparty_account_id": self.counterparty_account_id,
            "counterparty_name": self.counterparty_name,
            "beneficiary_name": self.beneficiary_name,
            "demo_bank_account_number": self.demo_bank_account_number,
            "demo_bank_code": self.demo_bank_code,
        }
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def validate_idempotency_reuse(
    existing_fingerprint: str,
    requested_fingerprint: str,
) -> None:
    """Reject reuse of one idempotency key for a different request."""

    if existing_fingerprint != requested_fingerprint:
        raise IdempotencyConflictError(
            "Idempotency key was already used for a different request."
        )


@dataclass(frozen=True, slots=True)
class PaymentExecution:
    """Deterministic domain result before persistence/event publication."""

    account: Account
    transaction: Transaction


def authorize_payment(
    account: Account,
    command: PaymentCommand,
    *,
    transaction_id: str,
    at: datetime | None = None,
) -> PaymentExecution:
    """Apply domain rules and construct a completed fictional payment."""

    timestamp = at or utc_now()
    if account.account_id != command.account_id or account.owner_id != command.owner_id:
        raise FinancialDomainError("Payment does not belong to the requested account owner.")
    if account.currency != command.currency:
        raise FinancialDomainError("Payment currency does not match the account currency.")

    updated_account = (
        account.credit(command.amount, at=timestamp)
        if command.direction is TransactionDirection.CREDIT
        else account.debit(command.amount, at=timestamp)
    )
    transaction = Transaction(
        transaction_id=transaction_id,
        account_id=account.account_id,
        owner_id=account.owner_id,
        currency=account.currency,
        amount=command.amount,
        status=TransactionStatus.INITIATED,
        idempotency_key=command.idempotency_key,
        request_fingerprint=command.fingerprint,
        transaction_channel=command.transaction_channel,
        created_at=timestamp,
        updated_at=timestamp,
        balance_before=account.balance,
        balance_after=updated_account.balance,
        merchant_id=command.merchant_id,
        merchant_name=command.merchant_name,
        category_id=command.category_id,
        category_name=command.category_name,
        subcategory_id=command.subcategory_id,
        subcategory_name=command.subcategory_name,
        actor_id=command.owner_id,
        correlation_id=command.correlation_id,
        causation_id=command.causation_id,
        note=command.note,
        transaction_type=command.transaction_type,
        direction=command.direction,
        counterparty_account_id=command.counterparty_account_id,
        counterparty_name=command.counterparty_name,
        beneficiary_name=command.beneficiary_name,
        demo_bank_account_number=command.demo_bank_account_number,
        demo_bank_code=command.demo_bank_code,
        transfer_reference=command.transfer_reference,
        demo_mode=True,
    )
    for status in (
        TransactionStatus.AUTHORIZED,
        TransactionStatus.PROCESSING,
        TransactionStatus.COMPLETED,
    ):
        transaction = transaction.transition(status, at=timestamp)
    return PaymentExecution(account=updated_account, transaction=transaction)


__all__ = [
    "Account",
    "AccountNotActiveError",
    "AccountStatus",
    "FinancialDomainError",
    "InvalidAccountStatusTransitionError",
    "IdempotencyConflictError",
    "InsufficientFundsError",
    "InvalidMoneyError",
    "InvalidTransactionTransitionError",
    "MONEY_QUANTUM",
    "PaymentCommand",
    "PaymentExecution",
    "PaymentConcurrencyError",
    "PaymentInProgressError",
    "Transaction",
    "TransactionChannel",
    "TransactionDirection",
    "TransactionStatus",
    "TransactionType",
    "VALID_ACCOUNT_STATUS_TRANSITIONS",
    "VALID_TRANSACTION_TRANSITIONS",
    "authorize_payment",
    "normalize_currency",
    "normalize_idempotency_key",
    "normalize_money",
    "validate_idempotency_reuse",
    "utc_now",
]
