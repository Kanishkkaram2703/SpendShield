"""Controlled, research-only anomaly ranking over the SpendShield v2 matrix.

The module intentionally stops at offline scoring and evaluation.  It does
not write MongoDB/Cassandra state, expose an API, block payments, or create a
deployable model artifact.  Synthetic scenario labels are carried through
only for evaluation after train-only, label-free fitting.
"""

from __future__ import annotations

import csv
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

from .explainability import (
    EXPLANATION_FEATURES,
    FORBIDDEN_EXPLANATION_TERMS,
    build_research_explanation,
    transparent_baseline_score,
    validate_explanations,
)


ANOMALY_MODEL_VERSION = "1.0.0"
ANOMALY_MODEL_SEED = 20260913
ANOMALY_ARTIFACT_VERSION = "1.0.0"
MODEL_TYPE = "robust_mad_distance"

# These fields are numeric, point-in-time candidate features.  Categorical
# one-hot fields remain approved in the general matrix but are excluded here
# because the first anomaly model is intentionally small and explainable.
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

AUDIT_COLUMNS: tuple[str, ...] = (
    "synthetic_transaction_id",
    "synthetic_user_id",
    "timestamp",
    "dataset_split",
)
TARGET_COLUMN = "target_scenario_label"
IDENTIFIER_FIELDS = {
    "synthetic_transaction_id",
    "synthetic_user_id",
    "synthetic_account_id",
    "synthetic_merchant_id",
}
LEAKAGE_FIELDS = {
    TARGET_COLUMN,
    "scenario_label",
    "scenario_id",
    "scenario_injection_reason",
    "generator_rule",
    "dataset_version",
    "dataset_split",
    "future_transaction_count",
    "future_average_amount",
    "post_event_outcome",
    "fraud",
    "confirmed_fraud",
}


