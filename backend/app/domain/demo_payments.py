"""Validation rules shared by the fictional demo-payment contracts.

These rules deliberately accept only demo identifiers and never attempt to
interpret real banking, UPI, or payment-provider instructions.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any

from app.domain.financial import FinancialDomainError, normalize_money

MAX_DEMO_TRANSACTION_AMOUNT = Decimal("1000000.00")
_DEMO_MERCHANT_RE = re.compile(r"^(?:demo-[a-z0-9][a-z0-9-]{2,63}|[A-Z][A-Z0-9-]{4,63})$")
_DEMO_BANK_ACCOUNT_RE = re.compile(r"^DEMO-[0-9]{6,18}$")
_DEMO_BANK_CODE_RE = re.compile(r"^BJP0DEMO[0-9A-Z]{4,7}$")
_REAL_PAYMENT_MARKER_RE = re.compile(
    r"(https?://|upi://|upi[-_ ]?id|paytm|phonepe|googlepay|gpay|@)[^\s]*",
    re.IGNORECASE,
)


def validate_demo_amount(value: Decimal | int | str) -> Decimal:
    """Normalize one positive demo amount within the documented demo limit."""

    amount = normalize_money(value, allow_zero=False)
    if amount > MAX_DEMO_TRANSACTION_AMOUNT:
        raise FinancialDomainError(
            f"Demo transactions cannot exceed {MAX_DEMO_TRANSACTION_AMOUNT}."
        )
    return amount


def validate_demo_text(value: str, *, field_name: str, max_length: int = 128) -> str:
    """Validate required human-readable demo text without accepting control data."""

    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        raise FinancialDomainError(f"{field_name} is invalid.")
    if any(ord(character) < 32 for character in normalized):
        raise FinancialDomainError(f"{field_name} is invalid.")
    return normalized


def validate_demo_merchant(merchant_id: str, merchant_name: str) -> tuple[str, str]:
    """Accept only explicitly namespaced demo merchant identifiers."""

    raw_id = validate_demo_text(merchant_id, field_name="Demo merchant ID", max_length=64)
    normalized_id = raw_id.lower() if raw_id.lower().startswith("demo-") else raw_id.upper()
    normalized_name = validate_demo_text(
        merchant_name, field_name="Demo merchant name", max_length=128
    )
    if not _DEMO_MERCHANT_RE.fullmatch(normalized_id):
        raise FinancialDomainError("Only demo merchant identifiers are supported.")
    return normalized_id, normalized_name


def validate_demo_bank_details(
    account_number: str,
    bank_code: str,
    beneficiary_name: str,
) -> tuple[str, str, str]:
    """Validate the deliberately fictional BJP Bank transfer vocabulary."""

    normalized_account = validate_demo_text(
        account_number, field_name="Demo bank account number", max_length=32
    ).upper()
    normalized_code = validate_demo_text(
        bank_code, field_name="Demo bank code", max_length=32
    ).upper()
    normalized_name = validate_demo_text(
        beneficiary_name, field_name="Beneficiary name", max_length=128
    )
    if not _DEMO_BANK_ACCOUNT_RE.fullmatch(normalized_account):
        raise FinancialDomainError("Only demo bank account numbers are supported.")
    if not _DEMO_BANK_CODE_RE.fullmatch(normalized_code):
        raise FinancialDomainError("Only BJP Bank demo codes are supported.")
    return normalized_account, normalized_code, normalized_name


def validate_demo_qr_payload(raw_payload: str | dict[str, Any]) -> dict[str, str | int]:
    """Parse one versioned demo QR payload without trusting it as a merchant record.

    Registry resolution is deliberately performed by the API boundary after this
    syntactic parse. The legacy shape remains accepted for existing isolated
    contract tests; persisted registry QR payloads use the versioned shape.
    """

    if isinstance(raw_payload, str):
        if len(raw_payload) > 2048 or _REAL_PAYMENT_MARKER_RE.search(raw_payload):
            raise FinancialDomainError("Only demo QR payloads are supported.")
        try:
            payload: Any = json.loads(raw_payload)
        except (TypeError, ValueError) as exc:
            raise FinancialDomainError("The demo QR payload is malformed.") from exc
    else:
        payload = raw_payload

    if not isinstance(payload, dict):
        raise FinancialDomainError("The demo QR payload is malformed.")
    if payload.get("type") == "spendshield_demo_merchant":
        required = (
            "version",
            "qr_type",
            "simulation_only",
            "merchant_id",
            "merchant_name",
            "category",
            "demo_bank",
            "merchant_account_id",
            "status",
        )
        if any(key not in payload for key in required) or payload.get("version") != 1:
            raise FinancialDomainError("The versioned demo QR payload is incomplete.")
        if (
            payload.get("qr_type") != "SPENDSHIELD_DEMO_MERCHANT"
            or payload.get("simulation_only") is not True
        ):
            raise FinancialDomainError("The demo QR simulation markers are invalid.")
        merchant_id, merchant_name = validate_demo_merchant(
            str(payload["merchant_id"]), str(payload["merchant_name"])
        )
        category = validate_demo_text(str(payload["category"]), field_name="Demo merchant category")
        demo_bank = validate_demo_text(str(payload["demo_bank"]), field_name="Demo bank")
        account_id = validate_demo_text(str(payload["merchant_account_id"]), field_name="Demo merchant account", max_length=64)
        status = str(payload["status"])
        if demo_bank != "BJP Bank Demo" or status != "ACTIVE":
            raise FinancialDomainError("Only active BJP Bank demo QR codes are supported.")
        return {
            "version": 1,
            "merchant_id": merchant_id,
            "merchant_name": merchant_name,
            "category": category,
            "demo_bank": demo_bank,
            "merchant_account_id": account_id,
            "status": status,
            "mode": "simulation",
        }

    required = ("type", "merchantId", "merchantName", "bank", "mode")
    if any(key not in payload for key in required):
        raise FinancialDomainError("The demo QR payload is incomplete.")
    if payload.get("type") != "demo_merchant":
        raise FinancialDomainError("The QR code is not a supported demo merchant code.")
    if payload.get("bank") != "BJP Bank" or payload.get("mode") != "simulation":
        raise FinancialDomainError("Only BJP Bank simulation QR codes are supported.")
    merchant_id, merchant_name = validate_demo_merchant(
        str(payload["merchantId"]), str(payload["merchantName"])
    )
    return {
        "version": 0,
        "merchant_id": merchant_id,
        "merchant_name": merchant_name,
        "bank": "BJP Bank",
        "demo_bank": "BJP Bank",
        "mode": "simulation",
    }


def validate_optional_note(value: str | None) -> str | None:
    """Normalize optional notes consistently across all demo flows."""

    if value is None:
        return None
    normalized = value.strip()
    if len(normalized) > 256 or any(ord(character) < 32 for character in normalized):
        raise FinancialDomainError("The note cannot exceed 256 characters.")
    return normalized or None


__all__ = [
    "MAX_DEMO_TRANSACTION_AMOUNT",
    "validate_demo_amount",
    "validate_demo_bank_details",
    "validate_demo_merchant",
    "validate_demo_qr_payload",
    "validate_demo_text",
    "validate_optional_note",
]
