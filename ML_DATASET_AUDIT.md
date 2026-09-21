# SpendShield ML Dataset Audit - 2026-09-12

## Result

The first evidence-driven ML audit is complete. The live MongoDB development database was reachable at the configured rs0 primary, but the spendshield.transactions collection currently contains:

- total transaction documents: 0;
- completed transaction documents: 0;
- candidate fraud/review labels: 0;
- earliest/latest completed timestamps: unavailable.

This is an INSUFFICIENT_DATA result, not a model failure. No training, inference, accuracy, fraud decision, or risk claim was produced.

## Source and ownership

The proposed dataset source is MongoDB.transactions, filtered to completed current transaction documents. MongoDB remains authoritative for current operational state. Cassandra remains historical event storage and is not used to reconstruct balances or create a competing current-state training table.

The observed operational data provenance is labelled APPLICATION_OPERATIONAL_DATA. It is not a real-world banking dataset and it does not provide fraud ground truth.

## Dataset contract

The unit of analysis is one COMPLETED transaction. Candidate observable features are amount, currency, timestamp, merchant identity/name, and payment-time category/subcategory snapshots. Transaction, account, and user identifiers are traceability fields, not automatic predictive evidence.

The following are excluded from point-in-time features because they may contain outcome or future information:

- status history;
- balance after the transaction;
- updated timestamps;
- failure details;
- event/publication identifiers;
- investigator or human-review outcomes.

The current operational documents contain no verified fraud or human-review target. Transaction status is an operational state, not a fraud label.

## Baseline boundary

Current status: MongoDB dependency AVAILABLE; completed records 0; verified target NOT AVAILABLE; baseline BLOCKED_INSUFFICIENT_DATA; metrics NONE.

No synthetic records were inserted into MongoDB. A future synthetic or public dataset must be explicitly labelled by provenance and kept separate from operational state.

## Reproducible artifact

Run output/jupyter-notebook/01_dataset_audit.ipynb. The notebook performs read-only source inspection, schema/label checks, provenance recording, leakage-boundary definition, and the baseline readiness decision. It does not write database state.

## Exact next dependency

The controlled synthetic dataset foundation is now available separately under
`data/synthetic/`. The next dependency is to build a deterministic feature
matrix from candidate fields only and evaluate a clearly research-only
baseline; no result may be interpreted as real-world fraud performance.

## Controlled synthetic research dataset - 2026-09-12

Because the operational collection was empty, a separate reproducible dataset
was generated without reading or writing MongoDB or Cassandra. It is marked
`dataset_type=synthetic_research`, `synthetic=true`, and uses only fictional
`syn-*` identifiers.

Actual generated values:

- 10,000 rows;
- 500 users and 500 accounts;
- 100 merchants and 12 categories;
- INR-only timestamps from `2024-01-01T00:05:35Z` through
  `2024-03-30T23:55:20Z` within a configured 90-day UTC period;
- scenario counts: 7,600 normal, 800 synthetic high amount, 600 synthetic
  rapid repeat, 600 synthetic unusual time, 300 synthetic behavior deviation,
  and 100 synthetic combined pattern;
- temporal split counts: 7,061 train, 1,481 validation, and 1,458 test.

The complete contract and limitations are in
`data/synthetic/dataset_manifest.json` and `data/synthetic/README.md`. Scenario
labels are generated-rule labels only; they are not confirmed fraud labels,
real financial-crime labels, or production decisions. Candidate features,
audit-only fields, and forbidden fields are explicitly separated in the
manifest.

Generation and validation are available through:

- `ml/synthetic_dataset_generator.py`;
- `output/jupyter-notebook/02_generate_synthetic_dataset.ipynb`;
- `output/jupyter-notebook/03_validate_synthetic_dataset.ipynb`.

## Candidate feature matrix and first baseline - 2026-09-12

The next research-only step is complete. The feature matrix is generated from
the synthetic CSV files only and is stored under `data/synthetic/features/`.
It contains 28 model features: numeric transaction/history fields plus a
missingness indicator, and one-hot currency, merchant-category, and
transaction-channel fields. Numeric imputation and categorical vocabularies
are fitted on training rows only, with explicit unknown buckets.

The target is multiclass `scenario_label`, exposed separately as
`target_scenario_label`. It is not included in the model feature list. No
binary fraud-like target was created.

Measured temporal results:

- Majority reference: test accuracy `0.776406`, macro F1 `0.145688`.
- Gaussian Naive Bayes: validation accuracy `0.868332`, macro F1 `0.651481`;
  test accuracy `0.862826`, macro F1 `0.617953`, weighted F1 `0.850388`.

These metrics measure classification of intentionally generated synthetic
scenarios only. They do not measure fraud detection, fraud prevention,
financial savings, risk reduction, or production performance. Complete
per-class metrics and confusion matrices are stored in
`data/synthetic/baseline/research_baseline_results.json`.

The next dependency is controlled error analysis and evaluation-protocol
review before any more complex model or model-export phase.

## Controlled Error Analysis and Evaluation-Protocol Review - 2026-09-12

The stored Gaussian Naive Bayes baseline was reproduced before inspecting
errors. Reproduction matched the stored feature names, target, seed, model
results, and data-usage metadata. The final held-out test result remains
accuracy `0.862826`, macro F1 `0.617953`, and weighted F1 `0.850388`.

The test confusion/error review found 131 false negatives for synthetic
pattern classes, 53 false positives against `normal`, and 16 confusions
between synthetic scenarios. Test per-class recall was `1.0` for
`synthetic_rapid_repeat`, `0.285714` for `synthetic_unusual_time`, `0.222222`
for `synthetic_behavior_deviation`, and `0.368421` for the rare
`synthetic_combined_pattern` class. These are generator-scenario findings,
not fraud findings.

