"""Generate and validate a controlled, research-only synthetic dataset.

This module intentionally has no dependency on the SpendShield backend or any
database client.  It creates fictional records in a caller-supplied directory
only.  Synthetic scenario labels describe generator rules; they are not fraud
labels, real-world outcomes, or production decisions.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Mapping

GENERATOR_VERSION = "1.0.0"
REVISED_GENERATOR_VERSION = "1.1.0"
DATASET_NAME = "spendshield_synthetic_transactions"
DATASET_TYPE = "synthetic_research"
SOURCE_SYSTEM = "SpendShield synthetic generator"
UTC = timezone.utc

SCENARIO_LABELS: tuple[str, ...] = (
    "normal",
    "synthetic_high_amount",
    "synthetic_rapid_repeat",
    "synthetic_unusual_time",
    "synthetic_behavior_deviation",
    "synthetic_combined_pattern",
)

DEFAULT_SCENARIO_COUNTS: dict[str, int] = {
    "normal": 7_600,
    "synthetic_high_amount": 800,
    "synthetic_rapid_repeat": 600,
    "synthetic_unusual_time": 600,
    "synthetic_behavior_deviation": 300,
    "synthetic_combined_pattern": 100,
}

REVISED_DATASET_VERSION = "v2"
REVISED_DATASET_SEED = 20260913
REVISED_SCENARIO_COUNTS: dict[str, int] = {
    "normal": 6_800,
    "synthetic_high_amount": 1_000,
    "synthetic_rapid_repeat": 800,
    "synthetic_unusual_time": 700,
    "synthetic_behavior_deviation": 500,
    "synthetic_combined_pattern": 200,
}

# These category IDs intentionally match the existing SpendShield catalog
# vocabulary, while the generated merchant/user identifiers remain fictional.
CATEGORY_IDS: tuple[str, ...] = (
    "bills",
    "education",
    "entertainment",
    "food",
    "grocery",
    "healthcare",
    "home",
    "other",
    "shopping",
    "subscriptions",
    "transport",
    "travel",
)

CHANNELS: tuple[str, ...] = (
    "QR_SIMULATED",
    "CARD_SIMULATED",
    "WALLET_SIMULATED",
    "BANK_SIMULATED",
)

REQUIRED_COLUMNS: tuple[str, ...] = (
    "synthetic_transaction_id",
    "synthetic_user_id",
    "synthetic_account_id",
    "timestamp",
    "amount",
    "currency",
    "synthetic_merchant_id",
    "merchant_category",
    "transaction_channel",
    "transaction_state",
    "scenario_label",
    "scenario_id",
    "is_synthetic_scenario",
    "label_source",
    "label_definition",
    "dataset_type",
    "synthetic",
    "source_system",
    "dataset_version",
    "transaction_hour",
    "day_of_week",
    "user_historical_transaction_count_before",
    "user_historical_average_amount_before",
    "time_since_previous_transaction_seconds",
    "user_historical_category_frequency_before",
    "dataset_split",
    "scenario_injection_reason",
    "generator_rule",
)

COLUMN_DATA_TYPES: dict[str, str] = {
    "synthetic_transaction_id": "string",
    "synthetic_user_id": "string",
    "synthetic_account_id": "string",
    "timestamp": "ISO-8601 UTC string",
    "amount": "decimal string, two fractional digits",
    "currency": "string enum",
    "synthetic_merchant_id": "string",
    "merchant_category": "string enum",
    "transaction_channel": "string enum",
    "transaction_state": "string enum",
    "scenario_label": "string enum",
    "scenario_id": "string",
    "is_synthetic_scenario": "boolean",
    "label_source": "string enum",
    "label_definition": "string",
    "dataset_type": "string enum",
    "synthetic": "boolean",
    "source_system": "string",
    "dataset_version": "string",
    "transaction_hour": "integer 0-23",
    "day_of_week": "integer 0-6",
    "user_historical_transaction_count_before": "integer >=0",
    "user_historical_average_amount_before": "decimal string, two fractional digits",
    "time_since_previous_transaction_seconds": "nullable integer >=0",
    "user_historical_category_frequency_before": "decimal number 0-1",
    "dataset_split": "string enum",
    "scenario_injection_reason": "string",
    "generator_rule": "string",
}

CANDIDATE_FEATURE_FIELDS: tuple[str, ...] = (
    "amount",
    "currency",
    "transaction_hour",
    "day_of_week",
    "merchant_category",
    "transaction_channel",
    "user_historical_transaction_count_before",
    "user_historical_average_amount_before",
    "time_since_previous_transaction_seconds",
    "user_historical_category_frequency_before",
)

AUDIT_ONLY_FIELDS: tuple[str, ...] = (
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
    "synthetic_transaction_id",
    "synthetic_user_id",
    "synthetic_account_id",
    "synthetic_merchant_id",
)

FORBIDDEN_FEATURE_FIELDS: tuple[str, ...] = (
    "future_transaction_count",
    "future_average_amount",
    "final_scenario_label",
    "scenario_injection_reason",
    "post_event_outcome",
    "manually_assigned_research_label",
    "confirmed_fraud",
    "fraud",
)

SCENARIO_DEFINITIONS: dict[str, dict[str, Any]] = {
    "normal": {
        "meaning": "A generated transaction using the user's ordinary synthetic behavior.",
        "generation_rule": "Preferred category/merchant, typical hour, and ordinary amount draw.",
        "real_fraud": False,
        "intended_use": "Control group for data-quality and feature experiments.",
        "supervised_target_allowed": True,
        "limitations": "Normal is a generator class, not evidence that a real transaction is safe.",
    },
    "synthetic_high_amount": {
        "meaning": "An amount intentionally increased relative to the synthetic user's ordinary range.",
        "generation_rule": "Multiply the user's ordinary amount draw by a controlled factor.",
        "real_fraud": False,
        "intended_use": "Controlled amount-signal experiment.",
        "supervised_target_allowed": True,
        "limitations": "The amount rule may be easier to detect than real-world behavior.",
    },
    "synthetic_rapid_repeat": {
        "meaning": "A generated transaction placed shortly after the same user's prior activity.",
        "generation_rule": "Place the transaction 1-10 minutes after the prior synthetic user event and usually reuse its merchant.",
        "real_fraud": False,
        "intended_use": "Controlled temporal repetition experiment.",
        "supervised_target_allowed": True,
        "limitations": "Short intervals are injected by rule and do not imply unauthorized activity.",
    },
    "synthetic_unusual_time": {
        "meaning": "A transaction generated during the documented unusual-hour window.",
        "generation_rule": "Use UTC hour 00-04 or 23 while retaining the user's synthetic date.",
        "real_fraud": False,
        "intended_use": "Controlled time-of-day experiment.",
        "supervised_target_allowed": True,
        "limitations": "Unusual time is user-profile-relative only in this synthetic dataset.",
    },
    "synthetic_behavior_deviation": {
        "meaning": "A transaction generated in a less-preferred synthetic category or merchant pattern.",
        "generation_rule": "Choose a category outside the user's preferred category set.",
        "real_fraud": False,
        "intended_use": "Controlled categorical-deviation experiment.",
        "supervised_target_allowed": True,
        "limitations": "Category preference is synthetic and not a ground-truth behavioral profile.",
    },
    "synthetic_combined_pattern": {
        "meaning": "A transaction combining high amount, unusual time, and category deviation rules.",
        "generation_rule": "Apply the high-amount, unusual-time, and behavior-deviation generators together.",
        "real_fraud": False,
        "intended_use": "Controlled multi-signal experiment.",
        "supervised_target_allowed": True,
        "limitations": "Combined signals are deliberately constructed and may overstate separability.",
    },
}

REVISED_SCENARIO_DEFINITIONS: dict[str, dict[str, Any]] = {
    "normal": {
        "meaning": "A generated transaction drawn from ordinary synthetic user behavior with natural variation.",
        "generation_rule": "Sample user-relative category, amount, time, merchant, channel, and transaction-gap behavior with overlap.",
        "real_fraud": False,
        "intended_use": "Control group for realistic-overlap data-quality and feature experiments.",
        "supervised_target_allowed": True,
        "limitations": "Normal is a generator class, not evidence that a real transaction is safe.",
    },
    "synthetic_high_amount": {
        "meaning": "A transaction with a controlled, variable increase relative to synthetic user behavior.",
        "generation_rule": "Apply a mixture of moderate, strong, user-relative, and category-compatible amount deviations.",
        "real_fraud": False,
        "intended_use": "Controlled amount-signal experiment with overlap from naturally expensive normal purchases.",
        "supervised_target_allowed": True,
        "limitations": "Amount deviations remain generator-defined and are not fraud outcomes.",
    },
    "synthetic_rapid_repeat": {
        "meaning": "A transaction with a varied short-to-borderline interval after the same user's prior activity.",
        "generation_rule": "Use a mixture of short, borderline, and longer repeat intervals with variable merchant/category reuse.",
        "real_fraud": False,
        "intended_use": "Controlled temporal-repetition experiment with natural short-gap overlap.",
        "supervised_target_allowed": True,
        "limitations": "A short interval is a synthetic signal and does not imply unauthorized activity.",
    },
    "synthetic_unusual_time": {
        "meaning": "A transaction with a user-relative time deviation across late, borderline, and ordinary clock hours.",
        "generation_rule": "Vary time relative to the user's typical hour; do not use one globally exclusive UTC-hour window.",
        "real_fraud": False,
        "intended_use": "Controlled user-relative temporal-deviation experiment.",
        "supervised_target_allowed": True,
        "limitations": "Time deviation is synthetic and not a real-world suspicious-activity decision.",
    },
    "synthetic_behavior_deviation": {
        "meaning": "A transaction with one or more moderate changes from synthetic user category, merchant, channel, amount, frequency, or time behavior.",
        "generation_rule": "Select a varied subset of user-relative behavior changes without exposing the scenario label as a feature.",
        "real_fraud": False,
        "intended_use": "Controlled behavioral-overlap experiment.",
        "supervised_target_allowed": True,
        "limitations": "The behavioral profile is synthetic and is not a verified user preference or outcome.",
    },
    "synthetic_combined_pattern": {
        "meaning": "A transaction combining two or more weak or moderate synthetic deviations with overlap across scenarios.",
        "generation_rule": "Sample a varied subset of amount, time, repeat, category, merchant, and channel deviations.",
        "real_fraud": False,
        "intended_use": "Controlled multi-signal overlap experiment.",
        "supervised_target_allowed": True,
        "limitations": "Combined signals remain generator-defined and cannot establish real-world detection performance.",
    },
}

LABEL_NOTICE = (
    "Synthetic scenario labels identify intentionally generated scenarios. "
    "They do not represent confirmed fraud, real financial crime, or real-world risk outcomes."
)


@dataclass(frozen=True, slots=True)
class SyntheticDatasetConfig:
    """Bounded generation settings with a deterministic default experiment."""

    total_transactions: int = 10_000
    user_count: int = 500
    merchant_count: int = 100
    duration_days: int = 90
    start_date: str = "2024-01-01T00:00:00+00:00"
    currency: str = "INR"
    seed: int = 20260912
    dataset_version: str = "v1"
    generator_version: str = GENERATOR_VERSION
    scenario_counts: Mapping[str, int] = field(
        default_factory=lambda: dict(DEFAULT_SCENARIO_COUNTS)
    )

    def __post_init__(self) -> None:
        if self.total_transactions <= 0 or self.user_count <= 0:
            raise ValueError("Transaction and user counts must be positive.")
        if self.total_transactions % self.user_count != 0:
            raise ValueError("total_transactions must divide evenly by user_count.")
        if self.merchant_count < len(CATEGORY_IDS):
            raise ValueError("merchant_count must cover every synthetic category.")
        if self.duration_days < 3:
            raise ValueError("duration_days must allow temporal splits.")
        if self.currency != "INR":
            raise ValueError("This controlled dataset uses the project convention INR only.")
        if set(self.scenario_counts) != set(SCENARIO_LABELS):
            raise ValueError("Scenario counts must cover exactly the approved labels.")
        if any(count < 0 for count in self.scenario_counts.values()):
            raise ValueError("Scenario counts cannot be negative.")
        if sum(self.scenario_counts.values()) != self.total_transactions:
            raise ValueError("Scenario counts must sum to total_transactions.")
        _parse_timestamp(self.start_date)

    @property
    def transactions_per_user(self) -> int:
        return self.total_transactions // self.user_count

    @property
    def start_timestamp(self) -> datetime:
        return _parse_timestamp(self.start_date)

    @property
    def end_timestamp_exclusive(self) -> datetime:
        return self.start_timestamp + timedelta(days=self.duration_days)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["scenario_counts"] = dict(self.scenario_counts)
        result["start_timestamp"] = self.start_timestamp.isoformat().replace("+00:00", "Z")
        result["end_timestamp_exclusive"] = self.end_timestamp_exclusive.isoformat().replace(
            "+00:00", "Z"
        )
        result["transactions_per_user"] = self.transactions_per_user
        return result


@dataclass(frozen=True, slots=True)
class UserProfile:
    user_id: str
    account_id: str
    preferred_categories: tuple[str, ...]
    typical_hour: int
    typical_amount: Decimal
    typical_daily_frequency: int


@dataclass(frozen=True, slots=True)
class MerchantProfile:
    merchant_id: str
    category: str


@dataclass(frozen=True, slots=True)
class GeneratedDataset:
    records: tuple[dict[str, Any], ...]
    splits: Mapping[str, tuple[dict[str, Any], ...]]
    manifest: Mapping[str, Any]


class DatasetValidationError(ValueError):
    """Raised when generated output violates its documented contract."""


def _parse_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Dataset timestamps must be timezone-aware.")
    return parsed.astimezone(UTC)


def _isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _money(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clamp_amount(value: Decimal) -> Decimal:
    return min(Decimal("50000.00"), max(Decimal("1.00"), value)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def generate_synthetic_users(
    config: SyntheticDatasetConfig, rng: random.Random
) -> tuple[UserProfile, ...]:
    """Create fictional user behavior profiles without personal attributes."""

    profiles: list[UserProfile] = []
    for index in range(config.user_count):
        preferred = tuple(rng.sample(CATEGORY_IDS, k=2))
        profiles.append(
            UserProfile(
                user_id=f"syn-user-{index + 1:04d}",
                account_id=f"syn-account-{index + 1:04d}",
                preferred_categories=preferred,
                typical_hour=rng.choice((7, 8, 9, 12, 13, 18, 19, 20, 21)),
                typical_amount=_money(rng.uniform(180, 1_250)),
                typical_daily_frequency=rng.choice((1, 1, 1, 2, 2, 3)),
            )
        )
    return tuple(profiles)


def generate_synthetic_merchants(
    config: SyntheticDatasetConfig, rng: random.Random
) -> tuple[MerchantProfile, ...]:
    """Create fictional merchants distributed across the project categories."""

    merchants: list[MerchantProfile] = []
    categories = list(CATEGORY_IDS)
    for index in range(config.merchant_count):
        category = categories[index % len(categories)]
        merchants.append(
            MerchantProfile(
                merchant_id=f"syn-merchant-{index + 1:04d}",
                category=category,
            )
        )
    rng.shuffle(merchants)
    return tuple(merchants)


def _merchant_for_category(
    merchants: tuple[MerchantProfile, ...], category: str, rng: random.Random
) -> MerchantProfile:
    matching = [merchant for merchant in merchants if merchant.category == category]
    return rng.choice(matching)


def _choose_base_category(profile: UserProfile, rng: random.Random) -> str:
    if rng.random() < 0.82:
        return rng.choice(profile.preferred_categories)
    return rng.choice(CATEGORY_IDS)


def _choose_base_timestamp(
    profile: UserProfile, day_offset: int, config: SyntheticDatasetConfig, rng: random.Random
) -> datetime:
    hour = int(round(rng.gauss(profile.typical_hour, 1.8)))
    hour = max(6, min(22, hour))
    minute = rng.randrange(0, 60)
    second = rng.randrange(0, 60)
    return config.start_timestamp + timedelta(
        days=day_offset, hours=hour, minutes=minute, seconds=second
    )


def _choose_base_amount(profile: UserProfile, rng: random.Random) -> Decimal:
    # A bounded log-normal-like draw creates varied but positive ordinary values.
    amount = float(profile.typical_amount) * (2.71828 ** rng.gauss(0, 0.34))
    return _clamp_amount(_money(amount))


def _assign_scenarios(
    raw_records: list[dict[str, Any]], config: SyntheticDatasetConfig, rng: random.Random
) -> dict[int, str]:
    assignments = {index: "normal" for index in range(len(raw_records))}
    eligible_rapid = [
        index for index, record in enumerate(raw_records) if record["user_sequence"] > 0
    ]
    rng.shuffle(eligible_rapid)
    rapid_count = config.scenario_counts["synthetic_rapid_repeat"]
    for index in eligible_rapid[:rapid_count]:
        assignments[index] = "synthetic_rapid_repeat"

    remaining = [index for index, label in assignments.items() if label == "normal"]
    rng.shuffle(remaining)
    cursor = 0
    for label in SCENARIO_LABELS:
        if label in {"normal", "synthetic_rapid_repeat"}:
            continue
        count = config.scenario_counts[label]
        for index in remaining[cursor : cursor + count]:
            assignments[index] = label
        cursor += count
    return assignments


def _scenario_reason(
    label: str,
    definitions: Mapping[str, Mapping[str, Any]] = SCENARIO_DEFINITIONS,
) -> str:
    return definitions[label]["meaning"]


def _scenario_rule(
    label: str,
    definitions: Mapping[str, Mapping[str, Any]] = SCENARIO_DEFINITIONS,
) -> str:
    return definitions[label]["generation_rule"]


def _apply_scenario(
    record: dict[str, Any],
    label: str,
    profile: UserProfile,
    merchants: tuple[MerchantProfile, ...],
    previous_record: dict[str, Any] | None,
    rng: random.Random,
) -> None:
    """Apply a documented scenario rule to one already-fictional event."""

    timestamp = record["timestamp"]
    category = record["merchant_category"]
    amount = Decimal(record["amount"])

    if label in {"synthetic_high_amount", "synthetic_combined_pattern"}:
        amount = _clamp_amount(amount * Decimal(str(rng.uniform(3.0, 6.5))))

    if label in {"synthetic_unusual_time", "synthetic_combined_pattern"}:
        unusual_hour = rng.choice((0, 1, 2, 3, 4, 23))
        timestamp = datetime.combine(
            timestamp.date(), time(unusual_hour, rng.randrange(0, 60), rng.randrange(0, 60)), tzinfo=UTC
        )

    if label in {"synthetic_behavior_deviation", "synthetic_combined_pattern"}:
        non_preferred = [item for item in CATEGORY_IDS if item not in profile.preferred_categories]
        category = rng.choice(non_preferred)
        merchant = _merchant_for_category(merchants, category, rng)
        record["synthetic_merchant_id"] = merchant.merchant_id

    if label == "synthetic_rapid_repeat" and previous_record is not None:
        timestamp = previous_record["timestamp"] + timedelta(seconds=rng.randint(60, 600))
        if rng.random() < 0.72:
            record["synthetic_merchant_id"] = previous_record["synthetic_merchant_id"]
            category = previous_record["merchant_category"]
        else:
            merchant = _merchant_for_category(merchants, category, rng)
            record["synthetic_merchant_id"] = merchant.merchant_id

    record["timestamp"] = timestamp
    record["merchant_category"] = category
    record["amount"] = _clamp_amount(amount)


def _generate_raw_records(
    config: SyntheticDatasetConfig,
    rng: random.Random,
    users: tuple[UserProfile, ...],
    merchants: tuple[MerchantProfile, ...],
) -> list[dict[str, Any]]:
    raw_records: list[dict[str, Any]] = []
    assignments_by_index: dict[int, str]
    for user in users:
        day_offsets = sorted(rng.sample(range(config.duration_days), config.transactions_per_user))
        for sequence, day_offset in enumerate(day_offsets):
            category = _choose_base_category(user, rng)
            merchant = _merchant_for_category(merchants, category, rng)
            raw_records.append(
                {
                    "synthetic_user_id": user.user_id,
                    "synthetic_account_id": user.account_id,
                    "user_sequence": sequence,
                    "timestamp": _choose_base_timestamp(user, day_offset, config, rng),
                    "amount": _choose_base_amount(user, rng),
                    "currency": config.currency,
                    "synthetic_merchant_id": merchant.merchant_id,
                    "merchant_category": merchant.category,
                    "transaction_channel": rng.choice(CHANNELS),
                }
            )
    assignments_by_index = _assign_scenarios(raw_records, config, rng)

    users_by_id = {profile.user_id: profile for profile in users}
    by_user: defaultdict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(raw_records):
        by_user[record["synthetic_user_id"]].append(index)

    for user_id, indexes in by_user.items():
        indexes.sort(key=lambda index: raw_records[index]["timestamp"])
        previous: dict[str, Any] | None = None
        for index in indexes:
            label = assignments_by_index[index]
            _apply_scenario(raw_records[index], label, users_by_id[user_id], merchants, previous, rng)
            raw_records[index]["scenario_label"] = label
            previous = raw_records[index]

    return raw_records


def _add_temporal_features(
    records: list[dict[str, Any]], config: SyntheticDatasetConfig
) -> list[dict[str, Any]]:
    sorted_records = sorted(
        records,
        key=lambda record: (record["timestamp"], record["synthetic_transaction_id"]),
    )
    history_count: Counter[str] = Counter()
    history_amount: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    history_category: defaultdict[tuple[str, str], int] = defaultdict(int)
    previous_timestamp: dict[str, datetime] = {}

    train_end = config.start_timestamp + (config.end_timestamp_exclusive - config.start_timestamp) * 0.70
    validation_end = config.start_timestamp + (config.end_timestamp_exclusive - config.start_timestamp) * 0.85

    for record in sorted_records:
        user_id = record["synthetic_user_id"]
        category_key = (user_id, record["merchant_category"])
        timestamp = record["timestamp"]
        prior_count = history_count[user_id]
        prior_amount = history_amount[user_id]
        record["transaction_hour"] = timestamp.hour
        record["day_of_week"] = timestamp.weekday()
        record["user_historical_transaction_count_before"] = prior_count
        record["user_historical_average_amount_before"] = (
            _money(prior_amount / prior_count) if prior_count else Decimal("0.00")
        )
        record["time_since_previous_transaction_seconds"] = (
            int((timestamp - previous_timestamp[user_id]).total_seconds())
            if user_id in previous_timestamp
            else None
        )
        record["user_historical_category_frequency_before"] = (
            round(history_category[category_key] / prior_count, 6) if prior_count else 0.0
        )
        if timestamp < train_end:
            record["dataset_split"] = "train"
        elif timestamp < validation_end:
            record["dataset_split"] = "validation"
        else:
            record["dataset_split"] = "test"
        history_count[user_id] += 1
        history_amount[user_id] += Decimal(record["amount"])
        history_category[category_key] += 1
        previous_timestamp[user_id] = timestamp

    return sorted_records


def _finalize_records(
    raw_records: list[dict[str, Any]],
    config: SyntheticDatasetConfig,
    definitions: Mapping[str, Mapping[str, Any]] = SCENARIO_DEFINITIONS,
) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_records, start=1):
        label = raw["scenario_label"]
        record = dict(raw)
        record.pop("user_sequence", None)
        record["synthetic_transaction_id"] = f"syn-transaction-{index:06d}"
        record["scenario_id"] = f"syn-scenario-{index:06d}"
        record["is_synthetic_scenario"] = True
        record["label_source"] = "generator_rule"
        record["label_definition"] = _scenario_reason(label, definitions)
        record["dataset_type"] = DATASET_TYPE
        record["synthetic"] = True
        record["source_system"] = SOURCE_SYSTEM
        record["dataset_version"] = config.dataset_version
        record["transaction_state"] = "COMPLETED"
        record["scenario_injection_reason"] = _scenario_reason(label, definitions)
        record["generator_rule"] = _scenario_rule(label, definitions)
        record["timestamp"] = _isoformat(record["timestamp"])
        record["amount"] = f"{Decimal(record['amount']):.2f}"
        record["user_historical_average_amount_before"] = f"{Decimal(record['user_historical_average_amount_before']):.2f}"
        records.append({column: record.get(column) for column in REQUIRED_COLUMNS})
    return tuple(records)


def build_manifest(
    records: tuple[dict[str, Any], ...],
    splits: Mapping[str, tuple[dict[str, Any], ...]],
    config: SyntheticDatasetConfig,
) -> dict[str, Any]:
    timestamps = [_parse_timestamp(record["timestamp"]) for record in records]
    scenario_distribution = dict(sorted(Counter(record["scenario_label"] for record in records).items()))
    full_csv_name = f"{DATASET_NAME}_{config.dataset_version}.csv"
    return {
        "dataset_name": DATASET_NAME,
        "dataset_version": config.dataset_version,
        "dataset_type": DATASET_TYPE,
        "synthetic": True,
        "source_system": SOURCE_SYSTEM,
        "currency": config.currency,
        "generator_version": config.generator_version,
        "random_seed": config.seed,
        "row_count": len(records),
        "column_count": len(REQUIRED_COLUMNS),
        "column_names": list(REQUIRED_COLUMNS),
        "data_types": dict(COLUMN_DATA_TYPES),
        "user_count": len({record["synthetic_user_id"] for record in records}),
        "account_count": len({record["synthetic_account_id"] for record in records}),
        "merchant_count": len({record["synthetic_merchant_id"] for record in records}),
        "category_count": len({record["merchant_category"] for record in records}),
        "date_range": {
            "start": _isoformat(min(timestamps)),
            "end": _isoformat(max(timestamps)),
            "configured_start": _isoformat(config.start_timestamp),
            "configured_end_exclusive": _isoformat(config.end_timestamp_exclusive),
            "timezone": "UTC",
            "timestamp_precision": "second",
        },
        "scenario_distribution": scenario_distribution,
        "label_notice": LABEL_NOTICE,
        "candidate_feature_fields": list(CANDIDATE_FEATURE_FIELDS),
        "audit_only_fields": list(AUDIT_ONLY_FIELDS),
        "forbidden_feature_fields": list(FORBIDDEN_FEATURE_FIELDS),
        "split_rule": {
            "method": "timestamp_threshold",
            "train_fraction_of_configured_period": 0.70,
            "validation_fraction_of_configured_period": 0.15,
            "test_fraction_of_configured_period": 0.15,
            "shuffle_before_split": False,
            "user_overlap_across_splits": True,
            "user_level_leakage_note": "Synthetic users may appear in multiple temporal splits; historical features use only records earlier than the current timestamp.",
            "user_history_features_use_prior_records_only": True,
        },
        "split_counts": {name: len(rows) for name, rows in splits.items()},
        "files": {
            "full_csv": full_csv_name,
            "train_csv": "train.csv",
            "validation_csv": "validation.csv",
            "test_csv": "test.csv",
            "generation_config": "generation_config.json",
            "label_dictionary": "label_dictionary.json",
            "readme": "README.md",
            "parquet": None,
        },
        "created_at_utc": _isoformat(datetime.now(UTC)),
        "known_limitations": [
            "All records are fictional and generated by deterministic rules.",
            "Synthetic scenario labels are not confirmed fraud labels.",
            "Rules may be easier to detect than real-world behavior.",
            "No real-world performance or generalization conclusion is possible.",
            "This dataset must not drive production decisions or transaction blocking.",
            "The dataset is single-currency INR and has no exchange-rate semantics.",
        ],
        "reproducibility": {
            "command": "python -m ml.synthetic_dataset_generator",
            "same_seed_and_configuration": "Produces equivalent CSV rows and split assignments; manifest creation time changes per run.",
        },
    }


def generate_dataset(config: SyntheticDatasetConfig | None = None) -> GeneratedDataset:
    """Generate records, temporal features, splits, and an evidence manifest."""

    config = config or SyntheticDatasetConfig()
    rng = random.Random(config.seed)
    users = generate_synthetic_users(config, rng)
    merchants = generate_synthetic_merchants(config, rng)
    raw_records = _generate_raw_records(config, rng, users, merchants)
    for index, record in enumerate(raw_records):
        record["synthetic_transaction_id"] = f"syn-transaction-{index + 1:06d}"
    featured_records = _add_temporal_features(raw_records, config)
    records = _finalize_records(featured_records, config)
    splits: dict[str, tuple[dict[str, Any], ...]] = {
        name: tuple(record for record in records if record["dataset_split"] == name)
        for name in ("train", "validation", "test")
    }
    validation = validate_records(records, config=config, splits=splits)
    if not validation["valid"]:
        raise DatasetValidationError(json.dumps(validation, indent=2, default=str))
    manifest = build_manifest(records, splits, config)
    return GeneratedDataset(records=records, splits=splits, manifest=manifest)


def revised_dataset_config() -> SyntheticDatasetConfig:
    """Return the fixed v2 configuration without changing the v1 defaults."""

    return SyntheticDatasetConfig(
        total_transactions=10_000,
        user_count=500,
        merchant_count=100,
        duration_days=90,
        start_date="2024-01-01T00:00:00+00:00",
        currency="INR",
        seed=REVISED_DATASET_SEED,
        dataset_version=REVISED_DATASET_VERSION,
        generator_version=REVISED_GENERATOR_VERSION,
        scenario_counts=dict(REVISED_SCENARIO_COUNTS),
    )


def _revised_hour(profile: UserProfile, rng: random.Random) -> int:
    """Sample an ordinary, late, borderline, or user-relative active hour."""

    mode = rng.random()
    if mode < 0.14:
        return rng.choice((22, 23, 0, 1, 2, 3))
    if mode < 0.27:
        return rng.choice((4, 5, 6, 21, 22))
    if mode < 0.42:
        return (profile.typical_hour + rng.choice((-6, -4, -3, 3, 4, 6))) % 24
    return max(0, min(23, int(round(rng.gauss(profile.typical_hour, 2.8)))))


def _revised_timestamp(
    profile: UserProfile,
    previous_timestamp: datetime | None,
    config: SyntheticDatasetConfig,
    rng: random.Random,
    sequence: int,
    total_events: int,
) -> datetime:
    if previous_timestamp is None:
        day = rng.uniform(0.0, 3.0)
        base = config.start_timestamp + timedelta(days=day)
        hour = _revised_hour(profile, rng)
        return datetime.combine(
            base.date(), time(hour, rng.randrange(0, 60), rng.randrange(0, 60)), tzinfo=UTC
        )
    if rng.random() < 0.18:
        return previous_timestamp + timedelta(seconds=rng.randint(90, 2_400))
    fraction = sequence / max(total_events - 1, 1)
    planned_seconds = (
        fraction * max(1, config.duration_days - 4) * 86_400
        + rng.uniform(-0.75, 0.75) * 86_400
    )
    candidate = config.start_timestamp + timedelta(seconds=max(0.0, planned_seconds))
    hour = _revised_hour(profile, rng)
    candidate = datetime.combine(
        candidate.date(), time(hour, rng.randrange(0, 60), rng.randrange(0, 60)), tzinfo=UTC
    )
    if candidate <= previous_timestamp:
        candidate += timedelta(days=1)
    if candidate >= config.end_timestamp_exclusive:
        candidate = config.end_timestamp_exclusive - timedelta(seconds=1)
    return candidate


def _revised_amount(profile: UserProfile, rng: random.Random) -> Decimal:
    amount = _choose_base_amount(profile, rng)
    if rng.random() < 0.10:
        amount *= Decimal(str(rng.uniform(1.4, 2.8)))
    return _clamp_amount(_money(amount))


def _choose_new_merchant(
    merchants: tuple[MerchantProfile, ...],
    category: str,
    seen_merchant_ids: set[str],
    rng: random.Random,
) -> MerchantProfile:
    candidates = [
        merchant
        for merchant in merchants
        if merchant.category == category and merchant.merchant_id not in seen_merchant_ids
    ]
    return rng.choice(candidates or [merchant for merchant in merchants if merchant.category == category])


def _apply_revised_signal(
    record: dict[str, Any],
    signal: str,
    profile: UserProfile,
    merchants: tuple[MerchantProfile, ...],
    previous_record: dict[str, Any] | None,
    seen_merchant_ids: set[str],
    seen_categories: set[str],
    seen_channels: set[str],
    rng: random.Random,
) -> None:
    if signal == "amount":
        factor = rng.choice((rng.uniform(1.25, 1.8), rng.uniform(1.8, 3.2), rng.uniform(0.55, 0.85)))
        record["amount"] = _clamp_amount(_money(Decimal(record["amount"]) * Decimal(str(factor))))
    elif signal == "time":
        hour = (profile.typical_hour + rng.choice((-7, -5, -4, -3, 3, 4, 5, 7))) % 24
        current = record["timestamp"]
        record["timestamp"] = datetime.combine(
            current.date(), time(hour, current.minute, current.second), tzinfo=UTC
        )
    elif signal == "rapid" and previous_record is not None:
        seconds = rng.choice(
            (
                rng.randint(180, 600),
                rng.randint(601, 1_200),
                rng.randint(1_201, 3_600),
                rng.randint(3_601, 7_200),
            )
        )
        record["timestamp"] = previous_record["timestamp"] + timedelta(seconds=seconds)
    elif signal == "category":
        if rng.random() < 0.65:
            candidates = [category for category in CATEGORY_IDS if category not in profile.preferred_categories]
        else:
            candidates = list(profile.preferred_categories)
        category = rng.choice(candidates)
        record["merchant_category"] = category
        record["synthetic_merchant_id"] = _choose_new_merchant(
            merchants, category, seen_merchant_ids, rng
        ).merchant_id
    elif signal == "merchant":
        merchant = _choose_new_merchant(
            merchants, record["merchant_category"], seen_merchant_ids, rng
        )
        record["synthetic_merchant_id"] = merchant.merchant_id
    elif signal == "channel":
        unseen = [channel for channel in CHANNELS if channel not in seen_channels]
        record["transaction_channel"] = rng.choice(unseen or list(CHANNELS))
    elif signal == "frequency" and previous_record is not None:
        record["timestamp"] = previous_record["timestamp"] + timedelta(
            seconds=rng.randint(2_401, 14_400)
        )


def _apply_revised_scenario(
    record: dict[str, Any],
    label: str,
    profile: UserProfile,
    merchants: tuple[MerchantProfile, ...],
    previous_record: dict[str, Any] | None,
    seen_merchant_ids: set[str],
    seen_categories: set[str],
    seen_channels: set[str],
    rng: random.Random,
) -> None:
    if label == "synthetic_high_amount":
        _apply_revised_signal(record, "amount", profile, merchants, previous_record, seen_merchant_ids, seen_categories, seen_channels, rng)
        if rng.random() < 0.35:
            _apply_revised_signal(record, "category", profile, merchants, previous_record, seen_merchant_ids, seen_categories, seen_channels, rng)
    elif label == "synthetic_rapid_repeat":
        _apply_revised_signal(record, "rapid", profile, merchants, previous_record, seen_merchant_ids, seen_categories, seen_channels, rng)
        if rng.random() < 0.55:
            _apply_revised_signal(record, rng.choice(("merchant", "category")), profile, merchants, previous_record, seen_merchant_ids, seen_categories, seen_channels, rng)
    elif label == "synthetic_unusual_time":
        _apply_revised_signal(record, "time", profile, merchants, previous_record, seen_merchant_ids, seen_categories, seen_channels, rng)
    elif label == "synthetic_behavior_deviation":
        count = rng.choices((1, 2, 3), weights=(0.35, 0.45, 0.20), k=1)[0]
        signals = rng.sample(("category", "merchant", "channel", "amount", "time", "frequency"), k=count)
        for signal in signals:
            _apply_revised_signal(record, signal, profile, merchants, previous_record, seen_merchant_ids, seen_categories, seen_channels, rng)
    elif label == "synthetic_combined_pattern":
        count = rng.choice((2, 2, 3))
        signals = rng.sample(("amount", "time", "rapid", "category", "merchant", "channel"), k=count)
        for signal in signals:
            _apply_revised_signal(record, signal, profile, merchants, previous_record, seen_merchant_ids, seen_categories, seen_channels, rng)


def _generate_revised_raw_records(
    config: SyntheticDatasetConfig,
    rng: random.Random,
    users: tuple[UserProfile, ...],
    merchants: tuple[MerchantProfile, ...],
) -> list[dict[str, Any]]:
    raw_records: list[dict[str, Any]] = []
    preferred_channels = {user.user_id: rng.choice(CHANNELS) for user in users}
    for user in users:
        previous_timestamp: datetime | None = None
        previous_base: dict[str, Any] | None = None
        for sequence in range(config.transactions_per_user):
            timestamp = _revised_timestamp(
                user,
                previous_timestamp,
                config,
                rng,
                sequence,
                config.transactions_per_user,
            )
            if previous_base is not None and rng.random() < 0.48:
                category = previous_base["merchant_category"]
            else:
                category = _choose_base_category(user, rng)
            merchant = (
                _merchant_for_category(merchants, category, rng)
                if previous_base is None or rng.random() >= 0.45
                else next(item for item in merchants if item.merchant_id == previous_base["synthetic_merchant_id"])
            )
            channel = preferred_channels[user.user_id] if rng.random() < 0.68 else rng.choice(CHANNELS)
            record = {
                "synthetic_user_id": user.user_id,
                "synthetic_account_id": user.account_id,
                "user_sequence": sequence,
                "timestamp": timestamp,
                "amount": _revised_amount(user, rng),
                "currency": config.currency,
                "synthetic_merchant_id": merchant.merchant_id,
                "merchant_category": category,
                "transaction_channel": channel,
            }
            raw_records.append(record)
            previous_timestamp = timestamp
            previous_base = record

    assignments = _assign_scenarios(raw_records, config, rng)
    users_by_id = {profile.user_id: profile for profile in users}
    by_user: defaultdict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(raw_records):
        by_user[record["synthetic_user_id"]].append(index)
    for user_id, indexes in by_user.items():
        indexes.sort(key=lambda index: raw_records[index]["timestamp"])
        previous: dict[str, Any] | None = None
        seen_merchant_ids: set[str] = set()
        seen_categories: set[str] = set()
        seen_channels: set[str] = set()
        for index in indexes:
            record = raw_records[index]
            label = assignments[index]
            _apply_revised_scenario(
                record,
                label,
                users_by_id[user_id],
                merchants,
                previous,
                seen_merchant_ids,
                seen_categories,
                seen_channels,
                rng,
            )
            record["scenario_label"] = label
            previous = record
            seen_merchant_ids.add(record["synthetic_merchant_id"])
            seen_categories.add(record["merchant_category"])
            seen_channels.add(record["transaction_channel"])
    return raw_records


def generate_revised_dataset(
    config: SyntheticDatasetConfig | None = None,
) -> GeneratedDataset:
    """Generate the v2 overlap-focused dataset while leaving v1 untouched."""

    config = config or revised_dataset_config()
    if config.generator_version != REVISED_GENERATOR_VERSION:
        raise ValueError("generate_revised_dataset requires generator version 1.1.0")
    rng = random.Random(config.seed)
    users = generate_synthetic_users(config, rng)
    merchants = generate_synthetic_merchants(config, rng)
    raw_records = _generate_revised_raw_records(config, rng, users, merchants)
    for index, record in enumerate(raw_records):
        record["synthetic_transaction_id"] = f"syn-transaction-{index + 1:06d}"
    featured_records = _add_temporal_features(raw_records, config)
    records = _finalize_records(featured_records, config, REVISED_SCENARIO_DEFINITIONS)
    splits: dict[str, tuple[dict[str, Any], ...]] = {
        name: tuple(record for record in records if record["dataset_split"] == name)
        for name in ("train", "validation", "test")
    }
    validation = validate_records(records, config=config, splits=splits)
    if not validation["valid"]:
        raise DatasetValidationError(json.dumps(validation, indent=2, default=str))
    manifest = build_manifest(records, splits, config)
    return GeneratedDataset(records=records, splits=splits, manifest=manifest)


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, datetime):
        return _isoformat(value)
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=_json_value) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REQUIRED_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow({column: _json_value(record.get(column)) for column in REQUIRED_COLUMNS})


def label_dictionary(config: SyntheticDatasetConfig | None = None) -> dict[str, Any]:
    """Return the explicit label semantics shipped with the dataset."""

    config = config or SyntheticDatasetConfig()
    definitions = (
        REVISED_SCENARIO_DEFINITIONS
        if config.generator_version == REVISED_GENERATOR_VERSION
        else SCENARIO_DEFINITIONS
    )
    return {
        "dataset_type": DATASET_TYPE,
        "dataset_version": config.dataset_version,
        "synthetic_label_notice": LABEL_NOTICE,
        "labels": definitions,
    }


def write_dataset(
    dataset: GeneratedDataset, output_dir: str | Path, config: SyntheticDatasetConfig | None = None
) -> dict[str, Any]:
    """Write only synthetic files beneath ``output_dir`` and return the manifest."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    config = config or SyntheticDatasetConfig()
    _write_csv(output_path / dataset.manifest["files"]["full_csv"], dataset.records)
    for split_name, split_records in dataset.splits.items():
        _write_csv(output_path / f"{split_name}.csv", split_records)
    _write_json(output_path / "generation_config.json", config.to_dict())
    _write_json(output_path / "label_dictionary.json", label_dictionary(config))
    manifest = dict(dataset.manifest)
    manifest["checksums_sha256"] = {
        file_name: _sha256(output_path / file_name)
        for file_name in (
            manifest["files"]["full_csv"],
            manifest["files"]["train_csv"],
            manifest["files"]["validation_csv"],
            manifest["files"]["test_csv"],
        )
    }
    _write_json(output_path / "dataset_manifest.json", manifest)
    return manifest


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows: list[dict[str, Any]] = []
        for raw_record in csv.DictReader(handle):
            record: dict[str, Any] = dict(raw_record)
            for field_name in ("synthetic", "is_synthetic_scenario"):
                record[field_name] = record[field_name].strip().lower() == "true"
            if record.get("time_since_previous_transaction_seconds", "") == "":
                record["time_since_previous_transaction_seconds"] = None
            rows.append(record)
        return tuple(rows)


