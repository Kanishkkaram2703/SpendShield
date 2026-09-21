"""Deterministic research explanations for the v2 anomaly experiment.

This module deliberately operates on observed candidate-feature values only.
It never reads synthetic labels, generator metadata, or future records.  The
returned text is a research explanation, not a decision or a causal claim.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


EXPLAINABILITY_VERSION = "1.0.0"

# These are intentionally conservative.  The validation routine rejects these
# terms in explanation text so a research artifact cannot silently become a
# production fraud claim.
FORBIDDEN_EXPLANATION_TERMS: tuple[str, ...] = (
    "fraud",
    "financial crime",
    "payment blocking",
    "payment rejection",
    "confirmed fraud",
    "guaranteed fraud",
    "automatic fraud decision",
)

EXPLANATION_FEATURES: tuple[str, ...] = (
    "amount",
    "transaction_hour",
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


def _number(row: Mapping[str, Any], field: str, default: float = 0.0) -> float:
    value = row.get(field, default)
    if value in (None, ""):
        return default
    parsed = float(value)
    if not math.isfinite(parsed):
        return default
    return parsed


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _strength(value: float) -> str:
    if value >= 0.75:
        return "strong"
    if value >= 0.40:
        return "moderate"
    if value > 0.0:
        return "weak"
    return "none"


def signal_components(row: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return fixed, label-free signal components from one feature row.

    The thresholds are research assumptions.  They are not fitted to labels,
    and the values are designed to be inspectable by a reviewer.
    """

    history_count = _number(row, "user_historical_transaction_count_before")
    amount_ratio = _number(row, "user_relative_amount_deviation")
    amount_signal = (
        _clamp(abs(math.log(max(amount_ratio, 1e-9))) / math.log(3.0))
        if history_count > 0 and amount_ratio > 0
        else 0.0
    )
    time_distance = _number(row, "user_relative_time_deviation")
    time_signal = _clamp(time_distance / 6.0) if history_count > 0 else 0.0
    gap = row.get("time_since_previous_transaction_seconds")
    rapid_signal = 0.0
    if gap not in (None, "") and history_count > 0:
        rapid_signal = 1.0 if _number(row, "time_since_previous_transaction_seconds") <= 600 else 0.0
    novelty_signal = _clamp(
        (_number(row, "merchant_novelty_before") + _number(row, "channel_novelty_before")) / 2.0
    )
    history_limited = 1.0 if history_count < 2 else 0.0

    return {
        "amount_deviation": {
            "value": round(amount_signal, 6),
            "strength": _strength(amount_signal),
            "feature_names": [
                "user_relative_amount_deviation",
                "user_historical_average_amount_before",
                "amount",
            ],
        },
        "time_deviation": {
            "value": round(time_signal, 6),
            "strength": _strength(time_signal),
            "feature_names": ["user_relative_time_deviation", "transaction_hour"],
        },
        "rapid_repeat": {
            "value": round(rapid_signal, 6),
            "strength": _strength(rapid_signal),
            "feature_names": ["time_since_previous_transaction_seconds"],
        },
        "novelty": {
            "value": round(novelty_signal, 6),
            "strength": _strength(novelty_signal),
            "feature_names": ["merchant_novelty_before", "channel_novelty_before"],
        },
        "history_limited": {
            "value": round(history_limited, 6),
            "strength": _strength(history_limited),
            "feature_names": [
                "user_historical_transaction_count_before",
                "time_since_previous_transaction_seconds__missing",
            ],
        },
    }


def transparent_baseline_score(row: Mapping[str, Any]) -> tuple[float, dict[str, dict[str, Any]]]:
    """Calculate the fixed weighted research baseline.

    Formula: 0.30 amount + 0.20 time + 0.20 rapid repeat + 0.20 novelty
    + 0.10 limited history.  The weights are manually selected research
    assumptions and are not optimized against synthetic labels.
    """

    components = signal_components(row)
    weights = {
        "amount_deviation": 0.30,
        "time_deviation": 0.20,
        "rapid_repeat": 0.20,
        "novelty": 0.20,
        "history_limited": 0.10,
    }
    score = sum(weights[name] * float(components[name]["value"]) for name in weights)
    return round(_clamp(score), 6), components


