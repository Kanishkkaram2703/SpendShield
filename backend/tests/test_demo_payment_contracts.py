"""Isolated tests for the fictional demo-payment contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.demo_payments import (
    MAX_DEMO_TRANSACTION_AMOUNT,
    validate_demo_qr_payload,
)
from app.domain.financial import Account, AccountStatus
from app.main import create_app
from app.repositories.fakes import (
    InMemoryAccountRepository,
    InMemoryAuditRepository,
    InMemoryCategoryRepository,
    InMemoryMerchantRepository,
    InMemoryPaymentRepository,
    InMemoryUserRepository,
)


PASSWORD = "Correct Horse Battery Staple"


def _account(owner_id: str, *, account_id: str | None = None, balance: str = "1000.00") -> Account:
    now = datetime.now(timezone.utc)
    return Account(
        account_id=account_id or str(uuid4()),
        owner_id=owner_id,
        currency="INR",
        balance=Decimal(balance),
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def _app() -> tuple[TestClient, InMemoryAccountRepository, InMemoryPaymentRepository]:
    settings = Settings(
        _env_file=None,
        environment="test",
        auth_secret_key="demo-contract-test-secret-" + ("x" * 64),
        mongodb_uri="",
        cassandra_hosts="",
    )
    users = InMemoryUserRepository()
    accounts = InMemoryAccountRepository()
    payments = InMemoryPaymentRepository()
    application = create_app(
        settings,
        user_repository=users,
        account_repository=accounts,
        audit_repository=InMemoryAuditRepository(),
        payment_repository=payments,
        category_repository=InMemoryCategoryRepository(),
        merchant_repository=InMemoryMerchantRepository(),
    )
    return TestClient(application), accounts, payments


def _login(client: TestClient, email: str) -> tuple[str, str]:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert registered.status_code == 201
    user_id = registered.json()["user_id"]
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    return user_id, f"Bearer {login.json()['access_token']}"


def test_demo_qr_validation_accepts_only_explicit_simulation_payloads() -> None:
    valid = validate_demo_qr_payload(
        '{"type":"demo_merchant","merchantId":"demo-shop-001",'
        '"merchantName":"Demo Shopkeeper","bank":"BJP Bank",'
        '"mode":"simulation"}'
    )
    assert valid["merchant_id"] == "demo-shop-001"

    for payload in (
        '{"type":"merchant","merchantId":"demo-shop-001","merchantName":"Shop","bank":"BJP Bank","mode":"simulation"}',
        '{"type":"demo_merchant","merchantId":"real@bank","merchantName":"Shop","bank":"BJP Bank","mode":"simulation"}',
        "https://real-payment.example/checkout",
    ):
        try:
            validate_demo_qr_payload(payload)
        except ValueError:
            pass
        else:
            raise AssertionError("non-demo QR payload was accepted")


def test_demo_send_is_atomic_and_idempotent_in_isolated_adapters() -> None:
    client, accounts, payments = _app()
    try:
        owner_id, owner_auth = _login(client, "demo-sender@example.com")
        receiver_id, _ = _login(client, "demo-receiver@example.com")
        source = _account(owner_id, balance="1000.00")
        receiver = _account(receiver_id, balance="100.00")
        accounts.create(source)
        accounts.create(receiver)
        payments._accounts.update({source.account_id: source, receiver.account_id: receiver})

        payload = {
            "account_id": source.account_id,
            "receiver_account_id": receiver.account_id,
            "receiver_name": "Demo Receiver",
            "amount": "250.00",
            "currency": "INR",
            "note": "Classroom demo",
        }
        headers = {"Authorization": owner_auth, "Idempotency-Key": "send-once"}
        first = client.post("/api/v1/payments/send", json=payload, headers=headers)
        assert first.status_code == 201
        transaction_id = first.json()["transaction"]["transaction_id"]
        assert first.json()["transaction"]["transaction_type"] == "SEND_MONEY"
        assert first.json()["transaction"]["direction"] == "DEBIT"
        assert first.json()["related_transaction_ids"]

        replay = client.post("/api/v1/payments/send", json=payload, headers=headers)
        assert replay.status_code == 201
        assert replay.json()["transaction"]["transaction_id"] == transaction_id
        assert payments._accounts[source.account_id].balance == Decimal("750.00")
        assert payments._accounts[receiver.account_id].balance == Decimal("350.00")

        conflict = client.post(
            "/api/v1/payments/send",
            json={**payload, "amount": "251.00"},
            headers=headers,
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "idempotency_conflict"
    finally:
        client.close()


def test_demo_manual_and_bank_contracts_reject_invalid_values() -> None:
    client, accounts, payments = _app()
    try:
        owner_id, owner_auth = _login(client, "demo-payment-user@example.com")
        source = _account(owner_id)
        accounts.create(source)
        payments._accounts[source.account_id] = source
        headers = {"Authorization": owner_auth, "Idempotency-Key": "invalid-demo"}

        manual = client.post(
            "/api/v1/payments/manual",
            json={
                "account_id": source.account_id,
                "amount": str(MAX_DEMO_TRANSACTION_AMOUNT + Decimal("0.01")),
                "currency": "INR",
                "merchant_id": "real-merchant-1",
                "merchant_name": "Not demo",
            },
            headers=headers,
        )
        assert manual.status_code == 422

        bank = client.post(
            "/api/v1/payments/bank-transfer",
            json={
                "account_id": source.account_id,
                "amount": "25.00",
                "currency": "INR",
                "beneficiary_name": "Demo Beneficiary",
                "demo_bank_account_number": "123456",
                "demo_bank_code": "REALBANK0001",
            },
            headers={**headers, "Idempotency-Key": "invalid-bank"},
        )
        assert bank.status_code == 422
        assert "internal_error" not in bank.text

        valid_qr_payload = '{"type":"demo_merchant","merchantId":"demo-shop-001","merchantName":"Demo Shopkeeper","bank":"BJP Bank","mode":"simulation"}'
        qr = client.post(
            "/api/v1/payments/qr",
            json={
                "account_id": source.account_id,
                "amount": "10.00",
                "currency": "INR",
                "qr_payload": valid_qr_payload,
            },
            headers={**headers, "Idempotency-Key": "valid-qr"},
        )
        assert qr.status_code == 201
        assert qr.json()["transaction"]["transaction_type"] == "QR_PAYMENT"

        manual_success = client.post(
            "/api/v1/payments/manual",
            json={
                "account_id": source.account_id,
                "amount": "15.00",
                "currency": "INR",
                "merchant_id": "demo-shop-002",
                "merchant_name": "Demo Manual Shop",
            },
            headers={**headers, "Idempotency-Key": "valid-manual"},
        )
        assert manual_success.status_code == 201
        assert manual_success.json()["transaction"]["transaction_type"] == "MANUAL_PAYMENT"

        bank_success = client.post(
            "/api/v1/payments/bank-transfer",
            json={
                "account_id": source.account_id,
                "amount": "20.00",
                "currency": "INR",
                "beneficiary_name": "Demo Beneficiary",
                "demo_bank_account_number": "DEMO-123456",
                "demo_bank_code": "BJP0DEMO1234",
            },
            headers={**headers, "Idempotency-Key": "valid-bank"},
        )
        assert bank_success.status_code == 201
        assert bank_success.json()["transaction"]["transaction_type"] == "BANK_TRANSFER_DEMO"
    finally:
        client.close()


def test_self_transfer_requires_distinct_owned_destination_and_records_link() -> None:
    client, accounts, payments = _app()
    try:
        owner_id, owner_auth = _login(client, "self-transfer-user@example.com")
        source = _account(owner_id, balance="1000.00")
        destination = _account(owner_id, balance="50.00")
        accounts.create(source)
        payments._accounts.update({source.account_id: source, destination.account_id: destination})
        response = client.post(
            "/api/v1/payments/self-transfer",
            json={
                "account_id": source.account_id,
                "destination_account_id": destination.account_id,
                "amount": "100.00",
                "currency": "INR",
            },
            headers={"Authorization": owner_auth, "Idempotency-Key": "self-once"},
        )
        assert response.status_code == 201
        assert response.json()["transaction"]["transaction_type"] == "SELF_TRANSFER_DEBIT"
        assert response.json()["related_transaction_ids"]
        assert payments._accounts[source.account_id].balance == Decimal("900.00")
        assert payments._accounts[destination.account_id].balance == Decimal("150.00")
    finally:
        client.close()
