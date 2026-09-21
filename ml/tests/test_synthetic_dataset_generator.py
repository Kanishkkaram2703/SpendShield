from __future__ import annotations

import csv
import json
from pathlib import Path

from ml.synthetic_dataset_generator import (
    CANDIDATE_FEATURE_FIELDS,
    FORBIDDEN_FEATURE_FIELDS,
    SyntheticDatasetConfig,
    generate_dataset,
    validate_records,
    validate_written_dataset,
    write_dataset,
)


def test_default_dataset_is_valid_and_has_expected_contract() -> None:
    dataset = generate_dataset()
    validation = validate_records(
        dataset.records,
        splits=dataset.splits,
        manifest=dataset.manifest,
    )

    assert validation["valid"] is True
    assert validation["row_count"] == 10_000
    assert validation["user_count"] == 500
    assert validation["account_count"] == 500
    assert validation["merchant_count"] == 100
    assert validation["category_count"] == 12
    assert validation["scenario_distribution"] == {
        "normal": 7_600,
        "synthetic_high_amount": 800,
        "synthetic_rapid_repeat": 600,
        "synthetic_unusual_time": 600,
        "synthetic_behavior_deviation": 300,
        "synthetic_combined_pattern": 100,
    }
    assert not set(CANDIDATE_FEATURE_FIELDS) & set(FORBIDDEN_FEATURE_FIELDS)
    assert "scenario_label" not in CANDIDATE_FEATURE_FIELDS


def test_same_seed_produces_identical_records_and_splits() -> None:
    first = generate_dataset(SyntheticDatasetConfig(seed=1234))
    second = generate_dataset(SyntheticDatasetConfig(seed=1234))

    assert first.records == second.records
    assert first.splits == second.splits


def test_different_seed_changes_records() -> None:
    first = generate_dataset(SyntheticDatasetConfig(seed=1234))
    second = generate_dataset(SyntheticDatasetConfig(seed=1235))

    assert first.records != second.records


def test_writer_and_cross_file_validation(tmp_path: Path) -> None:
    config = SyntheticDatasetConfig(
        total_transactions=120,
        user_count=12,
        merchant_count=24,
        scenario_counts={
            "normal": 90,
            "synthetic_high_amount": 10,
            "synthetic_rapid_repeat": 8,
            "synthetic_unusual_time": 6,
            "synthetic_behavior_deviation": 4,
            "synthetic_combined_pattern": 2,
        },
    )
    dataset = generate_dataset(config)
    write_dataset(dataset, tmp_path, config)

    validation = validate_written_dataset(tmp_path)
    assert validation["valid"] is True
    assert validation["row_count"] == 120
    assert json.loads((tmp_path / "dataset_manifest.json").read_text())[
        "split_counts"
    ] == validation["split_counts"]
    with (tmp_path / "train.csv").open(newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == validation["split_counts"]["train"]


def test_generator_has_no_production_fraud_label() -> None:
    dataset = generate_dataset(SyntheticDatasetConfig(total_transactions=120, user_count=12, merchant_count=24,
        scenario_counts={
            "normal": 90,
            "synthetic_high_amount": 10,
            "synthetic_rapid_repeat": 8,
            "synthetic_unusual_time": 6,
            "synthetic_behavior_deviation": 4,
            "synthetic_combined_pattern": 2,
        }))
    for record in dataset.records:
        assert "fraud" not in record
        assert record["synthetic"] is True
        assert record["label_source"] == "generator_rule"
