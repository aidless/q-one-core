# 本轮采用的方法与架构来源

复核日期：2026-10-25。只自主实现方法；没有复制第三方训练代码或引入模型权重。

## 共轭贝叶斯回归

- 来源：[Learning from data，第25章](https://cforssen.gitlab.io/tif285-book/content/BayesianStatistics/BayesianLinearRegression/BayesianLinearRegression_ConjugatePrior.html)。教学材料，非新研究论文；出版年份未核实。
- 阅读范围：25.1–25.3的后验和后验预测公式、25.5的限制讨论。
- 问题：小样本下同时表达回归参数与未知噪声的不确定性。
- 方法：Normal-Inverse-Gamma先验、解析后验、Student-t预测。
- 采用：`life/adaptive.py`；在线更新与批量闭式解对照，均值、协方差和beta均受测试约束。Student-t `scale` 使用方差表达式的平方根。
- 局限：条件于似然/先验/特征定义，外推和模型错设可能失败。此材料不证明本项目对个人行为有效；没有照抄页面示例代码。

## DreamerV3

- 来源：[作者项目页](https://danijar.com/dreamerv3/)、[正式发表记录](https://doi.org/10.1038/s41586-025-08744-2)。原始研究，Nature 2025；搜索结果元数据与作者页摘要交叉核验。
- 阅读范围：摘要、作者项目介绍及出版元数据；Nature正文打开遇到身份重定向，未声称精读全文。
- 核心问题：学习环境模型并用想象轨迹改进行为。
- 对项目意义：提供未来“预测后果→规划”的结构参考。
- 限制：未复现，没有接入其网络或权重；控制/游戏结果不代表人生推荐效果。本项目不采用论文的实验成绩作为验收数字。

## TD-MPC2

- 来源：[作者页](https://www.tdmpc2.com/)、[arXiv:2310.16828v2](https://arxiv.org/abs/2310.16828v2)。ICLR 2024原始研究；题名、作者、版本及会议备注核验。
- 阅读范围：摘要、作者页架构介绍和开源数据说明；未执行代码。
- 方法：隐式潜在环境模型上的局部轨迹优化。
- 对项目意义：为后续动态模型和滚动规划定义研究路线。
- 限制：当前实现是固定时域回归与组合比较，不是TD-MPC2；控制数据的状态、动作与奖励不具有个人生活语义。

## Doubly Robust Policy Evaluation and Learning

- 来源：[Microsoft Research出版记录](https://www.microsoft.com/en-us/research/publication/doubly-robust-policy-evaluation-and-learning-2/)、[作者公开PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/double_robust.pdf)。ICML 2011原始研究，Miroslav Dudík、John Langford、Lihong Li。
- 阅读范围：摘要和引言，部分反馈、奖励模型与记录策略差异。
- 对项目意义：预测误差与推荐策略价值必须分开；之后离线策略评估需要行动支持、记录策略等条件。
- 限制：当前没有实现DR估计。用户手选行动通常存在未观察混杂；不能事后补概率或默认论文保证成立。

## 延续采用的来源

个人信息学阶段模型：Li/Dey/Forlizzi作者PDF；Meadows作者档案的存量、流量与反馈概念；W3C PROV-O的实体、活动、来源区分；pymoo官方约束处理文档。前两项提供组织视角，不产生本项目的效果证据。当前图是自定义有类型图，不声明PROV-O/RDF一致性；未使用pymoo求解器。
