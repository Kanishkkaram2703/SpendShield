"""Authentication, token, and role-authorization tests."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends
from fastapi.testclient import TestClient

from app.api.v1.dependencies import require_role
from app.core.config import Settings
from app.core.security import TokenManager, hash_password
from app.main import create_app
from app.repositories.fakes import InMemoryUserRepository
from app.repositories.users import UserRecord, UserRole


PASSWORD = "Correct Horse Battery Staple"


def register_user(client: TestClient, email: str = "user@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    return response.json()


def login_user(client: TestClient, email: str = "user@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return response.json()


def test_valid_registration_returns_safe_user(auth_context) -> None:
    client, repository, _ = auth_context

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "User@Example.com", "password": PASSWORD},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["role"] == "USER"
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body

    stored = repository.get_by_email("user@example.com")
    assert stored is not None
    assert stored.password_hash != PASSWORD
    assert stored.password_hash.startswith("$argon2")


def test_duplicate_identity_is_rejected(auth_context) -> None:
    client, _, _ = auth_context
    register_user(client)

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "USER@example.com", "password": PASSWORD},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_identity"


def test_invalid_registration_input_is_rejected(auth_context) -> None:
    client, _, _ = auth_context

    invalid_email = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": PASSWORD},
    )
    short_password = client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )

    assert invalid_email.status_code == 422
    assert short_password.status_code == 422


def test_public_registration_cannot_select_privileged_roles(auth_context) -> None:
    client, repository, _ = auth_context

    for role in ("ADMIN", "INVESTIGATOR"):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{role.lower()}@example.com",
                "password": PASSWORD,
                "role": role,
            },
        )
        assert response.status_code == 422

    assert repository.get_by_email("admin@example.com") is None
    assert repository.get_by_email("investigator@example.com") is None


def test_valid_login_returns_bearer_token_and_safe_user(auth_context) -> None:
    client, _, settings = auth_context
    register_user(client)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "USER@example.com", "password": PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.auth_access_token_expire_minutes * 60
    assert body["access_token"]
    assert body["user"]["email"] == "user@example.com"
    assert "password_hash" not in body
    assert "auth_secret_key" not in body
    claims = TokenManager(settings).decode_access_token(body["access_token"])
    assert claims["iss"] == settings.auth_issuer
    assert claims["aud"] == settings.auth_audience


def test_invalid_password_and_unknown_user_fail_identically(auth_context) -> None:
    client, _, _ = auth_context
    register_user(client)

    invalid_password = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Wrong password"},
    )
    unknown_user = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "Wrong password"},
    )

    assert invalid_password.status_code == 401
    assert unknown_user.status_code == 401
    assert invalid_password.json() == unknown_user.json()


def test_inactive_user_cannot_login(auth_context) -> None:
    client, repository, _ = auth_context
    registered = register_user(client)
    user = repository.get_by_id(registered["user_id"])
    assert user is not None
    repository.set_active(user.user_id, False)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": PASSWORD},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_current_user_requires_authentication(auth_context) -> None:
    client, _, _ = auth_context

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_current_user_returns_safe_authenticated_user(auth_context) -> None:
    client, _, _ = auth_context
    register_user(client)
    token_response = login_user(client)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_response['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    assert response.json()["role"] == "USER"
    assert "password_hash" not in response.json()


def test_malformed_expired_and_bad_signature_tokens_are_rejected(auth_context) -> None:
    client, repository, settings = auth_context
    registered = register_user(client)
    user = repository.get_by_id(registered["user_id"])
    assert user is not None
    manager = TokenManager(settings)

    expired_token = manager.create_access_token(
        user.user_id,
        expires_delta=timedelta(seconds=-1),
    )
    now = datetime.now(timezone.utc)
    bad_signature = jwt.encode(
        {
            "sub": user.user_id,
            "jti": "bad-signature",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "token_type": "access",
        },
        "wrong-secret-" + ("x" * 64),
        algorithm="HS256",
    )

    for token in ("not-a-token", expired_token, bad_signature):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "authentication_required"


def test_default_application_does_not_fake_persistence() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        auth_secret_key="test-only-secret-" + ("x" * 64),
    )
    application = create_app(settings)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": PASSWORD},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "persistence_not_configured"


def test_role_authorization_is_server_side(auth_context) -> None:
    client, repository, settings = auth_context

    @client.app.get("/test/investigator-only")
    def investigator_only(
        user: UserRecord = Depends(
            require_role(UserRole.INVESTIGATOR, UserRole.ADMIN)
        ),
    ) -> dict[str, str]:
        return {"user_id": user.user_id}

    register_user(client)
    user_token = login_user(client)["access_token"]
    denied = client.get(
        "/test/investigator-only",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert denied.status_code == 403

    now = datetime.now(timezone.utc)
    admin = UserRecord(
        user_id="admin-user",
        email="admin@example.com",
        password_hash=hash_password(PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    repository.create(admin)
    admin_token = login_user(client, "admin@example.com")["access_token"]
    allowed = client.get(
        "/test/investigator-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert allowed.status_code == 200
    assert allowed.json() == {"user_id": "admin-user"}


def test_credentials_and_tokens_are_not_written_to_logs(auth_context, caplog) -> None:
    client, repository, settings = auth_context
    caplog.set_level(logging.INFO, logger="spendshield")
    register_user(client)
    token_response = login_user(client)
    password_hash = repository.get_by_email("user@example.com").password_hash

    logs = caplog.text
    assert PASSWORD not in logs
    assert password_hash not in logs
    assert token_response["access_token"] not in logs
    assert settings.auth_secret_key not in logs