def _component_sentence(name: str, row: Mapping[str, Any], component: Mapping[str, Any]) -> str | None:
    strength = component["strength"]
    if strength == "none":
        return None
    if name == "amount_deviation":
        ratio = _number(row, "user_relative_amount_deviation")
        average = _number(row, "user_historical_average_amount_before")
        amount = _number(row, "amount")
        if ratio >= 1:
            return (
                f"The amount is {ratio:.2f}x the user's prior observed average "
                f"({average:.2f} to {amount:.2f}); this is a {strength} amount-deviation signal."
            )
        return (
            f"The amount is {ratio:.2f}x the user's prior observed average "
            f"({average:.2f} to {amount:.2f}); this is a {strength} two-sided amount-deviation signal."
        )
    if name == "time_deviation":
        return (
            f"The transaction hour differs from the user's prior observed timing by "
            f"{_number(row, 'user_relative_time_deviation'):.2f} circular hours; "
            f"this is a {strength} time-deviation signal."
        )
    if name == "rapid_repeat":
        return (
            f"The transaction followed the previous observed transaction after "
            f"{_number(row, 'time_since_previous_transaction_seconds'):.0f} seconds; "
            f"this is a {strength} rapid-repeat signal under the fixed 600-second research rule."
        )
    if name == "novelty":
        merchant = _number(row, "merchant_novelty_before") > 0
        channel = _number(row, "channel_novelty_before") > 0
        parts = []
        if merchant:
            parts.append("merchant")
        if channel:
            parts.append("channel")
        joined = " and ".join(parts) if parts else "merchant/channel"
        return f"The user's observed {joined} history is new at this row; this is a {strength} novelty signal."
    if name == "history_limited":
        return (
            f"Only {_number(row, 'user_historical_transaction_count_before'):.0f} prior transaction(s) "
            "are available, so historical comparison is limited and research confidence is low."
        )
    return None


def build_research_explanation(
    row: Mapping[str, Any],
    *,
    anomaly_score: float,
    rank: int,
    total_rows: int,
    max_signals: int = 3,
) -> dict[str, Any]:
    """Build one deterministic, label-free explanation record."""

    score, components = transparent_baseline_score(row)
    ordered = sorted(
        components.items(),
        key=lambda item: (-float(item[1]["value"]), item[0]),
    )
    selected = [item for item in ordered if item[1]["value"] > 0][:max_signals]
    sentences = [
        sentence
        for name, component in selected
        if (sentence := _component_sentence(name, row, component)) is not None
    ]
    if len(selected) >= 2:
        sentences.append("Multiple observed signals occurred together and jointly raised the research anomaly score.")
    if not sentences:
        sentences.append("No strong observed behavioral signal was identified by the transparent signal rules.")
    text = "Research explanation: " + " ".join(sentences)
    percentile = 100.0 * (total_rows - rank + 1) / total_rows if total_rows else 0.0
    return {
        "synthetic_transaction_id": row.get("synthetic_transaction_id", ""),
        "anomaly_score": round(float(anomaly_score), 6),
        "transparent_baseline_score": score,
        "rank": int(rank),
        "anomaly_rank_percentile": round(percentile, 4),
        "signal_strengths": {name: component["strength"] for name, component in selected},
        "signal_feature_names": sorted(
            {feature for _, component in selected for feature in component["feature_names"]}
        ),
        "explanation_text": text,
        "missing_history_warning": _number(row, "user_historical_transaction_count_before") < 2,
        "explainability_version": EXPLAINABILITY_VERSION,
    }


def validate_explanations(
    explanations: Sequence[Mapping[str, Any]],
    *,
    available_features: Sequence[str],
    synthetic_labels: Sequence[str] = (),
    max_rows: int = 25,
) -> dict[str, Any]:
    """Validate explanation safety and structural determinism contracts."""

    available = set(available_features)
    labels = {str(label).lower() for label in synthetic_labels}
    errors: list[str] = []
    warnings: list[str] = []
    if len(explanations) > max_rows:
        errors.append(f"explanation sample exceeds bounded size {max_rows}")
    for index, explanation in enumerate(explanations):
        text = str(explanation.get("explanation_text", ""))
        lowered = text.lower()
        forbidden = [term for term in FORBIDDEN_EXPLANATION_TERMS if term in lowered]
        if forbidden:
            errors.append(f"row {index}: forbidden terms present: {forbidden}")
        leaked_labels = [label for label in labels if label and label in lowered]
        if leaked_labels:
            errors.append(f"row {index}: synthetic labels appear in explanation text")
        if any(term in lowered for term in ("generator_rule", "injection reason", "scenario_id", "future_")):
            errors.append(f"row {index}: generator or future metadata appears in explanation text")
        referenced = set(explanation.get("signal_feature_names", []))
        if not referenced:
            errors.append(f"row {index}: no available feature was referenced")
        if not referenced.issubset(available):
            errors.append(f"row {index}: explanation referenced unavailable features")
        if explanation.get("missing_history_warning") and "limited" not in lowered:
            errors.append(f"row {index}: missing-history case lacks a limitation warning")
        if "confidence" not in lowered and explanation.get("missing_history_warning"):
            warnings.append(f"row {index}: limitation warning does not use the word confidence")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "rows_checked": len(explanations),
        "bounded_sample_limit": max_rows,
        "forbidden_terms_checked": list(FORBIDDEN_EXPLANATION_TERMS),
        "labels_used_for_validation_only": True,
    }
