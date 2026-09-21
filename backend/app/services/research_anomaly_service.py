"""Artifact-backed, read-only research anomaly scoring.

This module deliberately does not train, regenerate, write database state, or
make payment/investigator decisions.  MongoDB supplies current transaction
records and prior completed records; the versioned JSON artifact supplies the
research model parameters and metadata.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.core.config import Settings
from app.core.exceptions import AppError
from app.domain.financial import PaymentExecution, Transaction, TransactionStatus
from app.repositories.payments import PaymentHistoryWindow, PaymentRepository
from app.schemas.research import (
    ResearchAnomalyScoreItem,
    ResearchExplanation,
    ResearchModelMetadata,
    ResearchTransactionSummary,
)


MODEL_FEATURE_NAMES: tuple[str, ...] = (
    "amount",
    "transaction_hour",
    "day_of_week",
    "user_historical_transaction_count_before",
    "user_historical_average_amount_before",
    "time_since_previous_transaction_seconds",
    "user_historical_category_frequency_before",
    "merchant_novelty_before",
    "channel_novelty_before",
    "user_relative_amount_deviation",
    "user_relative_time_deviation",
    "time_since_previous_transaction_seconds__missing",
)
FORBIDDEN_FEATURE_FIELDS = {
    "target_scenario_label",
    "scenario_label",
    "scenario_id",
    "generator_rule",
    "future_transaction_count",
    "future_average_amount",
    "post_event_outcome",
    "fraud",
    "confirmed_fraud",
    "synthetic_transaction_id",
    "synthetic_user_id",
}
FORBIDDEN_EXPLANATION_TERMS = (
    "fraud",
    "financial crime",
    "payment blocking",
    "payment rejection",
    "confirmed fraud",
    "guaranteed fraud",
    "automatic fraud decision",
)
EXPLAINABILITY_VERSION = "1.0.0"


class ResearchArtifactError(ValueError):
    """Raised when a versioned research artifact is missing or incompatible."""


class ResearchFeatureUnavailableError(ValueError):
    """Raised when a live transaction cannot satisfy the approved contract."""


@dataclass(frozen=True, slots=True)
class ResearchArtifact:
    """Validated immutable in-memory view of JSON model artifacts."""

    config: Mapping[str, Any]
    manifest: Mapping[str, Any]
    parameters: Mapping[str, Any]
    thresholds: Mapping[str, Any]

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(str(value) for value in self.config["feature_names"])

    @property
    def metadata(self) -> ResearchModelMetadata:
        threshold_version = str(
            self.thresholds.get("artifact_version")
            or self.config.get("artifact_version")
            or "1.0.0"
        )
        # Numeric threshold values are intentionally not returned. They are
        # research percentiles, not operational decisions.
        return ResearchModelMetadata(
            dataset_version=str(self.manifest["dataset_version"]),
            generator_version=str(self.manifest["generator_version"]),
            feature_version=str(self.manifest["feature_generation_version"]),
            model_name=str(self.config["model_type"]),
            model_version=str(self.config["model_version"]),
            score_semantics=str(
                self.config["score_semantics"]["anomaly_score"]
            ),
            threshold_source=(
                "research_thresholds.json; fixed train-only percentiles; "
                "not a decision threshold"
            ),
            threshold_version=threshold_version,
        )

    def score(self, features: Mapping[str, Any]) -> tuple[float, float]:
        """Score one exact feature vector using serialized fitted parameters."""

        if set(features) & FORBIDDEN_FEATURE_FIELDS:
            raise ResearchArtifactError("forbidden fields entered the model input")
        missing = [name for name in self.feature_names if name not in features]
        if missing:
            raise ResearchFeatureUnavailableError(
                f"required model features are unavailable: {', '.join(missing)}"
            )
        medians = self.parameters["train_medians"]
        scales = self.parameters["train_scales"]
        distances: list[float] = []
        for name in self.feature_names:
            raw_value = features[name]
            value = float(medians[name] if raw_value in (None, "") else raw_value)
            if not math.isfinite(value):
                raise ResearchFeatureUnavailableError(
                    f"feature {name} is non-finite"
                )
            distance = min(8.0, abs(value - float(medians[name])) / float(scales[name]))
            distances.append(distance)
        raw_score = sum(distances) / len(distances)
        raw_min = float(self.parameters["train_raw_min"])
        raw_max = float(self.parameters["train_raw_max"])
        if raw_max <= raw_min:
            normalized = 0.5
        else:
            normalized = max(0.0, min(1.0, (raw_score - raw_min) / (raw_max - raw_min)))
        return round(normalized, 6), round(raw_score, 8)


class AnomalyArtifactLoader:
    """Load and validate JSON artifacts without training or data generation."""

    REQUIRED_FILES = (
        "anomaly_model_config.json",
        "anomaly_feature_manifest.json",
        "anomaly_model_parameters.json",
        "research_thresholds.json",
    )

    def __init__(self, artifact_root: str | Path) -> None:
        self._artifact_root = Path(artifact_root)

    def load(self) -> ResearchArtifact:
        documents = {name: self._read_json(name) for name in self.REQUIRED_FILES}
        config = documents["anomaly_model_config.json"]
        manifest = documents["anomaly_feature_manifest.json"]
        parameters = documents["anomaly_model_parameters.json"]
        thresholds = documents["research_thresholds.json"]
        try:
            self._validate(config, manifest, parameters, thresholds)
        except ResearchArtifactError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ResearchArtifactError(
                "research artifact metadata is incomplete or incompatible"
            ) from exc
        return ResearchArtifact(config, manifest, parameters, thresholds)

    def _read_json(self, name: str) -> dict[str, Any]:
        path = self._artifact_root / name
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise ResearchArtifactError(
                f"required research artifact {name} is unavailable or malformed"
            ) from exc
        if not isinstance(value, dict):
            raise ResearchArtifactError(f"research artifact {name} must be a JSON object")
        return value

    @staticmethod
    def _validate(
        config: Mapping[str, Any],
        manifest: Mapping[str, Any],
        parameters: Mapping[str, Any],
        thresholds: Mapping[str, Any],
    ) -> None:
        expected = list(MODEL_FEATURE_NAMES)
        if config.get("model_type") != "robust_mad_distance":
            raise ResearchArtifactError("research model type is unsupported")
        if parameters.get("model_type") != config.get("model_type"):
            raise ResearchArtifactError("serialized parameter model type is incompatible")
        if parameters.get("model_version") != config.get("model_version"):
            raise ResearchArtifactError("serialized parameter model version is incompatible")
        if parameters.get("dataset_version") != manifest.get("dataset_version"):
            raise ResearchArtifactError("serialized parameter dataset version is incompatible")
        if parameters.get("feature_version") != manifest.get("feature_generation_version"):
            raise ResearchArtifactError("serialized parameter feature version is incompatible")
        if list(config.get("feature_names", ())) != expected:
            raise ResearchArtifactError("research model feature order is incompatible")
        if list(manifest.get("model_feature_names", ())) != expected:
            raise ResearchArtifactError("research manifest feature order is incompatible")
        if manifest.get("feature_count") != len(expected):
            raise ResearchArtifactError("research manifest feature count is incompatible")
        if manifest.get("leakage_review", {}).get("valid") is not True:
            raise ResearchArtifactError("research feature leakage contract is invalid")
        if list(parameters.get("feature_names", ())) != expected:
            raise ResearchArtifactError("serialized parameter feature order is incompatible")
        if parameters.get("labels_used_during_fit") is not False:
            raise ResearchArtifactError("research parameters do not prove label-free fitting")
        if parameters.get("scenario_metadata_used_during_fit") is not False:
            raise ResearchArtifactError(
                "research parameters do not prove scenario metadata was excluded"
            )
        medians = parameters.get("train_medians")
        scales = parameters.get("train_scales")
        if not isinstance(medians, dict) or not isinstance(scales, dict):
            raise ResearchArtifactError("serialized fitted parameters are incomplete")
        if set(medians) != set(expected) or set(scales) != set(expected):
            raise ResearchArtifactError("serialized fitted parameters do not cover features")
        try:
            for name in expected:
                if not math.isfinite(float(medians[name])) or float(scales[name]) <= 0:
                    raise ResearchArtifactError("serialized fitted parameters are invalid")
            if not math.isfinite(float(parameters["train_raw_min"])):
                raise ResearchArtifactError("serialized raw score minimum is invalid")
            if not math.isfinite(float(parameters["train_raw_max"])):
                raise ResearchArtifactError("serialized raw score maximum is invalid")
            if float(parameters["train_raw_max"]) < float(parameters["train_raw_min"]):
                raise ResearchArtifactError("serialized raw score bounds are invalid")
        except (KeyError, TypeError, ValueError) as exc:
            raise ResearchArtifactError("serialized fitted parameters are invalid") from exc
        if thresholds.get("not_a_decision_threshold") is not True:
            raise ResearchArtifactError("threshold artifact is marked as operational")
        if thresholds.get("synthetic_label_evaluation_only") is not True:
            raise ResearchArtifactError("threshold artifact is not research-only")


def resolve_artifact_root(settings: Settings) -> Path:
    """Resolve a configured path without returning it through an API response."""

    configured = Path(settings.research_anomaly_artifact_path)
    if configured.is_absolute():
        return configured
    repository_root = Path(__file__).resolve().parents[3]
    return repository_root / configured


def _number(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    parsed = float(value)
    return parsed if math.isfinite(parsed) else default


def _strength(value: float) -> str:
    if value >= 0.75:
        return "strong"
    if value >= 0.40:
        return "moderate"
    if value > 0.0:
        return "weak"
    return "none"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class ResearchFeatureBuilder:
    """Build the v2 point-in-time features from approved current/history data."""

    def build(
        self,
        transaction: Transaction,
        history: PaymentHistoryWindow,
    ) -> dict[str, Any]:
        if transaction.status is not TransactionStatus.COMPLETED:
            raise ResearchFeatureUnavailableError("transaction status is not supported")
        if history.truncated:
            raise ResearchFeatureUnavailableError(
                "approved historical context exceeds the bounded research window"
            )
        if not history.items:
            raise ResearchFeatureUnavailableError(
                "insufficient prior transaction history for research comparison"
            )
        if transaction.merchant_id is None:
            raise ResearchFeatureUnavailableError("merchant context is unavailable")
        if transaction.category_id is None:
            raise ResearchFeatureUnavailableError("category context is unavailable")
        transaction_channel = transaction.transaction_channel
        if transaction_channel is None:
            raise ResearchFeatureUnavailableError(
                "transaction_channel is not present in the current transaction source"
            )
        if any(
            item.transaction.transaction_channel is None
            for item in history.items
        ):
            raise ResearchFeatureUnavailableError(
                "transaction_channel history is not present in the approved history source"
            )

        prior = sorted(
            history.items,
            key=lambda item: (
                item.transaction.created_at,
                item.transaction.transaction_id,
            ),
        )
        count = len(prior)
        amount = Decimal(transaction.amount)
        average = (
            sum((Decimal(item.transaction.amount) for item in prior), Decimal("0")) / count
            if count
            else Decimal("0")
        )
        current_time = transaction.created_at.astimezone(timezone.utc)
        current_hour = current_time.hour
        previous = prior[-1] if prior else None
        gap = (
            (current_time - previous.transaction.created_at.astimezone(timezone.utc)).total_seconds()
            if previous is not None
            else None
        )
        if gap is not None and gap < 0:
            raise ResearchFeatureUnavailableError("history is not strictly prior-only")
        prior_hours = [
            item.transaction.created_at.astimezone(timezone.utc).hour for item in prior
        ]
        average_hour = sum(prior_hours) / count if count else float(current_hour)
        hour_delta = abs(current_hour - average_hour)
        category_count = sum(
            item.transaction.category_id == transaction.category_id for item in prior
        )
        seen_merchants = {item.transaction.merchant_id for item in prior}
        seen_channels = {
            item.transaction.transaction_channel for item in prior
            if item.transaction.transaction_channel is not None
        }
        ratio = float(amount / average) if average else 0.0
        return {
            "amount": float(amount),
            "transaction_hour": current_hour,
            "day_of_week": current_time.weekday(),
            "user_historical_transaction_count_before": count,
            "user_historical_average_amount_before": float(average),
            "time_since_previous_transaction_seconds": gap,
            "user_historical_category_frequency_before": category_count / count if count else 0.0,
            "merchant_novelty_before": 0.0 if transaction.merchant_id in seen_merchants else 1.0,
            "channel_novelty_before": (
                0.0 if transaction_channel in seen_channels else 1.0
            ),
            "user_relative_amount_deviation": ratio,
            "user_relative_time_deviation": (
                min(hour_delta, 24.0 - hour_delta) if count else 0.0
            ),
            "time_since_previous_transaction_seconds__missing": 0.0 if gap is not None else 1.0,
        }


def build_research_explanation(
    features: Mapping[str, Any],
) -> ResearchExplanation:
    """Build the same bounded, label-free signal summary as the offline study."""

    history_count = _number(features.get("user_historical_transaction_count_before"))
    amount_ratio = _number(features.get("user_relative_amount_deviation"))
    amount_signal = (
        _clamp(abs(math.log(max(amount_ratio, 1e-9))) / math.log(3.0))
        if history_count > 0 and amount_ratio > 0
        else 0.0
    )
    time_signal = (
        _clamp(_number(features.get("user_relative_time_deviation")) / 6.0)
        if history_count > 0
        else 0.0
    )
    gap = features.get("time_since_previous_transaction_seconds")
    rapid_signal = (
        1.0
        if gap not in (None, "")
        and history_count > 0
        and _number(gap) <= 600
        else 0.0
    )
    novelty_signal = _clamp(
        (_number(features.get("merchant_novelty_before"))
         + _number(features.get("channel_novelty_before"))) / 2.0
    )
    history_limited = 1.0 if history_count < 2 else 0.0
    components = {
        "amount_deviation": (amount_signal, [
            "user_relative_amount_deviation",
            "user_historical_average_amount_before",
            "amount",
        ]),
        "time_deviation": (time_signal, ["user_relative_time_deviation", "transaction_hour"]),
        "rapid_repeat": (rapid_signal, ["time_since_previous_transaction_seconds"]),
        "novelty": (novelty_signal, ["merchant_novelty_before", "channel_novelty_before"]),
        "history_limited": (history_limited, [
            "user_historical_transaction_count_before",
            "time_since_previous_transaction_seconds__missing",
        ]),
    }
    selected = sorted(
        ((name, value, fields) for name, (value, fields) in components.items() if value > 0),
        key=lambda item: (-item[1], item[0]),
    )[:3]
    strengths = {name: _strength(value) for name, value, _ in selected}
    feature_names = sorted({field for _, _, fields in selected for field in fields})
    if selected:
        text = (
            "Research explanation: observed amount, timing, repeat, novelty, "
            "or history signals contributed to this research score."
        )
    else:
        text = "Research explanation: no strong observed behavioral signal was identified by the fixed research rules."
    lowered = text.lower()
    if any(term in lowered for term in FORBIDDEN_EXPLANATION_TERMS):
        raise ResearchArtifactError("generated explanation contains a forbidden decision term")
    if set(feature_names) - set(MODEL_FEATURE_NAMES):
        raise ResearchArtifactError("generated explanation references an unapproved feature")
    return ResearchExplanation(
        explanation_text=text,
        signal_strengths=strengths,
        signal_feature_names=feature_names,
        missing_history_warning=history_count < 2,
        explainability_version=EXPLAINABILITY_VERSION,
    )


@dataclass(frozen=True, slots=True)
class _Score:
    execution: PaymentExecution
    features: Mapping[str, Any]
    score: float
    artifact: ResearchArtifact


class ResearchAnomalyService:
    """Owner-scoped read-only anomaly service."""

    def __init__(
        self,
        repository: PaymentRepository,
        settings: Settings,
        *,
        loader: AnomalyArtifactLoader | None = None,
        feature_builder: ResearchFeatureBuilder | None = None,
    ) -> None:
        self._repository = repository
        self._loader = loader or AnomalyArtifactLoader(resolve_artifact_root(settings))
        self._feature_builder = feature_builder or ResearchFeatureBuilder()

    def _artifact(self) -> ResearchArtifact:
        try:
            return self._loader.load()
        except ResearchArtifactError as exc:
            raise AppError(
                code="research_artifact_unavailable",
                message="Research anomaly artifacts are unavailable or incompatible.",
                status_code=503,
                details={"reason": str(exc)},
            ) from exc

    @staticmethod
    def summary(execution: PaymentExecution) -> ResearchTransactionSummary:
        transaction = execution.transaction
        return ResearchTransactionSummary(
            transaction_id=transaction.transaction_id,
            amount=transaction.amount,
            currency=transaction.currency,
            status=transaction.status,
            created_at=transaction.created_at,
        )

    def _get(self, transaction_id: str, owner_id: str) -> PaymentExecution:
        execution = self._repository.get_by_id(transaction_id, owner_id=owner_id)
        if execution is None:
            raise AppError(
                code="research_transaction_not_found",
                message="Transaction was not found.",
                status_code=404,
            )
        return execution

    def _history(self, transaction: Transaction) -> PaymentHistoryWindow:
        method = getattr(self._repository, "list_for_owner_before", None)
        if method is None:
            raise AppError(
                code="research_history_unavailable",
                message="Approved historical transaction context is unavailable.",
                status_code=503,
            )
        try:
            return method(
                transaction.owner_id,
                before=transaction.created_at,
                before_transaction_id=transaction.transaction_id,
                limit=5000,
            )
        except AppError:
            raise
        except (TypeError, ValueError) as exc:
            raise AppError(
                code="research_history_unavailable",
                message="Approved historical transaction context is unavailable.",
                status_code=503,
            ) from exc

    def _score_execution(
        self,
        execution: PaymentExecution,
        *,
        artifact: ResearchArtifact | None = None,
    ) -> _Score:
        transaction = execution.transaction
        if transaction.status is not TransactionStatus.COMPLETED:
            raise AppError(
                code="research_transaction_status_unsupported",
                message="Research anomaly scoring supports completed transactions only.",
                status_code=422,
            )
        loaded = artifact or self._artifact()
        history = self._history(transaction)
        try:
            features = self._feature_builder.build(transaction, history)
            score, _ = loaded.score(features)
        except ResearchFeatureUnavailableError as exc:
            reason = str(exc)
            code = (
                "research_insufficient_history"
                if reason in {
                    "insufficient prior transaction history for research comparison",
                    "approved historical context exceeds the bounded research window",
                }
                else "research_feature_contract_unavailable"
            )
            raise AppError(
                code=code,
                message="Research anomaly scoring is unavailable for this transaction.",
                status_code=503,
                details={"reason": reason},
            ) from exc
        except ResearchArtifactError as exc:
            raise AppError(
                code="research_scoring_failed",
                message="Research anomaly scoring could not be completed.",
                status_code=503,
                details={"reason": str(exc)},
            ) from exc
        except (TypeError, ValueError, KeyError) as exc:
            raise AppError(
                code="research_scoring_failed",
                message="Research anomaly scoring could not be completed.",
                status_code=503,
            ) from exc
        return _Score(execution, features, score, loaded)

    def score_for_owner(self, transaction_id: str, owner_id: str) -> _Score:
        return self._score_execution(self._get(transaction_id, owner_id))

    def explanation_for_owner(self, transaction_id: str, owner_id: str) -> tuple[_Score, ResearchExplanation]:
        scored = self.score_for_owner(transaction_id, owner_id)
        try:
            explanation = build_research_explanation(scored.features)
        except ResearchArtifactError as exc:
            raise AppError(
                code="research_explanation_failed",
                message="The research explanation could not be generated safely.",
                status_code=503,
            ) from exc
        return scored, explanation

    def list_for_owner(
        self,
        owner_id: str,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[ResearchAnomalyScoreItem], str | None]:
        try:
            page = self._repository.list_for_owner(
                owner_id,
                limit=limit,
                cursor=cursor,
                status=TransactionStatus.COMPLETED,
            )
        except ValueError as exc:
            raise AppError(
                code="invalid_research_pagination",
                message="The research score pagination request is invalid.",
                status_code=422,
            ) from exc
        try:
            artifact = self._artifact()
        except AppError as exc:
            return [
                ResearchAnomalyScoreItem(
                    transaction=self.summary(execution),
                    status="unavailable",
                    unavailable_reason="research_artifact_unavailable",
                )
                for execution in page.items
            ], page.next_cursor
        items: list[ResearchAnomalyScoreItem] = []
        for execution in page.items:
            try:
                scored = self._score_execution(execution, artifact=artifact)
            except AppError as exc:
                if exc.code in {
                    "research_feature_contract_unavailable",
                    "research_insufficient_history",
                    "research_transaction_status_unsupported",
                    "research_history_unavailable",
                    "research_scoring_failed",
                }:
                    items.append(
                        ResearchAnomalyScoreItem(
                            transaction=self.summary(execution),
                            status="unavailable",
                            model_metadata=artifact.metadata,
                            unavailable_reason=exc.code,
                        )
                    )
                    continue
                raise
            items.append(
                ResearchAnomalyScoreItem(
                    transaction=self.summary(execution),
                    status="scored",
                    anomaly_score=scored.score,
                    model_metadata=artifact.metadata,
                )
            )
        return items, page.next_cursor


__all__ = [
    "AnomalyArtifactLoader",
    "MODEL_FEATURE_NAMES",
    "ResearchAnomalyService",
    "ResearchArtifact",
    "ResearchArtifactError",
    "ResearchFeatureBuilder",
    "build_research_explanation",
    "resolve_artifact_root",
]
