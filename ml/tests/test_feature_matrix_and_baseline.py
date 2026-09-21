from __future__ import annotations

import csv
import json
from pathlib import Path

from ml.feature_matrix import (
    EXCLUDED_FIELDS,
    audit_historical_features,
    build_feature_artifact,
    validate_feature_artifact,
)
from ml.research_baseline import evaluate_research_baseline


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPOSITORY_ROOT / "data" / "synthetic"
FEATURE_DIR = SOURCE_DIR / "features"


def test_feature_artifact_is_valid_and_excludes_leakage_fields() -> None:
    validation = validate_feature_artifact(FEATURE_DIR)

    assert validation["valid"] is True
    assert validation["feature_count"] == 28
    assert validation["excluded_fields_present_as_features"] == []
    assert validation["split_counts"] == {"train": 7061, "validation": 1481, "test": 1458}
    assert "target_scenario_label" not in validation["feature_names"]
    assert not set(validation["feature_names"]) & set(EXCLUDED_FIELDS)


def test_historical_features_are_prior_only() -> None:
    with (SOURCE_DIR / "spendshield_synthetic_transactions_v1.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        records = tuple(csv.DictReader(handle))

    audit = audit_historical_features(records)
    assert audit["valid"] is True
    assert audit["rows_audited"] == 10_000
    assert "timestamp ascending" in audit["tie_breaking"]


def test_feature_artifact_rebuild_is_deterministic(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_manifest = build_feature_artifact(SOURCE_DIR, first_dir)
    second_manifest = build_feature_artifact(SOURCE_DIR, second_dir)

    for split_name in ("train", "validation", "test"):
        assert (first_dir / f"candidate_features_{split_name}.csv").read_bytes() == (
            second_dir / f"candidate_features_{split_name}.csv"
        ).read_bytes()
    assert first_manifest["feature_names"] == second_manifest["feature_names"]
    assert first_manifest["split_counts"] == second_manifest["split_counts"]


def test_baseline_is_reproducible_and_keeps_test_held_out() -> None:
    first = evaluate_research_baseline(FEATURE_DIR, output_path=None)
    second = evaluate_research_baseline(FEATURE_DIR, output_path=None)

    assert first["models"] == second["models"]
    assert first["models"]["gaussian_naive_bayes"]["test"]["row_count"] == 1458
    assert first["data_usage"]["fit"] == "train only"
    assert first["data_usage"]["test"].startswith("final held-out")
    assert first["model_artifact_written"] is False
    assert first["production_inference_created"] is False
