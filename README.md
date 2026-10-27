# Q-One Core

> 中文研究入口：[多学科融合蓝图](docs/SYNTHESIS_BLUEPRINT.zh-CN.md)。v0.2 已接入完整个人应用；[使用入口与验收](https://github.com/aidless/q-one-life)。

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
