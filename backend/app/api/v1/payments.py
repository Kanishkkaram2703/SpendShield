"""Authenticated API boundary for controlled fictional payments."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.api.v1.dependencies import (
    get_account_service,
    get_current_user,
    get_payment_service,
    get_optional_demo_merchant_repository,
    get_cards_repository,
    get_optional_demo_security_repository,
)
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.domain.demo_payments import (
    validate_demo_bank_details,
    validate_demo_merchant,
    validate_demo_qr_payload,
    validate_demo_text,
)
from app.domain.financial import (
    FinancialDomainError,
    PaymentCommand,
    TransactionChannel,
    TransactionDirection,
    TransactionType,
    TransactionStatus,
)
from app.repositories.users import UserRecord
from app.schemas.payments import (
    PaymentCreateRequest,
    PaymentHistoryResponse,
    PaymentResponse,
    PaymentTransactionResponse,
)
from app.schemas.demo_payments import (
    BankTransferRequest,
    CardPaymentRequest,
    DemoAccountOperationRequest,
    DemoPaymentResponse,
    DemoQRValidateRequest,
    DemoQRValidationResponse,
    ManualPaymentRequest,
    PhonePaymentRequest,
    QRPaymentRequest,
    SelfTransferRequest,
    SendMoneyRequest,
)
from app.schemas.demo_modules import BillPaymentRequest
from app.services.account_service import AccountService
from app.services.payment_service import PaymentService
from app.services.demo_security_service import require_demo_mpin
from app.repositories.demo_merchants import DemoMerchantRepositoryProtocol
from app.repositories.demo_resources import DemoResourceRepository

router = APIRouter(prefix="/payments", tags=["payments"])
LOGGER = get_logger(__name__)


def _invalid_demo_request(exc: Exception) -> AppError:
    # The exception message contains only domain validation text; request
    # payloads, MPINs, tokens, and QR contents are intentionally excluded.
    LOGGER.warning(
        "demo_payment_validation_failed reason=%s error_type=%s",
        str(exc),
        type(exc).__name__,
    )
    return AppError(
        code="invalid_demo_payment_request",
        message="The demo payment details are invalid.",
        status_code=422,
    )


def _invalid_qr_request(exc: Exception) -> AppError:
    """Return a useful, non-sensitive error for rejected demo QR content."""

    reason = str(exc)
    if "malformed" in reason.casefold():
        code = "demo_qr_malformed"
        message = "This is not a valid SpendShield demo QR."
    elif "incomplete" in reason.casefold():
        code = "demo_qr_incomplete"
        message = "Merchant data is incomplete."
    elif "unsupported" in reason.casefold() or "supported" in reason.casefold():
        code = "demo_qr_unsupported"
        message = "This QR format is unsupported."
    else:
        code = "demo_qr_invalid"
        message = "This is not a valid SpendShield demo QR."
    LOGGER.warning(
        "demo_qr_validation_failed code=%s reason=%s error_type=%s",
        code,
        reason,
        type(exc).__name__,
    )
    return AppError(code=code, message=message, status_code=422)


def _qr_category_snapshot(merchant: dict[str, str | int]) -> dict[str, str]:
    """Build the complete category snapshot required by the financial domain.

    Demo QR merchants have their own small registry and intentionally do not
    participate in the general merchant/category catalog. Their human-readable
    category still belongs in the transaction, so provide stable demo-local
    identifiers rather than passing a partial category snapshot.
    """

    merchant_id = str(merchant["merchant_id"]).lower()
    safe_id = "".join(character if character.isalnum() else "-" for character in merchant_id)
    safe_id = "-".join(part for part in safe_id.split("-") if part)
    return {
        "category_id": "demo-merchant",
        "category_name": str(merchant.get("category") or "Demo merchant"),
        "subcategory_id": f"merchant-{safe_id}",
        "subcategory_name": "Demo merchant",
    }


def _demo_command(
    *,
    account_id: str,
    owner_id: str,
    amount,
    currency: str,
    idempotency_key: str,
    transaction_channel: TransactionChannel,
    transaction_type: TransactionType,
    request: Request,
    causation_id: str | None,
    note: str | None = None,
    **kwargs,
) -> PaymentCommand:
    try:
        return PaymentCommand(
            account_id=account_id,
            owner_id=owner_id,
            amount=amount,
            currency=currency,
            idempotency_key=idempotency_key,
            transaction_channel=transaction_channel,
            transaction_type=transaction_type,
            note=note,
            correlation_id=request.state.request_id,
            causation_id=causation_id,
            **kwargs,
        )
    except FinancialDomainError as exc:
        raise _invalid_demo_request(exc) from exc


def _demo_response(
    execution,
    *,
    request: Request,
    related_transaction_ids: list[str] | None = None,
    merchant: dict[str, str] | None = None,
) -> DemoPaymentResponse:
    return DemoPaymentResponse.from_execution(
        execution,
        request_id=request.state.request_id,
        related_transaction_ids=related_transaction_ids,
        merchant=merchant,
    )


def _resolve_qr_merchant(
    raw_payload: str,
    repository: DemoMerchantRepositoryProtocol | None,
) -> dict[str, str | int]:
    try:
        parsed = validate_demo_qr_payload(raw_payload)
    except FinancialDomainError as exc:
        raise _invalid_qr_request(exc) from exc
    if repository is None:
        return parsed
    if int(parsed.get("version", 0)) != 1:
        raise AppError(
            code="demo_qr_version_unsupported",
            message="Only versioned SpendShield demo merchant QR codes are accepted.",
            status_code=422,
        )
    merchant = repository.get(str(parsed["merchant_id"]))
    if merchant is None:
        raise AppError(
            code="demo_merchant_not_found",
            message="The QR merchant is not registered in the demo merchant registry.",
            status_code=404,
        )
    if str(merchant.get("status", "ACTIVE")) != "ACTIVE":
        raise AppError(
            code="demo_merchant_inactive",
            message="This demo merchant is not currently accepting simulated payments.",
            status_code=409,
        )
    for payload_key, record_key in (
        ("merchant_name", "merchant_name"),
        ("category", "category"),
        ("demo_bank", "demo_bank"),
        ("merchant_account_id", "merchant_account_id"),
    ):
        if str(parsed[payload_key]) != str(merchant[record_key]):
            raise AppError(
                code="demo_qr_registry_mismatch",
                message="The QR payload does not match the registered demo merchant.",
                status_code=422,
            )
    return {
        "version": 1,
        "merchant_id": str(merchant["merchant_id"]),
        "merchant_name": str(merchant["merchant_name"]),
        "category": str(merchant["category"]),
        "demo_bank": str(merchant["demo_bank"]),
        "merchant_account_id": str(merchant["merchant_account_id"]),
        "status": str(merchant.get("status", "ACTIVE")),
    }


@router.post("/send", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def send_money(
    payload: SendMoneyRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoPaymentResponse:
    """Create one server-authorized, two-account simulated send-money transfer."""

    account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    try:
        receiver_name = validate_demo_text(
            payload.receiver_name, field_name="Receiver name", max_length=128
        )
    except FinancialDomainError as exc:
        raise _invalid_demo_request(exc) from exc
    command = _demo_command(
        account_id=str(payload.account_id),
        owner_id=user.user_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.WALLET_SIMULATED,
        transaction_type=TransactionType.SEND_MONEY,
        request=request,
        causation_id=causation_id,
        note=payload.note,
        counterparty_account_id=str(payload.receiver_account_id),
        counterparty_name=receiver_name,
    )
    execution, related_id = service.execute_transfer(
        command,
        destination_account_id=str(payload.receiver_account_id),
        destination_owner_id=None,
        destination_name=receiver_name,
    )
    return _demo_response(execution, request=request, related_transaction_ids=[related_id])


@router.post("/qr/validate", response_model=DemoQRValidationResponse)
def validate_qr(
    payload: DemoQRValidateRequest,
    request: Request,
    _: UserRecord = Depends(get_current_user),
    repository: DemoMerchantRepositoryProtocol | None = Depends(get_optional_demo_merchant_repository),
) -> DemoQRValidationResponse:
    """Validate a demo QR payload without creating a payment."""

    validated = _resolve_qr_merchant(payload.qr_payload, repository)
    return DemoQRValidationResponse(
        valid=True,
        demo_mode=True,
        merchant_id=str(validated["merchant_id"]),
        merchant_name=str(validated["merchant_name"]),
        bank=str(validated.get("bank") or validated.get("demo_bank") or "BJP Bank Demo"),
        mode="simulation",
        version=int(validated.get("version", 1)),
        category=str(validated["category"]) if "category" in validated else None,
        demo_bank=str(validated["demo_bank"]) if "demo_bank" in validated else None,
        merchant_account_id=str(validated["merchant_account_id"]) if "merchant_account_id" in validated else None,
        qr_payload=payload.qr_payload,
        request_id=request.state.request_id,
    )


@router.post("/qr", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def qr_payment(
    payload: QRPaymentRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    service: PaymentService = Depends(get_payment_service),
    repository: DemoMerchantRepositoryProtocol | None = Depends(get_optional_demo_merchant_repository),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoPaymentResponse:
    """Create one debit from a validated demo merchant QR payload."""

    account_service.require_payment_owner(str(payload.account_id), user.user_id)
    merchant = _resolve_qr_merchant(payload.qr_payload, repository)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    command = _demo_command(
        account_id=str(payload.account_id),
        owner_id=user.user_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.QR_SIMULATED,
        transaction_type=TransactionType.QR_PAYMENT,
        request=request,
        causation_id=causation_id,
        note=payload.note,
        merchant_id=merchant["merchant_id"],
        merchant_name=merchant["merchant_name"],
        **_qr_category_snapshot(merchant),
        counterparty_name=merchant["merchant_name"],
    )
    merchant_details = {
        key: str(merchant[key])
        for key in ("merchant_id", "merchant_name", "category", "demo_bank", "merchant_account_id")
        if key in merchant
    }
    return _demo_response(service.execute_demo(command), request=request, merchant=merchant_details)


@router.post("/manual", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def manual_payment(
    payload: ManualPaymentRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoPaymentResponse:
    """Create one debit from explicit demo merchant details."""

    account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    try:
        merchant_id, merchant_name = validate_demo_merchant(
            payload.merchant_id, payload.merchant_name
        )
    except FinancialDomainError as exc:
        raise _invalid_demo_request(exc) from exc
    command = _demo_command(
        account_id=str(payload.account_id),
        owner_id=user.user_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.QR_SIMULATED,
        transaction_type=TransactionType.MANUAL_PAYMENT,
        request=request,
        causation_id=causation_id,
        note=payload.note,
        merchant_id=merchant_id,
        merchant_name=merchant_name,
    )
    return _demo_response(service.execute_demo(command), request=request)


@router.post("/bank-transfer", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def bank_transfer(
    payload: BankTransferRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoPaymentResponse:
    """Create one simulated BJP Bank transfer without contacting a bank."""

    account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    try:
        account_number, bank_code, beneficiary_name = validate_demo_bank_details(
            payload.demo_bank_account_number,
            payload.demo_bank_code,
            payload.beneficiary_name,
        )
    except FinancialDomainError as exc:
        raise _invalid_demo_request(exc) from exc
    command = _demo_command(
        account_id=str(payload.account_id),
        owner_id=user.user_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.BANK_SIMULATED,
        transaction_type=TransactionType.BANK_TRANSFER_DEMO,
        request=request,
        causation_id=causation_id,
        note=payload.remarks or payload.note,
        beneficiary_name=beneficiary_name,
        demo_bank_account_number=account_number,
        demo_bank_code=bank_code,
        counterparty_name=beneficiary_name,
    )
    return _demo_response(service.execute_demo(command), request=request)


@router.post("/self-transfer", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def self_transfer(
    payload: SelfTransferRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoPaymentResponse:
    """Move simulated funds between two distinct owned demo accounts."""

    account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    command = _demo_command(
        account_id=str(payload.account_id),
        owner_id=user.user_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.BANK_SIMULATED,
        transaction_type=TransactionType.SELF_TRANSFER_DEBIT,
        request=request,
        causation_id=causation_id,
        note=payload.note,
        counterparty_account_id=str(payload.destination_account_id),
    )
    execution, related_id = service.execute_transfer(
        command,
        destination_account_id=str(payload.destination_account_id),
        destination_owner_id=user.user_id,
        destination_name="Self transfer destination",
    )
    return _demo_response(execution, request=request, related_transaction_ids=[related_id])


@router.post("/deposit", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def demo_deposit(
    payload: DemoAccountOperationRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoPaymentResponse:
    """Credit one owned account with fictional demo funds."""

    account = account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    command = _demo_command(
        account_id=account.account_id,
        owner_id=user.user_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.BANK_SIMULATED,
        transaction_type=TransactionType.DEMO_DEPOSIT,
        request=request,
        causation_id=causation_id,
        note=payload.reason or payload.note,
        direction=TransactionDirection.CREDIT,
        counterparty_name="BJP Bank demo deposit",
    )
    return _demo_response(service.execute_demo(command), request=request)


@router.post("/withdraw", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def demo_withdrawal(
    payload: DemoAccountOperationRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoPaymentResponse:
    """Debit one owned account with fictional demo funds."""

    account = account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    command = _demo_command(
        account_id=account.account_id,
        owner_id=user.user_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.BANK_SIMULATED,
        transaction_type=TransactionType.DEMO_WITHDRAWAL,
        request=request,
        causation_id=causation_id,
        note=payload.reason or payload.note,
        direction=TransactionDirection.DEBIT,
        counterparty_name="BJP Bank demo withdrawal",
    )
    return _demo_response(service.execute_demo(command), request=request)


@router.post("/card", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def demo_card_payment(
    payload: CardPaymentRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    cards: DemoResourceRepository = Depends(get_cards_repository),
    service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoPaymentResponse:
    """Execute a fictional card payment only while the demo card is active."""

    account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    card = cards.get(user.user_id, str(payload.card_id))
    if card is None:
        raise AppError(code="card_not_found", message="The demo card was not found.", status_code=404)
    if card.get("status") != "ACTIVE":
        raise AppError(code="card_not_active", message="The demo card is not active.", status_code=409)
    if payload.amount > Decimal(str(card.get("spending_limit", "0"))):
        raise AppError(code="card_spending_limit_exceeded", message="The demo card spending limit was exceeded.", status_code=409)
    command = _demo_command(
        account_id=str(payload.account_id),
        owner_id=user.user_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.CARD_SIMULATED,
        transaction_type=TransactionType.CARD_PAYMENT_DEMO,
        request=request,
        causation_id=causation_id,
        note=payload.note,
        counterparty_name=payload.merchant_name.strip(),
    )
    return _demo_response(service.execute_demo(command), request=request)


@router.post("/bill", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def demo_bill_payment(
    payload: BillPaymentRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoPaymentResponse:
    """Debit an owned account for a fictional, provider-free bill payment."""

    account = account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    transaction_types = {
        "MOBILE_RECHARGE": TransactionType.MOBILE_RECHARGE_DEMO,
        "ELECTRICITY": TransactionType.ELECTRICITY_BILL_DEMO,
        "WATER": TransactionType.WATER_BILL_DEMO,
        "GAS": TransactionType.GAS_BILL_DEMO,
        "INTERNET": TransactionType.INTERNET_BILL_DEMO,
        "DTH": TransactionType.DTH_RECHARGE_DEMO,
        "POSTPAID": TransactionType.POSTPAID_BILL_DEMO,
        "LOAN_EMI": TransactionType.LOAN_EMI_DEMO,
    }
    command = _demo_command(
        account_id=account.account_id,
        owner_id=user.user_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.BANK_SIMULATED,
        transaction_type=transaction_types[payload.category],
        request=request,
        causation_id=causation_id,
        note=payload.note,
        counterparty_name=payload.provider,
        beneficiary_name=payload.identifier,
    )
    return _demo_response(service.execute_demo(command), request=request)


@router.post("/phone", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def phone_payment(
    payload: PhonePaymentRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
    causation_id: Annotated[str | None, Header(alias="X-Causation-ID", min_length=1, max_length=128)] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> DemoPaymentResponse:
    """Create a debit-only fictional phone-number demo payment."""

    account = account_service.require_payment_owner(str(payload.account_id), user.user_id)
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    command = _demo_command(
        account_id=account.account_id,
        owner_id=user.user_id,
        amount=payload.amount,
        currency=payload.currency,
        idempotency_key=idempotency_key,
        transaction_channel=TransactionChannel.WALLET_SIMULATED,
        transaction_type=TransactionType.SEND_MONEY,
        request=request,
        causation_id=causation_id,
        note=payload.note,
        counterparty_name=payload.phone_number,
    )
    return _demo_response(service.execute_demo(command), request=request)


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    payload: PaymentCreateRequest,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=128,
            description="Client-generated key for safe payment retries.",
        ),
    ],
    causation_id: Annotated[
        str | None,
        Header(alias="X-Causation-ID", min_length=1, max_length=128),
    ] = None,
    user: UserRecord = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    service: PaymentService = Depends(get_payment_service),
    security_repository: DemoResourceRepository | None = Depends(get_optional_demo_security_repository),
) -> PaymentResponse:
    """Create one authenticated, owner-authorized fictional payment."""

    account_service.require_payment_owner(
        str(payload.account_id),
        user.user_id,
    )
    require_demo_mpin(security_repository, user.user_id, payload.demo_mpin)
    try:
        command = PaymentCommand(
            account_id=str(payload.account_id),
            owner_id=user.user_id,
            amount=payload.amount,
            currency=payload.currency,
            idempotency_key=idempotency_key,
            transaction_channel=payload.transaction_channel,
            note=payload.note,
            merchant_id=str(payload.merchant_id),
            correlation_id=request.state.request_id,
            causation_id=causation_id,
        )
    except FinancialDomainError as exc:
        raise AppError(
            code="invalid_payment_request",
            message="The payment request violates a financial rule.",
            status_code=422,
        ) from exc

    execution = service.execute(command)
    return PaymentResponse(
        transaction=PaymentTransactionResponse.from_execution(execution),
        request_id=request.state.request_id,
    )


@router.get(
    "",
    response_model=PaymentHistoryResponse,
)
def list_payments(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: UUID | None = Query(default=None),
    status_filter: TransactionStatus | None = Query(default=None, alias="status"),
    merchant_id: UUID | None = Query(default=None),
    user: UserRecord = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentHistoryResponse:
    """Return a bounded page of the authenticated user's current payments."""

    page = service.list_for_owner(
        user.user_id,
        limit=limit,
        cursor=str(cursor) if cursor is not None else None,
        status=status_filter,
        merchant_id=str(merchant_id) if merchant_id is not None else None,
    )
    return PaymentHistoryResponse(
        transactions=[
            PaymentTransactionResponse.from_execution(item) for item in page.items
        ],
        next_cursor=page.next_cursor,
        request_id=request.state.request_id,
    )


@router.get(
    "/{transaction_id}",
    response_model=PaymentResponse,
)
def get_payment(
    transaction_id: UUID,
    request: Request,
    user: UserRecord = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Return one current payment only when owned by the authenticated user."""

    execution = service.get_for_owner(
        str(transaction_id),
        owner_id=user.user_id,
    )
    return PaymentResponse(
        transaction=PaymentTransactionResponse.from_execution(execution),
        request_id=request.state.request_id,
    )


__all__ = ["router"]
