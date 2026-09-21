# Controlled Error Analysis Artifacts

This directory contains research-only analysis of the fixed synthetic
scenario-classification baseline. It does not contain a production model,
fraud decision, payment decision, or database state.

## Reproduce

From the repository root:

```text
backend\\.venv\\Scripts\\python.exe -m ml.error_analysis
```

The analysis re-runs the stored standard-library Gaussian Naive Bayes
baseline, writes validation and test confusion matrices and per-class
metrics, exports at most 200 bounded misclassified test records, and performs
validation-only feature distribution, shortcut, leakage, temporal, and
protocol reviews.

## Interpretation boundary

The target classes are generator scenarios, not fraud labels. The test set is
not used for fitting or model selection. `DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST`
is the current decision: review overlap and generator semantics before adding
model complexity.
