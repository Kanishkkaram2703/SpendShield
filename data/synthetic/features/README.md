# Candidate Feature Matrix

This directory contains the deterministic, research-only feature matrix built
from `../spendshield_synthetic_transactions_v1.csv`.

## Files

- `candidate_features_train.csv`
- `candidate_features_validation.csv`
- `candidate_features_test.csv`
- `feature_manifest.json`
- `feature_dictionary.json`

The matrix has 28 model features. Audit columns retain the synthetic
transaction ID, synthetic user ID, timestamp, and split. The separate
`target_scenario_label` column is retained for research evaluation but is not
part of the model feature list.

Numeric fields use medians fitted from training rows only. Categorical fields
use one-hot encoding fitted from training categories plus an explicit unknown
bucket. Historical source fields are audited using timestamp ascending and
synthetic transaction ID ascending; the current row is excluded from every
historical aggregate.

No scenario metadata, target-derived value, future statistic, or post-event
outcome is a model input. This artifact is not production-ready.