The validation-only shortcut review found that every validation
`synthetic_rapid_repeat` row met the generated <=600-second interval rule,
and every validation `synthetic_unusual_time` and
`synthetic_combined_pattern` row was in the configured unusual UTC-hour
window. This may make those labels directly recoverable from observable
features. The generator was not modified.

The leakage and temporal review passed: prior-only history, deterministic
timestamp/ID ordering, training-only preprocessing, target/metadata
exclusion, test isolation, and timestamp partitions were all preserved. The
full class distribution is 76% `normal` versus 1% combined pattern; therefore
macro/per-class metrics are more informative than accuracy alone.

Added:

- `ml/error_analysis.py`;
- `ml/tests/test_error_analysis.py`;
- `data/synthetic/error_analysis/` reports and machine-readable artifacts;
- `output/jupyter-notebook/06_error_analysis.ipynb`.

The explicit decision is `DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST`.
No complex model, model artifact, production inference, fraud/risk API,
blocking, notification, payment behavior, backend code, or database state was
changed.

## Versioned Synthetic Generator Revision and Re-evaluation - 2026-09-12

Version 1.0.0 was not sufficient for the next ML phase because exact generator
rules made rapid-repeat and unusual-time scenarios too easy to recover, while
behavior-deviation lacked explicit user-relative candidate signals.

Version 1.1.0 creates a separate `data/synthetic/v2/` artifact using seed
`20260913`. It preserves 10,000 rows, 500 users, 100 merchants, 12
categories, INR-only values, six generator-defined scenario classes, and
timestamp-based evaluation. The distribution is 6,800 normal, 1,000
high-amount, 800 rapid-repeat, 700 unusual-time, 500 behavior-deviation, and
200 combined-pattern rows. Temporal files contain 7,328 train, 1,474
validation, and 1,198 test rows.

The feature matrix now contains 32 fields, adding prior-only merchant novelty,
channel novelty, user-relative amount deviation, and user-relative time
deviation. The feature dictionary documents each definition and missing-value
policy; no target or scenario metadata was added to model inputs.

Validation-only shortcut rates in v2 are no longer near-perfect: rapid-repeat
rows in the <=600-second window are `0.233871`, unusual-time rows in the fixed
global-hour window are `0.333333`, and combined-pattern rows in that window
are `0.166667`; the combined fixed late-hour + <=600-second + >=3x amount
rule rate is `0.0`. Normal overlap is measurable: normal late-hour prevalence is
`0.246646` and normal <=600-second prevalence is `0.034056`. Candidate-signal
coverage for behavior-deviation is `0.976744`.

The same Gaussian Naive Bayes baseline was re-run without test tuning. v2
test accuracy is `0.703673`, macro F1 `0.262793`, and weighted F1 `0.651407`.
These are lower than v1 because the revised task is harder and more
overlapping; higher accuracy was not used as the quality criterion. v2 has
valid reproducibility, checksums, temporal integrity, leakage review, and
meaningful test support for every class.

The exact decision is `REVISED_DATASET_READY_FOR_NEXT_ML_PHASE`. This means
the artifact is suitable for controlled research-only anomaly-detection and
explainability work; it does not authorize production inference or fraud
claims. No MongoDB/Cassandra/backend/payment/frontend change was made.

## Controlled Research-Only Anomaly Detection and Explainability - 2026-09-12

The approved v2 feature matrix was evaluated with a dependency-free robust
median-absolute-deviation distance model because the established project test
environment does not include scikit-learn. The model is fit on the 7,328-row
training split only, uses 12 numeric/prior-only features, and retains no
identifier, split, target, scenario metadata, future field, or post-event field
as a model input. A fixed weighted signal baseline is also written for
transparent comparison; its weights are research assumptions, not label-fitted
parameters.

The normalized `anomaly_score` is min-max derived from training raw robust
distances and clipped to `[0, 1]`; higher means more anomalous within this
dataset/model configuration. Thresholds are fixed training score percentiles
(90th `0.518579`, 95th `0.740225`, 99th `0.787968`) and are explicitly not
decision thresholds or probabilities. Scores are not claimed comparable across
dataset versions without recalibration.

Validation score distribution is min/median/mean/p95/max
`0.070426/0.210498/0.234781/0.457670/0.885543`; test is
`0.071109/0.216859/0.237656/0.446533/0.877492`. Synthetic-label binary
ranking analysis is ROC-AUC/AP `0.562733/0.417902` on validation and
`0.553095/0.367124` on test. These are weak, synthetic-only ranking results,
not real-world detection metrics. Normal rows remain represented in the top
ranked records. All five non-normal scenario classes appear in both
validation/test top-10% groups; the test top-5% contains all five, while the
validation top-5% contains four of five. This demonstrates overlap rather than
certainty.

Deterministic research explanations are generated from amount, timing,
prior-only history, novelty, rapid-repeat, and missing-history signals. A
bounded 20-row test sample passed feature-reference, forbidden-language,
scenario-label, generator-rule, missing-history, and deterministic-output
checks. Artifacts are under `data/synthetic/anomaly_detection/v2/`; notebooks
11 and 12 reproduce the run. No backend, database, payment, model-serving,
or production inference change was made.

The exact phase decision is
`ANOMALY_EVALUATION_READY_FOR_BACKEND_RESEARCH_INTEGRATION`. This permits only
the next read-only, explicitly non-production research integration step; it is
not approval for financial decisions or payment controls.
