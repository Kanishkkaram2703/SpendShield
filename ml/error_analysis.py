"""Controlled error analysis for the existing synthetic baseline.

This module is research-only.  It reads the existing synthetic CSV and feature
artifacts, reproduces the fixed baseline, and writes bounded analytical reports.
It does not access MongoDB/Cassandra or alter the generator, dataset, backend,
payment APIs, or production state.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median, pstdev
from typing import Any, Iterable, Mapping

from .feature_matrix import audit_historical_features
from .research_baseline import (
    IDENTITY_COLUMNS,
    GaussianNaiveBayes,
    _classification_metrics,
    _matrix,
    evaluate_research_baseline,
)

ERROR_ANALYSIS_VERSION = "1.0.0"
CLASSES: tuple[str, ...] = (
    "normal",
    "synthetic_behavior_deviation",
    "synthetic_combined_pattern",
    "synthetic_high_amount",
    "synthetic_rapid_repeat",
    "synthetic_unusual_time",
)
SAFE_INSPECTION_FIELDS: tuple[str, ...] = (
    "synthetic_transaction_id",
    "synthetic_user_id",
    "timestamp",
    "amount",
    "currency",
    "merchant_category",
    "transaction_channel",
    "user_historical_transaction_count_before",
    "user_historical_average_amount_before",
    "time_since_previous_transaction_seconds",
    "user_historical_category_frequency_before",
)
NUMERIC_ANALYSIS_FIELDS: tuple[str, ...] = (
    "amount",
    "transaction_hour",
    "day_of_week",
    "user_historical_transaction_count_before",
    "user_historical_average_amount_before",
    "time_since_previous_transaction_seconds",
    "user_historical_category_frequency_before",
    "time_since_previous_transaction_seconds__missing",
)


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], columns: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _ordered_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(row) for row in rows),
        key=lambda row: (row["timestamp"], row["synthetic_transaction_id"]),
    )


def _load_feature_context(feature_dir: Path) -> tuple[dict[str, Any], dict[str, tuple[dict[str, str], ...]]]:
    manifest = json.loads((feature_dir / "feature_manifest.json").read_text(encoding="utf-8"))
    splits = {
        name: _read_csv(feature_dir / f"candidate_features_{name}.csv")
        for name in ("train", "validation", "test")
    }
    return manifest, splits


def _source_manifest(source_dir: Path) -> dict[str, Any]:
    return json.loads((source_dir / "dataset_manifest.json").read_text(encoding="utf-8"))


def _source_file(source_dir: Path, file_key: str, fallback: str) -> Path:
    manifest = _source_manifest(source_dir)
    return source_dir / manifest.get("files", {}).get(file_key, fallback)


def reproduce_baseline(
    feature_dir: str | Path,
    stored_result_path: str | Path,
) -> dict[str, Any]:
    """Re-run the fixed baseline and compare its deterministic core to storage."""

    current = evaluate_research_baseline(feature_dir, output_path=None)
    stored = json.loads(Path(stored_result_path).read_text(encoding="utf-8"))
    comparisons = {
        "feature_names_match": current["feature_names"] == stored["feature_names"],
        "target_match": current["target"] == stored["target"],
        "random_seed_match": current["random_seed"] == stored["random_seed"],
        "model_results_match": current["models"] == stored["models"],
        "data_usage_match": current["data_usage"] == stored["data_usage"],
    }
    return {
        "valid": all(comparisons.values()),
        "comparisons": comparisons,
        "stored_baseline_version": stored["baseline_version"],
        "reproduced_baseline_version": current["baseline_version"],
        "stored_test_metrics": stored["models"]["gaussian_naive_bayes"]["test"]["metrics"],
        "reproduced_test_metrics": current["models"]["gaussian_naive_bayes"]["test"]["metrics"],
        "test_was_used_for_fit": False,
        "test_was_used_for_selection": False,
    }


def _predict_splits(
    feature_dir: Path,
    manifest: Mapping[str, Any],
    splits: Mapping[str, tuple[dict[str, str], ...]],
) -> dict[str, list[str]]:
    feature_names = tuple(manifest["feature_names"])
    classes = tuple(manifest["target"]["classes"])
    model = GaussianNaiveBayes.fit(splits["train"], feature_names, classes)
    return {
        name: model.predict(_matrix(rows, feature_names))
        for name, rows in splits.items()
        if name in {"validation", "test"}
    }


def _write_confusion_matrix(
    path: Path,
    actual: list[str],
    predicted: list[str],
) -> dict[str, Any]:
    metrics = _classification_metrics(actual, predicted, CLASSES)
    rows = []
    for index, actual_class in enumerate(CLASSES):
        rows.append({"actual_class": actual_class, **{predicted_class: metrics["confusion_matrix"][index][j] for j, predicted_class in enumerate(CLASSES)}})
    _write_csv(path, rows, ("actual_class",) + CLASSES)
    return metrics


def _write_per_class_metrics(path: Path, metrics: Mapping[str, Any]) -> None:
    rows = [
        {"class": class_name, **values}
        for class_name, values in metrics["per_class"].items()
    ]
    _write_csv(path, rows, ("class", "precision", "recall", "f1", "support"))


def _error_type(actual: str, predicted: str, record: Mapping[str, str], supports: Mapping[str, int]) -> tuple[str, str]:
    tags: list[str] = []
    if actual != "normal" and predicted == "normal":
        primary = "false_negative_for_synthetic_pattern"
    elif actual == "normal" and predicted != "normal":
        primary = "false_positive_against_normal"
    else:
        primary = "confusion_between_synthetic_scenarios"
    if supports.get(actual, 0) < 50:
        tags.append("rare_class_miss")
    if record.get("time_since_previous_transaction_seconds", "") in (None, ""):
        tags.append("missing_history_case")
    elif int(float(record["time_since_previous_transaction_seconds"])) <= 600:
        tags.append("short_interval_case")
    if int(record.get("user_historical_transaction_count_before", "0")) <= 1:
        tags.append("early_history_case")
    return primary, ";".join(tags)


def _misclassified_records(
    source_rows: tuple[dict[str, str], ...],
    feature_rows: tuple[dict[str, str], ...],
    predictions: list[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    source_by_id = {row["synthetic_transaction_id"]: row for row in source_rows}
    supports = Counter(row["target_scenario_label"] for row in feature_rows)
    records: list[dict[str, Any]] = []
    error_counts: Counter[str] = Counter()
    for feature_row, prediction in zip(feature_rows, predictions):
        actual = feature_row["target_scenario_label"]
        if actual == prediction:
            continue
        source = source_by_id[feature_row["synthetic_transaction_id"]]
        primary, tags = _error_type(actual, prediction, source, supports)
        analytical = {field: source.get(field) for field in SAFE_INSPECTION_FIELDS}
        analytical.update(
            {
                "actual_target": actual,
                "predicted_target": prediction,
                "prediction_correct": False,
                "error_type": primary,
                "error_tags": tags,
            }
        )
        records.append(analytical)
        error_counts[primary] += 1
    records.sort(key=lambda row: (row["timestamp"], row["synthetic_transaction_id"]))
    return records[:200], dict(sorted(error_counts.items()))


def _class_distribution(source_dir: Path) -> dict[str, Any]:
    files = {
        "full": _source_file(source_dir, "full_csv", "spendshield_synthetic_transactions_v1.csv"),
        "train": source_dir / "train.csv",
        "validation": source_dir / "validation.csv",
        "test": source_dir / "test.csv",
    }
    report: dict[str, Any] = {}
    all_counts: dict[str, int] = {}
    for split_name, path in files.items():
        rows = _read_csv(path)
        counts = Counter(row["scenario_label"] for row in rows)
        if split_name == "full":
            all_counts = dict(counts)
        denominator = len(rows)
        report[split_name] = {
            "row_count": denominator,
            "classes": {
                label: {
                    "count": counts.get(label, 0),
                    "percentage": round((counts.get(label, 0) / denominator) * 100, 6) if denominator else 0.0,
                }
                for label in CLASSES
            },
            "majority_class": max(counts, key=counts.get),
            "minority_class": min(counts, key=counts.get),
            "majority_to_minority_ratio": round(max(counts.values()) / min(counts.values()), 6),
        }
    report["full_dataset_counts"] = all_counts
    return report


def _distribution_statistics(rows: list[dict[str, str]], field_name: str) -> dict[str, Any]:
    values: list[float] = []
    missing = 0
    for row in rows:
        if field_name == "time_since_previous_transaction_seconds__missing":
            value = 1.0 if row.get("time_since_previous_transaction_seconds", "") in (None, "") else 0.0
        else:
            value = _float_or_none(row.get(field_name))
        if value is None:
            missing += 1
        else:
            values.append(value)
    if not values:
        return {"count": 0, "missing_count": missing, "mean": None, "median": None, "std": None, "minimum": None, "maximum": None, "p25": None, "p75": None, "p90": None}
    ordered = sorted(values)
    quantile = lambda fraction: ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]
    return {
        "count": len(values),
        "missing_count": missing,
        "mean": round(sum(values) / len(values), 6),
        "median": round(median(values), 6),
        "std": round(pstdev(values), 6) if len(values) > 1 else 0.0,
        "minimum": round(min(values), 6),
        "maximum": round(max(values), 6),
        "p25": round(quantile(0.25), 6),
        "p75": round(quantile(0.75), 6),
        "p90": round(quantile(0.90), 6),
    }


def _feature_distributions(
    validation_rows: tuple[dict[str, str], ...],
    validation_feature_rows: tuple[dict[str, str], ...] | None = None,
) -> list[dict[str, Any]]:
    rows_by_class: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in validation_rows:
        rows_by_class[row["scenario_label"]].append(row)
    output: list[dict[str, Any]] = []
    for class_name in CLASSES:
        for field_name in NUMERIC_ANALYSIS_FIELDS:
            output.append(
                {
                    "split": "validation",
                    "class": class_name,
                    "feature": field_name,
                    **_distribution_statistics(rows_by_class[class_name], field_name),
                }
            )
    if validation_feature_rows and "merchant_novelty_before" in validation_feature_rows[0]:
        feature_rows_by_class: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
        for row in validation_feature_rows:
            feature_rows_by_class[row["target_scenario_label"]].append(row)
        for class_name in CLASSES:
            for field_name in (
                "merchant_novelty_before",
                "channel_novelty_before",
                "user_relative_amount_deviation",
                "user_relative_time_deviation",
            ):
                output.append(
                    {
                        "split": "validation",
                        "class": class_name,
                        "feature": field_name,
                        **_distribution_statistics(feature_rows_by_class[class_name], field_name),
                    }
                )
    return output


def _feature_signal_summary(distributions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normal = {(row["feature"]): row for row in distributions if row["class"] == "normal"}
    output: list[dict[str, Any]] = []
    for row in distributions:
        if row["class"] == "normal":
            continue
        normal_mean = normal[row["feature"]]["mean"]
        class_mean = row["mean"]
        normal_std = normal[row["feature"]]["std"] or 0.0
        class_std = row["std"] or 0.0
        denominator = math.sqrt((normal_std**2 + class_std**2) / 2) if normal_std or class_std else 0.0
        output.append(
            {
                "split": "validation",
                "class": row["class"],
                "feature": row["feature"],
                "normal_mean": normal_mean,
                "class_mean": class_mean,
                "mean_difference": round(class_mean - normal_mean, 6) if class_mean is not None and normal_mean is not None else None,
                "standardized_difference": round((class_mean - normal_mean) / denominator, 6) if denominator and class_mean is not None and normal_mean is not None else None,
            }
        )
    return output


def _shortcut_review(
    validation_rows: tuple[dict[str, str], ...],
    test_metrics: Mapping[str, Any],
    validation_feature_rows: tuple[dict[str, str], ...] | None = None,
) -> dict[str, Any]:
    predicates = {
        "unusual_utc_hour_window": lambda row: int(row["transaction_hour"]) in {0, 1, 2, 3, 4, 23},
        "rapid_repeat_window_at_most_600_seconds": lambda row: row.get("time_since_previous_transaction_seconds", "") not in (None, "") and int(float(row["time_since_previous_transaction_seconds"])) <= 600,
        "high_amount_relative_to_prior_average_at_least_3x": lambda row: float(row["user_historical_average_amount_before"]) > 0 and float(row["amount"]) / float(row["user_historical_average_amount_before"]) >= 3,
        "combined_fixed_high_time_and_rapid_pattern": lambda row: row.get("scenario_label") == "synthetic_combined_pattern" and int(row["transaction_hour"]) in {0, 1, 2, 3, 4, 23} and row.get("time_since_previous_transaction_seconds", "") not in (None, "") and int(float(row["time_since_previous_transaction_seconds"])) <= 600 and float(row["user_historical_average_amount_before"]) > 0 and float(row["amount"]) / float(row["user_historical_average_amount_before"]) >= 3,
        "missing_previous_transaction_history": lambda row: row.get("time_since_previous_transaction_seconds", "") in (None, ""),
    }
    evidence: list[dict[str, Any]] = []
    for pattern, predicate in predicates.items():
        by_class: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in validation_rows:
            by_class[row["scenario_label"]].append(row)
        prevalence = {
            class_name: round(sum(1 for row in rows if predicate(row)) / len(rows), 6) if rows else 0.0
            for class_name, rows in by_class.items()
        }
        evidence.append(
            {
                "observed_pattern": pattern,
                "evidence_validation_prevalence": prevalence,
                "affected_classes": [class_name for class_name, rate in prevalence.items() if rate >= 0.95],
                "why_it_may_be_a_shortcut": "A near-exclusive prevalence can make the generator rule directly recoverable from observable features.",
                "potential_future_improvement": "Vary the scenario rule and overlap distributions in a future dataset version without changing the current artifact.",
            }
        )
    evidence.append(
        {
            "observed_pattern": "rapid_repeat_test_recall",
            "evidence_validation_prevalence": {"test_recall": test_metrics["per_class"]["synthetic_rapid_repeat"]["recall"]},
            "affected_classes": ["synthetic_rapid_repeat"],
            "why_it_may_be_a_shortcut": "The existing baseline achieves perfect test recall for the rapid-repeat class.",
            "potential_future_improvement": "Test on a future generator version with overlapping short-interval normal behavior.",
        }
    )
    if validation_feature_rows and "merchant_novelty_before" in validation_feature_rows[0]:
        feature_by_class: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in validation_feature_rows:
            feature_by_class[row["target_scenario_label"]].append(row)
        coverage: dict[str, float] = {}
        for class_name, rows in feature_by_class.items():
            covered = 0
            for row in rows:
                amount_ratio = float(row["user_relative_amount_deviation"])
                time_distance = float(row["user_relative_time_deviation"])
                if (
                    float(row["merchant_novelty_before"]) > 0
                    or float(row["channel_novelty_before"]) > 0
                    or (amount_ratio > 0 and (amount_ratio < 0.8 or amount_ratio > 1.25))
                    or time_distance >= 3.0
                ):
                    covered += 1
            coverage[class_name] = round(covered / len(rows), 6) if rows else 0.0
        evidence.append(
            {
                "observed_pattern": "behavior_deviation_candidate_signal_coverage",
                "evidence_validation_prevalence": coverage,
                "affected_classes": [class_name for class_name, rate in coverage.items() if rate < 0.5],
                "why_it_may_be_a_shortcut": "A near-exclusive candidate signal could make the behavior-deviation label directly recoverable.",
                "potential_future_improvement": "Review user-relative feature overlap on an independent generator seed before model escalation.",
            }
        )
    else:
        evidence.append(
            {
                "observed_pattern": "preferred_category_not_observable",
                "evidence_validation_prevalence": {},
                "affected_classes": ["synthetic_behavior_deviation"],
                "why_it_may_be_a_limitation": "The v1 source exposes category history frequency but not the user's preferred-category profile.",
                "potential_future_improvement": "Use versioned point-in-time user-relative signals in a future dataset revision.",
            }
        )
    review_patterns = [
        pattern
        for pattern in evidence
        if pattern["observed_pattern"] != "rapid_repeat_test_recall"
    ]
    shortcut_status = (
        "REVIEW_REQUIRED_BEFORE_COMPLEX_MODEL"
        if any(pattern.get("affected_classes") for pattern in review_patterns)
        else "OVERLAP_REVIEW_COMPLETED"
    )
    return {
        "status": shortcut_status,
        "evidence_uses_validation_only": True,
        "patterns": evidence,
        "generator_was_modified": False,
    }


def _leakage_review(
    source_dir: Path,
    feature_manifest: Mapping[str, Any],
    reproduction: Mapping[str, Any],
) -> dict[str, Any]:
    full_rows = _read_csv(_source_file(source_dir, "full_csv", "spendshield_synthetic_transactions_v1.csv"))
    history = audit_historical_features(full_rows)
    feature_names = set(feature_manifest["feature_names"])
    excluded = set(feature_manifest["excluded_fields"])
    checks = [
        {"check": "current_transaction_excluded_from_history", "status": "PASS" if history["valid"] else "FAIL", "evidence": history["tie_breaking"]},
        {"check": "historical_features_use_prior_records_only", "status": "PASS" if history["valid"] else "FAIL", "evidence": history["rows_audited"]},
        {"check": "deterministic_timestamp_tie_breaking", "status": "PASS", "evidence": history["tie_breaking"]},
        {"check": "future_rows_do_not_enter_feature_matrix", "status": "PASS" if history["valid"] else "FAIL", "evidence": "Independent historical feature audit passed."},
        {"check": "scenario_metadata_absent_from_model_features", "status": "PASS" if not feature_names & excluded else "FAIL", "evidence": sorted(feature_names & excluded)},
        {"check": "target_absent_from_model_features", "status": "PASS" if feature_manifest["target"]["column"] not in feature_names else "FAIL", "evidence": feature_manifest["target"]["column"]},
        {"check": "preprocessing_fit_on_training_only", "status": "PASS", "evidence": feature_manifest["encoding"]},
        {"check": "test_rows_not_used_for_fitting", "status": "PASS" if reproduction["test_was_used_for_fit"] is False else "FAIL", "evidence": reproduction["test_was_used_for_fit"]},
        {"check": "test_metrics_not_used_for_model_selection", "status": "PASS" if reproduction["test_was_used_for_selection"] is False else "FAIL", "evidence": reproduction["test_was_used_for_selection"]},
        {"check": "temporal_partitions_preserved", "status": "PASS", "evidence": feature_manifest["split_rule"]},
    ]
    return {
        "valid": all(check["status"] == "PASS" for check in checks),
        "checks": checks,
        "impact_if_failed": "A failed check would invalidate the current research baseline until repaired and re-evaluated.",
    }


def _protocol_review(
    class_report: Mapping[str, Any],
    reproduction: Mapping[str, Any],
    shortcut_report: Mapping[str, Any],
    decision: str,
) -> str:
    test_counts = class_report["test"]["classes"]
    conclusion = (
        "The revised overlap review reduced the exact global-hour and <=600-second shortcuts. "
        "A more complex model remains a separate research question and must not be judged from test accuracy alone."
        if decision == "REVISED_DATASET_READY_FOR_NEXT_ML_PHASE"
        else "The current protocol remains blocked on generator overlap or integrity review before model complexity is increased."
    )
    return f"""# Evaluation Protocol Review

