"""Build and validate a deterministic candidate feature matrix.

The feature artifact is research-only.  It reads the already-generated CSV
files and writes under ``data/synthetic/features``; it never imports or calls
MongoDB, Cassandra, FastAPI, or payment code.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

from .synthetic_dataset_generator import (
    CANDIDATE_FEATURE_FIELDS,
    DATASET_TYPE,
    REQUIRED_COLUMNS,
    SyntheticDatasetConfig,
    _parse_timestamp,
    validate_written_dataset,
)

FEATURE_GENERATION_VERSION = "1.0.0"
REVISED_FEATURE_GENERATION_VERSION = "1.1.0"
TARGET_COLUMN = "target_scenario_label"
AUDIT_COLUMNS: tuple[str, ...] = (
    "synthetic_transaction_id",
    "synthetic_user_id",
    "timestamp",
    "dataset_split",
)
NUMERIC_SOURCE_FIELDS: tuple[str, ...] = (
    "amount",
    "transaction_hour",
    "day_of_week",
    "user_historical_transaction_count_before",
    "user_historical_average_amount_before",
    "time_since_previous_transaction_seconds",
    "user_historical_category_frequency_before",
)
REVISED_DERIVED_NUMERIC_FIELDS: tuple[str, ...] = (
    "merchant_novelty_before",
    "channel_novelty_before",
    "user_relative_amount_deviation",
    "user_relative_time_deviation",
)
CATEGORICAL_SOURCE_FIELDS: tuple[str, ...] = (
    "currency",
    "merchant_category",
    "transaction_channel",
)
MISSING_INDICATOR_FIELD = "time_since_previous_transaction_seconds__missing"
UNKNOWN_CATEGORY = "__unknown"

EXCLUDED_FIELDS: tuple[str, ...] = (
    "scenario_label",
    "scenario_id",
    "is_synthetic_scenario",
    "label_source",
    "label_definition",
    "dataset_type",
    "synthetic",
    "source_system",
    "dataset_version",
    "dataset_split",
    "scenario_injection_reason",
    "generator_rule",
    "future_transaction_count",
    "future_average_amount",
    "final_scenario_label",
    "post_event_outcome",
    "manually_assigned_research_label",
    "fraud",
    "confirmed_fraud",
)

LEAKAGE_EXCLUSIONS: tuple[str, ...] = (
    "scenario metadata and target labels",
    "future transaction statistics",
    "post-event outcomes",
    "fields derived directly from the synthetic target",
    "identifiers and split assignment as model inputs",
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]], columns: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _decimal(value: Any) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid decimal value: {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"Non-finite decimal value: {value!r}")
    return parsed


def _numeric_value(record: Mapping[str, Any], field_name: str) -> float | None:
    value = record.get(field_name)
    if value in (None, ""):
        return None
    return float(_decimal(value))


def _sorted_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (dict(record) for record in records),
        key=lambda record: (_parse_timestamp(record["timestamp"]), record["synthetic_transaction_id"]),
    )


def audit_historical_features(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Recompute the generator's prior-only history features for an audit.

    Equal timestamps are ordered by ``synthetic_transaction_id``.  The current
    row is never included in its own history aggregate.
    """

    rows = _sorted_records(records)
    count_by_user: Counter[str] = Counter()
    amount_by_user: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    category_by_user: Counter[tuple[str, str]] = Counter()
    previous_by_user: dict[str, datetime] = {}
    errors: list[str] = []

    for row_number, record in enumerate(rows):
        user_id = record["synthetic_user_id"]
        category_key = (user_id, record["merchant_category"])
        prior_count = count_by_user[user_id]
        expected_average = (amount_by_user[user_id] / prior_count) if prior_count else Decimal("0.00")
        expected_previous_seconds = (
            int((_parse_timestamp(record["timestamp"]) - previous_by_user[user_id]).total_seconds())
            if user_id in previous_by_user
            else None
        )
        observed_average = _decimal(record["user_historical_average_amount_before"])
        observed_seconds = record.get("time_since_previous_transaction_seconds")
        observed_seconds = None if observed_seconds in (None, "") else int(observed_seconds)

        if int(record["user_historical_transaction_count_before"]) != prior_count:
            errors.append(f"row {row_number}: historical count includes current/future data")
        if observed_average != expected_average.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):
            errors.append(f"row {row_number}: historical average does not match prior rows")
        if observed_seconds != expected_previous_seconds:
            errors.append(f"row {row_number}: previous-transaction interval is inconsistent")
        expected_frequency = category_by_user[category_key] / prior_count if prior_count else 0.0
        if abs(float(record["user_historical_category_frequency_before"]) - expected_frequency) > 1e-6:
            errors.append(f"row {row_number}: category frequency is not prior-only")

        count_by_user[user_id] += 1
        amount_by_user[user_id] += _decimal(record["amount"])
        category_by_user[category_key] += 1
        previous_by_user[user_id] = _parse_timestamp(record["timestamp"])

    return {
        "valid": not errors,
        "errors": errors,
        "rows_audited": len(rows),
        "tie_breaking": "timestamp ascending, then synthetic_transaction_id ascending",
        "first_transaction_policy": {
            "historical_count": 0,
            "historical_average": "0.00 fallback",
            "time_since_previous": "missing and imputed from training median for model input",
        },
    }


