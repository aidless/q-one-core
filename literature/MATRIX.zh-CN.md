# 研究与采用矩阵

初筛日期：2026-10-23。表内为设计候选，不表示已集成或已验证。

| ID | 来源 | 借鉴方向 | 仓库 | 优先级 | 决策 |
| --- | --- | --- | --- | --- | --- |
| S01 | [Laya: typed System 1 decision engine](notes/S01-laya.md) | 为重复的局部判断提供可替换的本地 provider。 | q-one-agent | P1 | 采用候选 |
| S02 | [TypeSafe System One / Jev documentation](notes/S02-jev.md) | 保留托管决策 provider 的接口对照。 | q-one-agent | P2 | 对照候选 |
| S03 | [Qwen3 Technical Report](notes/S03-qwen3.md) | 复杂问题交给可配置的生成模型，记录推理预算。 | q-one-agent | P1 | 采用候选 |
| S04 | [DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning](notes/S04-deepseek-r1.md) | 借鉴可验证奖励和蒸馏思路，先比较现成模型。 | q-one-agent | P2 | 方法参考 |
| S05 | [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](notes/S05-rag.md) | 建议附带可回溯到原文的证据片段。 | q-one-agent | P1 | 采用候选 |
| S06 | [ReAct: Synergizing Reasoning and Acting in Language Models](notes/S06-react.md) | 把任务拆为有观察反馈的有限步骤。 | q-one-agent | P1 | 方法参考 |
| S07 | [Reflexion: Language Agents with Verbal Reinforcement Learning](notes/S07-reflexion.md) | 为失败记录生成可审核的复盘建议。 | q-one-agent | P2 | 方法参考 |
| S08 | [MemGPT: Towards LLMs as Operating Systems](notes/S08-memgpt.md) | 工作上下文、长期事实、原始证据分开存储与检索。 | q-one-agent | P2 | 方法参考 |
| S09 | [DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines](notes/S09-dspy.md) | 用固定开发集比较提示与路由规则。 | q-one-agent | P2 | 方法参考 |
| S10 | [LoRA: Low-Rank Adaptation of Large Language Models](notes/S10-lora.md) | 将来用少量可管理参数进行领域适配。 | q-one-agent | P3 | 延后 |
| S11 | [Direct Preference Optimization: Your Language Model is Secretly a Reward Model](notes/S11-dpo.md) | 未来学习用户对表达与工作流的明确偏好。 | q-one-agent | P3 | 延后 |
| S12 | [Efficient Memory Management for Large Language Model Serving with PagedAttention](notes/S12-vllm.md) | 当并发与显存瓶颈被测量确认时评估推理服务。 | q-one-agent | P3 | 延后 |
| S13 | [On Calibration of Modern Neural Networks](notes/S13-calibration.md) | 校准分类概率，按任务、模型版本和数据窗口报告。 | q-one-core | P0 | 采用方法 |
| S14 | [A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification](notes/S14-conformal.md) | 数据满足所选方法假设时可输出候选集合并允许弃权。 | q-one-core | P2 | 条件候选 |
| S15 | [Strictly Proper Scoring Rules, Prediction, and Estimation](notes/S15-proper-scoring.md) | 将已定义预测事件的概率与同一事件结果配对。 | q-one-core | P0 | 采用方法 |
| S16 | [$\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains](notes/S16-tau-bench.md) | 通过最终状态和副作用验收工作流。 | q-one-agent | P1 | 采用评测思路 |
| S17 | [ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities](notes/S17-toolsandbox.md) | 检查信息不足、状态依赖及错误工具调用。 | q-one-agent | P1 | 采用评测思路 |
| S18 | [A Stage-Based Model of Personal Informatics Systems](notes/S18-personal-informatics.md) | 围绕完整个人使用循环设计数据入口和复盘。 | q-one-life | P1 | 采用设计思路 |
| S19 | [Self-Determination Theory and the Facilitation of Intrinsic Motivation, Social Development, and Well-Being](notes/S19-self-determination.md) | 让用户选择目标、关闭追踪、否决建议，并记录使用负担。 | q-one-life | P1 | 设计约束 |
| S20 | [Leverage Points: Places to Intervene in a System](notes/S20-systems.md) | 描述行动的延迟、反馈和跨维度影响。 | q-one-life | P2 | 概念参考 |
| S21 | [Causal Inference: What If](notes/S21-what-if.md) | 未来研究行动是否带来变化时，先明确反事实问题和假设。 | q-one-life | P2 | 方法候选 |
| S22 | [Self-Supervised Learning from Images with a Joint-Embedding Predictive Architecture](notes/S22-ijepa.md) | 未来多模态表征研究的背景。 | q-one-agent | P3 | 探索 |
| S23 | [LangGraph](notes/S23-langgraph.md) | 复杂流程出现时评估恢复与人工确认机制。 | q-one-agent | P2 | 工程候选 |
| S24 | [pymoo: Multi-objective Optimization in Python](notes/S24-pymoo.md) | 以权衡集合展示时间、成本、恢复等目标。 | q-one-life | P2 | 方法参考 |
| S25 | [CONSORT extension for reporting N-of-1 trials (CENT) 2015 Statement](notes/S25-n-of-1.md) | 为未来可逆低风险习惯实验列出周期、结果与偏离记录。 | q-one-life | P2 | 精读候选 |
| S26 | [JEV / Laya Lab](notes/S26-jev-laya-lab.md) | 借鉴实验问题的组织方式。 | q-one-agent | P2 | 只读参考 |
| S27 | [Laya / Jev 学习工程](notes/S27-decisionmodel-demo.md) | 借鉴 mock/真实连接区分与输入模式教学。 | q-one-agent | P2 | 只读参考 |
| S28 | [Calibrated Decision Models for Autonomous Penetration-Testing Harnesses: JEV and Laya as System One Decision Layers for LLM-Driven Pentest Agents](notes/S28-pentest-decision.md) | 借鉴把局部决策点与完整Agent任务分开描述。 | q-one-agent | P2 | 领域参考 |
| S29 | [Fast Models, Slow Evidence: A Paired and Self-Audited Evaluation of System-1 Decision Models for LLM Agent Harnesses](notes/S29-paired-system-one.md) | 将顺序扰动、相似选项、留出阈值与完整链路成本纳入评测。 | q-one-agent | P1 | 评测参考 |
