# 检索与核查日志

日期：2026-10-23（用户所在时区 America/Los_Angeles）。渠道：web.run、GitHub 连接器只读 fetch、Hugging Face 连接器模型元数据；arXiv 元数据另用公开 abs 页交叉核查。搜索引擎未提供可复算的全部命中总数，因此总命中数统一记为“未提供”，不把展示条数当作总数。

## 问题

Q-One 如何组合快速类型化决策、复杂推理、证据检索、记忆、概率评估和个人反思？哪些技术可直接形成工程候选，哪些只能作为研究背景？

## 实际搜索式

| 检索式 | 采用/处理 |
| --- | --- |
| `"Laya" "Jev" model agent` | 发现线索，转原始仓库与官方文档核查：S01、S02；社区帖子不作技术论断依据 |
| `site.arxiv.org "Self-Supervised Learning from Images with a Joint-Embedding Predictive Architecture"` | S22；与 Jev 明确区分 |
| `site.arxiv.org "ReAct: Synergizing Reasoning and Acting in Language Models"` | S06 |
| `site.arxiv.org "A Five-Stage Model of Personal Informatics Systems"` | 未按错误题名入库，后续改正确题名 |
| `Jev TypeSafe AI system one official documentation decision` | S02；第三方产品介绍站未作为官方来源 |
| `site.arxiv.org "Qwen3 Technical Report"` | S03 |
| `site.arxiv.org "DeepSeek-R1: Incentivizing Reasoning Capability"` | S04 |
| `"A Stage-Based Model of Personal Informatics Systems" Li Dey Forlizzi` | S18 作者公开PDF |
| `site.selfdeterminationtheory.org Ryan Deci 2000 intrinsic motivation self determination pdf` | S19 |
| `site.cmu.edu Donella Meadows leverage points places to intervene system pdf` | 改为作者档案原文核查：S20 |
| `site.bmj.com "CONSORT extension for reporting N-of-1 trials"` | S25；正文403，限定为精读候选 |
| `site.stat.berkeley.edu "Strictly Proper Scoring Rules" Gneiting Raftery` | 转作者公开PDF：S15 |
| `pymoo Multi-Objective Optimization in Python Blank Deb arxiv` | S24 |
| `"Strictly Proper Scoring Rules, Prediction, and Estimation" 2007 pdf Raftery` | S15 |

## 定向查阅

S05–S17 中的相关论文通过 abs 页定向查阅；29 个采用条目的具体 URL、阅读范围和复核日期均在 `source-registry.json`。16 条 arXiv 来源另保存页面响应 SHA-256 与抓取时间作为元数据收据，不保存整篇论文。其余来源使用 web 或连接器核验；没有响应哈希的条目不伪造哈希。来源数量可从登记文件重算。

用户补充的 KarlPeixoto/jev-laya-lab、zhaojie911272507/jev-laya-decisionmodel 及 arXiv:2609.28940 已逐一核查（S26–S28）。另补入配对评测预印本 arXiv:2610.02267（S29），用于反例和评测设计。

Laya 代码快照：`0a05a45052e23ae0b887a490fe8d6d9c8cff2ab5`；固定快照的 README 与 Apache-2.0 LICENSE 已读取。LangGraph 仓库核查时 HEAD：`4c52e129eb1ab69a3da58b799f67929f77d81149`；README 使用默认分支读取，不宣称读取发生在该固定快照。未下载权重或调用付费模型。

Hugging Face 元数据核查对象：`convaiinnovations/laya`、`Qwen/Qwen3-8B`、`deepseek-ai/DeepSeek-R1`。模型卡声明是许可线索，正式接入仍要锁定 revision 并核查权重、代码、数据与蒸馏上游各自条件。

## 排除与失败

