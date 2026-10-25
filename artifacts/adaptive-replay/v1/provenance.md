# adaptive-replay v1

Date: 2026-10-25. Producer: Codex, Q-One kernel implementation.

Tool-specific artifact_save was unavailable; this archive follows the same versioned file/manifest contract directly.

Command: `python scripts/evaluate_life_kernel.py`. Seeds: 17, 29, 41; 96 entirely synthetic episodes per seed. Features, priors, thresholds and event/knowledge-time rules are frozen in the included sources and example.

The output records per-observation errors and densities. Source and output SHA-256 values and Python/NumPy/SciPy versions are in the manifests. Reproduction hashes require the recorded runtime; numerical equality across different BLAS/software builds is not asserted.

This is an engineering fixture designed around the model family. No real user data, policy value, causal effect or life benefit is established. The broad intervals over-cover this fixture; this is not evidence of calibrated uncertainty.
