# SpendShield v2 Research-Only Anomaly Evaluation

This report evaluates anomaly ranking against intentionally generated synthetic scenarios only.
It is not real-world fraud detection, a production risk score, or a payment decision.

## Model

- Model: `robust_mad_distance`
- Model version: `1.0.0`
- Seed: `20260913`
- Model features: `12` numeric/prior-only fields
- Fit protocol: training split only; labels and scenario metadata excluded from fitting.
- Higher normalized `anomaly_score` means more anomalous under this research model.

## Thresholds

Thresholds are fixed training-score percentiles (90th, 95th, and 99th). They are not decision thresholds.

## Validation and test summary

### Validation

- Rows: 1474; score min/median/mean/p95/max: 0.070426/0.210498/0.234781/0.45767/0.885543
- Synthetic-only ROC-AUC: `0.562733`; average precision: `0.417902`.
- Top-k composition, scenario coverage, normal representation, and threshold tables are in the JSON artifact.

### Test

- Rows: 1198; score min/median/mean/p95/max: 0.071109/0.216859/0.237656/0.446533/0.877492
- Synthetic-only ROC-AUC: `0.553095`; average precision: `0.367124`.
- Top-k composition, scenario coverage, normal representation, and threshold tables are in the JSON artifact.

## Explainability

- Explanation version: `1.0.0`
- Bounded samples: `20` test rows.
- Validation: `True`.
- Explanations use observed amount, timing, prior-only history, novelty, and missing-history signals.

## Limitations

- Synthetic scenarios are not real ground truth and may be easier to separate than real behavior.
- Normal and synthetic patterns overlap; score ranking is not a certainty measure.
- Thresholds are fixed research percentiles and were not selected with test labels.
- Explanation components are deterministic signal summaries, not causal explanations.
- No production inference, backend integration, payment control, database write, or deployed model was created.