- 一次手工访问将 `2610.02267` 误写为 `2510.02267`，返回量子点论文，已排除。
- 一次 pymoo 定向访问使用 `2002.04599`，返回对抗鲁棒性论文，已排除；正确来源为 `2002.04504`。
- 旧 Harvard 书籍链接跳转到作者简介；改用作者 `miguelhernan.org/whatifbook`（S21）。
- UW 技术报告页面打开超时；使用作者公开 JASA PDF（S15）。
- GitHub `/license` 连接器端点不在允许集合内；改读 Laya 固定 commit 的原始 LICENSE。
- S26、S27 的 GitHub 仓库元数据均为 `license=null`。未取得代码复用授权，本轮只阅读 README 并自主归纳。
- S25 搜索可见原文片段，正文打开返回403。未标记为全文核查或已采用指南。

没有对上述来源执行训练、模型推理或基准复现。检索结果的性能数字不作为 Q-One 的性能数字。

元数据写入期间，一次尝试把大体积README作为命令参数传入，被操作系统以参数过长拒绝；未完成写入。随后改为按公开URL逐项交叉抓取，只保存摘要哈希到 `source-probes.json`。没有将第三方README全文提交到仓库。

## 2026-10-25：人生内核与技术进阶

引擎：web.run。搜索接口未给出可靠的总命中数，记为不可得；不以展示结果数冒充全网命中数。

| 检索式 | 采用与用途 |
|---|---|
| `site.ianli.com stage based model personal informatics systems 2010` | 重读作者PDF的整合/反思阶段，S18 |
| `site.donellameadows.org leverage points stocks flows delays feedback` | 作者档案，S20，概念来源 |
| `site.pymoo.org multi objective constraint handling Pareto dominance` | 官方约束文档，S24，不宣称采用求解器 |
| `site.danijar.com DreamerV3 mastering diverse domains world models Nature 2025` | 作者摘要与正式出版元数据；架构参考 |
| `site.tdmpc2.com scalable robust world models TD-MPC2` | 作者页及arXiv号题核验；架构参考 |
| `site.microsoft.com research contextual bandit doubly robust policy evaluation learning 2011` | 官方出版记录和作者PDF；界定未来策略评估条件 |
| `site.cs.ubc.ca Murphy conjugate Bayesian linear regression normal inverse gamma` | 发现共轭分析材料，并定向阅读原授课者公开回归章节25.1–25.3 |

定向读取 W3C PROV-O 与 Learning from data 第25章。Nature正文身份跳转不可访问，Dreamer项目页一次返回重定向占位；出版信息有搜索索引及作者摘要支持，未标记全文阅读。pymoo MCDM旧地址无法访问，未以该页支撑实现。

新增来源笔记：`notes/adaptive-kernel-sources-2026-10-25.md`。本轮新来源尚未加入旧S01–S29登记编号，避免把旧登记条目数当作完整文献计数。

## 2026-10-25：在线校准技术对照迭代

问题：现有 Student-t 范围在合成回放中过宽，能否通过仅使用已知结果的在线校准改善范围质量，并在突变场景通过同样的采用条件？

引擎：web.run 与 GitHub 连接器；总命中数未提供，记为不可得。

| 检索式 | 采用来源与范围 |
|---|---|
| `adaptive conformal inference distribution shift official github Gibbs Candes ACI` | NeurIPS 2021原文、arXiv号题核对；读取公式(2)和长期/单时点覆盖区别 |
| `strongly adaptive online conformal prediction official GitHub SAOCP` | arXiv:2302.07869摘要、方法引言、论文内官方GitHub链接 |
| `MAPIE time series adaptive conformal inference official github latest release` | GitHub官方元数据、最新发布版v1.6.0、固定commit的ACI更新方法与LICENSE |

普通GitHub关键词“SAOCP”检索命中无关仓库，未采用；随后从论文链接找到salesforce/online_conformal。SI-OCP由检索发现作者实验室页面并核对仓库元数据；一次arXiv链接点击失败，未写入未经核验的arXiv编号。

来源版本与阅读范围：`calibration-source-probes.json`；方法采用结论：`notes/calibration-2026-10-25.md`。本轮自主实现方程和适配协议，不复制仓库实现、不引入MAPIE或SAOCP运行依赖；未宣称复现论文基准或达到最先进排名。
