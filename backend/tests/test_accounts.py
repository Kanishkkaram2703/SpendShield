"""API tests for backend-authoritative account creation and ownership."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import hash_password
from app.main import create_app
from app.repositories.fakes import (
    InMemoryAccountRepository,
    InMemoryAuditRepository,
    InMemoryUserRepository,
)
from app.repositories.users import UserRecord, UserRole


PASSWORD = "Correct Horse Battery Staple"


def account_context() -> tuple[
    TestClient,
    InMemoryUserRepository,
    InMemoryAccountRepository,
    InMemoryAuditRepository,
]:
    settings = Settings(
        _env_file=None,
        environment="test",
        auth_secret_key="test-only-secret-" + ("x" * 64),
        account_initial_balance="10000.00",
        account_currency="INR",
    )
    users = InMemoryUserRepository()
    accounts = InMemoryAccountRepository()
    audits = InMemoryAuditRepository()
    application = create_app(
        settings,
        user_repository=users,
        account_repository=accounts,
        audit_repository=audits,
    )
    return TestClient(application), users, accounts, audits


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert registered.status_code == 201
    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert logged_in.status_code == 200
    return logged_in.json()["access_token"]


def test_account_creation_uses_server_owned_defaults() -> None:
    client, _, accounts, audits = account_context()
    with client:
        token = register_and_login(client, "account-owner@example.com")
        response = client.post(
            "/api/v1/accounts",
            json={"balance": "999999999.99", "owner_id": "attacker"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["currency"] == "INR"
    assert body["balance"] == "10000.00"
    assert body["status"] == "ACTIVE"
    assert accounts.get_by_owner("attacker") is None
    assert [event.event_type for event in audits.events] == ["ACCOUNT_CREATED"]
    assert audits.events[0].payload["outcome"] == "succeeded"


def test_duplicate_account_and_owner_access_are_rejected() -> None:
    client, _, accounts, _ = account_context()
    with client:
        owner_token = register_and_login(client, "owner@example.com")
        created = client.post(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert created.status_code == 201
        duplicate = client.post(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert duplicate.status_code == 409

        other_token = register_and_login(client, "other@example.com")
        other_account = client.post(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert other_account.status_code == 201
        forbidden_lookup = client.get(
            f"/api/v1/accounts/{other_account.json()['account_id']}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    assert forbidden_lookup.status_code == 404


def test_account_requires_authentication() -> None:
    client, _, _, _ = account_context()
    with client:
        response = client.get("/api/v1/accounts/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def add_admin(repository: InMemoryUserRepository) -> UserRecord:
    now = datetime.now(timezone.utc)
    admin = UserRecord(
        user_id=str(uuid4()),
        email="account-admin@example.com",
        password_hash=hash_password(PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    repository.create(admin)
    return admin


def test_non_admin_cannot_change_account_status() -> None:
    client, _, accounts, audits = account_context()
    with client:
        owner_token = register_and_login(client, "status-owner@example.com")
        created = client.post(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        response = client.patch(
            f"/api/v1/accounts/{created.json()['account_id']}/status",
            json={"status": "SUSPENDED"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert accounts.get_by_id(created.json()["account_id"]).status.value == "ACTIVE"
    assert [event.event_type for event in audits.events] == ["ACCOUNT_CREATED"]


def test_admin_status_change_is_persisted_and_audited() -> None:
    client, users, accounts, audits = account_context()
    with client:
        owner_token = register_and_login(client, "status-owner-2@example.com")
        created = client.post(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        admin = add_admin(users)
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": PASSWORD},
        )
        response = client.patch(
            f"/api/v1/accounts/{created.json()['account_id']}/status",
            json={
                "status": "SUSPENDED",
                "expected_version": 0,
                "reason": "manual review",
            },
            headers={"Authorization": f"Bearer {admin_login.json()['access_token']}"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "SUSPENDED"
    assert response.json()["version"] == 1
    assert accounts.get_by_id(created.json()["account_id"]).status.value == "SUSPENDED"
    assert [event.event_type for event in audits.events] == [
        "ACCOUNT_CREATED",
        "ACCOUNT_STATUS_CHANGED",
    ]
    assert audits.events[-1].payload["previous_status"] == "ACTIVE"
    assert audits.events[-1].payload["new_status"] == "SUSPENDED"


def test_status_update_rejects_invalid_transition_and_stale_version() -> None:
    client, users, _, _ = account_context()
    with client:
        owner_token = register_and_login(client, "status-owner-3@example.com")
        created = client.post(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        admin = add_admin(users)
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": PASSWORD},
        )
        headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        closed = client.patch(
            f"/api/v1/accounts/{created.json()['account_id']}/status",
            json={"status": "CLOSED", "expected_version": 0},
            headers=headers,
        )
        stale = client.patch(
            f"/api/v1/accounts/{created.json()['account_id']}/status",
            json={"status": "SUSPENDED", "expected_version": 0},
            headers=headers,
        )
        invalid_transition = client.patch(
            f"/api/v1/accounts/{created.json()['account_id']}/status",
            json={"status": "ACTIVE", "expected_version": 1},
            headers=headers,
        )

    assert closed.status_code == 200
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "account_version_conflict"
    assert invalid_transition.status_code == 409
    assert invalid_transition.json()["error"]["code"] == (
        "invalid_account_status_transition"
    )


def test_status_update_rejects_unknown_fields_and_invalid_status() -> None:
    client, users, _, _ = account_context()
    with client:
        owner_token = register_and_login(client, "status-owner-4@example.com")
        created = client.post(
            "/api/v1/accounts",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        admin = add_admin(users)
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": PASSWORD},
        )
        headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        unknown_status = client.patch(
            f"/api/v1/accounts/{created.json()['account_id']}/status",
            json={"status": "DELETED"},
            headers=headers,
        )
        unknown_field = client.patch(
            f"/api/v1/accounts/{created.json()['account_id']}/status",
            json={"status": "SUSPENDED", "owner_id": "attacker"},
            headers=headers,
        )

    assert unknown_status.status_code == 422
    assert unknown_field.status_code == 422