def _point_in_time_derived_features(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, float]]:
    """Calculate v2 behavioral features from history strictly before each row."""

    rows = _sorted_records(records)
    seen_merchants: defaultdict[str, set[str]] = defaultdict(set)
    seen_channels: defaultdict[str, set[str]] = defaultdict(set)
    amount_totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    history_counts: Counter[str] = Counter()
    historical_hours: defaultdict[str, list[int]] = defaultdict(list)
    derived: dict[str, dict[str, float]] = {}
    for row in rows:
        user_id = row["synthetic_user_id"]
        transaction_id = row["synthetic_transaction_id"]
        prior_count = history_counts[user_id]
        prior_average = amount_totals[user_id] / prior_count if prior_count else Decimal("0.00")
        current_hour = int(row["transaction_hour"])
        average_hour = sum(historical_hours[user_id]) / prior_count if prior_count else float(current_hour)
        hour_distance = min(abs(current_hour - average_hour), 24.0 - abs(current_hour - average_hour))
        derived[transaction_id] = {
            "merchant_novelty_before": 1.0 if row["synthetic_merchant_id"] not in seen_merchants[user_id] else 0.0,
            "channel_novelty_before": 1.0 if row["transaction_channel"] not in seen_channels[user_id] else 0.0,
            "user_relative_amount_deviation": float(Decimal(row["amount"]) / prior_average) if prior_average else 0.0,
            "user_relative_time_deviation": round(float(hour_distance), 6) if prior_count else 0.0,
        }
        seen_merchants[user_id].add(row["synthetic_merchant_id"])
        seen_channels[user_id].add(row["transaction_channel"])
        amount_totals[user_id] += Decimal(row["amount"])
        history_counts[user_id] += 1
        historical_hours[user_id].append(current_hour)
    return derived


