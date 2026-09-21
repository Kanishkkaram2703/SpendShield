# SpendShield Synthetic Dataset Version Comparison

## Decision

`REVISED_DATASET_READY_FOR_NEXT_ML_PHASE`

## Version summary

| Field | v1 | v2 |
|---|---:|---:|
| Dataset version | v1 | v2 |
| Generator version | 1.0.0 | 1.1.0 |
| Feature version | 1.0.0 | 1.1.0 |
| Baseline version | 1.0.0 | 1.1.0 |
| Seed | 20260912 | 20260913 |
| Rows | 10000 | 10000 |
| Test rows | 1458 | 1198 |
| Feature count | 28 | 32 |

## Baseline comparison

- Validation macro F1: `0.651481` -> `0.268254` (delta `-0.383227`).
- Test macro F1: `0.617953` -> `0.262793` (delta `-0.35516`).
- Test weighted F1: `0.850388` -> `0.651407` (delta `-0.198981`).
- False-positive rate against normal: `0.04682` -> `0.110472`.

The revised baseline is intentionally interpreted together with overlap and
protocol evidence. It is not a real-world fraud-performance comparison.

## Test per-class recall

| Class | v1 | v2 |
|---|---:|---:|
| normal | 0.95318 | 0.889528 |
| synthetic_behavior_deviation | 0.222222 | 0.0 |
| synthetic_combined_pattern | 0.368421 | 0.0 |
| synthetic_high_amount | 0.719298 | 0.189655 |
| synthetic_rapid_repeat | 1.0 | 1.0 |
| synthetic_unusual_time | 0.285714 | 0.0 |

## Shortcut comparison

| Pattern | v1 validation evidence | v2 validation evidence |
|---|---|---|
| behavior_deviation_candidate_signal_coverage | `{}` | `{'normal': 0.937049, 'synthetic_behavior_deviation': 0.976744, 'synthetic_combined_pattern': 1.0, 'synthetic_high_amount': 0.96988, 'synthetic_rapid_repeat': 0.983871, 'synthetic_unusual_time': 0.929293}` |
| combined_fixed_high_time_and_rapid_pattern | `{'normal': 0.0, 'synthetic_behavior_deviation': 0.0, 'synthetic_combined_pattern': 0.0, 'synthetic_high_amount': 0.0, 'synthetic_rapid_repeat': 0.0, 'synthetic_unusual_time': 0.0}` | `{'normal': 0.0, 'synthetic_behavior_deviation': 0.0, 'synthetic_combined_pattern': 0.0, 'synthetic_high_amount': 0.0, 'synthetic_rapid_repeat': 0.0, 'synthetic_unusual_time': 0.0}` |
| high_amount_relative_to_prior_average_at_least_3x | `{'normal': 0.00089, 'synthetic_behavior_deviation': 0.0, 'synthetic_combined_pattern': 0.62963, 'synthetic_high_amount': 0.65812, 'synthetic_rapid_repeat': 0.0, 'synthetic_unusual_time': 0.0}` | `{'normal': 0.009288, 'synthetic_behavior_deviation': 0.05814, 'synthetic_combined_pattern': 0.0, 'synthetic_high_amount': 0.072289, 'synthetic_rapid_repeat': 0.016129, 'synthetic_unusual_time': 0.0}` |
| missing_previous_transaction_history | `{'normal': 0.0, 'synthetic_behavior_deviation': 0.0, 'synthetic_combined_pattern': 0.0, 'synthetic_high_amount': 0.0, 'synthetic_rapid_repeat': 0.0, 'synthetic_unusual_time': 0.0}` | `{'normal': 0.0, 'synthetic_behavior_deviation': 0.0, 'synthetic_combined_pattern': 0.0, 'synthetic_high_amount': 0.0, 'synthetic_rapid_repeat': 0.0, 'synthetic_unusual_time': 0.0}` |
| preferred_category_not_observable | `{}` | `{}` |
| rapid_repeat_test_recall | `{'test_recall': 1.0}` | `{'test_recall': 1.0}` |
| rapid_repeat_window_at_most_600_seconds | `{'normal': 0.0, 'synthetic_behavior_deviation': 0.0, 'synthetic_combined_pattern': 0.0, 'synthetic_high_amount': 0.0, 'synthetic_rapid_repeat': 1.0, 'synthetic_unusual_time': 0.0}` | `{'normal': 0.034056, 'synthetic_behavior_deviation': 0.011628, 'synthetic_combined_pattern': 0.1, 'synthetic_high_amount': 0.036145, 'synthetic_rapid_repeat': 0.233871, 'synthetic_unusual_time': 0.010101}` |
| unusual_utc_hour_window | `{'normal': 0.0, 'synthetic_behavior_deviation': 0.0, 'synthetic_combined_pattern': 1.0, 'synthetic_high_amount': 0.0, 'synthetic_rapid_repeat': 0.089888, 'synthetic_unusual_time': 1.0}` | `{'normal': 0.246646, 'synthetic_behavior_deviation': 0.302326, 'synthetic_combined_pattern': 0.166667, 'synthetic_high_amount': 0.277108, 'synthetic_rapid_repeat': 0.274194, 'synthetic_unusual_time': 0.333333}` |

The v2 shortcut review status is `OVERLAP_REVIEW_COMPLETED`. The exact
global-hour and <=600-second patterns were reduced rather than treated as
required labels. The complete comparison remains in
`v1_vs_v2_comparison.json`.

## Integrity

- Reproducibility: v1=`True`, v2=`True`.
- Leakage review: v1=`True`, v2=`True`.
- Temporal splits remain chronological and non-overlapping by transaction ID.

## Limitations

Both datasets are fictional, synthetic research artifacts. Neither establishes
fraud detection, financial-crime detection, production accuracy, prevention,
savings, or risk reduction.
