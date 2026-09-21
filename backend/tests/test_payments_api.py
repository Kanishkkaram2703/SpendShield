"""Real HTTP integration tests for the controlled fictional payment API."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import Settings
from app.core.exceptions import DatabaseUnavailableError
from app.db.events import CassandraEventRepository
from app.db.manager import DatabaseManager
from app.domain.catalog import CategoryRecord, MerchantRecord, MerchantStatus
from app.domain.financial import Account, AccountStatus
from app.main import create_app
from app.repositories.accounts import MongoAccountRepository
from app.repositories.audit import MongoAuditRepository
from app.repositories.categories import MongoCategoryRepository
from app.repositories.fakes import InMemoryUserRepository
from app.repositories.merchants import MongoMerchantRepository


PASSWORD = "Correct Horse Battery Staple"


def api_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        auth_secret_key="api-test-secret-" + ("x" * 64),
        mongodb_uri="mongodb://127.0.0.1:27018",
        mongodb_replica_set="rs0",
        mongodb_database=f"spendshield_api_test_{uuid4().hex}",
        cassandra_hosts="127.0.0.1",
        cassandra_keyspace="spendshield_events",
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        cassandra_connect_timeout_seconds=5,
    )


def require_services(settings: Settings) -> None:
    manager = DatabaseManager(settings)
    try:
        manager.connect_mongodb()
        manager.connect_cassandra()
        hello = manager.mongo_database.client.admin.command("hello")
        if hello.get("setName") != "rs0" or not hello.get("isWritablePrimary"):
            pytest.skip("MongoDB rs0 is not a writable primary")
    except DatabaseUnavailableError as exc:
        pytest.skip(f"payment API integration service unavailable: {exc}")
    finally:
        manager.close()


@pytest.fixture
def payment_api():
    settings = api_settings()
    require_services(settings)
    manager = DatabaseManager(settings)
    users = InMemoryUserRepository()
    account_repository = MongoAccountRepository(manager)
    audit_repository = MongoAuditRepository(manager)
    category_repository = MongoCategoryRepository(manager)
    merchant_repository = MongoMerchantRepository(manager)
    manager.ensure_mongodb_schema()
    now = datetime.now(timezone.utc)
    category_repository.ensure(
        CategoryRecord(
            category_id="food",
            category_name="Food",
            subcategory_id="cafes",
            subcategory_name="Cafes",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    merchant_repository.create(
        MerchantRecord(
            merchant_id="00000000-0000-0000-0000-000000000001",
            merchant_name="CoffeeHub",
            category_id="food",
            subcategory_id="cafes",
            status=MerchantStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    application = create_app(
        settings,
        user_repository=users,
        database_manager=manager,
        account_repository=account_repository,
        audit_repository=audit_repository,
        category_repository=category_repository,
        merchant_repository=merchant_repository,
    )
    try:
        with TestClient(application) as client:
            yield client, users, manager, account_repository
    finally:
        manager.close()
        cleanup_database(settings)


def cleanup_database(settings: Settings) -> None:
    client = MongoClient(
        settings.mongodb_uri,
        replicaSet=settings.mongodb_replica_set,
        serverSelectionTimeoutMS=3000,
    )
    try:
        try:
            client.drop_database(settings.mongodb_database)
        except PyMongoError:
            pass
    finally:
        client.close()


def register_and_login(client: TestClient, email: str) -> tuple[dict, dict[str, str]]:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert registered.status_code == 201
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert token.status_code == 200
    headers = {
        "Authorization": f"Bearer {token.json()['access_token']}"
    }
    configured = client.put(
        "/api/v1/demo-security/mpin",
        headers=headers,
        json={"pin": "123456", "confirm_pin": "123456"},
    )
    assert configured.status_code == 200, configured.text
    return registered.json(), headers


def create_account(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post("/api/v1/accounts", headers=headers)
    assert response.status_code == 201
    return response.json()


def insert_account(
    repository: MongoAccountRepository,
    *,
    owner_id: str,
    balance: str = "1000.00",
) -> Account:
    now = datetime.now(timezone.utc)
    account = Account(
        account_id=str(uuid4()),
        owner_id=owner_id,
        currency="INR",
        balance=Decimal(balance),
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    repository.create(account)
    return account


def payment_payload(
    account_id: str,
    amount: str = "250.00",
    *,
    note: str | None = None,
) -> dict[str, str]:
    payload = {
        "account_id": account_id,
        "amount": amount,
        "currency": "INR",
        "merchant_id": "00000000-0000-0000-0000-000000000001",
        "transaction_channel": "QR_SIMULATED",
        "demo_mpin": "123456",
    }
    if note is not None:
        payload["note"] = note
    return payload


def test_payment_api_requires_authentication_and_validates_input(payment_api) -> None:
    client, _, _, _ = payment_api
    unauthenticated = client.post(
        "/api/v1/payments",
        json=payment_payload(str(uuid4())),
        headers={"Idempotency-Key": "missing-auth"},
    )
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "authentication_required"

    _, authenticated_headers = register_and_login(
        client,
        "validation-owner@example.com",
    )

    malformed = client.post(
        "/api/v1/payments",
        json={"account_id": "not-an-uuid", "amount": "NaN", "currency": "USD"},
        headers={**authenticated_headers, "Idempotency-Key": "malformed"},
    )
    assert malformed.status_code == 422
    assert "internal_error" not in malformed.text

    for amount in ("0", "-1.00", "1.001", "Infinity"):
        invalid_amount = client.post(
            "/api/v1/payments",
            json=payment_payload(str(uuid4()), amount),
            headers={**authenticated_headers, "Idempotency-Key": f"amount-{amount}"},
        )
        assert invalid_amount.status_code == 422

    invalid_channel = client.post(
        "/api/v1/payments",
        json={**payment_payload(str(uuid4())), "transaction_channel": "NOT_A_CHANNEL"},
        headers={**authenticated_headers, "Idempotency-Key": "invalid-channel"},
    )
    assert invalid_channel.status_code == 422

    invalid_token = client.post(
        "/api/v1/payments",
        json=payment_payload(str(uuid4())),
        headers={
            "Authorization": "Bearer not-a-token",
            "Idempotency-Key": "bad-token",
        },
    )
    assert invalid_token.status_code == 401


def test_payment_api_success_replay_conflict_and_event_trace(payment_api) -> None:
    client, _, manager, account_repository = payment_api
    user, headers = register_and_login(client, "payment-owner@example.com")
    account = create_account(client, headers)
    payment_headers = {
        **headers,
        "Idempotency-Key": "api-payment-once",
        "X-Causation-ID": "api-parent-operation",
        "X-Request-ID": "api-payment-request",
    }

    first = client.post(
        "/api/v1/payments",
        json=payment_payload(account["account_id"], note="Coffee with the team"),
        headers=payment_headers,
    )
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["success"] is True
    assert first_body["transaction"]["status"] == "COMPLETED"
    assert first_body["transaction"]["transaction_channel"] == "QR_SIMULATED"
    assert first_body["transaction"]["note"] == "Coffee with the team"
    assert first_body["transaction"]["merchant_id"] == (
        "00000000-0000-0000-0000-000000000001"
    )
    assert first_body["transaction"]["category_id"] == "food"
    assert first_body["transaction"]["subcategory_id"] == "cafes"
    assert first_body["transaction"]["status_history"] == [
        "INITIATED",
        "AUTHORIZED",
        "PROCESSING",
        "COMPLETED",
    ]
    assert first_body["request_id"] == "api-payment-request"
    transaction_id = first_body["transaction"]["transaction_id"]

    replay = client.post(
        "/api/v1/payments",
        json=payment_payload(account["account_id"]),
        headers={**headers, "Idempotency-Key": "api-payment-once"},
    )
    assert replay.status_code == 201
    assert replay.json()["transaction"]["transaction_id"] == transaction_id
    assert replay.json()["transaction"]["transaction_channel"] == "QR_SIMULATED"

    conflict = client.post(
        "/api/v1/payments",
        json=payment_payload(account["account_id"], "300.00"),
        headers={**headers, "Idempotency-Key": "api-payment-once"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"

    persisted_account = account_repository.get_by_id(account["account_id"])
    assert persisted_account is not None
    assert persisted_account.balance == Decimal("9750.00")

    fetched = client.get(f"/api/v1/payments/{transaction_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["transaction"]["transaction_id"] == transaction_id

    event_record = manager.mongo_database["audit_records"].find_one(
        {"audit_id": {"$exists": True}, "subject_id": transaction_id}
    )
    assert event_record is not None
    transaction_document = manager.mongo_database["transactions"].find_one(
        {"transaction_id": transaction_id}
    )
    assert transaction_document is not None
    assert transaction_document["transaction_channel"] == "QR_SIMULATED"
    assert transaction_document["note"] == "Coffee with the team"
    events = CassandraEventRepository(manager).list_by_partition(
        "transaction_events_by_account_day",
        account["account_id"],
        datetime.fromisoformat(
            first_body["transaction"]["updated_at"].replace("Z", "+00:00")
        ).date(),
    )
    matching = [
        event
        for event in events
        if event.payload.get("payload", {}).get("transaction_id") == transaction_id
    ]
    assert len(matching) == 1
    assert str(matching[0].event_id) == event_record["audit_id"]
    assert matching[0].payload["payload"]["transaction_channel"] == "QR_SIMULATED"
    assert matching[0].payload["correlation_id"] == "api-payment-request"
    assert matching[0].payload["causation_id"] == "api-parent-operation"


def test_payment_api_rejects_unknown_and_inactive_merchants(payment_api) -> None:
    client, _, _, _ = payment_api
    user, headers = register_and_login(client, "merchant-rules-owner@example.com")
    account = create_account(client, headers)
    now = datetime.now(timezone.utc)
    inactive_id = "00000000-0000-0000-0000-000000000002"
    client.app.state.merchant_repository.create(
        MerchantRecord(
            merchant_id=inactive_id,
            merchant_name="Closed Cafe",
            category_id="food",
            subcategory_id="cafes",
            status=MerchantStatus.INACTIVE,
            created_at=now,
            updated_at=now,
        )
    )

    unknown = client.post(
        "/api/v1/payments",
        headers={**headers, "Idempotency-Key": "unknown-merchant"},
        json={
            **payment_payload(account["account_id"]),
            "merchant_id": "00000000-0000-0000-0000-000000000099",
        },
    )
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "merchant_not_found"

    inactive = client.post(
        "/api/v1/payments",
        headers={**headers, "Idempotency-Key": "inactive-merchant"},
        json={**payment_payload(account["account_id"]), "merchant_id": inactive_id},
    )
    assert inactive.status_code == 409
    assert inactive.json()["error"]["code"] == "merchant_inactive"


def test_live_anomaly_score_uses_persisted_transaction_channels(payment_api) -> None:
    client, _, _, _ = payment_api
    _, headers = register_and_login(client, "live-anomaly-owner@example.com")
    account = create_account(client, headers)

    first = client.post(
        "/api/v1/payments",
        json={**payment_payload(account["account_id"]), "transaction_channel": "QR_SIMULATED"},
        headers={**headers, "Idempotency-Key": "live-anomaly-1"},
    )
    second = client.post(
        "/api/v1/payments",
        json={**payment_payload(account["account_id"]), "transaction_channel": "CARD_SIMULATED"},
        headers={**headers, "Idempotency-Key": "live-anomaly-2"},
    )
    current = client.post(
        "/api/v1/payments",
        json={**payment_payload(account["account_id"]), "transaction_channel": "BANK_SIMULATED"},
        headers={**headers, "Idempotency-Key": "live-anomaly-3"},
    )
    assert [response.status_code for response in (first, second, current)] == [201, 201, 201]
    transaction_id = current.json()["transaction"]["transaction_id"]

    score = client.get(
        f"/api/v1/research/anomaly-score/{transaction_id}",
        headers=headers,
    )
    explanation = client.get(
        f"/api/v1/research/anomaly-score/{transaction_id}/explanation",
        headers=headers,
    )
    listing = client.get("/api/v1/research/anomaly-scores?limit=10", headers=headers)

    assert score.status_code == 200
    assert score.json()["research_only"] is True
    assert score.json()["transaction"]["transaction_id"] == transaction_id
    assert explanation.status_code == 200
    assert explanation.json()["research_only"] is True
    assert listing.status_code == 200
    assert any(item["status"] == "scored" for item in listing.json()["items"])


def test_payment_api_cassandra_failure_does_not_repeat_financial_effect(payment_api) -> None:
    client, _, _, account_repository = payment_api
    user, headers = register_and_login(client, "delivery-failure-owner@example.com")
    account = create_account(client, headers)
    delivery = client.app.state.event_delivery_service
    original_publisher = delivery._publisher

    class FailingPublisher:
        def publish(self, event, *, table: str, partition_value: str) -> None:
            raise DatabaseUnavailableError()

    delivery._publisher = FailingPublisher()
    try:
        first = client.post(
            "/api/v1/payments",
            json=payment_payload(account["account_id"], "250.00"),
            headers={**headers, "Idempotency-Key": "delivery-failure-once"},
        )
        assert first.status_code == 201
        transaction_id = first.json()["transaction"]["transaction_id"]

        persisted_event = client.app.state.database_manager.mongo_database[
            "audit_records"
        ].find_one({"subject_id": transaction_id})
        assert persisted_event is not None
        assert persisted_event["publication_status"] == "FAILED"
        assert persisted_event["publication_attempts"] == 1

        replay = client.post(
            "/api/v1/payments",
            json=payment_payload(account["account_id"], "250.00"),
            headers={**headers, "Idempotency-Key": "delivery-failure-once"},
        )
        assert replay.status_code == 201
        assert replay.json()["transaction"]["transaction_id"] == transaction_id
        persisted_account = account_repository.get_by_id(account["account_id"])
        assert persisted_account is not None
        assert persisted_account.balance == Decimal("9750.00")
    finally:
        delivery._publisher = original_publisher


def test_payment_api_ownership_and_safe_transaction_visibility(payment_api) -> None:
    client, _, _, _ = payment_api
    _, owner_headers = register_and_login(client, "owner@example.com")
    owner_account = create_account(client, owner_headers)
    _, other_headers = register_and_login(client, "other@example.com")

    forbidden = client.post(
        "/api/v1/payments",
        json=payment_payload(owner_account["account_id"]),
        headers={**other_headers, "Idempotency-Key": "cross-owner"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"

    owner_payment = client.post(
        "/api/v1/payments",
        json=payment_payload(owner_account["account_id"], "10.00"),
        headers={**owner_headers, "Idempotency-Key": "owner-lookup-payment"},
    )
    assert owner_payment.status_code == 201
    foreign_transaction_lookup = client.get(
        f"/api/v1/payments/{owner_payment.json()['transaction']['transaction_id']}",
        headers=other_headers,
    )
    assert foreign_transaction_lookup.status_code == 404

    missing = client.post(
        "/api/v1/payments",
        json=payment_payload(str(uuid4())),
        headers={**owner_headers, "Idempotency-Key": "missing-account"},
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "account_not_found"

    foreign_lookup = client.get(
        f"/api/v1/payments/{uuid4()}", headers=other_headers
    )
    assert foreign_lookup.status_code == 404


def test_payment_api_rejects_inactive_users(payment_api) -> None:
    client, users, _, _ = payment_api
    user, headers = register_and_login(client, "inactive-owner@example.com")
    users.set_active(user["user_id"], False)

    response = client.post(
        "/api/v1/payments",
        json=payment_payload(str(uuid4())),
        headers={**headers, "Idempotency-Key": "inactive-user"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_payment_api_history_is_bounded_filtered_and_cursor_paged(payment_api) -> None:
    client, _, _, _ = payment_api
    _, headers = register_and_login(client, "history-owner@example.com")
    account = create_account(client, headers)
    for index in range(2):
        response = client.post(
            "/api/v1/payments",
            json=payment_payload(account["account_id"], "10.00"),
            headers={**headers, "Idempotency-Key": f"history-{index}"},
        )
        assert response.status_code == 201

    first_page = client.get(
        "/api/v1/payments",
        params={
            "limit": 1,
            "status": "COMPLETED",
            "merchant_id": "00000000-0000-0000-0000-000000000001",
        },
        headers=headers,
    )
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["transactions"]) == 1
    assert first_body["next_cursor"]

    second_page = client.get(
        "/api/v1/payments",
        params={"limit": 1, "cursor": first_body["next_cursor"]},
        headers=headers,
    )
    assert second_page.status_code == 200
    assert len(second_page.json()["transactions"]) == 1
    assert (
        second_page.json()["transactions"][0]["transaction_id"]
        != first_body["transactions"][0]["transaction_id"]
    )

    too_large = client.get(
        "/api/v1/payments",
        params={"limit": 101},
        headers=headers,
    )
    assert too_large.status_code == 422


def test_payment_api_inactive_account_insufficient_funds_and_unknown_currency(
    payment_api,
) -> None:
    client, _, _, account_repository = payment_api
    user, headers = register_and_login(client, "rules-owner@example.com")
    account = insert_account(account_repository, owner_id=user["user_id"], balance="100.00")

    insufficient = client.post(
        "/api/v1/payments",
        json=payment_payload(account.account_id, "100.01"),
        headers={**headers, "Idempotency-Key": "insufficient"},
    )
    assert insufficient.status_code == 409
    assert insufficient.json()["error"]["code"] == "insufficient_funds"

    suspended = account.transition_status(
        AccountStatus.SUSPENDED,
        at=datetime.now(timezone.utc),
    )
    account_repository.update(suspended, expected_version=account.version)
    inactive = client.post(
        "/api/v1/payments",
        json=payment_payload(account.account_id, "10.00"),
        headers={**headers, "Idempotency-Key": "inactive"},
    )
    assert inactive.status_code == 409
    assert inactive.json()["error"]["code"] == "account_not_active"

    invalid_currency = client.post(
        "/api/v1/payments",
        json={**payment_payload(account.account_id, "10.00"), "currency": "USD"},
        headers={**headers, "Idempotency-Key": "wrong-currency"},
    )
    assert invalid_currency.status_code == 422
    assert invalid_currency.json()["error"]["code"] == "financial_rule_violation"


def test_payment_api_concurrent_same_key_has_one_effect(payment_api) -> None:
    client, _, _, account_repository = payment_api
    user, headers = register_and_login(client, "concurrent-owner@example.com")
    account = insert_account(account_repository, owner_id=user["user_id"], balance="1000.00")
    request_headers = {**headers, "Idempotency-Key": "concurrent-api-key"}

    def submit() -> int:
        return client.post(
            "/api/v1/payments",
            json=payment_payload(account.account_id, "500.00"),
            headers=request_headers,
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: submit(), range(2)))

    assert statuses == [201, 201]
    persisted = account_repository.get_by_id(account.account_id)
    assert persisted is not None
    assert persisted.balance == Decimal("500.00")


def test_payment_api_concurrent_different_keys_cannot_overspend(payment_api) -> None:
    client, _, _, account_repository = payment_api
    user, headers = register_and_login(client, "race-owner@example.com")
    account = insert_account(account_repository, owner_id=user["user_id"], balance="1000.00")
    commands = (("800.00", "race-800"), ("700.00", "race-700"))

    def submit(item: tuple[str, str]) -> int:
        amount, key = item
        return client.post(
            "/api/v1/payments",
            json=payment_payload(account.account_id, amount),
            headers={**headers, "Idempotency-Key": key},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(submit, commands))

    assert sorted(statuses) == [201, 409]
    persisted = account_repository.get_by_id(account.account_id)
    assert persisted is not None
    assert persisted.balance in {Decimal("200.00"), Decimal("300.00")}
    assert persisted.balance >= Decimal("0.00")


def test_demo_recharge_and_subscription_catalogs_are_server_backed_and_mpin_protected(payment_api) -> None:
    client, _, _, _ = payment_api
    user, headers = register_and_login(client, "lifestyle-owner@example.com")
    account = create_account(client, headers)

    recharge_catalog = client.get("/api/v1/recharge/operators", headers=headers)
    assert recharge_catalog.status_code == 200
    assert set(recharge_catalog.json()["operators"]) == {"AIRTEL", "JIO", "VI", "BSNL"}

    recharge_payload = {
        "account_id": account["account_id"],
        "operator": "AIRTEL",
        "plan_id": "AIRTEL-199",
        "mobile_number": "9000000000",
        "currency": "INR",
        "demo_mpin": "123456",
    }
    recharge = client.post(
        "/api/v1/recharge",
        headers={**headers, "Idempotency-Key": "lifestyle-recharge"},
        json=recharge_payload,
    )
    assert recharge.status_code == 201, recharge.text
    assert recharge.json()["operator"] == "AIRTEL"
    assert recharge.json()["payment"]["remaining_balance"] == "9801.00"

    subscription_catalog = client.get("/api/v1/subscriptions/platforms", headers=headers)
    assert subscription_catalog.status_code == 200
    assert {item["platform_name"] for item in subscription_catalog.json()["platforms"]} == {
        "BJPPrime",
        "BJP Entertainments",
    }

    subscription_payload = {
        "account_id": account["account_id"],
        "platform_id": "BJPPRIME",
        "plan_id": "BJPPRIME-MONTHLY",
        "currency": "INR",
        "demo_mpin": "123456",
    }
    subscription_headers = {**headers, "Idempotency-Key": "lifestyle-subscription"}
    subscription = client.post("/api/v1/subscriptions", headers=subscription_headers, json=subscription_payload)
    assert subscription.status_code == 201, subscription.text
    replay = client.post("/api/v1/subscriptions", headers=subscription_headers, json=subscription_payload)
    assert replay.status_code == 201
    assert replay.json()["subscription_id"] == subscription.json()["subscription_id"]

    paused = client.patch(
        f"/api/v1/subscriptions/{subscription.json()['subscription_id']}/status",
        headers=headers,
        json={"status": "PAUSED"},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "PAUSED"
