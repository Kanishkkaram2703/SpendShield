# SpendShield v2 research-only anomaly detection

This directory contains a deterministic robust-MAD anomaly experiment, a transparent weighted signal baseline, synthetic-label offline evaluation, bounded research explanations, and serialized fitted parameters for the read-only backend research integration.

The model is fit on v2 training features only. Synthetic scenario labels are never used for fitting, threshold selection, or explanation generation. Higher normalized `anomaly_score` means more anomalous within this model configuration. The artifacts are not real fraud detection, are not production inference, and do not write to backend databases or control payments. The backend may load these artifacts only for owner-scoped research reads when the approved live feature contract is available.
