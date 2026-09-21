"""Compare the preserved v1 synthetic artifacts with the revised v2 artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping


READY = "REVISED_DATASET_READY_FOR_NEXT_ML_PHASE"
REVIEW_REQUIRED = "REVISED_DATASET_REQUIRES_ANOTHER_GENERATOR_REVIEW"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _shortcut_rates(path: Path) -> dict[str, dict[str, float]]:
    report = _read_json(path / "shortcut_review.json")
    return {
        pattern["observed_pattern"]: pattern.get("evidence_validation_prevalence", {})
        for pattern in report["patterns"]
    }


def _test_metrics(path: Path) -> dict[str, Any]:
    baseline = _read_json(path / "baseline" / "research_baseline_results.json")
    return baseline["models"]["gaussian_naive_bayes"]["test"]["metrics"]


def _false_positive_rate_against_normal(metrics: Mapping[str, Any]) -> float:
    normal_index = metrics["classes"].index("normal")
    normal_support = metrics["per_class"]["normal"]["support"]
    false_positives = sum(
        metrics["confusion_matrix"][normal_index][index]
        for index in range(len(metrics["classes"]))
        if index != normal_index
    )
    return round(false_positives / normal_support, 6) if normal_support else 0.0


def _false_negative_counts(metrics: Mapping[str, Any]) -> dict[str, int]:
    normal_index = metrics["classes"].index("normal")
    return {
        class_name: metrics["confusion_matrix"][index][normal_index]
        for index, class_name in enumerate(metrics["classes"])
        if class_name != "normal"
    }


def _feature_mean_summary(path: Path) -> dict[str, float | None]:
    rows = _read_csv(path / "error_analysis" / "feature_distribution_summary.csv")
    return {
        f"{row['class']}::{row['feature']}": float(row["mean"]) if row["mean"] not in ("", "None") else None
        for row in rows
    }


def _version_snapshot(path: Path) -> dict[str, Any]:
    manifest = _read_json(path / "dataset_manifest.json")
    feature_manifest = _read_json(path / "features" / "feature_manifest.json")
    baseline = _read_json(path / "baseline" / "research_baseline_results.json")
    summary = _read_json(path / "error_analysis" / "analysis_summary.json")
    return {
        "dataset_version": manifest["dataset_version"],
        "generator_version": manifest["generator_version"],
        "feature_version": feature_manifest["feature_generation_version"],
        "baseline_version": baseline["baseline_version"],
        "seed": manifest["random_seed"],
        "row_count": manifest["row_count"],
        "user_count": manifest["user_count"],
        "merchant_count": manifest["merchant_count"],
        "category_count": manifest["category_count"],
        "date_range": manifest["date_range"],
        "scenario_distribution": manifest["scenario_distribution"],
        "split_counts": manifest["split_counts"],
        "feature_count": feature_manifest["feature_count"],
        "baseline_test_metrics": _test_metrics(path),
        "baseline_validation_metrics": baseline["models"]["gaussian_naive_bayes"]["validation"]["metrics"],
        "majority_test_metrics": baseline["models"]["majority_class"]["test"]["metrics"],
        "majority_validation_metrics": baseline["models"]["majority_class"]["validation"]["metrics"],
        "shortcut_rates": _shortcut_rates(path / "error_analysis"),
        "shortcut_status": _read_json(path / "error_analysis" / "shortcut_review.json")["status"],
        "leakage_valid": _read_json(path / "error_analysis" / "leakage_review.json")["valid"],
        "reproduction_valid": _read_json(path / "error_analysis" / "reproduction_check.json")["valid"],
        "decision": summary["decision"],
        "feature_means": _feature_mean_summary(path),
    }


def _metric_delta(old: Mapping[str, Any], new: Mapping[str, Any], key: str) -> float:
    return round(float(new[key]) - float(old[key]), 6)


def compare_versions(
    v1_dir: str | Path = "data/synthetic",
    v2_dir: str | Path = "data/synthetic/v2",
    output_dir: str | Path = "data/synthetic/comparison",
) -> dict[str, Any]:
    """Write a machine-readable and Markdown comparison of v1 and v2."""

    old = _version_snapshot(Path(v1_dir))
    new = _version_snapshot(Path(v2_dir))
    shared_features = sorted(set(old["feature_means"]) & set(new["feature_means"]))
    feature_mean_deltas = {
        key: round(float(new["feature_means"][key]) - float(old["feature_means"][key]), 6)
        for key in shared_features
        if old["feature_means"][key] is not None and new["feature_means"][key] is not None
    }
    old_test = old["baseline_test_metrics"]
    new_test = new["baseline_test_metrics"]
    old_validation = old["baseline_validation_metrics"]
    new_validation = new["baseline_validation_metrics"]
    comparison = {
        "old": old,
        "new": new,
        "metric_deltas": {
            "validation_accuracy": _metric_delta(old_validation, new_validation, "accuracy"),
            "validation_macro_f1": _metric_delta(old_validation, new_validation, "macro_f1"),
            "validation_weighted_f1": _metric_delta(old_validation, new_validation, "weighted_f1"),
            "test_accuracy": _metric_delta(old_test, new_test, "accuracy"),
            "test_macro_f1": _metric_delta(old_test, new_test, "macro_f1"),
            "test_weighted_f1": _metric_delta(old_test, new_test, "weighted_f1"),
        },
        "false_positive_rate_against_normal": {
            "old": _false_positive_rate_against_normal(old_test),
            "new": _false_positive_rate_against_normal(new_test),
            "delta": round(
                _false_positive_rate_against_normal(new_test)
                - _false_positive_rate_against_normal(old_test),
                6,
            ),
        },
        "false_negative_counts_by_synthetic_scenario": {
            "old": _false_negative_counts(old_test),
            "new": _false_negative_counts(new_test),
        },
        "confusion_matrices": {
            "class_order": old_test["classes"],
            "old": old_test["confusion_matrix"],
            "new": new_test["confusion_matrix"],
        },
        "feature_distribution_mean_deltas_shared_features": feature_mean_deltas,
        "reproducibility": {
            "old": old["reproduction_valid"],
            "new": new["reproduction_valid"],
        },
        "leakage_checks": {
            "old": old["leakage_valid"],
            "new": new["leakage_valid"],
        },
    }
    ready = (
        new["decision"] == READY
        and new["reproduction_valid"]
        and new["leakage_valid"]
        and new["shortcut_status"] == "OVERLAP_REVIEW_COMPLETED"
        and all(count > 0 for count in new["split_counts"].values())
    )
    decision = READY if ready else REVIEW_REQUIRED
    comparison["decision"] = decision
    comparison["comparison_notes"] = [
        "Higher accuracy is not treated as automatic evidence of a better dataset.",
        "Overlap, temporal integrity, class support, reproducibility, and leakage are evaluated alongside metrics.",
        "All labels remain generator-defined synthetic scenarios and are not fraud ground truth.",
    ]
    recall_table = "\n".join(
        f"| {class_name} | {old_test['per_class'][class_name]['recall']} | {new_test['per_class'][class_name]['recall']} |"
        for class_name in old_test["classes"]
    )
    shortcut_table = "\n".join(
        f"| {pattern} | `{old['shortcut_rates'].get(pattern, {})}` | `{new['shortcut_rates'].get(pattern, {})}` |"
        for pattern in sorted(set(old["shortcut_rates"]) | set(new["shortcut_rates"]))
    )
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "v1_vs_v2_comparison.json").write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = f"""# SpendShield Synthetic Dataset Version Comparison

