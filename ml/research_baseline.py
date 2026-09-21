"""Evaluate a transparent, research-only synthetic scenario baseline.

No production model artifact or inference service is created.  The baseline
uses only the generated feature CSVs and a train-fitted deterministic Gaussian
Naive Bayes classifier, alongside a majority-class reference.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

BASELINE_VERSION = "1.0.0"
REVISED_BASELINE_VERSION = "1.1.0"
TARGET_COLUMN = "target_scenario_label"
IDENTITY_COLUMNS = {
    "synthetic_transaction_id",
    "synthetic_user_id",
    "timestamp",
    "dataset_split",
    TARGET_COLUMN,
}


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _feature_names(rows: tuple[dict[str, str], ...]) -> tuple[str, ...]:
    if not rows:
        raise ValueError("Feature split is empty.")
    return tuple(name for name in rows[0] if name not in IDENTITY_COLUMNS)


def _matrix(rows: Iterable[Mapping[str, str]], feature_names: tuple[str, ...]) -> list[list[float]]:
    return [[float(row[name]) for name in feature_names] for row in rows]


def class_counts(rows: Iterable[Mapping[str, str]]) -> dict[str, int]:
    return dict(sorted(Counter(row[TARGET_COLUMN] for row in rows).items()))


def _classification_metrics(
    actual: list[str], predicted: list[str], classes: tuple[str, ...]
) -> dict[str, Any]:
    if len(actual) != len(predicted) or not actual:
        raise ValueError("Metric inputs must have equal non-zero length.")
    confusion = {actual_class: {predicted_class: 0 for predicted_class in classes} for actual_class in classes}
    for actual_class, predicted_class in zip(actual, predicted):
        confusion[actual_class][predicted_class] += 1
    per_class: dict[str, dict[str, float | int]] = {}
    total = len(actual)
    for class_name in classes:
        true_positive = confusion[class_name][class_name]
        false_positive = sum(confusion[other][class_name] for other in classes if other != class_name)
        false_negative = sum(confusion[class_name][other] for other in classes if other != class_name)
        support = sum(confusion[class_name].values())
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[class_name] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
            "support": support,
        }
    accuracy = sum(1 for actual_class, predicted_class in zip(actual, predicted) if actual_class == predicted_class) / total
    macro_precision = sum(float(values["precision"]) for values in per_class.values()) / len(classes)
    macro_recall = sum(float(values["recall"]) for values in per_class.values()) / len(classes)
    macro_f1 = sum(float(values["f1"]) for values in per_class.values()) / len(classes)
    weighted_f1 = sum(float(values["f1"]) * int(values["support"]) for values in per_class.values()) / total
    return {
        "accuracy": round(accuracy, 6),
        "macro_precision": round(macro_precision, 6),
        "macro_recall": round(macro_recall, 6),
        "macro_f1": round(macro_f1, 6),
        "weighted_f1": round(weighted_f1, 6),
        "classes": list(classes),
        "per_class": per_class,
        "confusion_matrix": [[confusion[actual_class][predicted_class] for predicted_class in classes] for actual_class in classes],
    }


def _majority_label(train_rows: Iterable[Mapping[str, str]]) -> str:
    counts = Counter(row[TARGET_COLUMN] for row in train_rows)
    return min(counts, key=lambda label: (-counts[label], label))


@dataclass(frozen=True, slots=True)
class GaussianNaiveBayes:
    classes: tuple[str, ...]
    means: Mapping[str, tuple[float, ...]]
    variances: Mapping[str, tuple[float, ...]]
    log_priors: Mapping[str, float]

    @classmethod
    def fit(
        cls,
        rows: Iterable[Mapping[str, str]],
        feature_names: tuple[str, ...],
        classes: tuple[str, ...],
    ) -> "GaussianNaiveBayes":
        rows_list = list(rows)
        grouped = {class_name: [] for class_name in classes}
        for row in rows_list:
            grouped[row[TARGET_COLUMN]].append(row)
        means: dict[str, tuple[float, ...]] = {}
        variances: dict[str, tuple[float, ...]] = {}
        log_priors: dict[str, float] = {}
        for class_name in classes:
            if not grouped[class_name]:
                raise ValueError(f"Training split does not contain class {class_name!r}.")
            matrix = _matrix(grouped[class_name], feature_names)
            class_means = tuple(sum(row[index] for row in matrix) / len(matrix) for index in range(len(feature_names)))
            class_variances = tuple(
                max(
                    1e-9,
                    sum((row[index] - class_means[index]) ** 2 for row in matrix) / len(matrix),
                )
                for index in range(len(feature_names))
            )
            means[class_name] = class_means
            variances[class_name] = class_variances
            log_priors[class_name] = math.log(len(matrix) / len(rows_list))
        return cls(classes=classes, means=means, variances=variances, log_priors=log_priors)

    def predict(self, matrix: Iterable[list[float]]) -> list[str]:
        predictions: list[str] = []
        for row in matrix:
            scores: dict[str, float] = {}
            for class_name in self.classes:
                score = self.log_priors[class_name]
                for value, mean, variance in zip(row, self.means[class_name], self.variances[class_name]):
                    score += -0.5 * (math.log(2 * math.pi * variance) + ((value - mean) ** 2 / variance))
                scores[class_name] = score
            predictions.append(max(self.classes, key=lambda class_name: (scores[class_name], class_name)))
        return predictions


def _evaluate_one(
    rows: tuple[dict[str, str], ...],
    *,
    classes: tuple[str, ...],
    prediction: list[str],
) -> dict[str, Any]:
    return {
        "row_count": len(rows),
        "class_counts": class_counts(rows),
        "metrics": _classification_metrics(
            [row[TARGET_COLUMN] for row in rows], prediction, classes
        ),
    }


def evaluate_research_baseline(
    feature_dir: str | Path = "data/synthetic/features",
    output_path: str | Path | None = "data/synthetic/baseline/research_baseline_results.json",
) -> dict[str, Any]:
    """Evaluate majority and Gaussian-NB baselines using temporal partitions."""

    feature_root = Path(feature_dir)
    feature_manifest = json.loads((feature_root / "feature_manifest.json").read_text(encoding="utf-8"))
    split_rows = {
        name: _read_csv(feature_root / f"candidate_features_{name}.csv")
        for name in ("train", "validation", "test")
    }
    feature_names = tuple(feature_manifest["feature_names"])
    if set(feature_names) & IDENTITY_COLUMNS:
        raise ValueError("Identity or target columns entered the model feature list.")
    classes = tuple(feature_manifest["target"]["classes"])
    majority = _majority_label(split_rows["train"])
    majority_results = {
        name: _evaluate_one(rows, classes=classes, prediction=[majority] * len(rows))
        for name, rows in (("validation", split_rows["validation"]), ("test", split_rows["test"]))
    }
    model = GaussianNaiveBayes.fit(split_rows["train"], feature_names, classes)
    model_results = {
        name: _evaluate_one(
            rows,
            classes=classes,
            prediction=model.predict(_matrix(rows, feature_names)),
        )
        for name, rows in (("validation", split_rows["validation"]), ("test", split_rows["test"]))
    }
    result = {
        "baseline_version": (
            REVISED_BASELINE_VERSION
            if feature_manifest["generator_version"] == "1.1.0"
            else BASELINE_VERSION
        ),
        "dataset_type": feature_manifest["dataset_type"],
        "dataset_version": feature_manifest["dataset_version"],
        "feature_generation_version": feature_manifest["feature_generation_version"],
        "random_seed": feature_manifest["random_seed"],
        "target": feature_manifest["target"],
        "evaluation_type": "multiclass synthetic scenario classification",
        "real_fraud_detection": False,
        "feature_count": len(feature_names),
        "feature_names": list(feature_names),
        "data_usage": {
            "fit": "train only",
            "validation": "reported for research comparison; no test tuning",
            "test": "final held-out evaluation after fixed baseline configuration",
            "random_row_split": False,
        },
        "models": {
            "majority_class": {
                "majority_label_from_train": majority,
                "validation": majority_results["validation"],
                "test": majority_results["test"],
            },
            "gaussian_naive_bayes": {
                "configuration": {
                    "variance_floor": 1e-9,
                    "class_priors": "training class frequencies",
                    "preprocessing": "feature matrix generated with train-fitted medians and one-hot vocabulary",
                },
                "validation": model_results["validation"],
                "test": model_results["test"],
            },
        },
        "interpretation_notice": "Metrics measure performance on intentionally generated synthetic scenarios only. They do not measure real fraud detection, prevention, savings, blocking, or risk reduction.",
        "model_artifact_written": False,
        "production_inference_created": False,
        "created_at_utc": _now(),
        "reproducibility": {
            "command": "python -m ml.research_baseline",
            "same_feature_files_and_configuration": "Produces equivalent predictions and metrics; creation timestamp varies per run.",
        },
        "known_limitations": [
            "Synthetic scenario patterns may be easier to classify than real behavior.",
            "No real fraud ground truth exists.",
            "Gaussian Naive Bayes assumptions may not reflect feature relationships.",
            "No hyperparameter tuning or class rebalancing was performed.",
            "Results are not production-ready and must not drive financial decisions.",
        ],
    }
    if output_path is not None:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        _write_json(output_file, result)
    return result


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    result = evaluate_research_baseline(
        repository_root / "data" / "synthetic" / "features",
        repository_root / "data" / "synthetic" / "baseline" / "research_baseline_results.json",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
