# Controlled ML Error Analysis Report

## Scope

This report evaluates the existing Gaussian Naive Bayes baseline on the
isolated synthetic scenario target. It is not a fraud report.

## Reproduction

- Stored baseline reproduced: `True`.
- Test accuracy: `0.703673`.
- Test macro F1: `0.262793`.
- Test weighted F1: `0.651407`.

## Main error groups

{
  "confusion_between_synthetic_scenarios": 54,
  "false_negative_for_synthetic_pattern": 205,
  "false_positive_against_normal": 96
}

The largest analytical questions are separation of normal from unusual-time
and behavior-deviation cases, and separation of combined patterns from
high-amount cases. These terms describe synthetic scenario classes only.

## Per-class test summary

{
  "normal": {
    "f1": 0.837033,
    "precision": 0.790389,
    "recall": 0.889528,
    "support": 869
  },
  "synthetic_behavior_deviation": {
    "f1": 0.0,
    "precision": 0.0,
    "recall": 0.0,
    "support": 50
  },
  "synthetic_combined_pattern": {
    "f1": 0.0,
    "precision": 0.0,
    "recall": 0.0,
    "support": 24
  },
  "synthetic_high_amount": {
    "f1": 0.25731,
    "precision": 0.4,
    "recall": 0.189655,
    "support": 116
  },
  "synthetic_rapid_repeat": {
    "f1": 0.482412,
    "precision": 0.317881,
    "recall": 1.0,
    "support": 48
  },
  "synthetic_unusual_time": {
    "f1": 0.0,
    "precision": 0.0,
    "recall": 0.0,
    "support": 91
  }
}

## Review conclusions

- Leakage review valid: `True`.
- Validation metrics were used for review; test metrics were not used for
  fitting or model selection.
- Class imbalance makes macro F1 and per-class recall more informative than
  accuracy alone.
- Generator shortcut review: `OVERLAP_REVIEW_COMPLETED`.
- Decision: `REVISED_DATASET_READY_FOR_NEXT_ML_PHASE`.

## Limitations

The dataset contains no real fraud ground truth. Errors and metrics reflect
only controlled generator rules and cannot establish real-world detection,
prevention, savings, or risk-reduction performance.
