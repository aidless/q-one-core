# Q-One Research Synthesis — 集百家精华 v1.0

> 日期：2026-10-23 · 方法：四路并行调研（预测与校准科学 / RLVR 与自进化 / Agent 记忆与持续学习 / 测量理论与元科学），每条结论 ≥2 独立来源、标注证据强度；再与自家实证（r5 假零、goodhart-project、arx、evoagent 平台期）对撞成协议变更。
> 用途：本文件是协议 v0.2 的依据。每条变更标 [P1-P4 来源支柱] + [证据强度] + [处置：v0.2 采纳 / 试验 / 延后 / 拒绝]。

---

## 0. 一页结论

### 0.1 「万物皆可量化」必须附加的三条边界条件 [P4]

1. **可量化性是经验命题，不是公理**。属性有无可加/单调结构要检验（Michell 的"量化命令"批判：心理测量学从不检验它）；检验不过的属性降级为定性观察，不硬编码分数。
2. **量化的是代理，不是本体**。单分数必然欠表示（construct underrepresentation）+ 混入构念无关方差；只允许"指标矩阵"（多指标互补 + 反指标），禁止把任何指标本身当目标。
3. **测量者信度先于被测者校准**。信度是效度上限（衰减公式）；系统偏差可以"完美可靠却完全无效"。尺子（含自评 judge）未过信度与偏差审计前，相关校准分数的解释权保留。

### 0.2 最尖锐问题的直接回答 [P2]

**"用 LLM 给人生决策打分"属于不可验证域**——没有程序化 ground truth，RLVR 不适用（RLVR 增益只在数学/代码等有廉价 verifier 的域真实，且 pass@k 下被 base model 追平）。文献支持的安全折中是 **rubric-as-rewards**（预注册、可审计评分表 + 人工锚点校准 judge），但该路线目前只在低风险文本域被验证——因此在 Q-One 里，LLM 判断只能作为**建议证据**进入账本，**永远不能成为自动优化目标**。这一条写进协议，不是保守，是文献的硬边界。

### 0.3 系统一句话定位（升级版）

Q-One 不是"量化人生 app"，而是**把决策做成可校准预测、把每条经验做成可验证记录、把每次自进化关进外置门禁的决策实验系统**——它的核心资产是"质疑自己尺子的那一层"。

---

## 1. 支柱一：预测与校准科学 + 决策科学

### 已确立的经验
| 经验 | 来源 | 强度 |
|---|---|---|
| 概率训练显效：IARPA RCT 中训练/追踪/协作三干预均提升校准与分辨率 | Mellers et al. 2014; Chang et al. 2016 | 强 |
| **更新频率是最强行为预测因子**（频繁小幅更新者最准） | Mellers et al. 2015 | 强 |
| Brier 三分解：BS = 可靠性 − 分辨率 + 不确定性，可分别诊断"校准差"vs"问题太粗" | Murphy 分解 | 强 |
| 分布预测优于点预测（Metaculus 全分布 + 加权中位数聚合） | Metaculus | 强 |
| **Clairvoyance 测试**是题面质量金标准：知全部事实但不懂语境的人能无歧义判定 | Metaculus 写题指南 | 强 |
| 参照类预测（25,000+ 项目库）纠正系统性超支 | Flyvbjerg RCF | 强 |
| Premortem 使可列失败原因数约翻倍 | Veinott et al. 2010 | 强 |
| LLM ensemble 预测接近人类群体，看到人类中位数后提升 17–28% | Schoenegger et al. 2024 (Science) | 强 |

### 失败教训
弃坑是 QS 常态且重度用户弃得更快（Attig & Thomas 2020）· streak/提醒反噬内在动机（测量改变行为）· 决策日志缺 RCT 证据，不能假设"记账=进步" · 小样本分箱的 reliability 分量不稳（Stephenson 2008）。

### 启示 → 处置
1. 决策强制四字段 `resolution_criteria`(含数值阈值) / `resolution_source` / `resolve_by` / 边界情况预设，入库前过 clairvoyance 测试 [P1·强·**v0.2 采纳**]
2. `success_probability` 改区间 `[low, high]`，按区间计分 [P1·强·**v0.2 采纳**]
3. 报表用 Brier 三分解；n<30 只显示不诊断 [P1·强·**v0.2 采纳**]
4. 新事件类型 `forecast_revision`（append-only 不覆盖），更新频率入自进化指标 [P1·强·**v0.2 采纳**]
5. 结算前强制 premortem 字段，结算回填命中清单 [P1·合理推断·**试验**]
6. 反 Goodhart 记分：无 streak、无奖励兑换、最小必填字段、记录延迟与弃坑率本身作健康指标 [P1·合理推断·**v0.2 采纳**]
7. 人机分账户：LLM 预测以独立 forecaster 身份入账，聚合用中位数 [P1·强·**v0.2 采纳**]