@dataclass(frozen=True, slots=True)
class FittedPreprocessor:
    """Train-fitted numeric imputation and categorical one-hot vocabulary."""

    numeric_medians: Mapping[str, float]
    categorical_values: Mapping[str, tuple[str, ...]]
    feature_names: tuple[str, ...]
    numeric_source_fields: tuple[str, ...]

    @classmethod
    def fit(
        cls,
        records: Iterable[Mapping[str, Any]],
        numeric_source_fields: tuple[str, ...] = NUMERIC_SOURCE_FIELDS,
    ) -> "FittedPreprocessor":
        rows = list(records)
        medians: dict[str, float] = {}
        for field_name in numeric_source_fields:
            values = [value for row in rows if (value := _numeric_value(row, field_name)) is not None]
            medians[field_name] = float(median(values)) if values else 0.0

        categories: dict[str, tuple[str, ...]] = {}
        for field_name in CATEGORICAL_SOURCE_FIELDS:
            categories[field_name] = tuple(sorted({str(row[field_name]) for row in rows} | {UNKNOWN_CATEGORY}))

        feature_names = list(numeric_source_fields)
        feature_names.append(MISSING_INDICATOR_FIELD)
        for field_name in CATEGORICAL_SOURCE_FIELDS:
            feature_names.extend(f"{field_name}__{value}" for value in categories[field_name])
        return cls(
            numeric_medians=medians,
            categorical_values=categories,
            feature_names=tuple(feature_names),
            numeric_source_fields=numeric_source_fields,
        )

    def transform(self, record: Mapping[str, Any]) -> dict[str, float]:
        values: dict[str, float] = {}
        for field_name in self.numeric_source_fields:
            raw_value = _numeric_value(record, field_name)
            values[field_name] = self.numeric_medians[field_name] if raw_value is None else raw_value
        values[MISSING_INDICATOR_FIELD] = (
            1.0 if record.get("time_since_previous_transaction_seconds") in (None, "") else 0.0
        )
        for field_name in CATEGORICAL_SOURCE_FIELDS:
            current_value = str(record[field_name])
            values_seen = self.categorical_values[field_name]
            selected_value = current_value if current_value in values_seen else UNKNOWN_CATEGORY
            for category_value in values_seen:
                values[f"{field_name}__{category_value}"] = 1.0 if category_value == selected_value else 0.0
        return {feature_name: values[feature_name] for feature_name in self.feature_names}


def _feature_dictionary(preprocessor: FittedPreprocessor) -> dict[str, Any]:
    dictionary: dict[str, Any] = {}
    for field_name in preprocessor.numeric_source_fields:
        dictionary[field_name] = {
            "type": "numeric",
            "source_field": field_name,
            "allowed": True,
            "reason": "Available at prediction time; historical fields are prior-only.",
            "missing_value_policy": "Training median; first-user-row historical average uses source fallback 0.00.",
        }
    dictionary[MISSING_INDICATOR_FIELD] = {
        "type": "numeric_indicator",
        "source_field": "time_since_previous_transaction_seconds",
        "allowed": True,
        "reason": "Makes the documented first-transaction missingness explicit.",
    }
    if any(field in preprocessor.numeric_source_fields for field in REVISED_DERIVED_NUMERIC_FIELDS):
        dictionary.update(
            {
            "merchant_novelty_before": {
                "type": "numeric_indicator",
                "source_field": "synthetic_merchant_id",
                "allowed": True,
                "definition": "1 when the current user's merchant has not appeared in earlier user records; otherwise 0.",
                "missing_value_policy": "0.0 when no prior merchant exists; otherwise computed point-in-time.",
                "leakage_status": "prior-only",
                "version": "1.1.0",
            },
            "channel_novelty_before": {
                "type": "numeric_indicator",
                "source_field": "transaction_channel",
                "allowed": True,
                "definition": "1 when the current user's channel has not appeared in earlier user records; otherwise 0.",
                "missing_value_policy": "0.0 when no prior channel exists; otherwise computed point-in-time.",
                "leakage_status": "prior-only",
                "version": "1.1.0",
            },
            "user_relative_amount_deviation": {
                "type": "numeric_ratio",
                "source_field": "amount / user_historical_average_amount_before",
                "allowed": True,
                "definition": "Current amount divided by the user's prior average amount; 0.0 when no prior amount exists.",
                "missing_value_policy": "0.0 for the first user transaction.",
                "leakage_status": "prior-only",
                "version": "1.1.0",
            },
            "user_relative_time_deviation": {
                "type": "numeric_distance",
                "source_field": "transaction_hour and prior user transaction hours",
                "allowed": True,
                "definition": "Circular hour distance from the user's prior average transaction hour; 0.0 for the first user transaction.",
                "missing_value_policy": "0.0 for the first user transaction.",
                "leakage_status": "prior-only",
                "version": "1.1.0",
            },
            }
        )
    for field_name in CATEGORICAL_SOURCE_FIELDS:
        dictionary[field_name] = {
            "type": "categorical",
            "source_field": field_name,
            "allowed": True,
            "encoding": "one_hot_fit_on_train_with_unknown_bucket",
            "categories_fit_on_train": list(preprocessor.categorical_values[field_name]),
        }
    return dictionary


