# Initial research plan

## Research question

Can a local, append-only decision ledger make quantified-life recommendations inspectable and measurable while keeping the human responsible for consequential choices?

## Hypotheses

- **H1 — provenance:** a hash-chained event history makes it possible to reconstruct what was known, recommended, chosen, and observed.
- **H2 — calibration:** explicit probability and outcome fields make forecast quality measurable after enough resolved decisions.
- **H3 — agency:** a required baseline and human decision event make recommendation adoption visible without treating adoption as correctness.

## First milestone

Collect 20 resolved decisions across at least two low-risk domains. Keep the decision template stable during a measurement window. Record unknown and partial outcomes instead of forcing binary labels.

The milestone is a data-collection gate, not a claim that 20 observations are statistically sufficient for a general model. After the first window, review missingness, repeated decisions, outcome definitions, and whether the criteria were observable at the declared deadline.

## Metrics

- **Protocol integrity:** event count, successful hash-chain verification, and replayable state projection.
- **Process:** baseline coverage, recommendation coverage, human decision coverage, and recommendation adoption.
- **Forecasting:** Brier score and observed success rate on rows with a probability and a binary outcome; Wilson 95% interval for the latter.
- **Missingness:** fraction of decisions with no baseline, no outcome, `unknown`, or `partial` outcome.
- **Agency:** recommendation override rate, with qualitative reasons preserved.

## Guardrails

- Do not treat a single score as a person's value or identity.
- Do not train or evaluate on private logs without an explicit consent and retention policy.
- Do not compare model versions when the decision criterion, deadline, or population changed without recording the change.
- Keep a frozen export and a manifest before any analysis that may influence a product or paper.
- Report denominators, exclusions, uncertainty, and failed runs.

## Next research loop

1. Review the first 20 resolved records.
2. Freeze a v0.1 export and its hash.
3. Inspect outcome definitions and missingness.
4. Add a pre-registered comparison of baseline versus recommendation adoption only if the protocol is stable.
5. Move model routing and evidence retrieval into `q-one-agent` after the core event contract has remained backward-compatible for one release.

## Extension (2026-10-23): toward verifiable self-improvement

The long-horizon direction — running the proposal/verification loop with LLM development paths as proposal generators and Q-One as the verifier — is written down as architecture with falsifiable milestones instead of an "AGI" narrative:

- `ARCHITECTURE.md` — the three-layer loop (proposal → quantified verification → calibration/meta-audit → gated self-evolution), with a mapping from each current LLM development path to an existing sibling repo.
- `MILESTONE1_PREREG.md` — frozen pre-registration for the first-20-decisions gate (domains, metrics, analysis plan, kill criteria).
- **M1** calibration improves over time (this plan's first milestone, operationalized) · **M2** break the self-evolution plateau on a frozen benchmark · **M3** cross-domain transfer without calibration collapse.

Guardrails unchanged: private logs stay local; the human decision event is mandatory; protocol changes are dated amendments.