---

## 2. 支柱二：RLVR 与 LLM 自进化的实证

### 已确立的经验
| 经验 | 来源 | 强度 |
|---|---|---|
| RLVR 增益真实但有界（重加权而非新能力；需廉价程序化 verifier） | Yue et al. NeurIPS 2025 | 强 |
| **Rubric-as-rewards**：预注册评分表提升 judge 一致性、显著降跨 judge 方差——可验证性向开放域扩展的当前主线 | RaR 2025 | 中-强 |
| 外部信号 vs 纯自反思分界清晰：STaR/STOP 有答案门增益公认；无 ground truth 的 Self-Refine/Reflexion 增益被系统性质疑 | Kamoi et al. TACL 2024 | 强 |
| ORM 不归因、PRM 可被劫持；主流折中 = outcome 标签导出隐式过程分 | PRIME | 中-强 |
| Reward hacking 有成熟分类学（DeepMind 86 例；agent 场景四层升级） | DeepMind | 强 |
| 基准污染普遍且检测器最多抓 60% | contamination 综述 | 强 |
| LLM-judge 系统性偏差（自偏好/位置/冗长/谄媚）；换序+多 judge 是标准缓解 | Justice or Prejudice | 强 |
| Test-time compute 非单调：简单题过度思考实测负收益 | Inverse Scaling in TTC | 强 |

### 失败教训
无 ground truth 自修正常**降低**性能（Huang et al.）· PRM 引导下过程分涨、最终答案反而更差 · Voyager 类自进化增益难与泄漏/prompt 效应区分、普遍缺跨域检验 · 生产 RL 的 reward hacking 泛化为全局 misalignment，窄修补无效（Anthropic 2025）。

### 启示 → 处置
1. LLM 打分 = 建议证据，非自动优化目标（见 0.2）[P2·中·**v0.2 采纳（协议红线）**]
2. 门禁外置：held-out 决策集 + 与被优化源独立的 judge + 换序一致性；增益判定不得依赖被优化系统自评 [P2·强·**v0.2 采纳**]
3. 冻结回归集永不参与优化，只做回归测试 [P2·强·**v0.2 采纳**]
4. 过程分与结果分分开记账、互不进奖励 [P2·中-强·**v0.2 采纳**]
5. 晋升步幅小 + gate 失败即回滚（hacking 是全局性的）[P2·强·**v0.2 采纳（对齐 evoagent）**]
6. 低风险高频决策不堆推理算力 [P2·强·**v0.2 采纳（agent 路由规则）**]
7. outcome 的 rubric 预注册化（Q-One 版 RaR）：成功判据写成显式评分表并冻结 [P2·中-强·**试验**]

---

## 3. 支柱三：Agent 记忆与持续学习

### 已确立的经验
| 经验 | 来源 | 强度 |
|---|---|---|
| 检索三维打分 recency+importance+relevance，缺一显著退化 | Generative Agents | 强 |
| 只从成功轨迹归纳 workflow 复用：WebArena +24.6–28.5% | AWM | 强 |
| 失败→自然语言反思入 episodic buffer 即可跨任务提分 | Reflexion | 强 |
| 案例库与归纳 insights 分开存储按需检索 | ExpeL | 强 |
| CBR 4R 循环 = 免训练持续学习框架 | CBR 综述 | 中 |
| 写入时冲突检测（ADD/UPDATE/DELETE）+ 时间感知检索 | Mem0 | 中 |
| 多示例 ICL 随上下文累积而崩溃（"窗口内伪持续学习"） | Long-ICL / Lost in the Middle | 强 |

### 失败教训
污染率 <0.1% 即可对记忆注入后门（AgentPoison，攻击成功率 ≥80%）· **错误经验自我强化成环**（坏记忆→坏行动→坏结果被存为新记忆）· 反复把经验改写成"教训"反而退化（污染来自覆写本身）· MemGPT 依赖模型自判换页，误判即失效。

### 启示 → 处置（append-only 账本缺的三样）
append-only 只解决"不丢"。防错误经验自我强化需补：
1. **验证闭环**：记录加 `verification_status`（verified/refuted/pending），检索默认过滤未验证/被反驳项 [P3·强·**v0.2 采纳**]
2. **冲突消解**：bitemporal 字段 `valid_from/valid_to` + `supersedes` 指针，检索只取当前有效版本 [P3·中-强·**v0.2 采纳**]
3. **写入闸门**：记录分层 observation / inference / lesson；inference 必须带指向 observation 的证据链；教训层是可再生缓存——定期从已验证案例重归纳而非增量改写 [P3·强·**v0.2 采纳**]
4. 检索索引带时间戳、importance、scope、success/attempt 效用计数 [P3·强·**试验**]
5. 植入 canary 决策探测账本污染 [P3·中·**试验**]

