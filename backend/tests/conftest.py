"""Shared pytest fixtures for the backend foundation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.repositories.fakes import InMemoryUserRepository  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """Create an isolated application with dependency-free test settings."""

    settings = Settings(_env_file=None, environment="test")
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def auth_context() -> tuple[TestClient, InMemoryUserRepository, Settings]:
    """Create an auth test app with explicit volatile test persistence."""

    settings = Settings(
        _env_file=None,
        environment="test",
        auth_secret_key="test-only-secret-" + ("x" * 64),
    )
    repository = InMemoryUserRepository()
    application = create_app(settings, user_repository=repository)
    with TestClient(application) as test_client:
        yield test_client, repository, settings