## Decision

`{decision}`

## Version summary

| Field | v1 | v2 |
|---|---:|---:|
| Dataset version | {old['dataset_version']} | {new['dataset_version']} |
| Generator version | {old['generator_version']} | {new['generator_version']} |
| Feature version | {old['feature_version']} | {new['feature_version']} |
| Baseline version | {old['baseline_version']} | {new['baseline_version']} |
| Seed | {old['seed']} | {new['seed']} |
| Rows | {old['row_count']} | {new['row_count']} |
| Test rows | {old['split_counts']['test']} | {new['split_counts']['test']} |
| Feature count | {old['feature_count']} | {new['feature_count']} |

## Baseline comparison

- Validation macro F1: `{old_validation['macro_f1']}` -> `{new_validation['macro_f1']}` (delta `{comparison['metric_deltas']['validation_macro_f1']}`).
- Test macro F1: `{old_test['macro_f1']}` -> `{new_test['macro_f1']}` (delta `{comparison['metric_deltas']['test_macro_f1']}`).
- Test weighted F1: `{old_test['weighted_f1']}` -> `{new_test['weighted_f1']}` (delta `{comparison['metric_deltas']['test_weighted_f1']}`).
- False-positive rate against normal: `{comparison['false_positive_rate_against_normal']['old']}` -> `{comparison['false_positive_rate_against_normal']['new']}`.

The revised baseline is intentionally interpreted together with overlap and
protocol evidence. It is not a real-world fraud-performance comparison.

## Test per-class recall

| Class | v1 | v2 |
|---|---:|---:|
{recall_table}

## Shortcut comparison

| Pattern | v1 validation evidence | v2 validation evidence |
|---|---|---|
{shortcut_table}

The v2 shortcut review status is `{new['shortcut_status']}`. The exact
global-hour and <=600-second patterns were reduced rather than treated as
required labels. The complete comparison remains in
`v1_vs_v2_comparison.json`.

## Integrity

- Reproducibility: v1=`{old['reproduction_valid']}`, v2=`{new['reproduction_valid']}`.
- Leakage review: v1=`{old['leakage_valid']}`, v2=`{new['leakage_valid']}`.
- Temporal splits remain chronological and non-overlapping by transaction ID.

## Limitations

Both datasets are fictional, synthetic research artifacts. Neither establishes
fraud detection, financial-crime detection, production accuracy, prevention,
savings, or risk reduction.
"""
    (output_root / "v1_vs_v2_comparison.md").write_text(report, encoding="utf-8")
    return comparison


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    result = compare_versions(
        repository_root / "data" / "synthetic",
        repository_root / "data" / "synthetic" / "v2",
        repository_root / "data" / "synthetic" / "comparison",
    )
    print(json.dumps({"decision": result["decision"], "metric_deltas": result["metric_deltas"]}, indent=2))


if __name__ == "__main__":
    main()