def validate_records(
    records: Iterable[Mapping[str, Any]],
    *,
    config: SyntheticDatasetConfig | None = None,
    splits: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate schema, provenance, labels, causality, leakage, and temporal splits."""

    config = config or SyntheticDatasetConfig()
    rows = [dict(record) for record in records]
    errors: list[str] = []
    if not rows:
        errors.append("Dataset contains no rows.")
    for index, record in enumerate(rows):
        missing = [column for column in REQUIRED_COLUMNS if column not in record]
        if missing:
            errors.append(f"Row {index} missing required columns: {missing}")
            continue
        if any(record[column] in (None, "") for column in REQUIRED_COLUMNS if column not in {"time_since_previous_transaction_seconds"}):
            errors.append(f"Row {index} contains a null required value.")
        try:
            timestamp = _parse_timestamp(record["timestamp"])
            amount = Decimal(str(record["amount"]))
            if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
                errors.append(f"Row {index} has an invalid amount.")
            if not (config.start_timestamp <= timestamp < config.end_timestamp_exclusive):
                errors.append(f"Row {index} timestamp is outside configured range.")
        except (InvalidOperation, TypeError, ValueError) as exc:
            errors.append(f"Row {index} has invalid timestamp/amount: {exc}")
        if record.get("currency") != config.currency:
            errors.append(f"Row {index} has unsupported currency.")
        if not str(record.get("synthetic_transaction_id", "")).startswith("syn-transaction-"):
            errors.append(f"Row {index} has a non-synthetic transaction identifier.")
        if not str(record.get("synthetic_user_id", "")).startswith("syn-user-"):
            errors.append(f"Row {index} has a non-synthetic user identifier.")
        if not str(record.get("synthetic_account_id", "")).startswith("syn-account-"):
            errors.append(f"Row {index} has a non-synthetic account identifier.")
        if not str(record.get("synthetic_merchant_id", "")).startswith("syn-merchant-"):
            errors.append(f"Row {index} has a non-synthetic merchant identifier.")
        if record.get("merchant_category") not in CATEGORY_IDS:
            errors.append(f"Row {index} has an unknown merchant category.")
        if record.get("transaction_channel") not in CHANNELS:
            errors.append(f"Row {index} has an unknown transaction channel.")
        if record.get("transaction_state") != "COMPLETED":
            errors.append(f"Row {index} has an unsupported transaction state.")
        if record.get("scenario_label") not in SCENARIO_LABELS:
            errors.append(f"Row {index} has an unknown scenario label.")
        if record.get("synthetic") is not True or record.get("is_synthetic_scenario") is not True:
            errors.append(f"Row {index} is not explicitly marked synthetic.")
        if record.get("dataset_type") != DATASET_TYPE or record.get("label_source") != "generator_rule":
            errors.append(f"Row {index} has invalid provenance markers.")
        if record.get("dataset_version") != config.dataset_version:
            errors.append(f"Row {index} has an unexpected dataset version.")
    transaction_ids = [record.get("synthetic_transaction_id") for record in rows]
    if len(transaction_ids) != len(set(transaction_ids)):
        errors.append("Transaction identifiers are duplicated.")
    timestamps = [_parse_timestamp(record["timestamp"]) for record in rows if record.get("timestamp")]
    if timestamps != sorted(timestamps):
        errors.append("Full dataset is not sorted in temporal order.")

    if set(CANDIDATE_FEATURE_FIELDS) & set(AUDIT_ONLY_FIELDS):
        errors.append("Candidate feature fields overlap audit-only fields.")
    if set(CANDIDATE_FEATURE_FIELDS) & set(FORBIDDEN_FEATURE_FIELDS):
        errors.append("Candidate feature fields overlap forbidden fields.")
    if "scenario_label" in CANDIDATE_FEATURE_FIELDS:
        errors.append("Scenario label is not allowed as a candidate feature.")

    by_user: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in rows:
        by_user[str(record.get("synthetic_user_id"))].append(record)
    for user_rows in by_user.values():
        user_rows.sort(key=lambda record: _parse_timestamp(record["timestamp"]))
        for position, record in enumerate(user_rows):
            if int(record["user_historical_transaction_count_before"]) != position:
                errors.append("Historical count feature includes current/future records.")
                break
            if position == 0 and record["time_since_previous_transaction_seconds"] not in (None, "", "0"):
                errors.append("First user record has a prior-transaction interval.")
                break

    split_rows: dict[str, list[dict[str, Any]]] = {}
    if splits is None:
        split_rows = {
            split_name: [record for record in rows if record.get("dataset_split") == split_name]
            for split_name in ("train", "validation", "test")
        }
    else:
        split_rows = {name: [dict(record) for record in split] for name, split in splits.items()}
    split_ids = [
        {record.get("synthetic_transaction_id") for record in split_rows.get(name, [])}
        for name in ("train", "validation", "test")
    ]
    if any(split_ids[index] & split_ids[j] for index in range(3) for j in range(index + 1, 3)):
        errors.append("Temporal splits overlap transaction identifiers.")
    if sum(len(ids) for ids in split_ids) != len(rows):
        errors.append("Temporal split row counts do not reconcile with the full dataset.")
    split_times = {
        name: sorted(_parse_timestamp(record["timestamp"]) for record in split_rows.get(name, []))
        for name in ("train", "validation", "test")
    }
    if split_times["train"] and split_times["validation"] and not split_times["train"][-1] < split_times["validation"][0]:
        errors.append("Training timestamps are not earlier than validation timestamps.")
    if split_times["validation"] and split_times["test"] and not split_times["validation"][-1] < split_times["test"][0]:
        errors.append("Validation timestamps are not earlier than test timestamps.")

    scenario_distribution = dict(sorted(Counter(record.get("scenario_label") for record in rows).items()))
    expected_distribution = dict(sorted(config.scenario_counts.items()))
    if scenario_distribution != expected_distribution:
        errors.append("Scenario distribution does not match generation configuration.")

    if manifest is not None:
        if manifest.get("row_count") != len(rows):
            errors.append("Manifest row_count does not match generated data.")
        if manifest.get("column_count") != len(REQUIRED_COLUMNS):
            errors.append("Manifest column_count does not match generated data.")
        if manifest.get("scenario_distribution") != scenario_distribution:
            errors.append("Manifest scenario distribution does not match generated data.")
        if manifest.get("split_counts") != {name: len(split_rows.get(name, [])) for name in ("train", "validation", "test")}:
            errors.append("Manifest split counts do not match generated data.")

    return {
        "valid": not errors,
        "errors": errors,
        "row_count": len(rows),
        "column_count": len(rows[0]) if rows else 0,
        "user_count": len({record.get("synthetic_user_id") for record in rows}),
        "account_count": len({record.get("synthetic_account_id") for record in rows}),
        "merchant_count": len({record.get("synthetic_merchant_id") for record in rows}),
        "category_count": len({record.get("merchant_category") for record in rows}),
        "scenario_distribution": scenario_distribution,
        "split_counts": {name: len(split_rows.get(name, [])) for name in ("train", "validation", "test")},
    }


def validate_written_dataset(output_dir: str | Path) -> dict[str, Any]:
    """Read generated CSV/JSON artifacts and validate their cross-file contract."""

    output_path = Path(output_dir)
    config_data = json.loads((output_path / "generation_config.json").read_text(encoding="utf-8"))
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
    manifest = json.loads((output_path / "dataset_manifest.json").read_text(encoding="utf-8"))
    for file_name, expected_hash in manifest.get("checksums_sha256", {}).items():
        if not (output_path / file_name).is_file() or _sha256(output_path / file_name) != expected_hash:
            return {
                "valid": False,
                "errors": [f"Checksum mismatch for {file_name}."],
            }
    records = _read_csv(output_path / manifest["files"]["full_csv"])
    splits = {name: _read_csv(output_path / f"{name}.csv") for name in ("train", "validation", "test")}
    return validate_records(records, config=config, splits=splits, manifest=manifest)


def main() -> None:
    """Generate the default bounded dataset in the repository data boundary."""

    repository_root = Path(__file__).resolve().parents[1]
    output_dir = repository_root / "data" / "synthetic"
    config = SyntheticDatasetConfig()
    dataset = generate_dataset(config)
    manifest = write_dataset(dataset, output_dir, config)
    validation = validate_written_dataset(output_dir)
    if not validation["valid"]:
        raise SystemExit(json.dumps(validation, indent=2))
    print(json.dumps({"manifest": manifest, "validation": validation}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