FEATURE_SPECS: dict[str, dict[str, Any]] = {
    "amount": {
        "data_type": "numeric",
        "source_column": "amount",
        "transformation": "candidate matrix numeric value in synthetic INR units",
        "missing_value_behavior": "training median if missing",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: current transaction value",
        "reason_for_inclusion": "Direct transaction magnitude is observable at transaction time.",
    },
    "transaction_hour": {
        "data_type": "numeric",
        "source_column": "transaction_hour",
        "transformation": "UTC hour encoded as 0 through 23 numeric value",
        "missing_value_behavior": "training median if missing",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: current timestamp-derived value",
        "reason_for_inclusion": "Supports research analysis of timing deviation.",
    },
    "day_of_week": {
        "data_type": "numeric",
        "source_column": "day_of_week",
        "transformation": "UTC weekday encoded as 0 through 6 numeric value",
        "missing_value_behavior": "training median if missing",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: current timestamp-derived value",
        "reason_for_inclusion": "Captures coarse calendar context without identifiers.",
    },
    "user_historical_transaction_count_before": {
        "data_type": "numeric",
        "source_column": "user_historical_transaction_count_before",
        "transformation": "prior-only count from the existing v2 feature artifact",
        "missing_value_behavior": "training median if missing",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: prior-only",
        "reason_for_inclusion": "Provides behavioral-history depth and uncertainty context.",
    },
    "user_historical_average_amount_before": {
        "data_type": "numeric",
        "source_column": "user_historical_average_amount_before",
        "transformation": "prior-only user average amount",
        "missing_value_behavior": "training median if missing; source first-row fallback is 0.00",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: prior-only",
        "reason_for_inclusion": "Provides a user-relative amount reference.",
    },
    "time_since_previous_transaction_seconds": {
        "data_type": "numeric",
        "source_column": "time_since_previous_transaction_seconds",
        "transformation": "prior-only elapsed time since the previous user transaction",
        "missing_value_behavior": "training median plus explicit missing indicator",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: prior-only",
        "reason_for_inclusion": "Supports rapid-repeat research signals.",
    },
    "user_historical_category_frequency_before": {
        "data_type": "numeric",
        "source_column": "user_historical_category_frequency_before",
        "transformation": "prior-only frequency of the current category for the user",
        "missing_value_behavior": "training median if missing",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: prior-only",
        "reason_for_inclusion": "Represents prior category familiarity without using the label.",
    },
    "merchant_novelty_before": {
        "data_type": "numeric_indicator",
        "source_column": "synthetic_merchant_id",
        "transformation": "prior-only unseen-merchant indicator from v2",
        "missing_value_behavior": "0.0 source fallback for first user row",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: prior-only",
        "reason_for_inclusion": "Supports a transparent novelty signal.",
    },
    "channel_novelty_before": {
        "data_type": "numeric_indicator",
        "source_column": "transaction_channel",
        "transformation": "prior-only unseen-channel indicator from v2",
        "missing_value_behavior": "0.0 source fallback for first user row",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: prior-only",
        "reason_for_inclusion": "Supports a transparent channel-change signal.",
    },
    "user_relative_amount_deviation": {
        "data_type": "numeric_ratio",
        "source_column": "amount / user_historical_average_amount_before",
        "transformation": "prior-only current-to-prior-average amount ratio",
        "missing_value_behavior": "0.0 for first user transaction",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: prior-only",
        "reason_for_inclusion": "Makes the amount explanation user-relative and inspectable.",
    },
    "user_relative_time_deviation": {
        "data_type": "numeric_distance",
        "source_column": "transaction_hour and prior user transaction hours",
        "transformation": "prior-only circular-hour distance from user prior average",
        "missing_value_behavior": "0.0 for first user transaction",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: prior-only",
        "reason_for_inclusion": "Makes timing explanations user-relative.",
    },
    "time_since_previous_transaction_seconds__missing": {
        "data_type": "numeric_indicator",
        "source_column": "time_since_previous_transaction_seconds",
        "transformation": "explicit indicator for unavailable previous transaction",
        "missing_value_behavior": "0.0 or 1.0 as supplied by v2 feature artifact",
        "available_at_transaction_time": True,
        "leakage_status": "PASS: prior-only missingness",
        "reason_for_inclusion": "Prevents imputation from hiding limited history.",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _number(row: Mapping[str, Any], field: str, default: float = 0.0) -> float:
    value = row.get(field, default)
    if value in (None, ""):
        return default
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Non-finite value for feature {field}: {value!r}")
    return number


def _quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a quantile from no values.")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _summary(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "minimum": 0.0, "maximum": 0.0, "mean": 0.0, "median": 0.0, "p95": 0.0, "p99": 0.0}
    return {
        "count": len(values),
        "minimum": round(min(values), 6),
        "maximum": round(max(values), 6),
        "mean": round(sum(values) / len(values), 6),
        "median": round(median(values), 6),
        "p95": round(_quantile(values, 0.95), 6),
        "p99": round(_quantile(values, 0.99), 6),
    }


def _validate_feature_contract(manifest: Mapping[str, Any]) -> dict[str, Any]:
    manifest_features = set(manifest.get("feature_names", []))
    errors: list[str] = []
    missing = sorted(set(MODEL_FEATURE_NAMES) - manifest_features)
    if missing:
        errors.append(f"Required v2 anomaly features are absent: {missing}")
    if set(MODEL_FEATURE_NAMES) & IDENTIFIER_FIELDS:
        errors.append("Identifier entered anomaly model feature list.")
    if set(MODEL_FEATURE_NAMES) & LEAKAGE_FIELDS:
        errors.append("Label, split, future, or post-event field entered anomaly model feature list.")
    if manifest.get("target", {}).get("column") in MODEL_FEATURE_NAMES:
        errors.append("Target column entered anomaly model feature list.")
    for field in MODEL_FEATURE_NAMES:
        if field not in FEATURE_SPECS:
            errors.append(f"Feature {field!r} has no anomaly feature specification.")
    return {
        "valid": not errors,
        "errors": errors,
        "model_feature_names": list(MODEL_FEATURE_NAMES),
        "target_absent_from_model_inputs": TARGET_COLUMN not in MODEL_FEATURE_NAMES,
        "identifiers_absent_from_model_inputs": not bool(set(MODEL_FEATURE_NAMES) & IDENTIFIER_FIELDS),
        "scenario_metadata_absent_from_model_inputs": not bool(set(MODEL_FEATURE_NAMES) & LEAKAGE_FIELDS),
        "feature_specs_complete": all(field in FEATURE_SPECS for field in MODEL_FEATURE_NAMES),
    }


def _train_medians(rows: Sequence[Mapping[str, Any]], feature_names: Sequence[str]) -> dict[str, float]:
    medians: dict[str, float] = {}
    for field in feature_names:
        values = [_number(row, field) for row in rows if row.get(field) not in (None, "")]
        medians[field] = median(values) if values else 0.0
    return medians


def _matrix(rows: Sequence[Mapping[str, Any]], feature_names: Sequence[str], medians: Mapping[str, float]) -> list[list[float]]:
    return [
        [medians[field] if row.get(field) in (None, "") else _number(row, field) for field in feature_names]
        for row in rows
    ]


def _normalize(raw_scores: Sequence[float], train_min: float, train_max: float) -> list[float]:
    if train_max <= train_min:
        return [0.5 for _ in raw_scores]
    return [round(max(0.0, min(1.0, (score - train_min) / (train_max - train_min))), 6) for score in raw_scores]


def _robust_scale(values: Sequence[float]) -> tuple[float, float]:
    center = float(median(values)) if values else 0.0
    deviations = [abs(value - center) for value in values]
    mad = float(median(deviations)) if deviations else 0.0
    q1 = _quantile(values, 0.25) if values else 0.0
    q3 = _quantile(values, 0.75) if values else 0.0
    # MAD is robust to extreme synthetic values; IQR is a deterministic
    # fallback when MAD is zero because a column is mostly identical.
    scale = max(1.4826 * mad, (q3 - q1) / 1.349, 1e-9)
    return center, scale


def fit_research_anomaly_model(
    train_rows: Sequence[Mapping[str, Any]],
    *,
    feature_names: Sequence[str] = MODEL_FEATURE_NAMES,
    seed: int = ANOMALY_MODEL_SEED,
) -> dict[str, Any]:
    """Fit a deterministic robust-distance model using feature values only.

    A dependency-free robust MAD distance is used because the repository's
    established backend virtual environment does not include scikit-learn.
    This is the specification's allowed transparent-statistical fallback.
    """

    selected = tuple(feature_names)
    if set(selected) & (IDENTIFIER_FIELDS | LEAKAGE_FIELDS):
        raise ValueError("Anomaly model input contains an identifier or leakage-prone field.")
    medians = _train_medians(train_rows, selected)
    scales: dict[str, float] = {}
    for field in selected:
        values = [medians[field] if row.get(field) in (None, "") else _number(row, field) for row in train_rows]
        _, scales[field] = _robust_scale(values)

    def raw_score(row: Mapping[str, Any]) -> float:
        distances = [
            min(
                8.0,
                abs((medians[field] if row.get(field) in (None, "") else _number(row, field)) - medians[field])
                / scales[field],
            )
            for field in selected
        ]
        return sum(distances) / len(distances) if distances else 0.0

    raw_train = [raw_score(row) for row in train_rows]
    return {
        "algorithm": "train-fitted robust median absolute deviation distance",
        "feature_names": selected,
        "train_medians": medians,
        "train_scales": scales,
        "train_raw_scores": raw_train,
        "train_raw_min": min(raw_train),
        "train_raw_max": max(raw_train),
        "seed": seed,
    }


def score_rows(model: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Score rows with higher normalized values meaning more anomalous."""

    feature_names = tuple(model["feature_names"])
    medians = model["train_medians"]
    scales = model["train_scales"]
    raw: list[float] = []
    for row in rows:
        distances = [
            min(
                8.0,
                abs((medians[field] if row.get(field) in (None, "") else _number(row, field)) - medians[field])
                / scales[field],
            )
            for field in feature_names
        ]
        raw.append(sum(distances) / len(distances) if distances else 0.0)
    normalized = _normalize(raw, float(model["train_raw_min"]), float(model["train_raw_max"]))
    results: list[dict[str, Any]] = []
    for row, raw_score, score in zip(rows, raw, normalized):
        results.append(
            {
                "synthetic_transaction_id": row.get("synthetic_transaction_id", ""),
                "synthetic_user_id": row.get("synthetic_user_id", ""),
                "timestamp": row.get("timestamp", ""),
                "dataset_split": row.get("dataset_split", ""),
                TARGET_COLUMN: row.get(TARGET_COLUMN, ""),
                "anomaly_score_raw": round(raw_score, 8),
                "anomaly_score": score,
            }
        )
    return results


def _enrich_scores(rows: Sequence[Mapping[str, Any]], scored: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row, score in zip(rows, scored):
        baseline, components = transparent_baseline_score(row)
        item = dict(score)
        # Keep the observed model feature values attached to the in-memory
        # score record so explanation generation can use the actual row.  The
        # score CSV writer intentionally ignores these fields; they are not a
        # second model input or a new persisted artifact column.
        for feature_name in MODEL_FEATURE_NAMES:
            item[feature_name] = row.get(feature_name, "")
        item["transparent_baseline_score"] = baseline
        for component_name, component in components.items():
            item[f"baseline_signal_{component_name}"] = component["value"]
        item["synthetic_label_evaluation_only"] = "true"
        item["synthetic_label_notice"] = "Offline synthetic scenario reference only; not real-world ground truth."
        enriched.append(item)
    return enriched


def _scenario_score_stats(rows: Sequence[Mapping[str, Any]], classes: Sequence[str]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for class_name in classes:
        values = [float(row["anomaly_score"]) for row in rows if row.get(TARGET_COLUMN) == class_name]
        output[class_name] = _summary(values)
    return output


def _top_k(rows: Sequence[Mapping[str, Any]], classes: Sequence[str], fraction: float) -> dict[str, Any]:
    count = max(1, math.ceil(len(rows) * fraction)) if rows else 0
    ranked = sorted(rows, key=lambda row: (-float(row["anomaly_score"]), str(row["synthetic_transaction_id"])))
    selected = ranked[:count]
    class_counts = {class_name: sum(row.get(TARGET_COLUMN) == class_name for row in selected) for class_name in classes}
    synthetic_classes = [class_name for class_name in classes if class_name != "normal"]
    present = sum(class_counts[name] > 0 for name in synthetic_classes)
    return {
        "fraction": fraction,
        "top_k_count": count,
        "class_counts": class_counts,
        "class_composition": {
            name: round(class_counts[name] / count, 6) if count else 0.0 for name in classes
        },
        "normal_class_representation": {
            "count": class_counts.get("normal", 0),
            "rate_within_top_k": round(class_counts.get("normal", 0) / count, 6) if count else 0.0,
            "source_rate": round(sum(row.get(TARGET_COLUMN) == "normal" for row in rows) / len(rows), 6) if rows else 0.0,
        },
        "synthetic_scenario_coverage": {
            "present_non_normal_classes": present,
            "total_non_normal_classes": len(synthetic_classes),
            "rate": round(present / len(synthetic_classes), 6) if synthetic_classes else 0.0,
        },
        "synthetic_label_evaluation_only": True,
    }


def _threshold_results(rows: Sequence[Mapping[str, Any]], thresholds: Mapping[str, float], classes: Sequence[str]) -> dict[str, Any]:
    total_synthetic = sum(row.get(TARGET_COLUMN) != "normal" for row in rows)
    total_normal = sum(row.get(TARGET_COLUMN) == "normal" for row in rows)
    output: dict[str, Any] = {}
    for name, threshold in thresholds.items():
        flagged = [row for row in rows if float(row["anomaly_score"]) >= threshold]
        synthetic_flagged = sum(row.get(TARGET_COLUMN) != "normal" for row in flagged)
        normal_flagged = sum(row.get(TARGET_COLUMN) == "normal" for row in flagged)
        per_scenario = {
            class_name: {
                "flagged": sum(row.get(TARGET_COLUMN) == class_name for row in flagged),
                "total": sum(row.get(TARGET_COLUMN) == class_name for row in rows),
                "recall": round(
                    sum(row.get(TARGET_COLUMN) == class_name for row in flagged)
                    / max(1, sum(row.get(TARGET_COLUMN) == class_name for row in rows)),
                    6,
                ),
            }
            for class_name in classes
        }
        output[name] = {
            "threshold": round(float(threshold), 6),
            "flagged_count": len(flagged),
            "flagged_rate": round(len(flagged) / len(rows), 6) if rows else 0.0,
            "normal_flagged_count": normal_flagged,
            "normal_flagged_rate_against_normal": round(normal_flagged / max(1, total_normal), 6),
            "synthetic_flagged_count": synthetic_flagged,
            "synthetic_only_precision_style": round(synthetic_flagged / len(flagged), 6) if flagged else 0.0,
            "synthetic_only_recall_style": round(synthetic_flagged / max(1, total_synthetic), 6),
            "per_scenario": per_scenario,
            "interpretation": "Synthetic-label evaluation only; not a decision threshold.",
        }
    return output


def _binary_roc_auc(labels: Sequence[bool], scores: Sequence[float]) -> float | None:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None
    ordered = sorted(enumerate(scores), key=lambda item: (item[1], item[0]))
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average_rank = (index + 1 + end) / 2.0
        rank_sum += sum(average_rank for position, _ in ordered[index:end] if labels[position])
        index = end
    u_statistic = rank_sum - positives * (positives + 1) / 2.0
    return u_statistic / (positives * negatives)


def _binary_average_precision(labels: Sequence[bool], scores: Sequence[float]) -> float | None:
    positives = sum(labels)
    if positives == 0:
        return None
    ordered = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
    found = 0
    precision_sum = 0.0
    for rank, index in enumerate(ordered, start=1):
        if labels[index]:
            found += 1
            precision_sum += found / rank
    return precision_sum / positives


def _ranking_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    y = [row.get(TARGET_COLUMN) != "normal" for row in rows]
    scores = [float(row["anomaly_score"]) for row in rows]
    result: dict[str, Any] = {
        "target_definition": "normal versus any non-normal synthetic scenario",
        "synthetic_label_evaluation_only": True,
        "roc_auc": None,
        "average_precision": None,
        "limitation": "These are synthetic-label ranking analyses, not real-world detection metrics.",
    }
    if len(set(y)) < 2:
        result["limitation"] = "Binary metric unavailable because the split contains one synthetic-label group only."
        return result
    result["roc_auc"] = round(float(_binary_roc_auc(y, scores)), 6)
    result["average_precision"] = round(float(_binary_average_precision(y, scores)), 6)
    return result


def _evaluate_split(rows: Sequence[Mapping[str, Any]], classes: Sequence[str], thresholds: Mapping[str, float]) -> dict[str, Any]:
    return {
        "row_count": len(rows),
        "score_distribution": _summary([float(row["anomaly_score"]) for row in rows]),
        "raw_score_distribution": _summary([float(row["anomaly_score_raw"]) for row in rows]),
        "score_distribution_by_synthetic_scenario": _scenario_score_stats(rows, classes),
        "top_k_composition": {
            "top_1_percent": _top_k(rows, classes, 0.01),
            "top_5_percent": _top_k(rows, classes, 0.05),
            "top_10_percent": _top_k(rows, classes, 0.10),
        },
        "research_threshold_evaluation": _threshold_results(rows, thresholds, classes),
        "synthetic_only_ranking_metrics": _ranking_metrics(rows),
    }


def _ranked_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: (-float(row["anomaly_score"]), str(row["synthetic_transaction_id"])))
    total = len(ordered)
    result: list[dict[str, Any]] = []
    for rank, row in enumerate(ordered, start=1):
        result.append({**row, "rank": rank, "total_rows": total})
    return result


def _score_columns() -> tuple[str, ...]:
    return (
        *AUDIT_COLUMNS,
        TARGET_COLUMN,
        "anomaly_score_raw",
        "anomaly_score",
        "transparent_baseline_score",
        "baseline_signal_amount_deviation",
        "baseline_signal_time_deviation",
        "baseline_signal_rapid_repeat",
        "baseline_signal_novelty",
        "baseline_signal_history_limited",
        "synthetic_label_evaluation_only",
        "synthetic_label_notice",
    )


def _report(result: Mapping[str, Any]) -> str:
    lines = [
        "# SpendShield v2 Research-Only Anomaly Evaluation",
        "",
        "This report evaluates anomaly ranking against intentionally generated synthetic scenarios only.",
        "It is not real-world fraud detection, a production risk score, or a payment decision.",
        "",
        "## Model",
        "",
        f"- Model: `{result['model']['type']}`",
        f"- Model version: `{result['model']['version']}`",
        f"- Seed: `{result['model']['random_seed']}`",
        f"- Model features: `{result['model']['feature_count']}` numeric/prior-only fields",
        "- Fit protocol: training split only; labels and scenario metadata excluded from fitting.",
        "- Higher normalized `anomaly_score` means more anomalous under this research model.",
        "",
        "## Thresholds",
        "",
        "Thresholds are fixed training-score percentiles (90th, 95th, and 99th). They are not decision thresholds.",
        "",
        "## Validation and test summary",
        "",
    ]
    for split in ("validation", "test"):
        summary = result["evaluation"][split]["score_distribution"]
        ranking = result["evaluation"][split]["synthetic_only_ranking_metrics"]
        lines.extend(
            [
                f"### {split.title()}",
                "",
                f"- Rows: {summary['count']}; score min/median/mean/p95/max: "
                f"{summary['minimum']}/{summary['median']}/{summary['mean']}/{summary['p95']}/{summary['maximum']}",
                f"- Synthetic-only ROC-AUC: `{ranking['roc_auc']}`; average precision: `{ranking['average_precision']}`.",
                "- Top-k composition, scenario coverage, normal representation, and threshold tables are in the JSON artifact.",
                "",
            ]
        )
    lines.extend(
        [
            "## Explainability",
            "",
            f"- Explanation version: `{result['explainability']['version']}`",
            f"- Bounded samples: `{result['explainability']['sample_count']}` test rows.",
            f"- Validation: `{result['explainability']['validation']['valid']}`.",
            "- Explanations use observed amount, timing, prior-only history, novelty, and missing-history signals.",
            "",
            "## Limitations",
            "",
            "- Synthetic scenarios are not real ground truth and may be easier to separate than real behavior.",
            "- Normal and synthetic patterns overlap; score ranking is not a certainty measure.",
            "- Thresholds are fixed research percentiles and were not selected with test labels.",
            "- Explanation components are deterministic signal summaries, not causal explanations.",
            "- No production inference, backend integration, payment control, database write, or deployed model was created.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_anomaly_artifact(
    feature_dir: str | Path = "data/synthetic/v2/features",
    output_dir: str | Path = "data/synthetic/anomaly_detection/v2",
) -> dict[str, Any]:
    """Run the complete deterministic experiment and write bounded artifacts."""

    feature_root = Path(feature_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((feature_root / "feature_manifest.json").read_text(encoding="utf-8"))
    contract = _validate_feature_contract(manifest)
    if not contract["valid"]:
        raise ValueError(json.dumps(contract, indent=2))
    if manifest.get("dataset_version") != "v2":
        raise ValueError("This controlled anomaly artifact is defined for revised dataset v2 only.")
    split_rows = {
        name: _read_csv(feature_root / f"candidate_features_{name}.csv")
        for name in ("train", "validation", "test")
    }
    if any(not rows for rows in split_rows.values()):
        raise ValueError("A required anomaly split is empty.")

    model = fit_research_anomaly_model(split_rows["train"])
    scored = {
        name: _enrich_scores(rows, score_rows(model, rows))
        for name, rows in split_rows.items()
    }
    train_scores = [float(row["anomaly_score"]) for row in scored["train"]]
    thresholds = {
        "train_p90": _quantile(train_scores, 0.90),
        "train_p95": _quantile(train_scores, 0.95),
        "train_p99": _quantile(train_scores, 0.99),
    }
    classes = tuple(manifest["target"]["classes"])
    evaluation = {
        name: _evaluate_split(scored[name], classes, thresholds)
        for name in ("validation", "test")
    }
    train_evaluation = _evaluate_split(scored["train"], classes, thresholds)

    ranked_test = _ranked_rows(scored["test"])
    explanation_records = []
    for row in ranked_test[:20]:
        explanation = build_research_explanation(
            row,
            anomaly_score=float(row["anomaly_score"]),
            rank=int(row["rank"]),
            total_rows=int(row["total_rows"]),
        )
        explanation["synthetic_scenario_label"] = row[TARGET_COLUMN]
        explanation["synthetic_label_notice"] = "Offline synthetic scenario reference only; not real-world ground truth."
        explanation_records.append(explanation)
    explanation_validation = validate_explanations(
        explanation_records,
        available_features=MODEL_FEATURE_NAMES,
        synthetic_labels=classes,
        max_rows=25,
    )
    # Calling the generator again is a direct deterministic-output check.
    deterministic_again = [
        build_research_explanation(
            row,
            anomaly_score=float(row["anomaly_score"]),
            rank=int(row["rank"]),
            total_rows=int(row["total_rows"]),
        )
        for row in ranked_test[:20]
    ]
    deterministic_explanations = [
        {key: value for key, value in record.items() if key not in {"synthetic_scenario_label", "synthetic_label_notice"}}
        for record in explanation_records
    ] == deterministic_again
    if not deterministic_explanations:
        explanation_validation["valid"] = False
        explanation_validation["errors"].append("Explanation generation was not deterministic.")
    if not explanation_validation["valid"]:
        raise ValueError(json.dumps(explanation_validation, indent=2))

    feature_manifest = {
        "artifact_version": ANOMALY_ARTIFACT_VERSION,
        "dataset_version": manifest["dataset_version"],
        "generator_version": manifest["generator_version"],
        "feature_generation_version": manifest["feature_generation_version"],
        "anomaly_model_version": ANOMALY_MODEL_VERSION,
        "model_feature_names": list(MODEL_FEATURE_NAMES),
        "feature_count": len(MODEL_FEATURE_NAMES),
        "feature_specs": {name: FEATURE_SPECS[name] for name in MODEL_FEATURE_NAMES},
        "excluded_from_model_inputs": sorted(
            set(manifest.get("feature_names", [])) - set(MODEL_FEATURE_NAMES)
        ) + sorted(IDENTIFIER_FIELDS | LEAKAGE_FIELDS),
        "categorical_one_hot_policy": "Excluded from first model for a small transparent numeric baseline; source categorical novelty signals remain available in the v2 matrix.",
        "target_policy": "target_scenario_label is retained only in offline score outputs and evaluation; never used for fitting, thresholds, or explanations.",
        "temporal_policy": "Existing v2 train/validation/test files are preserved; model fit uses train only and current rows remain excluded from prior history.",
        "missing_value_policy": "Use train-only medians for missing model values; retain explicit previous-transaction missing indicator.",
        "leakage_review": contract,
        "creation_timestamp_utc": _now(),
    }
    model_config = {
        "artifact_version": ANOMALY_ARTIFACT_VERSION,
        "model_version": ANOMALY_MODEL_VERSION,
        "model_type": MODEL_TYPE,
        "library": "Python standard library",
        "library_version": platform.python_version(),
        "python_version": platform.python_version(),
        "random_seed": ANOMALY_MODEL_SEED,
        "parameters": {
            "distance": "absolute deviation from train median divided by train robust scale",
            "scale": "max(1.4826 * MAD, IQR / 1.349, 1e-9)",
            "per_feature_distance_cap": 8.0,
            "aggregation": "unweighted mean across 12 selected features",
        },
        "feature_names": list(MODEL_FEATURE_NAMES),
        "parameter_artifact": "anomaly_model_parameters.json",
        "fit_data": "train split only",
        "labels_used_during_fit": False,
        "scenario_metadata_used_during_fit": False,
        "score_semantics": {
            "raw_score": "mean capped robust distance from train-fitted feature medians; higher means more anomalous",
            "anomaly_score": "raw score min-max normalized with train raw min/max and clipped to [0, 1]",
            "direction": "higher means more anomalous",
            "comparability": "Comparable only within this dataset/model configuration; not comparable across versions without a controlled recalibration study.",
        },
        "production_artifact_written": False,
        "backend_integration_created": True,
    }
    thresholds_artifact = {
        "score_space": "normalized anomaly_score",
        "selection_policy": "Fixed percentiles of train anomaly scores; no validation/test labels used.",
        "thresholds": {
            name: {"percentile_of_train_scores": int(name.replace("train_p", "")), "value": round(value, 6)}
            for name, value in thresholds.items()
        },
        "not_a_decision_threshold": True,
        "synthetic_label_evaluation_only": True,
    }
    explanation_csv_rows = []
    for record in explanation_records:
        explanation_csv_rows.append(
            {
                **record,
                "signal_strengths": json.dumps(record["signal_strengths"], sort_keys=True),
                "signal_feature_names": json.dumps(record["signal_feature_names"]),
            }
        )
    for split_name in ("train", "validation", "test"):
        _write_csv(output_root / f"anomaly_scores_{split_name}.csv", scored[split_name], _score_columns())
    _write_json(output_root / "anomaly_model_config.json", model_config)
    _write_json(
        output_root / "anomaly_model_parameters.json",
        {
            "artifact_version": ANOMALY_ARTIFACT_VERSION,
            "model_version": ANOMALY_MODEL_VERSION,
            "model_type": MODEL_TYPE,
            "dataset_version": manifest["dataset_version"],
            "feature_version": manifest["feature_generation_version"],
            "feature_names": list(MODEL_FEATURE_NAMES),
            "fit_data": "train split only",
            "labels_used_during_fit": False,
            "scenario_metadata_used_during_fit": False,
            "train_medians": model["train_medians"],
            "train_scales": model["train_scales"],
            "train_raw_min": model["train_raw_min"],
            "train_raw_max": model["train_raw_max"],
        },
    )
    _write_json(output_root / "anomaly_feature_manifest.json", feature_manifest)
    _write_json(output_root / "research_thresholds.json", thresholds_artifact)
    _write_csv(
        output_root / "explanation_samples.csv",
        explanation_csv_rows,
        (
            "synthetic_transaction_id",
            "anomaly_score",
            "transparent_baseline_score",
            "rank",
            "anomaly_rank_percentile",
            "signal_strengths",
            "signal_feature_names",
            "explanation_text",
            "missing_history_warning",
            "synthetic_scenario_label",
            "synthetic_label_notice",
        ),
    )
    _write_json(
        output_root / "explanation_validation.json",
        {**explanation_validation, "deterministic_output": deterministic_explanations},
    )
    result = {
        "artifact_version": ANOMALY_ARTIFACT_VERSION,
        "dataset": {
            "version": manifest["dataset_version"],
            "feature_version": manifest["feature_generation_version"],
            "random_seed": manifest["random_seed"],
            "split_counts": manifest["split_counts"],
        },
        "model": {
            "type": MODEL_TYPE,
            "version": ANOMALY_MODEL_VERSION,
            "random_seed": ANOMALY_MODEL_SEED,
            "feature_count": len(MODEL_FEATURE_NAMES),
            "fit_rows": len(split_rows["train"]),
            "labels_used_during_fit": False,
            "scenario_metadata_used_during_fit": False,
        },
        "score_semantics": model_config["score_semantics"],
        "thresholds": thresholds_artifact,
        "evaluation": {
            "train": train_evaluation,
            "validation": evaluation["validation"],
            "test": evaluation["test"],
        },
        "explainability": {
            "version": "1.0.0",
            "method": "deterministic signal summaries from observed feature values",
            "sample_count": len(explanation_records),
            "validation": {**explanation_validation, "deterministic_output": deterministic_explanations},
        },
        "leakage_review": contract,
        "limitations": [
            "Synthetic scenario labels are not real ground truth.",
            "Synthetic patterns may be easier to rank than real behavior.",
            "Normal and synthetic patterns overlap, so ranking is not certainty.",
            "Thresholds are research percentiles, not decisions.",
            "Explanations are deterministic signal summaries, not causal explanations.",
            "The read-only backend integration is research-only and does not provide production inference or payment decisions.",
        ],
        "created_at_utc": _now(),
    }
    _write_json(output_root / "anomaly_evaluation_summary.json", result)
    (output_root / "anomaly_evaluation_report.md").write_text(_report(result), encoding="utf-8")
    (output_root / "README.md").write_text(
        "# SpendShield v2 research-only anomaly detection\n\n"
        "This directory contains a deterministic robust-MAD anomaly experiment, a transparent weighted signal baseline, "
        "synthetic-label offline evaluation, bounded research explanations, and serialized fitted parameters for the "
        "read-only backend research integration.\n\n"
        "The model is fit on v2 training features only. Synthetic scenario labels are never used for fitting, "
        "threshold selection, or explanation generation. Higher normalized `anomaly_score` means more anomalous "
        "within this model configuration. The artifacts are not real fraud detection, are not production inference, "
        "and do not write to backend databases or control payments. The backend may load these artifacts only for "
        "owner-scoped research reads when the approved live feature contract is available.\n",
        encoding="utf-8",
    )
    return result


def validate_anomaly_artifact(output_dir: str | Path = "data/synthetic/anomaly_detection/v2") -> dict[str, Any]:
    """Validate required files and core row-count/contract invariants."""

    root = Path(output_dir)
    required = (
        "anomaly_model_config.json",
        "anomaly_model_parameters.json",
        "anomaly_feature_manifest.json",
        "anomaly_scores_train.csv",
        "anomaly_scores_validation.csv",
        "anomaly_scores_test.csv",
        "research_thresholds.json",
        "anomaly_evaluation_report.md",
        "explanation_samples.csv",
        "explanation_validation.json",
        "anomaly_evaluation_summary.json",
        "README.md",
    )
    errors = [f"missing artifact: {name}" for name in required if not (root / name).exists()]
    if errors:
        return {"valid": False, "errors": errors}
    manifest = json.loads((root / "anomaly_feature_manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "anomaly_evaluation_summary.json").read_text(encoding="utf-8"))
    model_config = json.loads((root / "anomaly_model_config.json").read_text(encoding="utf-8"))
    model_parameters = json.loads(
        (root / "anomaly_model_parameters.json").read_text(encoding="utf-8")
    )
    explanation_validation = json.loads((root / "explanation_validation.json").read_text(encoding="utf-8"))
    for split_name, expected in summary["dataset"]["split_counts"].items():
        rows = _read_csv(root / f"anomaly_scores_{split_name}.csv")
        if len(rows) != expected:
            errors.append(f"{split_name} score rows {len(rows)} != expected {expected}")
        for row in rows:
            score = float(row["anomaly_score"])
            if not 0.0 <= score <= 1.0:
                errors.append(f"{split_name} contains out-of-range normalized score")
                break
    if model_config.get("labels_used_during_fit") is not False:
        errors.append("model config does not prove labels were excluded from fit")
    if model_config.get("scenario_metadata_used_during_fit") is not False:
        errors.append("model config does not prove scenario metadata was excluded from fit")
    if model_config.get("parameter_artifact") != "anomaly_model_parameters.json":
        errors.append("model config does not identify the fitted parameter artifact")
    if model_parameters.get("feature_names") != model_config.get("feature_names"):
        errors.append("fitted parameter feature order does not match model config")
    if set(model_parameters.get("train_medians", {})) != set(model_config.get("feature_names", [])):
        errors.append("fitted parameter medians do not cover the model features")
    if set(model_parameters.get("train_scales", {})) != set(model_config.get("feature_names", [])):
        errors.append("fitted parameter scales do not cover the model features")
    if any(float(value) <= 0 for value in model_parameters.get("train_scales", {}).values()):
        errors.append("fitted parameter scales must be positive")
    if manifest.get("leakage_review", {}).get("valid") is not True:
        errors.append("anomaly feature leakage contract is invalid")
    if explanation_validation.get("valid") is not True:
        errors.append("explanation validation is invalid")
    return {
        "valid": not errors,
        "errors": errors,
        "required_files": list(required),
        "split_counts": summary["dataset"]["split_counts"],
        "feature_count": manifest.get("feature_count"),
        "normalized_scores_in_range": not any("out-of-range" in error for error in errors),
    }


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    result = build_anomaly_artifact(
        repository_root / "data" / "synthetic" / "v2" / "features",
        repository_root / "data" / "synthetic" / "anomaly_detection" / "v2",
    )
    validation = validate_anomaly_artifact(repository_root / "data" / "synthetic" / "anomaly_detection" / "v2")
    if not validation["valid"]:
        raise SystemExit(json.dumps(validation, indent=2))
    print(json.dumps({"summary": result, "validation": validation}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
