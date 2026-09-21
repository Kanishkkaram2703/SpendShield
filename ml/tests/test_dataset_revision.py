import csv
import json
from decimal import Decimal
from pathlib import Path

from ml.dataset_comparison import READY, compare_versions
from ml.error_analysis import run_error_analysis
from ml.feature_matrix import build_feature_artifact, validate_feature_artifact
from ml.research_baseline import evaluate_research_baseline
from ml.synthetic_dataset_generator import (
    REQUIRED_COLUMNS,
    SCENARIO_LABELS,
    generate_revised_dataset,
    revised_dataset_config,
    validate_records,
    validate_written_dataset,
    write_dataset,
)


ROOT = Path(__file__).resolve().parents[2]
V2_DIR = ROOT / "data" / "synthetic" / "v2"
V2_FEATURE_DIR = V2_DIR / "features"
V2_BASELINE = V2_DIR / "baseline" / "research_baseline_results.json"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _rate(rows: list[dict[str, str]], predicate) -> float:
    selected = [row for row in rows if predicate(row)]
    return len(selected) / len(rows) if rows else 0.0


def test_revised_generator_metadata_schema_and_reproducibility(tmp_path: Path) -> None:
    config = revised_dataset_config()
    first = generate_revised_dataset(config)
    second = generate_revised_dataset(config)

    assert first.records == second.records
    assert first.manifest["dataset_version"] == "v2"
    assert first.manifest["generator_version"] == "1.1.0"
    assert first.manifest["random_seed"] == 20260913
    assert first.manifest["scenario_distribution"] == {
        "normal": 6800,
        "synthetic_high_amount": 1000,
        "synthetic_rapid_repeat": 800,
        "synthetic_unusual_time": 700,
        "synthetic_behavior_deviation": 500,
        "synthetic_combined_pattern": 200,
    }
    assert tuple(first.records[0]) == REQUIRED_COLUMNS
    assert {row["scenario_label"] for row in first.records} == set(SCENARIO_LABELS)
    assert len({row["synthetic_transaction_id"] for row in first.records}) == 10_000
    assert all(row["currency"] == "INR" for row in first.records)
    assert all("password" not in row and "token" not in row for row in first.records)
    assert validate_records(
        first.records,
        config=config,
        splits=first.splits,
        manifest=first.manifest,
    )["valid"] is True

    output_dir = tmp_path / "v2"
    manifest = write_dataset(first, output_dir, config)
    assert len(manifest["checksums_sha256"]) == 4
    assert len(manifest["data_types"]) == len(REQUIRED_COLUMNS)
    assert validate_written_dataset(output_dir)["valid"] is True


def test_revised_generator_has_realistic_overlap_in_validation() -> None:
    rows = [dict(row) for row in generate_revised_dataset().splits["validation"]]

    rapid_rate = _rate(
        [row for row in rows if row["scenario_label"] == "synthetic_rapid_repeat"],
        lambda row: row["time_since_previous_transaction_seconds"] is not None
        and row["time_since_previous_transaction_seconds"] <= 600,
    )
    unusual_rate = _rate(
        [row for row in rows if row["scenario_label"] == "synthetic_unusual_time"],
        lambda row: row["transaction_hour"] in {0, 1, 2, 3, 4, 23},
    )
    combined_fixed_rule_rate = _rate(
        [row for row in rows if row["scenario_label"] == "synthetic_combined_pattern"],
        lambda row: (
            row["transaction_hour"] in {0, 1, 2, 3, 4, 23}
            and row["time_since_previous_transaction_seconds"] is not None
            and row["time_since_previous_transaction_seconds"] <= 600
            and Decimal(row["user_historical_average_amount_before"]) > 0
            and Decimal(row["amount"])
            / Decimal(row["user_historical_average_amount_before"])
            >= 3
        ),
    )
    normal_rows = [row for row in rows if row["scenario_label"] == "normal"]
    normal_short_rate = _rate(
        normal_rows,
        lambda row: row["time_since_previous_transaction_seconds"] is not None
        and row["time_since_previous_transaction_seconds"] <= 600,
    )
    normal_late_rate = _rate(normal_rows, lambda row: row["transaction_hour"] in {0, 1, 2, 3, 4, 23})

    assert 0.0 < rapid_rate < 0.95
    assert 0.0 < unusual_rate < 0.95
    assert combined_fixed_rule_rate < 0.95
    assert normal_short_rate > 0.0
    assert normal_late_rate > 0.0


def test_revised_feature_artifact_has_prior_only_behavior_features() -> None:
    validation = validate_feature_artifact(V2_FEATURE_DIR)

    assert validation["valid"] is True
    assert validation["feature_count"] == 32
    manifest = json.loads((V2_FEATURE_DIR / "feature_manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["derived_candidate_feature_fields"]) == {
        "merchant_novelty_before",
        "channel_novelty_before",
        "user_relative_amount_deviation",
        "user_relative_time_deviation",
    }
    assert manifest["historical_feature_audit"]["valid"] is True
    assert not validation["excluded_fields_present_as_features"]


def test_revised_baseline_and_error_analysis_are_reproducible(tmp_path: Path) -> None:
    baseline = evaluate_research_baseline(V2_FEATURE_DIR, output_path=None)
    assert baseline["baseline_version"] == "1.1.0"
    assert baseline["feature_count"] == 32
    assert baseline["data_usage"]["fit"] == "train only"
    assert baseline["data_usage"]["test"].startswith("final held-out")

    output_dir = tmp_path / "error_analysis"
    summary = run_error_analysis(V2_DIR, V2_FEATURE_DIR, V2_BASELINE, output_dir)
    assert summary["valid"] is True
    assert summary["decision"] == READY
    assert summary["leakage_review_valid"] is True
    shortcut = json.loads((output_dir / "shortcut_review.json").read_text(encoding="utf-8"))
    assert shortcut["status"] == "OVERLAP_REVIEW_COMPLETED"


def test_version_comparison_reports_both_versions(tmp_path: Path) -> None:
    comparison = compare_versions(ROOT / "data" / "synthetic", V2_DIR, tmp_path / "comparison")

    assert comparison["decision"] == READY
    assert comparison["old"]["generator_version"] == "1.0.0"
    assert comparison["new"]["generator_version"] == "1.1.0"
    assert comparison["old"]["feature_count"] == 28
    assert comparison["new"]["feature_count"] == 32
    assert comparison["reproducibility"] == {"old": True, "new": True}
    assert comparison["leakage_checks"] == {"old": True, "new": True}
