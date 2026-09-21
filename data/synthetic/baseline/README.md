# Research-Only Baseline Results

`research_baseline_results.json` contains the measured result of the first
fixed multiclass synthetic-scenario experiment.

Evaluated baselines:

1. Majority-class reference.
2. Deterministic Gaussian Naive Bayes over the 28 train-fitted features.

The model is fit on `train`, validation is reported without test tuning, and
`test` is evaluated once as the final temporal holdout. The result is not a
fraud detector, production model, fraud API, risk score, transaction blocker,
or real-world performance claim. No model artifact or inference service is
written.
