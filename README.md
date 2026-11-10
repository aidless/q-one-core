# Q-One Core

[![CI](https://github.com/aidless/q-one-core/actions/workflows/checks.yml/badge.svg)](https://github.com/aidless/q-one-core/actions/workflows/checks.yml)

**中文文档：[README.zh-CN.md](README.zh-CN.md)**（完整中文版）

> **English TL;DR**: Q-One Core is the first repository of a three-part system for quantifying decisions: it records explicit variables, the pre-recommendation baseline, and the human decision in an append-only, hash-chained JSONL ledger, then compares agent predictions with observed outcomes. Run via a local CLI (`qone init` through `qone report`). It deliberately stays a small local protocol — recommendations always require a recorded baseline and a human final choice, and it does not automate consequential decisions.

> Research entry points: [multi-discipline synthesis blueprint](docs/SYNTHESIS.md) · v0.2 connects to the full personal application; [usage entry and acceptance](https://github.com/aidless/q-one-life).

Q-One Core is the first repository in a three-part open-source system for **“万事万物皆可量化”**: turn a decision into explicit variables, record what was known before an agent recommendation, preserve the human decision, and later compare the prediction with the observed outcome.

This repository deliberately starts with a small, local protocol. It does not claim that a score is a complete model of a person, and it does not automate consequential decisions.

## The three repositories

| Repository | Responsibility | Data boundary |
| --- | --- | --- |
| `q-one-core` | Decision schema, append-only ledger, safety gates, reports | Local JSONL; no provider credentials |
| `q-one-agent` | Model/tool adapters, retrieval, routing, evidence capture | Reads/writes the core protocol through an adapter |
| `q-one-life` | Personal ontology, reviews, local UI and integrations | User-owned private data; export is explicit |

`DecisionService` provides transactional product transitions: validation and append share one writer lock. The low-level `Ledger.append` remains a trusted-import primitive and does not enforce product transitions. These repositories are internal packages of one Q-One application, not three independent product implementations.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .

qone --data-dir .qone-data init
qone --data-dir .qone-data create --file examples/decision.json
qone --data-dir .qone-data baseline --decision D-YYYYMMDD-xxxxxx --option draft --note "human baseline"
qone --data-dir .qone-data recommend \
  --decision D-YYYYMMDD-xxxxxx --option draft \
  --confidence 0.82 --success-probability 0.70 \
  --rationale "The criterion rewards an early reviewable artifact." \
  --source "local-rule-v0.1"
qone --data-dir .qone-data decide --decision D-YYYYMMDD-xxxxxx --option draft --by human
qone --data-dir .qone-data resolve --decision D-YYYYMMDD-xxxxxx --success yes --notes "A reviewable draft was ready."
qone --data-dir .qone-data verify
qone --data-dir .qone-data report
```

The generated decision ID is printed by `create`; use it in subsequent commands. The example deadline is illustrative and should be edited for the date on which you run it.

### Verified on 2026-11-10 (fresh venv, `pip install -e .`)

```text
$ qone --data-dir .qone-demo init
initialized .qone-demo/ledger.jsonl (0 events)
$ qone --data-dir .qone-demo create --file examples/decision.json
D-20261110-6a4e5d
$ qone ... baseline / recommend / decide / resolve    (each prints one confirmation line)
$ qone --data-dir .qone-demo verify
verified 5 events
$ qone --data-dir .qone-demo report
ledger events: 5
decisions: 1 (1 resolved) / baselines: 1 / recommendations: 1 / human decisions: 1
recommendation adoption: 1.0
evidence status: descriptive_with_outcomes
calibration n: 1  calibration excluded: 0
brier score: 0.09
observed success rate: 1.0
```

## Results

| Check | Number | Command (2026-11-10) |
|---|---|---|
| CI test suite | **79 passed + 4 subtests** (13.1 s) | `pip install ".[adaptive]" pytest && python -m pytest -q` |
| Quickstart end-to-end | 5-event ledger verifies clean; report emits `descriptive_with_outcomes`, Brier 0.09 on the single resolved toy outcome | the `qone` sequence above |

The Brier 0.09 comes from one toy decision resolved as success against a 0.70
success probability — it demonstrates the scoring path, not calibration skill.

## Protocol properties

- Every event is one JSON object on one line.
- Each event contains a sequence number, UTC timestamp, previous hash, and SHA-256 hash of its canonical content.
- A recommendation requires a recorded baseline and always leaves the final choice to a human.
- Confidence and success probability are separate fields. Confidence describes how strongly the agent prefers its recommendation; success probability describes the predicted chance of meeting the declared criterion.
- Reports label their evidence status and only compute Brier score when a probability and a binary outcome are both present.

See [docs/PROTOCOL.md](docs/PROTOCOL.md) for the event contract and [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) for the first measurement plan.

## Evidence boundary

The ledger is an audit and measurement mechanism. It is not a clinical instrument, a financial adviser, a psychological diagnosis, or proof that life outcomes can be reduced to one scalar. Any personal calibration result must be treated as descriptive until there is enough frozen data, a defined protocol, and an independent review.

Do not commit personal decision logs, API keys, model outputs containing private data, or raw exports. The default data directory `.qone-data/` is ignored by Git.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), keep protocol changes versioned, preserve failed or unknown outcomes, and describe evidence limits in pull requests. This project is released under the MIT License.

## Life-decision kernel 0.3

Adds personal state with measurement semantics, a goal tree, value ordering,
resource accounts, delayed scenarios, multi-objective comparison, and a
Bayesian change predictor that learns from pre-/post-action observations.
Currently validated on **synthetic replay only** — it does not represent
real-life benefit.

- [Kernel documentation](docs/LIFE_KERNEL.zh-CN.md)
- [Advanced technical blueprint and integration conditions](docs/ADVANCED_ROADMAP.zh-CN.md)
- [Per-item synthetic-replay evidence](docs/evidence/adaptive-synthetic.json)
- [Runnable model example](examples/adaptive.synthetic.json)

Install the predictive components with `pip install '.[adaptive]'`;
reproduce with `python scripts/evaluate_life_kernel.py`.

## Online-calibration shadow evaluation 0.4

Adds delayed-outcome calibration credentials, calibration candidates grouped
by action composition, and frozen stable/abrupt controls. The candidate
**failed every adoption condition and stays in shadow evaluation**; the
intervals used for automatic recommendations are unchanged.

[Experiment and adoption decision](docs/CALIBRATION_EVALUATION.zh-CN.md) · [frozen protocol and per-item evidence](artifacts/calibration-evaluation/v1/) · [official-source probes](literature/calibration-source-probes.json)

## Non-stationary forecasting research: calendar-recency candidate

Adds an independent prototype that forgets by outcome time, plus frozen
controls for mean/noise shifts, irregular observations, and delayed outcomes.
The candidate **failed the adoption conditions on both the stable and the
sparse scenarios**; the full failure results are retained and the
auto-recommendation kernel stays on the previous version.

[Evaluation results, limits, reproduction](docs/RECENCY_EVALUATION.zh-CN.md) · [protocol and per-item evidence](artifacts/recency-evaluation/v1/) · [official-source probes](literature/recency-source-probes.json)

## Two-timescale research: long-run structure vs short-term drift

Adds an independent prototype that preserves action/context structure and
projects short-term drift along calendar time, with historical reconstruction
of late-arriving outcomes; plus an artifact-audit tool that accounts the
prediction denominator, per-item scoring, and adoption decisions. The
candidate **failed all stable/change counterexamples and remains
research-only**.

[Frozen evaluation and limits](docs/TWO_SCALE_EVALUATION.zh-CN.md) · [inputs, sources and per-item evidence](artifacts/two-scale-evaluation/v1/) · [official-source probes](literature/two-scale-source-probes.json)

## Evidence eligibility gate 0.4.1

Training and replay now exclude unresolved conflicts at the same data point,
explicitly superseded older observations, and pre-action references that were
not current when the action started; exclusion reasons and the
`available_n/trainable_n/excluded_n` counts are retained. Conflicts registered
in the future do not rewrite predictions already issued, and the kernel
continues to refuse recommendations when samples are too few.

[Rules, frozen counterexamples and limits](docs/EVIDENCE_GATE.zh-CN.md) · [protocol, baselines and candidates](artifacts/evidence-gate/v1/) · [source probes](literature/evidence-gate-source-probes.json)
