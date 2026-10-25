# calibration-evaluation v1

Date: 2026-10-25. Producer: Codex, Q-One project iteration.

Protocol was saved before the first benchmark, with seeds 17/29/41, three scenarios, 128 episodes, evaluation from episode 64, a fixed rolling score window and fixed adoption thresholds. It is a local protocol freeze, not external preregistration.

Command: `python scripts/evaluate_calibration.py`. Source, generator, protocol, results, per-prediction JSONL and input hashes are included. Python/NumPy/SciPy versions are recorded. Restore these files to their recorded project paths to reproduce; portable bit equality across software/BLAS versions is not asserted.

Both new candidates failed the full default-adoption gate. Stable-case improvements do not override shifted-case failures. Production bounds and recommendations remain on the original Student-t path; the optional layer is diagnostic only. Repeating the benchmark after this isolation yielded byte-identical result and prediction hashes.

No third-party source copied; methods independently implemented from the ACI equation. MAPIE, SAOCP and SI-OCP are research references with separately recorded reading and license boundaries. No personal outcomes, policy benefit, causality, theoretical coverage transfer or SOTA status is established.