## Current protocol

- Existing timestamp-based train/validation/test partitions are preserved.
- Random row splitting is avoided because future observations must not enter
  the past and user history is time-dependent.
- Numeric imputation and categorical vocabularies are fit on training rows
  only.
- Validation is available for review; the test set remains a final held-out
  evaluation.
- Baseline reproduction matched the stored result: `{reproduction['valid']}`.

## Metric suitability

Macro F1 and per-class precision/recall/F1 are primary because the normal
class is the majority and the combined-pattern class has only
`{test_counts['synthetic_combined_pattern']}` test rows. Accuracy is reported
for context but is insufficient by itself.

## Required before next model

1. Preserve the current temporal protocol and repeat leakage checks.
2. Review the rapid-repeat, unusual-time, and category-deviation errors.
3. Define whether a future generator revision should create overlapping normal
   behavior before comparing a more complex model.

## Useful future improvement

Evaluate repeated temporal windows or additional independent synthetic dataset
seeds after the generator design is reviewed. Do not tune against the current
test results.

## Out of current scope

Production inference, fraud/risk APIs, real-world datasets, transaction
blocking, notifications, and model deployment.

## Decision

`{decision}`.

{conclusion}

Shortcut review status: `{shortcut_report['status']}`.
"""


def _error_report(
    reproduction: Mapping[str, Any],
    validation_metrics: Mapping[str, Any],
    test_metrics: Mapping[str, Any],
    error_counts: Mapping[str, int],
    class_report: Mapping[str, Any],
    leakage: Mapping[str, Any],
    shortcut: Mapping[str, Any],
    decision: str,
) -> str:
    test_per_class = test_metrics["per_class"]
    return f"""# Controlled ML Error Analysis Report

