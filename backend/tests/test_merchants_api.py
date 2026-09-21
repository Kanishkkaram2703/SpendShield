"""MongoDB-backed merchant/category API and payment integration tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import Settings
from app.core.security import hash_password
from app.db.manager import DatabaseManager
from app.domain.catalog import MerchantRecord, MerchantStatus
from app.main import create_app
from app.repositories.audit import MongoAuditRepository
from app.repositories.categories import MongoCategoryRepository
from app.repositories.fakes import InMemoryUserRepository
from app.repositories.merchants import MongoMerchantRepository
from app.repositories.users import UserRecord, UserRole
from app.seed.catalog import seed_default_categories

PASSWORD = "Correct Horse Battery Staple"
ADMIN_EMAIL = "catalog-admin@example.com"


def catalog_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        auth_secret_key="catalog-test-secret-" + ("x" * 64),
        mongodb_uri="mongodb://127.0.0.1:27018",
        mongodb_replica_set="rs0",
        mongodb_database=f"spendshield_catalog_test_{uuid4().hex}",
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
    )


def require_mongodb(settings: Settings) -> None:
    manager = DatabaseManager(settings)
    try:
        manager.connect_mongodb()
        hello = manager.mongo_database.client.admin.command("hello")
        if hello.get("setName") != "rs0" or not hello.get("isWritablePrimary"):
            pytest.skip("MongoDB rs0 is not a writable primary")
    finally:
        manager.close()


@pytest.fixture
def catalog_api():
    settings = catalog_settings()
    try:
        require_mongodb(settings)
    except Exception as exc:  # noqa: BLE001 - external integration may be absent
        pytest.skip(f"merchant API integration service unavailable: {exc}")

    manager = DatabaseManager(settings)
    users = InMemoryUserRepository()
    audit = MongoAuditRepository(manager)
    categories = MongoCategoryRepository(manager)
    merchants = MongoMerchantRepository(manager)
    manager.ensure_mongodb_schema()
    seed_default_categories(categories)
    now = datetime.now(timezone.utc)
    users.create(
        UserRecord(
            user_id=str(uuid4()),
            email=ADMIN_EMAIL,
            password_hash=hash_password(PASSWORD),
            role=UserRole.ADMIN,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    application = create_app(
        settings,
        user_repository=users,
        database_manager=manager,
        audit_repository=audit,
        category_repository=categories,
        merchant_repository=merchants,
    )
    try:
        with TestClient(application) as client:
            yield client, users, manager, merchants
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


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register_user(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    headers = login(client, email)
    configured = client.put(
        "/api/v1/demo-security/mpin",
        headers=headers,
        json={"pin": "123456", "confirm_pin": "123456"},
    )
    assert configured.status_code == 200, configured.text
    return headers


def create_merchant(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "QuickBite",
    category_id: str = "food",
    subcategory_id: str = "restaurants",
) -> dict:
    response = client.post(
        "/api/v1/merchants",
        headers=headers,
        json={
            "merchant_name": name,
            "category_id": category_id,
            "subcategory_id": subcategory_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_categories_are_controlled_and_merchant_management_is_admin_only(catalog_api) -> None:
    client, _, _, _ = catalog_api
    user_headers = register_user(client, "catalog-user@example.com")
    admin_headers = login(client, ADMIN_EMAIL)

    categories = client.get("/api/v1/categories", headers=user_headers)
    assert categories.status_code == 200
    assert categories.json()["categories"]
    assert all("category_id" in item for item in categories.json()["categories"])

    denied = client.post(
        "/api/v1/merchants",
        headers=user_headers,
        json={
            "merchant_name": "Denied Merchant",
            "category_id": "food",
            "subcategory_id": "cafes",
        },
    )
    assert denied.status_code == 403

    merchant = create_merchant(client, admin_headers)
    retrieved = client.get(
        f"/api/v1/merchants/{merchant['merchant_id']}",
        headers=user_headers,
    )
    assert retrieved.status_code == 200
    assert retrieved.json()["category"]["category_id"] == "food"
    assert retrieved.json()["status"] == "ACTIVE"


def test_merchant_lifecycle_uses_versioned_admin_updates(catalog_api) -> None:
    client, _, _, _ = catalog_api
    admin_headers = login(client, ADMIN_EMAIL)
    merchant = create_merchant(client, admin_headers)

    updated = client.patch(
        f"/api/v1/merchants/{merchant['merchant_id']}",
        headers=admin_headers,
        json={"expected_version": 0, "status": "INACTIVE"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "INACTIVE"
    assert updated.json()["version"] == 1

    conflict = client.patch(
        f"/api/v1/merchants/{merchant['merchant_id']}",
        headers=admin_headers,
        json={"expected_version": 0, "status": "ACTIVE"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "merchant_version_conflict"

    reactivated = client.patch(
        f"/api/v1/merchants/{merchant['merchant_id']}",
        headers=admin_headers,
        json={"expected_version": 1, "status": "ACTIVE"},
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "ACTIVE"


def test_merchant_listing_is_bounded_filtered_and_cursor_paged(catalog_api) -> None:
    client, _, _, _ = catalog_api
    admin_headers = login(client, ADMIN_EMAIL)
    create_merchant(client, admin_headers, name="Alpha Cafe", subcategory_id="cafes")
    create_merchant(client, admin_headers, name="Beta Cafe", subcategory_id="cafes")

    first = client.get(
        "/api/v1/merchants",
        headers=admin_headers,
        params={"limit": 1, "category_id": "food", "subcategory_id": "cafes"},
    )
    assert first.status_code == 200
    body = first.json()
    assert len(body["merchants"]) == 1
    assert body["next_cursor"] is not None

    second = client.get(
        "/api/v1/merchants",
        headers=admin_headers,
        params={
            "limit": 1,
            "category_id": "food",
            "subcategory_id": "cafes",
            "cursor": body["next_cursor"],
        },
    )
    assert second.status_code == 200
    assert second.json()["merchants"][0]["merchant_id"] != body["merchants"][0]["merchant_id"]

    too_large = client.get(
        "/api/v1/merchants",
        headers=admin_headers,
        params={"limit": 101},
    )
    assert too_large.status_code == 422


def test_invalid_category_relationship_is_rejected(catalog_api) -> None:
    client, _, _, _ = catalog_api
    admin_headers = login(client, ADMIN_EMAIL)
    response = client.post(
        "/api/v1/merchants",
        headers=admin_headers,
        json={
            "merchant_name": "Unknown Category Merchant",
            "category_id": "food",
            "subcategory_id": "not_defined",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "merchant_category_not_found"


def test_payment_uses_category_snapshot_after_merchant_reclassification(catalog_api) -> None:
    client, _, _, _ = catalog_api
    admin_headers = login(client, ADMIN_EMAIL)
    user_headers = register_user(client, "snapshot-user@example.com")
    merchant = create_merchant(client, admin_headers, subcategory_id="restaurants")
    account = client.post("/api/v1/accounts", headers=user_headers)
    assert account.status_code == 201
    account_id = account.json()["account_id"]

    first = client.post(
        "/api/v1/payments",
        headers={**user_headers, "Idempotency-Key": "snapshot-before"},
        json={
            "account_id": account_id,
            "amount": "10.00",
            "currency": "INR",
            "merchant_id": merchant["merchant_id"],
            "transaction_channel": "QR_SIMULATED",
            "demo_mpin": "123456",
        },
    )
    assert first.status_code == 201, first.text
    assert first.json()["transaction"]["subcategory_id"] == "restaurants"

    reclassified = client.patch(
        f"/api/v1/merchants/{merchant['merchant_id']}",
        headers=admin_headers,
        json={
            "expected_version": 0,
            "category_id": "food",
            "subcategory_id": "cafes",
        },
    )
    assert reclassified.status_code == 200

    second = client.post(
        "/api/v1/payments",
        headers={**user_headers, "Idempotency-Key": "snapshot-after"},
        json={
            "account_id": account_id,
            "amount": "10.00",
            "currency": "INR",
            "merchant_id": merchant["merchant_id"],
            "transaction_channel": "CARD_SIMULATED",
            "demo_mpin": "123456",
        },
    )
    assert second.status_code == 201, second.text
    assert second.json()["transaction"]["subcategory_id"] == "cafes"

    history = client.get("/api/v1/payments", headers=user_headers)
    assert history.status_code == 200
    assert {item["subcategory_id"] for item in history.json()["transactions"]} == {
        "restaurants",
        "cafes",
    }

    inactive = client.patch(
        f"/api/v1/merchants/{merchant['merchant_id']}",
        headers=admin_headers,
        json={"expected_version": 1, "status": "INACTIVE"},
    )
    assert inactive.status_code == 200
    replay = client.post(
        "/api/v1/payments",
        headers={**user_headers, "Idempotency-Key": "snapshot-before"},
        json={
            "account_id": account_id,
            "amount": "10.00",
            "currency": "INR",
            "merchant_id": merchant["merchant_id"],
            "transaction_channel": "QR_SIMULATED",
            "demo_mpin": "123456",
        },
    )
    assert replay.status_code == 201
    assert replay.json()["transaction"]["subcategory_id"] == "restaurants"

    rejected = client.post(
        "/api/v1/payments",
        headers={**user_headers, "Idempotency-Key": "inactive-merchant"},
        json={
            "account_id": account_id,
            "amount": "10.00",
            "currency": "INR",
            "merchant_id": merchant["merchant_id"],
            "transaction_channel": "QR_SIMULATED",
            "demo_mpin": "123456",
        },
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "merchant_inactive"
