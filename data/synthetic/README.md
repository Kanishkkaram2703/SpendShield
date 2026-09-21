# SpendShield Synthetic Research Dataset

This directory contains the versioned, controlled synthetic dataset generated
by `ml/synthetic_dataset_generator.py`.

## Status and provenance

- `dataset_type`: `synthetic_research`
- `synthetic`: `true`
- `source_system`: `SpendShield synthetic generator`
- Dataset version: `v1`
- Generator version: `1.0.0`
- Default random seed: `20260912`
- Currency: INR only; no currency conversion is performed.

Every identifier is fictional and uses a `syn-` prefix. No real people,
accounts, cards, credentials, bank records, or production database records are
used. MongoDB and Cassandra are not read or written by the generator.

## Label semantics

The scenario labels describe intentionally generated rules: `normal`, high
amount, rapid repeat, unusual UTC time, category deviation, and a combined
synthetic pattern. They are not confirmed fraud labels, real financial-crime
labels, or real-world risk outcomes. No field named `fraud` or
`confirmed_fraud` is generated.

## Files

- `spendshield_synthetic_transactions_v1.csv`: full timestamp-sorted dataset.
- `train.csv`, `validation.csv`, `test.csv`: deterministic temporal splits.
- `dataset_manifest.json`: actual counts, ranges, provenance, field groups,
  split policy, limitations, and reproducibility metadata.
- `generation_config.json`: generation configuration and seed.
- `label_dictionary.json`: explicit meaning and limitations for every label.

The split boundaries use the first 70%, next 15%, and final 15% of the
configured 90-day UTC period. Historical user features use records available
before each transaction only. The same synthetic user may occur in multiple
time splits, which is intentional and documented in the manifest; no future
record is used to calculate a current row's history features. Audit/label
fields must not enter model features.

Regenerate and validate from the repository root with:

```text
backend\.venv\Scripts\python.exe -m ml.synthetic_dataset_generator
backend\.venv\Scripts\python.exe -m pytest ml/tests -q
```

This dataset is for controlled academic and engineering experiments only. It
must not drive production payment decisions, fraud blocking, notifications,
or model-performance claims.
