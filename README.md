# Q-One Core

<!-- problem:start -->
Q-One Core records a decision protocol on the local machine: options, a pre-recommendation baseline, the human choice, and a later outcome, in an append-only hash-chained JSONL ledger.
It does not give life advice, it does not treat a score as a model of a person, and it does not execute or automate consequential decisions.
Run `python3 -m qone_core` offline (`init` through `verify` and `report`); this repository does not send the ledger anywhere.
<!-- problem:end -->

<!-- package-identity: q-one-core 0.4.1 -->

Package `q-one-core` version `0.4.1`. The console script `qone` is the same program as `python -m qone_core` after a local install. [CI](https://github.com/aidless/q-one-core/actions/workflows/checks.yml) runs the offline smoke, `pytest`, and `scripts/check_drift.py` (see `.github/workflows/checks.yml`).

## STATUS: WORK-IN-PROGRESS

This repository is not grade A. It is a local protocol and audit ledger with development tests and frozen synthetic experiments. It has no external validation study.

Remaining gaps:

- No external validation study, preregistered human trial, or independent replication of personal benefit.
- No user counts, PyPI download counts, or GitHub star counts are stated, because this repository does not publish them.
- `verify` detects a broken hash chain. It does not detect a rehashed suffix, a truncated valid prefix, or two forked copies. See [FAILURE_MODES.md](FAILURE_MODES.md).
- `DecisionService` enforces product transitions inside the writer lock. `Ledger.append` and the CLI do not. See [Writers](#writers).
- A baseline is whatever the writer appended. The ledger cannot show that it was chosen before a person saw a recommendation.
- The life-kernel, calibration, recency, and two-scale sections below are synthetic or frozen research records. They do not authorize an automatic recommendation.

中文研究入口：[多学科融合蓝图](docs/SYNTHESIS_BLUEPRINT.zh-CN.md)。个人应用入口在姊妹仓库 [q-one-life](https://github.com/aidless/q-one-life)。本仓库不代替那个应用，也不声称已经测得真实个人决策收益。

## Offline demo

The core ledger uses the Python 3.10+ standard library only. From a fresh clone, with no network and no install:

```bash
python3 scripts/offline_smoke.py
```

That script creates a temporary ledger from `examples/decision.json`, appends one baseline, recommendation, human choice, and outcome, then runs `verify` and `report`. It does not download packages. One run on the machine used to prepare this change finished in under a second. That timing is a single observation, not a benchmark, and it is inside a 15-minute fresh-clone budget.

The same commands by hand. `create` prints the decision id. Substitute that id for `D-YYYYMMDD-xxxxxx`. The id shape is `D-` + UTC `YYYYMMDD` + `-` + 6 hex characters (`new_decision_id` in `src/qone_core/models.py`). `examples/decision.json` has no `decision_id`, so each `create` mints a new one. Edit the example deadline before using the file for a real decision; the deadline in the file is illustrative.

<!-- cli-demo:start -->
```bash
export PYTHONPATH=src
python3 -m qone_core --data-dir .qone-data init
python3 -m qone_core --data-dir .qone-data create --file examples/decision.json
python3 -m qone_core --data-dir .qone-data baseline --decision D-YYYYMMDD-xxxxxx --option draft --note "human baseline"
python3 -m qone_core --data-dir .qone-data recommend --decision D-YYYYMMDD-xxxxxx --option draft --confidence 0.82 --success-probability 0.70 --rationale "The criterion rewards an early reviewable artifact." --source "local-rule-v0.1"
python3 -m qone_core --data-dir .qone-data decide --decision D-YYYYMMDD-xxxxxx --option draft --by human
python3 -m qone_core --data-dir .qone-data resolve --decision D-YYYYMMDD-xxxxxx --success yes --notes "A reviewable draft was ready."
python3 -m qone_core --data-dir .qone-data verify
python3 -m qone_core --data-dir .qone-data report
```
<!-- cli-demo:end -->

`.qone-data/` is gitignored. Do not commit it.

Development tests need pytest. The adaptive experiments also need NumPy and SciPy. Those extras are not part of the offline ledger path, and installing them may use the network:

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
```

After that install, `qone` and `python3 -m qone_core` call `qone_core.cli:main`.

## Writers

`DecisionService` (`src/qone_core/service.py`) is the product API. Each transition calls `Ledger.transact`, which holds the writer lock, verifies the chain, checks the projected state, and appends one event. `decide` stores `decided_by` as `human`.

`Ledger.append` (`src/qone_core/ledger.py`) is a trusted-import primitive. It verifies the chain and appends the payload it is given. It does not check baselines, gates, or allowed transitions. A caller can record a recommendation with no baseline, or a second baseline that replaces the first in the projection.

The CLI (`src/qone_core/cli.py`) is not `DecisionService`. It checks some transitions, then calls `Ledger.append`. Those checks sit outside the writer lock, and `append` does not repeat them. `decide --by` stores the string it is given. Neither writer executes the chosen option. `check_recommendation` blocks only a missing baseline; other gate reasons are recorded and the recommendation is still stored.

Limits of the hash chain, the append bypass, and baseline gaming are in [FAILURE_MODES.md](FAILURE_MODES.md).

## The three repositories

| Repository | Responsibility | Data boundary |
| --- | --- | --- |
| `q-one-core` | Decision schema, append-only ledger, safety gates, reports | Local JSONL; no provider credentials |
| `q-one-agent` | Model/tool adapters, retrieval, routing, evidence capture | Reads/writes the core protocol through an adapter |
| `q-one-life` | Personal ontology, reviews, local UI and integrations | User-owned private data; export is explicit |

These repositories are internal packages of one Q-One application, not three independent product implementations. This repository does not claim that the sister repositories have been validated with users.

## Protocol properties

- Every event is one JSON object on one line.
- Each event contains a sequence number, UTC timestamp, previous hash, and SHA-256 hash of its canonical content.
- On the `DecisionService` path, a recommendation requires a recorded baseline and leaves the final choice to a human. `Ledger.append` does not enforce that order. See [Writers](#writers).
- Confidence and success probability are separate fields. Confidence describes how strongly the recorded recommendation prefers its option; success probability describes the predicted chance of meeting the declared criterion.
- Reports label their evidence status and only compute Brier score when a probability and a binary outcome are both present for the option the human selected.

See [docs/PROTOCOL.md](docs/PROTOCOL.md) for the event contract and [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md) for the first measurement plan. The research plan is a plan, not a completed study.

## Evidence boundary

The ledger is an audit and measurement mechanism. It is not a clinical instrument, a financial adviser, a psychological diagnosis, or proof that life outcomes can be reduced to one scalar. Any personal calibration result must be treated as descriptive until there is enough frozen data, a defined protocol, and an independent review. This repository does not contain that review.

Do not commit personal decision logs, API keys, model outputs containing private data, or raw exports. The default data directory `.qone-data/` is ignored by Git.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), keep protocol changes versioned, preserve failed or unknown outcomes, and describe evidence limits in pull requests. This project is released under the MIT License.

## 人生决策内核 0.3

新增有测量语义的个人状态、目标树、价值顺序、资源账户、延迟情景、多目标比较，以及从行动前后观察学习的贝叶斯变化预测。当前验证为合成回放，不代表真实人生收益。

- [内核详细文档](docs/LIFE_KERNEL.zh-CN.md)
- [技术进阶蓝图与接入条件](docs/ADVANCED_ROADMAP.zh-CN.md)
- [合成回放逐条证据](docs/evidence/adaptive-synthetic.json)
- [可运行的模型示例](examples/adaptive.synthetic.json)

安装预测组件：`pip install '.[adaptive]'`；复现：`python scripts/evaluate_life_kernel.py`。

## 在线校准影子评测 0.4

新增延迟结果校准凭据、按行动组合分组的校准候选和冻结的稳定/突变对照。候选未通过全部采用条件，保持影子评测；自动推荐使用的区间不改变。

[实验与采用决定](docs/CALIBRATION_EVALUATION.zh-CN.md) · [固定协议与逐条证据](artifacts/calibration-evaluation/v1/) · [官方来源核验](literature/calibration-source-probes.json)

## 非平稳预测研究：日历遗忘候选

加入按结果发生时间遗忘的独立原型，以及均值/噪声变化、不规则观察和结果延迟的冻结对照。候选未通过稳定与稀疏场景的采用条件，保留完整失败结果，自动推荐内核保持原版本。

[评测结果、限制与复现](docs/RECENCY_EVALUATION.zh-CN.md) · [协议与逐条证据](artifacts/recency-evaluation/v1/) · [官方来源核验](literature/recency-source-probes.json)

## 双时间尺度研究：长期结构与短期变化

新增保留行动/上下文结构、按日历时间推演短期偏移的独立原型，支持晚到结果的历史重建；并提供能核算预测分母、逐条评分与采用决定的工件审计工具。候选未通过全部稳定/变化反例，继续保持研究用途。

[冻结评测与限制](docs/TWO_SCALE_EVALUATION.zh-CN.md) · [输入、源码与逐条证据](artifacts/two-scale-evaluation/v1/) · [官方来源核查](literature/two-scale-source-probes.json)

## 证据资格门 0.4.1

训练和回放现在会排除同一点位的未解决冲突、被显式更正的旧观察，以及行动开始时不是当前状态的事前引用；排除原因和 `available_n/trainable_n/excluded_n` 一并保留。未来登记的冲突不会改写过去已发出的预测，低样本时继续拒绝推荐。

[规则、冻结反例与限制](docs/EVIDENCE_GATE.zh-CN.md) · [协议、基线与候选](artifacts/evidence-gate/v1/) · [来源核验](literature/evidence-gate-source-probes.json)
