# SpendShield Synthetic Research Dataset v2

This is the preserved project's revised synthetic dataset artifact.

- Dataset version: `v2`
- Generator version: `1.1.0`
- Seed: `20260913`
- Rows: 10,000
- Users/accounts: 500
- Merchants: 100
- Categories: 12
- Currency: INR only

Version 2 retains six generator-defined scenario classes but introduces
behavioral overlap: normal rows can be late, expensive, repetitive, or
category-variable; scenario rows use mixtures of moderate and strong signals;
and combined rows do not always share one fixed combination.

The manifest contains the exact distribution, temporal split, provenance,
limitations, and SHA-256 hashes. The full CSV and split files are fictional
research data only. They are not fraud labels, real financial-crime data, or
production decisions. No MongoDB or Cassandra records were created.

The next artifacts are under `features/`, `baseline/`, `error_analysis/`, and
the v1/v2 comparison is under `../comparison/`.
