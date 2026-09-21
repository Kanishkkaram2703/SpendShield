# Controlled ML Error Analysis Report

## Scope

This report evaluates the existing Gaussian Naive Bayes baseline on the
isolated synthetic scenario target. It is not a fraud report.

## Reproduction

- Stored baseline reproduced: `True`.
- Test accuracy: `0.862826`.
- Test macro F1: `0.617953`.
- Test weighted F1: `0.850388`.

## Main error groups

{
  "confusion_between_synthetic_scenarios": 16,
  "false_negative_for_synthetic_pattern": 131,
  "false_positive_against_normal": 53
}

The largest analytical questions are separation of normal from unusual-time
and behavior-deviation cases, and separation of combined patterns from
high-amount cases. These terms describe synthetic scenario classes only.

## Per-class test summary

{
  "normal": {
    "f1": 0.921435,
    "precision": 0.891736,
    "recall": 0.95318,
    "support": 1132
  },
  "synthetic_behavior_deviation": {
    "f1": 0.216216,
    "precision": 0.210526,
    "recall": 0.222222,
    "support": 36
  },
  "synthetic_combined_pattern": {
    "f1": 0.4,
    "precision": 0.4375,
    "recall": 0.368421,
    "support": 19
  },
  "synthetic_high_amount": {
    "f1": 0.728889,
    "precision": 0.738739,
    "recall": 0.719298,
    "support": 114
  },
  "synthetic_rapid_repeat": {
    "f1": 1.0,
    "precision": 1.0,
    "recall": 1.0,
    "support": 52
  },
  "synthetic_unusual_time": {
    "f1": 0.441176,
    "precision": 0.967742,
    "recall": 0.285714,
    "support": 105
  }
}

## Review conclusions

- Leakage review valid: `True`.
- Validation metrics were used for review; test metrics were not used for
  fitting or model selection.
- Class imbalance makes macro F1 and per-class recall more informative than
  accuracy alone.
- Generator shortcut review: `REVIEW_REQUIRED_BEFORE_COMPLEX_MODEL`.
- Decision: `DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST`.

## Limitations

The dataset contains no real fraud ground truth. Errors and metrics reflect
only controlled generator rules and cannot establish real-world detection,
prevention, savings, or risk-reduction performance.
