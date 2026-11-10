# Q-One Core

[![CI](https://github.com/aidless/q-one-core/actions/workflows/checks.yml/badge.svg)](https://github.com/aidless/q-one-core/actions/workflows/checks.yml)

**English documentation: [README.md](README.md)**（本文件为完整中文版）

> 一句话：Q-One Core 是「万事万物皆可量化」三仓系统的第一仓：把一个决策拆成显式变量，把推荐前的基线、人的最终决定写进只追加、哈希链的 JSONL 账本，之后把 agent 预测与观察到的结果做对比。全部通过本地 CLI（`qone init` 到 `qone report`）完成。它刻意保持为一个小的本地协议——推荐永远要求已记录基线 + 人做最终选择，不自动化重大决策。

> 中文研究入口：[多学科融合蓝图](docs/SYNTHESIS_BLUEPRINT.zh-CN.md)。v0.2 已接入完整个人应用；[使用入口与验收](https://github.com/aidless/q-one-life)。

Q-One Core 是三仓开源系统的第一仓，主题是**"万事万物皆可量化"**：把决策变成显式变量、记录 agent 推荐之前已知的信息、保留人的决定，之后把预测与观察结果对比。

本仓刻意从小型本地协议起步。它不声称一个分数是「一个人的完整模型」，也不自动化重大决策。

## 三个仓库

| 仓库 | 职责 | 数据边界 |
| --- | --- | --- |
| `q-one-core` | 决策 schema、只追加账本、安全门、报告 | 本地 JSONL；无 provider 凭证 |
| `q-one-agent` | 模型/工具适配器、检索、路由、证据捕获 | 经适配器读写 core 协议 |
| `q-one-life` | 个人本体、复盘、本地 UI 与集成 | 用户私有数据；导出是显式动作 |

`DecisionService` 提供事务化的产品状态迁移：校验与追加共享一把写锁。底层 `Ledger.append` 仍是可信导入原语，不强制产品状态迁移。这三个仓库是同一个 Q-One 应用的内部包，不是三个独立产品实现。

## 快速开始

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

`create` 会打印生成的决策 ID，后续命令复用它。示例里的截止日期是示意值，运行时请改成当天日期。

### 2026-11-10 实测（全新 venv，`pip install -e .`）

```text
$ qone --data-dir .qone-demo init
initialized .qone-demo/ledger.jsonl (0 events)
$ qone --data-dir .qone-demo create --file examples/decision.json
D-20261110-6a4e5d
$ qone ... baseline / recommend / decide / resolve    （各打印一条确认）
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

## Results（真实数字）

| 检查 | 数字 | 命令（2026-11-10） |
|---|---|---|
| CI 测试套件 | **79 passed + 4 subtests**（13.1 s） | `pip install ".[adaptive]" pytest && python -m pytest -q` |
| Quickstart 端到端 | 5 事件账本校验通过；report 输出 `descriptive_with_outcomes`，单个已解析玩具结果的 Brier 0.09 | 上面的 `qone` 序列 |

Brier 0.09 来自一个玩具决策（0.70 成功概率 vs 实际成功）——它演示的是打分链路，不是校准能力。

## 协议性质

- 每个事件是独占一行的 JSON 对象。
- 每个事件含序号、UTC 时间戳、前事件哈希、自身规范内容的 SHA-256。
- 一条推荐要求已记录的基线，最终选择永远留给人。
- 置信度与成功概率是两个独立字段：置信度描述 agent 多倾向自己的推荐；成功概率描述达成声明判据的预测机会。
- 报告标注证据状态；只有概率与二元结果同时存在时才计算 Brier 分。

事件契约见 [docs/PROTOCOL.md](docs/PROTOCOL.md)，首个测量计划见 [docs/RESEARCH_PLAN.md](docs/RESEARCH_PLAN.md)。

## 证据边界

账本是审计与测量机制。它不是临床工具、财务顾问、心理诊断，也不证明「人生结果可以归约为一个标量」。任何个人校准结果在具备足够冻结数据、明确协议与独立评审之前，只能当作描述性结论。

不要把个人决策日志、API key、含隐私数据的模型输出或原始导出提交进 Git。默认数据目录 `.qone-data/` 已被 Git 忽略。

## Limits（限制）

- 全部校准/预测候选（见下方研究节）**均未通过采用条件**，保持影子评测或研究用途；不存在任何「已上线生效」的自动推荐升级。
- Quickstart 的 Brier 数字来自单个玩具决策，无统计意义。
- 本地协议：无多人协作、无云端同步、无权威仲裁；数据可信度依赖使用者自己诚实记录。

## Contributing

读 [CONTRIBUTING.md](CONTRIBUTING.md)，协议变更保持版本化，保留失败或未知结果，并在 PR 里描述证据边界。本项目以 MIT 许可发布。

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