def _feature_manifest(
    *,
    source_root: Path,
    output_root: Path,
    config: SyntheticDatasetConfig,
    source_manifest: Mapping[str, Any],
    preprocessor: FittedPreprocessor,
    source_validation: Mapping[str, Any],
    history_audit: Mapping[str, Any],
    split_counts: Mapping[str, int],
    numeric_source_fields: tuple[str, ...],
    feature_generation_version: str,
) -> dict[str, Any]:
    try:
        output_directory = str(output_root.relative_to(source_root.parent.parent))
    except ValueError:
        output_directory = str(output_root)
    return {
        "dataset_version": config.dataset_version,
        "generator_version": config.generator_version,
        "feature_generation_version": feature_generation_version,
        "dataset_type": DATASET_TYPE,
        "synthetic": True,
        "random_seed": config.seed,
        "source_files": {
            "full_csv": str((source_root / source_manifest["files"]["full_csv"]).relative_to(source_root.parent.parent)),
            "train_csv": str((source_root / "train.csv").relative_to(source_root.parent.parent)),
            "validation_csv": str((source_root / "validation.csv").relative_to(source_root.parent.parent)),
            "test_csv": str((source_root / "test.csv").relative_to(source_root.parent.parent)),
        },
        "source_row_counts": {
            "full": source_validation["row_count"],
            "train": split_counts["train"],
            "validation": split_counts["validation"],
            "test": split_counts["test"],
        },
        "feature_count": len(preprocessor.feature_names),
        "feature_names": list(preprocessor.feature_names),
        "numeric_features": list(numeric_source_fields) + [MISSING_INDICATOR_FIELD],
        "categorical_source_fields": list(CATEGORICAL_SOURCE_FIELDS),
        "encoding": "Numeric source values with train-fitted median imputation; categorical source values one-hot encoded using train categories plus an explicit unknown bucket.",
        "missing_value_handling": {
            "numeric": "Median calculated from training rows only.",
            "first_transaction": "Historical count is 0; historical average source fallback is 0.00; previous interval is missing and receives a training-median value plus a missingness indicator.",
        },
        "historical_window_definition": "All records for the same synthetic user strictly earlier under timestamp-plus-ID ordering; current record excluded.",
        "timestamp_rules": {
            "timezone": "UTC",
            "ordering": "timestamp ascending, then synthetic_transaction_id ascending",
            "split_method": "Existing timestamp-based train/validation/test files; no random reshuffle.",
        },
        "target": {
            "column": TARGET_COLUMN,
            "source_field": "scenario_label",
            "type": "multiclass synthetic scenario target",
            "classes": sorted(source_manifest["scenario_distribution"]),
            "real_fraud": False,
            "notice": "Classification of intentionally generated synthetic scenarios, not detection of real fraud.",
        },
        "audit_columns": list(AUDIT_COLUMNS),
        "excluded_fields": list(EXCLUDED_FIELDS),
        "leakage_exclusions": list(LEAKAGE_EXCLUSIONS),
        "candidate_source_fields": list(CANDIDATE_FEATURE_FIELDS) + list(
            field for field in numeric_source_fields if field in REVISED_DERIVED_NUMERIC_FIELDS
        ),
        "derived_candidate_feature_fields": list(
            field for field in numeric_source_fields if field in REVISED_DERIVED_NUMERIC_FIELDS
        ),
        "split_rule": source_manifest["split_rule"],
        "split_counts": dict(split_counts),
        "source_validation": dict(source_validation),
        "historical_feature_audit": dict(history_audit),
        "creation_timestamp_utc": _iso_now(),
        "reproducibility": {
            "command": "python -m ml.feature_matrix",
            "same_configuration_and_seed": "Produces equivalent feature rows and feature vocabulary; creation timestamp varies per run.",
            "source_is_read_only": True,
        },
        "known_limitations": [
            "Features are derived from controlled synthetic data only.",
            "Scenario labels are not real fraud ground truth.",
            "The source generator can create patterns easier to detect than real behavior.",
            "Identifiers are retained for audit but are excluded from model inputs.",
            "No feature matrix is production-ready without independent data and governance review.",
        ],
        "output_directory": output_directory,
    }


