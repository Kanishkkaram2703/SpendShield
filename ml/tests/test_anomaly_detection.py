import csv
import json
from pathlib import Path

from ml.anomaly_detection import (
    ANOMALY_MODEL_SEED,
    LEAKAGE_FIELDS,
    MODEL_FEATURE_NAMES,
    TARGET_COLUMN,
    _top_k,
    build_anomaly_artifact,
    fit_research_anomaly_model,
    score_rows,
    validate_anomaly_artifact,
)
from ml.explainability import (
    FORBIDDEN_EXPLANATION_TERMS,
    build_research_explanation,
    validate_explanations,
)


ROOT = Path(__file__).resolve().parents[2]
V2_FEATURE_DIR = ROOT / "data" / "synthetic" / "v2" / "features"
ANOMALY_DIR = ROOT / "data" / "synthetic" / "anomaly_detection" / "v2"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_model_contract_excludes_labels_identifiers_and_scenario_metadata() -> None:
    assert TARGET_COLUMN not in MODEL_FEATURE_NAMES
    assert not set(MODEL_FEATURE_NAMES) & LEAKAGE_FIELDS
    assert all("id" not in feature_name.lower() for feature_name in MODEL_FEATURE_NAMES)


def test_isolation_forest_is_train_only_deterministic_and_score_direction_is_documented() -> None:
    rows = _read_csv(V2_FEATURE_DIR / "candidate_features_train.csv")[:240]
    first = fit_research_anomaly_model(rows, seed=ANOMALY_MODEL_SEED)
    second = fit_research_anomaly_model(rows, seed=ANOMALY_MODEL_SEED)
    first_scores = score_rows(first, rows)
    second_scores = score_rows(second, rows)

    assert [row["anomaly_score"] for row in first_scores] == [row["anomaly_score"] for row in second_scores]
    assert all(0.0 <= row["anomaly_score"] <= 1.0 for row in first_scores)
    assert first["feature_names"] == MODEL_FEATURE_NAMES
    assert first["seed"] == ANOMALY_MODEL_SEED
    assert TARGET_COLUMN not in first["feature_names"]


def test_current_row_and_future_fields_are_not_model_inputs() -> None:
    manifest = json.loads((V2_FEATURE_DIR / "feature_manifest.json").read_text(encoding="utf-8"))
    assert manifest["historical_feature_audit"]["valid"] is True
    assert "future_transaction_count" in manifest["excluded_fields"]
    assert "future_average_amount" in manifest["excluded_fields"]
    assert "synthetic_transaction_id" not in MODEL_FEATURE_NAMES


def test_explanation_is_deterministic_label_free_and_feature_grounded() -> None:
    row = {
        "synthetic_transaction_id": "audit-row-1",
        "amount": "900.00",
        "user_historical_transaction_count_before": "4",
        "user_historical_average_amount_before": "100.00",
        "user_relative_amount_deviation": "9.0",
        "user_relative_time_deviation": "7.0",
        "transaction_hour": "2",
        "time_since_previous_transaction_seconds": "120",
        "merchant_novelty_before": "1",
        "channel_novelty_before": "1",
        "time_since_previous_transaction_seconds__missing": "0",
    }
    first = build_research_explanation(row, anomaly_score=0.91, rank=1, total_rows=10)
    second = build_research_explanation(row, anomaly_score=0.91, rank=1, total_rows=10)
    assert first == second
    assert set(first["signal_feature_names"]).issubset(set(MODEL_FEATURE_NAMES))
    assert not any(term in first["explanation_text"].lower() for term in FORBIDDEN_EXPLANATION_TERMS)
    assert "synthetic_high_amount" not in first["explanation_text"]
    validation = validate_explanations(
        [first], available_features=MODEL_FEATURE_NAMES, synthetic_labels=("synthetic_high_amount",)
    )
    assert validation["valid"] is True


def test_missing_history_explanation_is_explicitly_limited() -> None:
    row = {
        "synthetic_transaction_id": "first-row",
        "amount": "100.00",
        "user_historical_transaction_count_before": "0",
        "user_historical_average_amount_before": "0.00",
        "user_relative_amount_deviation": "0.0",
        "user_relative_time_deviation": "0.0",
        "transaction_hour": "1",
        "time_since_previous_transaction_seconds": "355667.5",
        "merchant_novelty_before": "1",
        "channel_novelty_before": "1",
        "time_since_previous_transaction_seconds__missing": "1",
    }
    explanation = build_research_explanation(row, anomaly_score=0.2, rank=2, total_rows=10)
    assert explanation["missing_history_warning"] is True
    assert "limited" in explanation["explanation_text"].lower()
    assert "confidence" in explanation["explanation_text"].lower()


def test_generated_artifact_has_required_rows_thresholds_and_validations() -> None:
    validation = validate_anomaly_artifact(ANOMALY_DIR)
    assert validation["valid"] is True
    assert validation["feature_count"] == 12
    thresholds = json.loads((ANOMALY_DIR / "research_thresholds.json").read_text(encoding="utf-8"))
    assert thresholds["not_a_decision_threshold"] is True
    assert set(thresholds["thresholds"]) == {"train_p90", "train_p95", "train_p99"}
    for split_name, count in {"train": 7328, "validation": 1474, "test": 1198}.items():
        assert len(_read_csv(ANOMALY_DIR / f"anomaly_scores_{split_name}.csv")) == count
    samples = _read_csv(ANOMALY_DIR / "explanation_samples.csv")
    assert samples
    assert "user_relative_amount_deviation" in samples[0]["signal_feature_names"]
    assert "Only 0 prior" not in samples[0]["explanation_text"]


def test_top_k_calculation_is_deterministic_and_label_evaluation_only() -> None:
    rows = [
        {"synthetic_transaction_id": "b", "anomaly_score": 0.9, TARGET_COLUMN: "normal"},
        {"synthetic_transaction_id": "a", "anomaly_score": 0.9, TARGET_COLUMN: "synthetic_high_amount"},
        {"synthetic_transaction_id": "c", "anomaly_score": 0.1, TARGET_COLUMN: "synthetic_rapid_repeat"},
    ]
    result = _top_k(rows, ("normal", "synthetic_high_amount", "synthetic_rapid_repeat"), 0.5)
    assert result["top_k_count"] == 2
    assert result["class_counts"]["synthetic_high_amount"] == 1
    assert result["synthetic_label_evaluation_only"] is True
