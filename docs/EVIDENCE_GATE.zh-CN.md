# 证据资格门：冲突、更正与迟到观察

日期：2026-10-26。实现版本：q-one-core 0.4.1。对应应用版本：q-one-life 0.7.1。

## 结论

本轮没有提高预测精度，也没有更换贝叶斯回归或校准算法。改动只修复训练证据的资格判断：同一点位互相矛盾的观察、明确更正、非当前的事前引用，不能再被静默当成干净标签；未来才登记的冲突也不能改写过去已经发出的预测。

冻结的合成验收中，候选在 11 个案例的 episode 选择上 11/11 与事先规则一致。无冲突案例仍保持原预测的既有字段不变；冲突案例明确保留被排除的 episode、原因和分母。该结果只证明冻结合成输入上的资格语义和工程回归，不证明真实个人收益、预测更准、因果关系或覆盖保证。

## 为什么需要门

原有预测器只按 `recorded_at <= cutoff` 和 `supersedes` 选取结果，但没有处理以下情况：

1. 同一个测量在同一 `observed_at` 出现两个不同报告，且没有任何报告被显式更正；
2. episode 的事前引用不是行动开始时可用的最新状态，而是旧观察或已被冲突覆盖的观察；
3. 冲突或更正发生在结果登记之后，不能把过去已经发出的预测算成“当时已经知道”。

Q-One 对这类情况采取保守规则：不猜测哪一方正确，不取平均，不从模型输出补造事实，也不把排除的标签当成成功样本。资格失败是数据状态，不是预测器的“输赢”。

## 双时间规则

- `observed_at` 表示事件发生时间，`recorded_at` 表示系统知道该记录的时间。
- 在 cutoff 之前不可见的观察，不参与该 cutoff 的训练或回放。
- cutoff 之前已知的显式 `supersedes` 会让被更正的旧观察失去资格。
- 同一测量、同一 `observed_at` 下出现两个语义不同的值时，引用这些观察的 episode 不被训练，也不进入最终回放。
- 行动开始前的上下文必须指向行动开始时 `snapshot(started_at)` 中当前已知且唯一的观察；不能引用未来记录、过期状态或同一时点的冲突状态。
- `available_n`、`trainable_n`、`excluded_n` 和每个 `excluded_episodes` 的 issue 一并输出。被排除的记录仍留在输入和分母中，不能被“清洗”后消失。

数值观察按测量语义比较等价性。例如同一数量的 JSON `1` 与 `1.0` 不被误报为冲突；数值仍按原单位和量表验证，不因规范化而允许单位或区间中点混用。

## 冻结验收

协议和逐条输入位于 [`artifacts/evidence-gate/v1/`](../artifacts/evidence-gate/v1/)：

- 三个干净种子 17、29、41，每个 40 条学习记录；
- 八个反例：迟到结果冲突、迟到事前冲突、开始前已存在冲突、旧事前引用、等值重复、显式更正、无关冲突、未来冲突；
- 固定 `as_of=2026-10-26T00:00:00Z`，过去对照点为 `2026-10-25T00:00:00Z`；
- 输入和基线源码 SHA-256 在协议中固定；[`baseline.json`](../artifacts/evidence-gate/v1/baseline.json) 是先冻结的旧实现输出，[`candidate.json`](../artifacts/evidence-gate/v1/candidate.json) 是同一运行时下的候选输出。

预期排除的五个案例为 `e25`：`late_outcome_conflict`、`late_before_conflict`、`known_before_conflict`、`older_before_reference`、`superseded_outcome`。`equal_duplicate`、`unrelated_conflict`、`future_conflict` 不应错误丢弃干净记录。候选脚本同时检查：

- episode 选择与协议中的预期集合一致；
- 被排除 episode 的双目标回放行数按 2 倍分母减少；
- 无冲突案例的旧预测字段和不含排除的旧回放字段保持不变；
- 迟到冲突不改变过去 cutoff 的预测与资格；
- 低于证据门槛时保持 `abstain`，不使用排除后的少量样本制造支持。

## 复现

安装预测依赖后，在仓库根目录运行：

```bash
python3 -m pip install '.[adaptive]' pytest
python3 scripts/evaluate_evidence_gate.py --phase candidate
python3 -m pytest -q
```

候选报告记录 Python、NumPy、SciPy 版本、协议哈希、候选源码哈希和每个案例的预测。工件中的数值不承诺跨不同数学库/BLAS 版本逐位相同；跨版本比较时应重新运行冻结源码，而不是直接比较旧 JSON 数字。

应用层的对应验收在 q-one-life：登记同一点位的第二份报告后，首页的学习样本数减少，`training_evidence` 明确列出被排除 episode，回放行数和分母同步变化，同时行动定义、资源承诺和推荐授权不被改写。

## 来源与边界

实现借鉴了 [TensorFlow Data Validation](https://github.com/tensorflow/data-validation) 将数据异常与 schema 分开记录的工程思路，以及 [OpenTelemetry logs data model](https://github.com/open-telemetry/opentelemetry-specification/blob/5740e9af3c82a3c89ef0b2357548946fbf5a9f5e/specification/logs/data-model.md) 对事件时间与采集时间的区分。固定版本、许可证和阅读范围见 [`literature/evidence-gate-source-probes.json`](../literature/evidence-gate-source-probes.json)。这些来源没有提供个人冲突消解器，也没有证明 Q-One 的预测质量。

真实个人数据、测量效度、未观察混杂、非平稳变化、策略价值和长期收益仍未验证。冲突门是防止证据污染的安全边界，不是完整的人生因果模型，也不是 SOTA 排名。
