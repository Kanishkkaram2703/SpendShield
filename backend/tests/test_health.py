"""Tests for the backend process and versioned health routes."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.main import create_app


def test_root_health_endpoint_returns_expected_response(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "spendshield-backend",
    }


def test_versioned_health_endpoint_returns_expected_response(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "spendshield-backend",
    }


def test_dependency_health_endpoint_reports_unconfigured_databases(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/health/dependencies")

    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "checks": {
            "mongodb": {
                "status": "not_configured",
                "detail": "MongoDB is not configured.",
            },
            "cassandra": {
                "status": "not_configured",
                "detail": "Cassandra is not configured.",
            },
        },
    }


def test_settings_validate_environment_and_api_prefix() -> None:
    settings = Settings(_env_file=None, environment="test", api_prefix="/v1/")

    assert settings.environment == "test"
    assert settings.api_prefix == "/v1"

    try:
        Settings(_env_file=None, environment="invalid")
    except ValidationError as error:
        assert "environment" in str(error)
    else:  # pragma: no cover - defensive assertion for the test itself
        raise AssertionError("Invalid environment should fail validation")


def test_production_settings_reject_insecure_defaults() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            auth_secret_key="test-only-secret-" + ("x" * 64),
            trusted_hosts="localhost",
            debug=True,
        )


def test_response_has_request_id_and_security_headers(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "test-request-1"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-1"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_configured_development_lan_host_is_accepted() -> None:
    application = create_app(
        Settings(
            _env_file=None,
            environment="test",
            allowed_hosts="localhost,127.0.0.1,0.0.0.0,10.165.59.245",
        )
    )

    with TestClient(application, base_url="http://10.165.59.245:8000") as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_unconfigured_development_lan_host_is_rejected() -> None:
    application = create_app(
        Settings(_env_file=None, environment="test", trusted_hosts="localhost")
    )

    with TestClient(application, base_url="http://10.165.59.245:8000") as client:
        response = client.get("/health")

    assert response.status_code == 400


def test_legacy_trusted_hosts_setting_remains_supported() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        trusted_hosts="localhost,10.165.59.245",
    )

    assert settings.trusted_host_list == ["localhost", "10.165.59.245"]


def test_production_rejects_wildcard_allowed_hosts() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            auth_secret_key="production-test-secret-" + ("x" * 64),
            allowed_hosts="*",
        )


def test_production_disables_interactive_docs() -> None:
    application = create_app(
        Settings(
            _env_file=None,
            environment="production",
            auth_secret_key="production-test-secret-" + ("x" * 64),
            trusted_hosts="testserver",
        )
    )

    with TestClient(application) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_expected_application_errors_use_safe_error_envelope() -> None:
    application = create_app(Settings(_env_file=None, environment="test"))

    @application.get("/test-expected-error")
    def expected_error() -> None:
        raise AppError(
            "expected_failure",
            "The expected operation failed.",
            status_code=409,
            details={"reason": "test"},
        )

    with TestClient(application) as client:
        response = client.get("/test-expected-error")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "expected_failure",
            "message": "The expected operation failed.",
            "details": {"reason": "test"},
        }
    }


def test_unexpected_errors_do_not_expose_internal_details() -> None:
    application = create_app(Settings(_env_file=None, environment="test"))

    @application.get("/test-unexpected-error")
    def unexpected_error() -> None:
        raise RuntimeError("database password should never be returned")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/test-unexpected-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "An unexpected error occurred.",
        }
    }
    assert "database password" not in response.text


def test_application_is_a_fastapi_instance() -> None:
    application = create_app(Settings(_env_file=None, environment="test"))

    assert isinstance(application, FastAPI)
