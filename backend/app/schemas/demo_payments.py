"""Request/response contracts for the fictional demo payment flows."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.demo_payments import validate_demo_amount, validate_optional_note
from app.domain.financial import PaymentExecution, normalize_currency
from app.schemas.payments import PaymentTransactionResponse


class DemoPaymentBaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: UUID
    amount: Decimal = Field(gt=0, max_digits=34, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    note: str | None = Field(default=None, max_length=256)
    demo_mpin: str | None = Field(default=None, min_length=6, max_length=6)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value.as_tuple().exponent < -2:
            raise ValueError("Amount must be a finite value with at most two decimals.")
        validate_demo_amount(value)
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        return validate_optional_note(value)

    @field_validator("demo_mpin")
    @classmethod
    def validate_demo_mpin(cls, value: str | None) -> str | None:
        if value is not None and not value.isdigit():
            raise ValueError("The demo MPIN must contain six digits.")
        return value


class SendMoneyRequest(DemoPaymentBaseRequest):
    receiver_account_id: UUID
    receiver_name: str = Field(min_length=1, max_length=128)


class QRPaymentRequest(DemoPaymentBaseRequest):
    qr_payload: str = Field(min_length=1, max_length=2048)


class ManualPaymentRequest(DemoPaymentBaseRequest):
    merchant_id: str = Field(min_length=1, max_length=64)
    merchant_name: str = Field(min_length=1, max_length=128)


class BankTransferRequest(DemoPaymentBaseRequest):
    beneficiary_name: str = Field(min_length=1, max_length=128)
    demo_bank_account_number: str = Field(min_length=1, max_length=32)
    demo_bank_code: str = Field(min_length=1, max_length=32)
    remarks: str | None = Field(default=None, max_length=256)

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value: str | None) -> str | None:
        return validate_optional_note(value)


class SelfTransferRequest(DemoPaymentBaseRequest):
    destination_account_id: UUID


class PhonePaymentRequest(DemoPaymentBaseRequest):
    phone_number: str = Field(min_length=7, max_length=32)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            raise ValueError("Enter a valid demo phone number.")
        return normalized


class CardPaymentRequest(DemoPaymentBaseRequest):
    card_id: UUID
    merchant_name: str = Field(min_length=1, max_length=128)

    @field_validator("merchant_name")
    @classmethod
    def validate_merchant_name(cls, value: str) -> str:
        return value.strip()


class DemoAccountOperationRequest(DemoPaymentBaseRequest):
    """Input for a fictional balance adjustment, never a real deposit."""

    reason: str | None = Field(default=None, max_length=256)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        return validate_optional_note(value)


class DemoPaymentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool = True
    demo_mode: bool = True
    transaction: PaymentTransactionResponse
    related_transaction_ids: list[str] = Field(default_factory=list)
    transfer_reference: str | None = None
    previous_balance: Decimal | None = None
    paid_amount: Decimal | None = None
    remaining_balance: Decimal | None = None
    merchant: dict[str, str] | None = None
    request_id: str

    @classmethod
    def from_execution(
        cls,
        execution: PaymentExecution,
        *,
        request_id: str,
        related_transaction_ids: list[str] | None = None,
        merchant: dict[str, str] | None = None,
    ) -> "DemoPaymentResponse":
        transaction = execution.transaction
        return cls(
            transaction=PaymentTransactionResponse.from_execution(execution),
            related_transaction_ids=related_transaction_ids or [],
            transfer_reference=transaction.transfer_reference,
            previous_balance=transaction.balance_before,
            paid_amount=transaction.amount,
            remaining_balance=transaction.balance_after,
            merchant=merchant,
            request_id=request_id,
        )


class DemoQRValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool = True
    demo_mode: bool = True
    merchant_id: str
    merchant_name: str
    bank: str
    mode: str
    version: int = 1
    category: str | None = None
    demo_bank: str | None = None
    merchant_account_id: str | None = None
    qr_payload: str | None = None
    request_id: str


class DemoQRValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qr_payload: str = Field(min_length=1, max_length=2048)


__all__ = [
    "BankTransferRequest",
    "CardPaymentRequest",
    "DemoAccountOperationRequest",
    "DemoPaymentResponse",
    "DemoPaymentBaseRequest",
    "DemoQRValidationResponse",
    "DemoQRValidateRequest",
    "ManualPaymentRequest",
    "QRPaymentRequest",
    "PhonePaymentRequest",
    "SelfTransferRequest",
    "SendMoneyRequest",
]
