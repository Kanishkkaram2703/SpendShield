import csv
import json
from pathlib import Path

from ml.error_analysis import CLASSES, reproduce_baseline, run_error_analysis


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "data" / "synthetic"
FEATURE_DIR = SOURCE_DIR / "features"
BASELINE_RESULT = SOURCE_DIR / "baseline" / "research_baseline_results.json"
CHECKED_OUTPUT = SOURCE_DIR / "error_analysis"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_baseline_reproduction_matches_stored_result() -> None:
    reproduction = reproduce_baseline(FEATURE_DIR, BASELINE_RESULT)

    assert reproduction["valid"] is True
    assert reproduction["test_was_used_for_fit"] is False
    assert reproduction["test_was_used_for_selection"] is False
    assert reproduction["stored_test_metrics"] == reproduction["reproduced_test_metrics"]


def test_analysis_writes_required_artifacts_and_authoritative_class_order(tmp_path: Path) -> None:
    output_dir = tmp_path / "error_analysis"
    summary = run_error_analysis(SOURCE_DIR, FEATURE_DIR, BASELINE_RESULT, output_dir)

    required = {
        "confusion_matrix_validation.csv",
        "confusion_matrix_test.csv",
        "per_class_metrics_validation.csv",
        "per_class_metrics_test.csv",
        "misclassified_test_records.csv",
        "class_distribution_report.json",
        "feature_distribution_summary.csv",
        "leakage_review.json",
        "evaluation_protocol_review.md",
        "error_analysis_report.md",
    }
    assert required.issubset({path.name for path in output_dir.iterdir()})
    assert summary["valid"] is True

    confusion = _read_csv(output_dir / "confusion_matrix_test.csv")
    assert [row["actual_class"] for row in confusion] == list(CLASSES)
    assert tuple(confusion[0].keys()) == ("actual_class",) + CLASSES


def test_metrics_cover_every_class_for_both_review_splits(tmp_path: Path) -> None:
    output_dir = tmp_path / "error_analysis"
    run_error_analysis(SOURCE_DIR, FEATURE_DIR, BASELINE_RESULT, output_dir)

    for split in ("validation", "test"):
        rows = _read_csv(output_dir / f"per_class_metrics_{split}.csv")
        assert [row["class"] for row in rows] == list(CLASSES)
        assert all(float(row["support"]) >= 0 for row in rows)
        assert all(0.0 <= float(row[metric]) <= 1.0 for row in rows for metric in ("precision", "recall", "f1"))


def test_misclassified_records_are_bounded_safe_and_deterministic(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    run_error_analysis(SOURCE_DIR, FEATURE_DIR, BASELINE_RESULT, first_dir)
    run_error_analysis(SOURCE_DIR, FEATURE_DIR, BASELINE_RESULT, second_dir)

    first = (first_dir / "misclassified_test_records.csv").read_bytes()
    second = (second_dir / "misclassified_test_records.csv").read_bytes()
    assert first == second

    rows = _read_csv(first_dir / "misclassified_test_records.csv")
    assert len(rows) <= 200
    assert rows
    assert all(row["prediction_correct"] == "False" for row in rows)
    assert {row["error_type"] for row in rows} <= {
        "false_negative_for_synthetic_pattern",
        "false_positive_against_normal",
        "confusion_between_synthetic_scenarios",
    }
    assert "password" not in first.decode("utf-8").lower()
    assert "token" not in first.decode("utf-8").lower()


def test_leakage_review_and_protocol_are_explicit(tmp_path: Path) -> None:
    output_dir = tmp_path / "error_analysis"
    run_error_analysis(SOURCE_DIR, FEATURE_DIR, BASELINE_RESULT, output_dir)

    leakage = json.loads((output_dir / "leakage_review.json").read_text(encoding="utf-8"))
    assert leakage["valid"] is True
    assert all(check["status"] == "PASS" for check in leakage["checks"])
    protocol = (output_dir / "evaluation_protocol_review.md").read_text(encoding="utf-8")
    assert "DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST" in protocol
    assert "test results" in protocol


def test_class_distribution_and_validation_only_feature_summary(tmp_path: Path) -> None:
    output_dir = tmp_path / "error_analysis"
    run_error_analysis(SOURCE_DIR, FEATURE_DIR, BASELINE_RESULT, output_dir)

    class_report = json.loads((output_dir / "class_distribution_report.json").read_text(encoding="utf-8"))
    assert class_report["full"]["row_count"] == 10000
    assert class_report["full"]["majority_class"] == "normal"
    assert class_report["full"]["minority_class"] == "synthetic_combined_pattern"
    assert class_report["full"]["classes"]["synthetic_combined_pattern"]["count"] == 100

    feature_rows = _read_csv(output_dir / "feature_distribution_summary.csv")
    assert feature_rows
    assert {row["split"] for row in feature_rows} == {"validation"}


def test_checked_in_analysis_outputs_match_current_run() -> None:
    summary = run_error_analysis(SOURCE_DIR, FEATURE_DIR, BASELINE_RESULT, CHECKED_OUTPUT)

    assert summary["valid"] is True
    stored = json.loads((CHECKED_OUTPUT / "analysis_summary.json").read_text(encoding="utf-8"))
    assert stored["reproduction_valid"] is True
    assert stored["leakage_review_valid"] is True
    assert stored["test_metrics"] == summary["test_metrics"]
