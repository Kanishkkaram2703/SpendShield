"""Public schemas for the controlled fictional payment API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.financial import (
    PaymentExecution,
    TransactionDirection,
    TransactionChannel,
    TransactionStatus,
    TransactionType,
    normalize_currency,
)


class PaymentCreateRequest(BaseModel):
    """Client-controlled fields for one fictional payment request."""

    model_config = ConfigDict(extra="forbid")

    account_id: UUID
    amount: Decimal = Field(gt=0, max_digits=34, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    merchant_id: UUID
    transaction_channel: TransactionChannel
    note: str | None = Field(default=None, max_length=256)
    demo_mpin: str | None = Field(default=None, min_length=6, max_length=6)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        """Reject non-finite values and precision the Decimal128 domain cannot use."""

        if not value.is_finite() or value.as_tuple().exponent < -2:
            raise ValueError("Amount must be a finite value with at most two decimals.")
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        """Normalize the currency without performing conversion."""

        return normalize_currency(value)

    @field_validator("demo_mpin")
    @classmethod
    def validate_demo_mpin(cls, value: str | None) -> str | None:
        if value is not None and not value.isdigit():
            raise ValueError("The demo MPIN must contain six digits.")
        return value

class PaymentTransactionResponse(BaseModel):
    """Safe client-facing transaction state."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    account_id: str
    amount: Decimal
    currency: str
    transaction_channel: TransactionChannel | None
    transaction_type: TransactionType
    direction: TransactionDirection
    note: str | None
    merchant_id: str | None
    merchant_name: str | None
    category_id: str | None
    category_name: str | None
    subcategory_id: str | None
    subcategory_name: str | None
    counterparty_account_id: str | None
    counterparty_name: str | None
    beneficiary_name: str | None
    demo_bank_account_number: str | None
    demo_bank_code: str | None
    transfer_reference: str | None
    demo_mode: bool
    status: TransactionStatus
    status_history: tuple[TransactionStatus, ...]
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_execution(cls, execution: PaymentExecution) -> "PaymentTransactionResponse":
        transaction = execution.transaction
        return cls(
            transaction_id=transaction.transaction_id,
            account_id=transaction.account_id,
            amount=transaction.amount,
            currency=transaction.currency,
            transaction_channel=transaction.transaction_channel,
            transaction_type=transaction.transaction_type,
            direction=transaction.direction,
            note=transaction.note,
            merchant_id=transaction.merchant_id,
            merchant_name=transaction.merchant_name,
            category_id=transaction.category_id,
            category_name=transaction.category_name,
            subcategory_id=transaction.subcategory_id,
            subcategory_name=transaction.subcategory_name,
            counterparty_account_id=transaction.counterparty_account_id,
            counterparty_name=transaction.counterparty_name,
            beneficiary_name=transaction.beneficiary_name,
            demo_bank_account_number=transaction.demo_bank_account_number,
            demo_bank_code=transaction.demo_bank_code,
            transfer_reference=transaction.transfer_reference,
            demo_mode=transaction.demo_mode,
            status=transaction.status,
            status_history=transaction.status_history,
            failure_reason=transaction.failure_reason,
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
        )


class PaymentResponse(BaseModel):
    """Successful payment response."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    transaction: PaymentTransactionResponse
    request_id: str


class PaymentHistoryResponse(BaseModel):
    """Bounded, owner-scoped payment history response."""

    model_config = ConfigDict(extra="forbid")

    success: Literal[True] = True
    transactions: list[PaymentTransactionResponse]
    next_cursor: str | None
    request_id: str


__all__ = [
    "PaymentCreateRequest",
    "PaymentHistoryResponse",
    "PaymentResponse",
    "PaymentTransactionResponse",
]