def build_feature_artifact(
    source_dir: str | Path = "data/synthetic",
    output_dir: str | Path = "data/synthetic/features",
) -> dict[str, Any]:
    """Build train/validation/test candidate features from the source CSVs."""

    source_root = Path(source_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    source_manifest = json.loads((source_root / "dataset_manifest.json").read_text(encoding="utf-8"))
    config_data = json.loads((source_root / "generation_config.json").read_text(encoding="utf-8"))
    config = SyntheticDatasetConfig(
        total_transactions=config_data["total_transactions"],
        user_count=config_data["user_count"],
        merchant_count=config_data["merchant_count"],
        duration_days=config_data["duration_days"],
        start_date=config_data["start_date"],
        currency=config_data["currency"],
        seed=config_data["seed"],
        dataset_version=config_data["dataset_version"],
        generator_version=config_data["generator_version"],
        scenario_counts=config_data["scenario_counts"],
    )
    source_validation = validate_written_dataset(source_root)
    if not source_validation["valid"]:
        raise ValueError(json.dumps(source_validation, indent=2))
    all_records = _read_csv(source_root / source_manifest["files"]["full_csv"])
    history_audit = audit_historical_features(all_records)
    if not history_audit["valid"]:
        raise ValueError(json.dumps(history_audit, indent=2))
    split_records = {
        name: _read_csv(source_root / f"{name}.csv")
        for name in ("train", "validation", "test")
    }
    is_revised = config.generator_version == "1.1.0"
    numeric_source_fields = NUMERIC_SOURCE_FIELDS + (
        REVISED_DERIVED_NUMERIC_FIELDS if is_revised else ()
    )
    derived_features = _point_in_time_derived_features(all_records) if is_revised else {}
    enriched_splits: dict[str, tuple[dict[str, Any], ...]] = {
        split_name: tuple(
            {**record, **derived_features.get(record["synthetic_transaction_id"], {})}
            for record in records
        )
        for split_name, records in split_records.items()
    }
    preprocessor = FittedPreprocessor.fit(enriched_splits["train"], numeric_source_fields)
    feature_columns = AUDIT_COLUMNS + (TARGET_COLUMN,) + preprocessor.feature_names
    for split_name, records in enriched_splits.items():
        output_rows: list[dict[str, Any]] = []
        for record in records:
            row: dict[str, Any] = {
                "synthetic_transaction_id": record["synthetic_transaction_id"],
                "synthetic_user_id": record["synthetic_user_id"],
                "timestamp": record["timestamp"],
                "dataset_split": split_name,
                TARGET_COLUMN: record["scenario_label"],
            }
            row.update({name: f"{value:.10f}" for name, value in preprocessor.transform(record).items()})
            output_rows.append(row)
        _write_csv(output_root / f"candidate_features_{split_name}.csv", output_rows, feature_columns)

    split_counts = {name: len(records) for name, records in enriched_splits.items()}
    feature_generation_version = (
        REVISED_FEATURE_GENERATION_VERSION if is_revised else FEATURE_GENERATION_VERSION
    )
    manifest = _feature_manifest(
        source_root=source_root,
        output_root=output_root,
        config=config,
        source_manifest=source_manifest,
        preprocessor=preprocessor,
        source_validation=source_validation,
        history_audit=history_audit,
        split_counts=split_counts,
        numeric_source_fields=numeric_source_fields,
        feature_generation_version=feature_generation_version,
    )
    _write_json(output_root / "feature_manifest.json", manifest)
    _write_json(output_root / "feature_dictionary.json", _feature_dictionary(preprocessor))
    return manifest


def _validate_feature_rows(
    rows: tuple[dict[str, str], ...],
    *,
    split_name: str,
    feature_names: tuple[str, ...],
    classes: set[str],
) -> list[str]:
    errors: list[str] = []
    expected_columns = set(AUDIT_COLUMNS) | {TARGET_COLUMN} | set(feature_names)
    for index, row in enumerate(rows):
        if set(row) != expected_columns:
            errors.append(f"{split_name} row {index}: feature columns differ from manifest")
            continue
        if row[TARGET_COLUMN] not in classes:
            errors.append(f"{split_name} row {index}: unknown target class")
        if row["dataset_split"] != split_name:
            errors.append(f"{split_name} row {index}: incorrect split metadata")
        for feature_name in feature_names:
            try:
                value = float(row[feature_name])
            except ValueError:
                errors.append(f"{split_name} row {index}: non-numeric feature {feature_name}")
                continue
            if value != value or value in (float("inf"), float("-inf")):
                errors.append(f"{split_name} row {index}: non-finite feature {feature_name}")
    return errors


def validate_feature_artifact(output_dir: str | Path = "data/synthetic/features") -> dict[str, Any]:
    """Validate feature files, target separation, temporal identity, and manifest."""

    output_root = Path(output_dir)
    manifest = json.loads((output_root / "feature_manifest.json").read_text(encoding="utf-8"))
    feature_names = tuple(manifest["feature_names"])
    classes = set(manifest["target"]["classes"])
    errors: list[str] = []
    split_rows: dict[str, tuple[dict[str, str], ...]] = {}
    for split_name in ("train", "validation", "test"):
        rows = _read_csv(output_root / f"candidate_features_{split_name}.csv")
        split_rows[split_name] = rows
        errors.extend(_validate_feature_rows(rows, split_name=split_name, feature_names=feature_names, classes=classes))
    if set(feature_names) & set(EXCLUDED_FIELDS):
        errors.append("Excluded or leakage-prone fields entered the model feature list.")
    ids = [{row["synthetic_transaction_id"] for row in rows} for rows in split_rows.values()]
    if any(ids[index] & ids[j] for index in range(3) for j in range(index + 1, 3)):
        errors.append("Feature split transaction identifiers overlap.")
    if sum(len(rows) for rows in split_rows.values()) != manifest["source_row_counts"]["full"]:
        errors.append("Feature split counts do not reconcile with source rows.")
    actual_counts = {name: len(rows) for name, rows in split_rows.items()}
    if actual_counts != manifest["split_counts"]:
        errors.append("Feature split counts do not match feature manifest.")
    return {
        "valid": not errors,
        "errors": errors,
        "feature_count": len(feature_names),
        "feature_names": list(feature_names),
        "split_counts": actual_counts,
        "target_classes": sorted(classes),
        "excluded_fields_present_as_features": sorted(set(feature_names) & set(EXCLUDED_FIELDS)),
    }


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    manifest = build_feature_artifact(
        repository_root / "data" / "synthetic",
        repository_root / "data" / "synthetic" / "features",
    )
    validation = validate_feature_artifact(repository_root / "data" / "synthetic" / "features")
    if not validation["valid"]:
        raise SystemExit(json.dumps(validation, indent=2))
    print(json.dumps({"manifest": manifest, "validation": validation}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
