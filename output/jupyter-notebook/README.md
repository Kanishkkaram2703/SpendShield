# SpendShield notebook foundation

The first notebook is an evidence audit, not a model-training notebook:

01_dataset_audit.ipynb

Run from the repository root with:

jupyter nbconvert --to notebook --execute --inplace output/jupyter-notebook/01_dataset_audit.ipynb

The notebook reads the configured MongoDB transaction collection and does not write database state. It reports INSUFFICIENT_DATA when no completed transactions exist and never fabricates labels or metrics.

## Controlled synthetic research dataset

The operational collection is currently empty, so the separate synthetic
dataset foundation is implemented without touching MongoDB or Cassandra:

- `02_generate_synthetic_dataset.ipynb` generates the bounded dataset under
  `data/synthetic/`;
- `03_validate_synthetic_dataset.ipynb` validates schema, provenance,
  leakage boundaries, temporal splits, manifest consistency, and
  same-seed reproducibility.

The generated labels describe synthetic generator scenarios only. They are not
fraud labels and must not be used for production decisions.

## Feature matrix and baseline

- `04_candidate_feature_matrix.ipynb` builds and validates the 28-feature
  train-fitted matrix under `data/synthetic/features/`.
- `05_first_research_baseline.ipynb` evaluates the majority reference and the
  fixed Gaussian Naive Bayes baseline under `data/synthetic/baseline/`.

Both notebooks use temporal partitions and keep the scenario target separate
from model inputs. Their metrics apply only to synthetic scenario
classification.

## Controlled error analysis

- `06_error_analysis.ipynb` reproduces the fixed Gaussian Naive Bayes
  baseline, exports bounded validation/test error artifacts, reviews class
  imbalance and generator shortcuts, and performs leakage/protocol checks.

Run from the repository root with:

```text
python -m nbconvert --to notebook --execute output/jupyter-notebook/06_error_analysis.ipynb --output 06_error_analysis.executed.ipynb
```

The notebook is research-only. Its decision is
`DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST`; it does not modify the dataset
or generator and does not produce fraud, risk, payment, or production ML
claims.

## Versioned generator revision and comparison

- `07_revised_dataset_generation.ipynb` generates isolated synthetic v2.
- `08_revised_dataset_validation.ipynb` validates v2 and builds the 32-feature
  prior-only candidate matrix.
- `09_revised_baseline_evaluation.ipynb` reruns the majority and fixed
  Gaussian Naive Bayes protocol plus controlled error analysis.
- `10_dataset_version_comparison.ipynb` compares preserved v1 with v2 across
  distributions, shortcuts, metrics, per-class recall, leakage, temporal
  integrity, and reproducibility.

The final v2 decision is `REVISED_DATASET_READY_FOR_NEXT_ML_PHASE`. This is a
research-data decision only; labels remain synthetic scenarios and no notebook
creates production inference, fraud decisions, payment controls, or database
writes.

## Research-only anomaly detection and explanations

- `11_anomaly_detection_evaluation.ipynb` runs the v2 train-only robust-MAD
  anomaly ranking experiment and reports validation/test synthetic-label
  ranking analysis, top-k composition, scenario coverage, normal overlap, and
  train-percentile research thresholds.
- `12_explainability_evaluation.ipynb` validates bounded deterministic
  explanations against the available feature contract and forbidden-language
  rules.

Artifacts are under `data/synthetic/anomaly_detection/v2/`. The project test
environment does not include scikit-learn, so the primary model is the
documented dependency-free robust statistical fallback. These notebooks do
not create production inference, fraud/risk APIs, payment controls, database
writes, or human decisions. Their final phase decision is
`ANOMALY_EVALUATION_READY_FOR_BACKEND_RESEARCH_INTEGRATION`.