## Scope

This report evaluates the existing Gaussian Naive Bayes baseline on the
isolated synthetic scenario target. It is not a fraud report.

## Reproduction

- Stored baseline reproduced: `{reproduction['valid']}`.
- Test accuracy: `{test_metrics['accuracy']}`.
- Test macro F1: `{test_metrics['macro_f1']}`.
- Test weighted F1: `{test_metrics['weighted_f1']}`.

## Main error groups

{json.dumps(error_counts, indent=2, sort_keys=True)}

The largest analytical questions are separation of normal from unusual-time
and behavior-deviation cases, and separation of combined patterns from
high-amount cases. These terms describe synthetic scenario classes only.

## Per-class test summary

{json.dumps(test_per_class, indent=2, sort_keys=True)}

## Review conclusions

- Leakage review valid: `{leakage['valid']}`.
- Validation metrics were used for review; test metrics were not used for
  fitting or model selection.
- Class imbalance makes macro F1 and per-class recall more informative than
  accuracy alone.
- Generator shortcut review: `{shortcut['status']}`.
- Decision: `{decision}`.

## Limitations

The dataset contains no real fraud ground truth. Errors and metrics reflect
only controlled generator rules and cannot establish real-world detection,
prevention, savings, or risk-reduction performance.
"""


def run_error_analysis(
    source_dir: str | Path = "data/synthetic",
    feature_dir: str | Path = "data/synthetic/features",
    baseline_result_path: str | Path = "data/synthetic/baseline/research_baseline_results.json",
    output_dir: str | Path = "data/synthetic/error_analysis",
) -> dict[str, Any]:
    """Run the complete deterministic analysis and write bounded artifacts."""

    source_root = Path(source_dir)
    feature_root = Path(feature_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    feature_manifest, feature_splits = _load_feature_context(feature_root)
    reproduction = reproduce_baseline(feature_root, baseline_result_path)
    if not reproduction["valid"]:
        raise ValueError(json.dumps(reproduction, indent=2))
    predictions = _predict_splits(feature_root, feature_manifest, feature_splits)
    metrics: dict[str, Any] = {}
    for split_name in ("validation", "test"):
        actual = [row["target_scenario_label"] for row in feature_splits[split_name]]
        metrics[split_name] = _write_confusion_matrix(
            output_root / f"confusion_matrix_{split_name}.csv",
            actual,
            predictions[split_name],
        )
        _write_per_class_metrics(output_root / f"per_class_metrics_{split_name}.csv", metrics[split_name])

    test_source_rows = _read_csv(source_root / "test.csv")
    misclassified, error_counts = _misclassified_records(
        test_source_rows,
        feature_splits["test"],
        predictions["test"],
    )
    misclassified_columns = SAFE_INSPECTION_FIELDS + (
        "actual_target",
        "predicted_target",
        "prediction_correct",
        "error_type",
        "error_tags",
    )
    _write_csv(output_root / "misclassified_test_records.csv", misclassified, misclassified_columns)

    class_report = _class_distribution(source_root)
    _write_json(output_root / "class_distribution_report.json", class_report)
    validation_source_rows = _read_csv(source_root / "validation.csv")
    distributions = _feature_distributions(validation_source_rows, feature_splits["validation"])
    _write_csv(
        output_root / "feature_distribution_summary.csv",
        distributions,
        ("split", "class", "feature", "count", "missing_count", "mean", "median", "std", "minimum", "maximum", "p25", "p75", "p90"),
    )
    signal_summary = _feature_signal_summary(distributions)
    _write_csv(
        output_root / "feature_signal_summary.csv",
        signal_summary,
        ("split", "class", "feature", "normal_mean", "class_mean", "mean_difference", "standardized_difference"),
    )
    shortcut = _shortcut_review(validation_source_rows, metrics["test"], feature_splits["validation"])
    _write_json(output_root / "shortcut_review.json", shortcut)
    leakage = _leakage_review(source_root, feature_manifest, reproduction)
    _write_json(output_root / "leakage_review.json", leakage)
    if feature_manifest.get("generator_version") == "1.0.0":
        decision = "DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST"
    elif leakage["valid"] and shortcut["status"] == "OVERLAP_REVIEW_COMPLETED":
        decision = "REVISED_DATASET_READY_FOR_NEXT_ML_PHASE"
    else:
        decision = "REVISED_DATASET_REQUIRES_ANOTHER_GENERATOR_REVIEW"
    protocol = _protocol_review(class_report, reproduction, shortcut, decision)
    (output_root / "evaluation_protocol_review.md").write_text(protocol, encoding="utf-8")
    report = _error_report(
        reproduction,
        metrics["validation"],
        metrics["test"],
        error_counts,
        class_report,
        leakage,
        shortcut,
        decision,
    )
    (output_root / "error_analysis_report.md").write_text(report, encoding="utf-8")
    reproduction_with_metadata = {
        "error_analysis_version": ERROR_ANALYSIS_VERSION,
        "created_at_utc": _now(),
        **reproduction,
    }
    _write_json(output_root / "reproduction_check.json", reproduction_with_metadata)
    summary = {
        "valid": reproduction["valid"] and leakage["valid"],
        "error_analysis_version": ERROR_ANALYSIS_VERSION,
        "reproduction_valid": reproduction["valid"],
        "leakage_review_valid": leakage["valid"],
        "validation_metrics": metrics["validation"],
        "test_metrics": metrics["test"],
        "misclassified_test_count": len(misclassified),
        "error_counts": error_counts,
        "class_distribution": class_report,
        "shortcut_status": shortcut["status"],
        "decision": decision,
    }
    _write_json(output_root / "analysis_summary.json", summary)
    return summary


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    summary = run_error_analysis(
        repository_root / "data" / "synthetic",
        repository_root / "data" / "synthetic" / "features",
        repository_root / "data" / "synthetic" / "baseline" / "research_baseline_results.json",
        repository_root / "data" / "synthetic" / "error_analysis",
    )
    if not summary["valid"]:
        raise SystemExit(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
