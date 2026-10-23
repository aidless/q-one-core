# Q-One Architecture — proposals, quantified verification, gated self-evolution

> Positioning (one sentence): **every LLM development path is a proposal generator; Q-One is the decision verifier; improvement is gated, not assumed.**

The field splits into a *proposal side* (bigger models, CoT, test-time compute, multi-agent) and a *verification side* (RLVR, process rewards, eval-gated self-improvement, calibration). The center of gravity is moving to the verification side, because proposal-side output is not directly trustworthy. Q-One is built entirely on the verification side — and its ambition is to run that verification loop on everyday decisions, not just benchmarks.

## Layers

```
┌─ Proposal layer (q-one-agent adapters) ──────────────────────────┐
│  any model · CoT · multi-agent debate · test-time search ·       │
│  fine-tuned small models · a new model release                   │
│  → every proposal becomes a STRUCTURED PREDICTION:               │
│    confidence ⊥ success-probability, with rationale + source     │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌─ Quantified verification layer (q-one-core) ─────────────────────┐
│  baseline required before any recommendation · human decision    │
│  event mandatory · append-only hash-chained ledger · reports     │
│  label their evidence status; Brier only when outcome exists     │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌─ Calibration & meta-audit layer ─────────────────────────────────┐
│  Brier/ECE feedback over time · evidence tiers (tier0–3) ·       │
│  baseline-freeze / proxy-backlash audit · proxy-divergence and   │
│  false-zero detection (a "verified safe" may be a collapsed      │
│  format — see sibling: r5-verify-vs-gate)                        │
│  Goodhart is the #1 enemy of quantify-everything systems;        │
│  auditing the quantification itself is a first-class layer       │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌─ Self-evolution gate (sibling: evoagent) ────────────────────────┐
│  a strategy/prompt/router is promoted only when it beats the     │
│  frozen baseline + min_gain on a hashed frozen benchmark, with   │
│  rollback; the "ten-round plateau" is the observable that M2     │
│  targets                                                         │
└──────────────────────────────────────────────────────────────────┘
        Memory: decision ledger (core) + personal ontology (life)
                + retrieval (paperKB, ~559k vectors)
```

## How "all current LLM development paths" plug in

| Development path | Q-One interface | Sibling repo (existing) |
|---|---|---|
| RLVR / verifiable rewards | structured prediction + outcome回流 = the reward signal | gsm8k-self-evolve (statistical gate, p=1.08e-06) |
| Eval-gated self-improvement | promotion gate + rollback | evoagent (360-task hashed registry) |
| Calibration / UQ | Brier/ECE over resolved decisions; evidence tiers | lifeplanner (188 tests) |
| Test-time compute allocation | effort allocation vs. measured divergence | agent-effort-r1 (3.44× modeled vs. measured) |
| Model routing / cost | preregistered A/B routing | scheduler (research-kit) |
| Agent memory | decision ledger as first-class memory | flowgrid-aml-retriever |
| Meta-audit of evaluators | proxy divergence + false-zero detection | r5-verify-vs-gate · approval-gates-r3 · arx |
| World models / embodied | critical companion, negative results kept | acvjepa-project · morphagent-textbook |

A new model or a new paradigm never changes the protocol — it enters as one more adapter and one more candidate at the promotion gate.

## Falsifiable milestones (the honest form of "approaching AGI")

"AGI" is not falsifiable; these are:

- **M1 — calibration improves over time.** Resolved decisions grow 20 → 200 across ≥2 domains; Brier decreases against the preregistered analysis plan (`MILESTONE1_PREREG.md`), with Wilson 95% CIs and missingness reported.
- **M2 — break the plateau.** On evoagent's frozen benchmark, a real policy (any paradigm) beats baseline + min_gain for N consecutive rounds without regression — the ten-round plateau is the standing negative result to beat.
- **M3 — cross-domain transfer without calibration collapse.** The decision protocol migrates from low-risk domains to a new domain with calibration intact (no tier-scheme re-tuning allowed mid-flight).

## Non-negotiable guardrails (inherited)

A single score is not a person's value or identity · private logs never train anything without an explicit consent/retention policy · protocol changes are dated amendments, never silent edits · reports carry denominators, exclusions, and failed runs · the human decision event cannot be removed, only annotated.
