# v2 Candidate Feature Matrix

This research-only matrix is built from the v2 temporal CSV files with
training-only numeric imputation and categorical vocabularies.

It contains 32 model features: the original point-in-time fields plus:

- `merchant_novelty_before`;
- `channel_novelty_before`;
- `user_relative_amount_deviation`;
- `user_relative_time_deviation`.

Each derived feature uses only records strictly earlier than the current row
under timestamp plus synthetic transaction-ID ordering. Target labels,
scenario metadata, identifiers, future values, and post-event values remain
outside the model feature list. The feature dictionary records definitions,
missing-value behavior, leakage status, and version.
