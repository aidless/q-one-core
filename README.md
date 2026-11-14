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

## 复算（可复现）

```bash
# 1) 单元测试：需要包可导入（qone_core）
python3 -m venv /tmp/qone-venv            # 注意：工作区路径含 ":"（如 F:\deepseek），venv 须建在无冒号路径
/tmp/qone-venv/bin/pip install -e . pytest numpy scipy
/tmp/qone-venv/bin/python -m pytest tests/ -q     # 期望：79 passed (+4 subtests)

# 2) 各评测/复现脚本（合成回放与工件审计）
python3 scripts/evaluate_life_kernel.py           # 0.3 人生决策内核
python3 scripts/evaluate_calibration.py           # 0.4 校准影子评测
python3 scripts/evaluate_recency.py               # 非平稳预测研究
python3 scripts/evaluate_two_scale.py             # 双时间尺度研究
python3 scripts/evaluate_evidence_gate.py         # 0.4.1 证据资格门
python3 scripts/verify_predictive_artifact.py     # 工件审计（核算预测分母/逐条评分）
```

> 若重算结果与 README 各节不符，先 `git diff` 检查 `src/` 与 `artifacts/` 是否被改动，不要直接改结论数字。所有评测采用**合成回放**（`artifacts/` 内逐条证据 JSON），不代表真实人生收益——见下方「证据资格门 0.4.1」与各评测限制。

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

## 验收标准与复算

本仓判为合格的条件是 `python3 eval/run_cases.py` 通过率必须为 100%（20/20），且 `make eval` 退出码必须为 0；任何一条失败即判为不合格。

题库 `eval/cases.jsonl` 共 20 条，每条都是**真调本仓 API 或真读本仓数据文件**（不 mock），期望值现算自当前源码。

| axis | 条数 | 判什么 |
| --- | --- | --- |
| models/decision | 3 | `validate_decision` 的 2–8 选项约束、选项 id 唯一性、`examples/decision.json` 真解析 |
| models/recommendation | 2 | `confidence` 值域校验、`auto_eligible` 恒为 `False`（协议不允许自动执行） |
| gate | 2 | `check_recommendation` 的拦截原因串：低置信+校准不足、无 baseline |
| ledger/chain | 2 | `canonical_json` 键排序与紧凑分隔符、落盘后篡改事件必须 `LedgerError` |
| ledger/project | 1 | `project_events` 对 `decision_created → baseline_recorded → human_decision` 投影出的 status |
| report/calibration | 3 | `wilson_interval` 下界、`brier_score`、`recommended_option_not_selected` 排除计数 |
| life/model | 2 | `schema_version` 校验、`canonical_measured_value` 规范化后的字符串下界 |
| life/state | 2 | 区间观察下的三值判定（`unknown`）、`snapshot` 在 as_of 下的 known 计数 |
| life/scenario | 1 | `dominates` 严格更优语义 |
| life/adaptive | 1 | `AdaptiveKernel` 设计矩阵特征名数量 |
| life/calibration | 1 | `DelayedACI` 在 12 条 issued→observed 后的 `status/calibration_n` |

三条复算命令（均在仓库根执行）：

```bash
python3 eval/run_cases.py             # 必须 20/20；任一失败非 0 退出
python3 eval/run_cases.py --selftest  # 必须 19/20（QOC-01 变红），证明这套题会失败
make eval                             # pytest 79 passed + 题库 20/20，退出码 0
```

**复算说明**：`--save` 会把逐条 `status/actual/axis` 与按 axis 汇总写入 `eval/run-report.json`，改完源码后重跑 `python3 eval/run_cases.py --save` 即可复算本节的每个数字；`--json` 输出机器可读结果。题库里的期望值全部来自 `examples/*.json` 真数据与真实返回值，没有任何手写常量来自猜测。

**失败归因**（`--selftest` 实跑样例，按 axis 汇总）：

```
失败归因（按 axis）：
  models/decision: 1 条 —— QOC-01
```

失败时的定位顺序：`models/*` 先查协议校验（选项数/id 唯一/值域），`gate` 查拦截原因与阈值顺序，`ledger/*` 查链哈希与投影状态，`report/*` 查校准排除口径，`life/*` 查三值判定与 as_of 截断。若整片 axis 同时红，先怀疑 `src/qone_core` 被另一份副本（如 `build/lib/qone_core`）抢了导入路径，再怀疑逻辑回归。
