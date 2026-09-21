# v2 Controlled Error Analysis

This directory contains the same bounded error-analysis workflow used for v1:
confusion matrices, per-class metrics, safe misclassified test records,
validation-only feature distributions, shortcut review, leakage review, and
evaluation-protocol review.

The v2 review found reduced exact-rule prevalence and passed reproducibility,
temporal, and leakage checks. The Gaussian baseline remains weak on several
overlapping classes; this is reported as a research limitation rather than
hidden through accuracy-only reporting.
