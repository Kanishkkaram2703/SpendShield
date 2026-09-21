# Evaluation Protocol Review

## Current protocol

- Existing timestamp-based train/validation/test partitions are preserved.
- Random row splitting is avoided because future observations must not enter
  the past and user history is time-dependent.
- Numeric imputation and categorical vocabularies are fit on training rows
  only.
- Validation is available for review; the test set remains a final held-out
  evaluation.
- Baseline reproduction matched the stored result: `True`.

## Metric suitability

Macro F1 and per-class precision/recall/F1 are primary because the normal
class is the majority and the combined-pattern class has only
`{'count': 19, 'percentage': 1.303155}` test rows. Accuracy is reported
for context but is insufficient by itself.

## Required before next model

1. Preserve the current temporal protocol and repeat leakage checks.
2. Review the rapid-repeat, unusual-time, and category-deviation errors.
3. Define whether a future generator revision should create overlapping normal
   behavior before comparing a more complex model.

## Useful future improvement

Evaluate repeated temporal windows or additional independent synthetic dataset
seeds after the generator design is reviewed. Do not tune against the current
test results.

## Out of current scope

Production inference, fraud/risk APIs, real-world datasets, transaction
blocking, notifications, and model deployment.

## Decision

`DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST`.

The current protocol remains blocked on generator overlap or integrity review before model complexity is increased.

Shortcut review status: `REVIEW_REQUIRED_BEFORE_COMPLEX_MODEL`.