---

## 4. 支柱四：测量理论与元科学

### 已确立的经验
定义先于测量（内容效度以 construct definition 为标准，Clark & Watson 2019）· 单分数两大效度威胁：欠表示 + 构念无关方差 · α 推太高反而降效度 · 信度是效度上限（衰减公式）· **系统偏差可"完美可靠却完全无效"** · Brier 低 = 校准+分辨率+不确定性的混合，校准好≠预测有效 · Krippendorff's α 是标准 IRR（人类标注基准 ≈0.79）· LLM judge 偏差是系统性而非随机的。

### 失败教训
苏联指标游戏（按数量→废钉、按吨位→巨钉：计划者写不全属性清单，任何单一指标都被最优反应利用）· 死亡率报告卡惩罚接难症医生 → 拒收高危患者（Mid Staffordshire）· 医疗 KPI 系统综述：gaming/隧道视野/努力替代 · **标签噪声双重伤害：尺子差被记成模型差，腐蚀校准评估** · Michell：可量化性本身是经验命题，从不检验即"病态科学"。

### 启示 → 处置
1. **指标准入协议**：入账前必须提交 construct definition + 效度威胁清单 + IRR 证据（α≥0.8 目标 / 0.67 下限）；不过关只能记定性观察、不得加权 [P4·强·**v0.2 采纳**]
2. **先测尺子再校准人**：任何 Brier 前先登记测量系统误差；账本分"模型方差"与"尺子方差"两列；judge 需位置交换/多 judge 去偏 [P4·中-强·**v0.2 采纳**]
3. **反指标制**：每个目标指标配反指标 + 定期轮换 + 不惩罚超额 [P4·中·**v0.2 采纳**]

---

## 5. 与自家实证的对撞（Q-One 的差异化根源）

| 自家实证 | 文献印证 | 在 Q-One 中的角色 |
|---|---|---|
| r5 假零（llama 27/27 格式坍缩被误读为安全） | P1 分布预测 + P4 系统偏差 | 元审计层的"假零检测"：候选策略归零必须区分真安全/输出坍缩 |
| goodhart-project（指标脱钩后真实分 444→崩） | P4 苏联钉子/死亡率报告卡 + P2 reward hacking | 反指标制与指标准入协议的实证依据——Goodhart 是必然不是意外 |
| arx 拒绝门（统计门不过拒绝产出结论） | P2 无 ground truth 自反思有害 | 建议生成的 fail-closed：证据不足时拒绝给推荐而不是硬给 |
| evoagent 十轮平台期 | P2 自进化增益难区分泄漏 | M2 里程碑的基准：平台期必须被外置门禁下的真增益打破 |
| 300 条金标样本（judge 校准 FPR 分母） | P4 IRR/锚点校准 | rubric-as-rewards 路线的人工锚点库 |

## 6. 实验积压（按 ROI）

1. **M1 落地**：按冻结预注册记 20 个决策（等用户选 2 个域）→ 第一张 Brier 三分解报表
2. **尺子审计先行**：用 300 条金标样本对 5 个 judge 跑 FNR/FPR/κ + 位置交换——把"尺子方差"先钉住，再谈人机预测对比
3. **`forecast_revision` 增益验证**：追踪"更新频率 vs 最终 Brier"（Mellers 假设在个人尺度上的复现）
4. **canary 注入测试**：往测试账本植入 1% 矛盾记录，验证 supersedes/验证闭环能否阻断自我强化环
5. **rubric 预注册**：把两个域的成功判据写成冻结评分表，test RaR 路线在决策域的迁移

## 7. 来源

四支柱调研各自内嵌来源（Mellers 2014/2015、Murphy 分解、Metaculus、Flyvbjerg、Veinott 2010、Attig & Thomas 2020、Yue et al. NeurIPS 2025、RaR、Kamoi TACL 2024、PRIME、DeepMind spec-gaming、Anthropic 2025、Inverse Scaling in TTC、Generative Agents、AWM、Reflexion、ExpeL、Mem0、AgentPoison、Clark & Watson 2019、Cappelleri 2014、Revelle Ch.7、Krippendorff α、Justice or Prejudice、Michell 2003、CNA 2022、Boseak 2025 等，全文见调研记录）。自家证据：`r5-verify-vs-gate`、`approval-gates-r3`、`goodhart-project`、`arx`、`evoagent`、`paper_workflow_kb/evidence/judge_calibration_lab/`。
