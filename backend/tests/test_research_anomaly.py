"""Tests for the read-only research anomaly integration boundary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import AppError
from app.domain.financial import (
    Account,
    AccountStatus,
    PaymentCommand,
    TransactionChannel,
    authorize_payment,
)
from app.main import create_app
from app.repositories.fakes import InMemoryPaymentRepository, InMemoryUserRepository
from app.repositories.payments import PaymentHistoryWindow
from app.services.research_anomaly_service import (
    AnomalyArtifactLoader,
    MODEL_FEATURE_NAMES,
    ResearchArtifactError,
    ResearchFeatureBuilder,
    build_research_explanation,
)


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / "data" / "synthetic" / "anomaly_detection" / "v2"
PASSWORD = "Correct Horse Battery Staple"
NOW = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def settings(**overrides) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        auth_secret_key="research-test-secret-" + ("x" * 64),
        **overrides,
    )


def register_and_login(client: TestClient, email: str) -> tuple[dict, dict[str, str]]:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    return registered.json(), {"Authorization": f"Bearer {login.json()['access_token']}"}


def add_completed_payment(
    repository: InMemoryPaymentRepository,
    owner_id: str,
    *,
    at: datetime = NOW,
    channel: TransactionChannel = TransactionChannel.CARD_SIMULATED,
    transaction_id: str | None = None,
):
    account_id = str(uuid4())
    account = Account(
        account_id=account_id,
        owner_id=owner_id,
        currency="INR",
        balance=Decimal("1000.00"),
        status=AccountStatus.ACTIVE,
        created_at=at,
        updated_at=at,
    )
    repository._accounts[account_id] = account
    return repository.execute(
        PaymentCommand(
            account_id=account_id,
            owner_id=owner_id,
            amount=Decimal("25.00"),
            currency="INR",
            idempotency_key=str(uuid4()),
            transaction_channel=channel,
            merchant_id="merchant-1",
            merchant_name="Merchant",
            category_id="category-1",
            category_name="Category",
            subcategory_id="subcategory-1",
            subcategory_name="Subcategory",
        ),
        transaction_id=transaction_id or str(uuid4()),
        at=at,
    )


def test_artifact_loader_validates_serialized_parameters_and_score_is_deterministic() -> None:
    artifact = AnomalyArtifactLoader(ARTIFACT_ROOT).load()
    features = {name: 0.0 for name in MODEL_FEATURE_NAMES}
    first = artifact.score(features)
    second = artifact.score(features)

    assert first == second
    assert 0.0 <= first[0] <= 1.0
    assert artifact.metadata.dataset_version == "v2"
    assert artifact.metadata.higher_score_means_more_anomalous is True
    assert artifact.metadata.thresholds_are_decisions is False


def test_artifact_loader_fails_safely_for_missing_parameters(tmp_path: Path) -> None:
    for filename in AnomalyArtifactLoader.REQUIRED_FILES:
        if filename != "anomaly_model_parameters.json":
            source = ARTIFACT_ROOT / filename
            (tmp_path / filename).write_bytes(source.read_bytes())

    with pytest.raises(ResearchArtifactError):
        AnomalyArtifactLoader(tmp_path).load()


def test_feature_builder_reproduces_prior_only_contract_when_channel_source_is_explicit() -> None:
    repository = InMemoryPaymentRepository()
    prior = add_completed_payment(repository, "owner-1", at=NOW)
    current = add_completed_payment(repository, "owner-1", at=NOW + timedelta(hours=2))
    history = PaymentHistoryWindow(items=(prior,), truncated=False)

    features = ResearchFeatureBuilder().build(
        current.transaction,
        history,
    )

    assert tuple(features) == MODEL_FEATURE_NAMES
    assert features["user_historical_transaction_count_before"] == 1
    assert features["time_since_previous_transaction_seconds"] == 7200.0
    assert features["time_since_previous_transaction_seconds__missing"] == 0.0
    assert features["merchant_novelty_before"] == 0.0
    assert features["channel_novelty_before"] == 0.0


def test_feature_builder_calculates_channel_novelty_from_persisted_transactions() -> None:
    repository = InMemoryPaymentRepository()
    prior = add_completed_payment(
        repository,
        "owner-1",
        channel=TransactionChannel.CARD_SIMULATED,
    )
    current = add_completed_payment(
        repository,
        "owner-1",
        at=NOW + timedelta(hours=1),
        channel=TransactionChannel.BANK_SIMULATED,
    )

    features = ResearchFeatureBuilder().build(
        current.transaction,
        repository.list_for_owner_before(
            "owner-1",
            before=current.transaction.created_at,
            before_transaction_id=current.transaction.transaction_id,
        ),
    )

    assert features["channel_novelty_before"] == 1.0
    assert features["user_historical_transaction_count_before"] == 1


def test_feature_builder_excludes_current_transaction_and_orders_equal_timestamps() -> None:
    repository = InMemoryPaymentRepository()
    first = add_completed_payment(
        repository,
        "owner-1",
        at=NOW,
        channel=TransactionChannel.QR_SIMULATED,
        transaction_id="a-first",
    )
    second = add_completed_payment(
        repository,
        "owner-1",
        at=NOW,
        channel=TransactionChannel.CARD_SIMULATED,
        transaction_id="b-second",
    )
    current = add_completed_payment(
        repository,
        "owner-1",
        at=NOW,
        channel=TransactionChannel.WALLET_SIMULATED,
        transaction_id="z-current",
    )
    history = repository.list_for_owner_before(
        "owner-1",
        before=current.transaction.created_at,
        before_transaction_id=current.transaction.transaction_id,
    )

    assert [
        item.transaction.transaction_id for item in history.items
    ] == sorted(
        [first.transaction.transaction_id, second.transaction.transaction_id]
    )
    assert current.transaction.transaction_id not in {
        item.transaction.transaction_id for item in history.items
    }
    features = ResearchFeatureBuilder().build(current.transaction, history)
    assert features["user_historical_transaction_count_before"] == 2
    assert features["channel_novelty_before"] == 1.0


def test_feature_builder_refuses_legacy_channel_in_history() -> None:
    repository = InMemoryPaymentRepository()
    prior = add_completed_payment(repository, "owner-1", at=NOW)
    current = add_completed_payment(
        repository,
        "owner-1",
        at=NOW + timedelta(hours=1),
        channel=TransactionChannel.BANK_SIMULATED,
    )
    legacy_prior = replace(prior.transaction, transaction_channel=None)

    with pytest.raises(ValueError, match="history"):
        ResearchFeatureBuilder().build(
            current.transaction,
            PaymentHistoryWindow(
                items=(replace(prior, transaction=legacy_prior),),
                truncated=False,
            ),
        )


def test_feature_builder_refuses_missing_channel_instead_of_defaulting() -> None:
    repository = InMemoryPaymentRepository()
    prior = add_completed_payment(repository, "owner-1", at=NOW)
    current = add_completed_payment(repository, "owner-1", at=NOW + timedelta(hours=1))

    legacy_current = replace(current.transaction, transaction_channel=None)
    with pytest.raises(ValueError, match="transaction_channel"):
        ResearchFeatureBuilder().build(
            legacy_current,
            PaymentHistoryWindow(items=(prior,), truncated=False),
        )


def test_explanation_is_deterministic_and_contains_no_decision_language() -> None:
    features = {
        name: 0.0 for name in MODEL_FEATURE_NAMES
    }
    features.update(
        {
            "amount": 900.0,
            "user_historical_transaction_count_before": 3,
            "user_historical_average_amount_before": 100.0,
            "user_relative_amount_deviation": 9.0,
            "user_relative_time_deviation": 8.0,
            "merchant_novelty_before": 1.0,
            "channel_novelty_before": 1.0,
            "time_since_previous_transaction_seconds": 120.0,
        }
    )
    first = build_research_explanation(features)
    second = build_research_explanation(features)

    assert first == second
    assert "fraud" not in first.explanation_text.lower()
    assert set(first.signal_feature_names) <= set(MODEL_FEATURE_NAMES)


def test_research_api_requires_authentication() -> None:
    repository = InMemoryPaymentRepository()
    application = create_app(
        settings(),
        user_repository=InMemoryUserRepository(),
        payment_repository=repository,
    )
    with TestClient(application) as client:
        response = client.get(f"/api/v1/research/anomaly-score/{uuid4()}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_research_api_enforces_owner_scope_and_returns_explicit_unavailable_item() -> None:
    users = InMemoryUserRepository()
    payments = InMemoryPaymentRepository()
    application = create_app(settings(), user_repository=users, payment_repository=payments)
    with TestClient(application) as client:
        owner, owner_headers = register_and_login(client, "owner@example.com")
        other, other_headers = register_and_login(client, "other@example.com")
        execution = add_completed_payment(payments, owner["user_id"])

        cross_owner = client.get(
            f"/api/v1/research/anomaly-score/{execution.transaction.transaction_id}",
            headers=other_headers,
        )
        listing = client.get(
            "/api/v1/research/anomaly-scores?limit=10",
            headers=owner_headers,
        )

    assert cross_owner.status_code == 404
    assert cross_owner.json()["error"]["code"] == "research_transaction_not_found"
    assert listing.status_code == 200
    body = listing.json()
    assert body["research_only"] is True
    assert len(body["items"]) == 1
    assert body["items"][0]["status"] == "unavailable"
    assert body["items"][0]["unavailable_reason"] == "research_insufficient_history"


def test_research_api_does_not_execute_or_mutate_payments() -> None:
    class SpyRepository(InMemoryPaymentRepository):
        execute_calls = 0

        def execute(self, *args, **kwargs):
            self.execute_calls += 1
            raise AssertionError("research API must not execute a payment")

    repository = SpyRepository()
    users = InMemoryUserRepository()
    application = create_app(settings(), user_repository=users, payment_repository=repository)
    with TestClient(application) as client:
        _, headers = register_and_login(client, "readonly@example.com")
        response = client.get("/api/v1/research/anomaly-scores", headers=headers)

    assert response.status_code == 200
    assert repository.execute_calls == 0


def test_research_api_reports_missing_artifact_without_exposing_filesystem_path(tmp_path: Path) -> None:
    users = InMemoryUserRepository()
    payments = InMemoryPaymentRepository()
    application = create_app(
        settings(research_anomaly_artifact_path=str(tmp_path / "missing")),
        user_repository=users,
        payment_repository=payments,
    )
    with TestClient(application) as client:
        user, headers = register_and_login(client, "artifact@example.com")
        execution = add_completed_payment(payments, user["user_id"])
        response = client.get(
            f"/api/v1/research/anomaly-score/{execution.transaction.transaction_id}",
            headers=headers,
        )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "research_artifact_unavailable"
    assert str(tmp_path) not in response.text
