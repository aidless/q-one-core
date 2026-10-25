# 在线校准候选与采用决策

日期：2026-10-25。

## Gibbs / Candès 2021，ACI

- 来源：[论文正式全文](https://papers.nips.cc/paper/2021/file/0d441de75945e5acbc865406fc9a2559-Paper.pdf)、[arXiv:2106.00170v3](https://arxiv.org/abs/2106.00170v3)。原始研究，NeurIPS 2021。
- 问题：分布随时间变化时持续调整预测集。
- 方法：根据预测集漏覆盖事件更新误覆盖参数 `alpha_next = alpha_now + gamma * (alpha_target - error)`。
- 阅读：摘要、更新公式(2)、第4.1节的长期频率及单时点保证区别。
- 意义：提供可复算的在线反馈基线。
- 限制：Q-One使用滚动标准化残差、按行动组合分组、支持延迟登记并拒绝不有限区间，协议不同；不迁移原文保证。没有复制论文实验结果。

## MAPIE 官方实现，当前发布v1.6.0

- 来源：[官方仓库](https://github.com/scikit-learn-contrib/MAPIE)、[固定版本代码](https://github.com/scikit-learn-contrib/MAPIE/blob/f1cc3d07460b2d7198f557d40d60cd563c51822b/mapie/regression/time_series_regression.py)。GitHub发布记录日期2026-10-19。
- 阅读：`adapt_conformal_inference` 中的已知标签更新及 `LICENSE`；仓库BSD-3-Clause。
- 意义：核对当前库的API与ACI实现处理方式。
- 限制：不是Q-One的运行依赖。我们的结果延迟处理使用发出预测时的区间，归一化残差和不有限状态处理也不同；不称作MAPIE等价实现。

## Bhatnagar 等 2023，SAOCP

- 来源：[论文](https://arxiv.org/abs/2302.07869)、[作者官方实现](https://github.com/salesforce/online_conformal/tree/95790a9b9e4061166e6d7a8a13282e019b1a8663)。仓库元数据声明Apache-2.0。
- 阅读：摘要、引言、README中的使用约定。
- 问题：除了全程误差，还关心局部时间窗口中的性能。
- 意义：后续候选，提示本轮必须包含突变场景。
- 限制：尚未实现SAOCP或复现实验。官方接口涉及预期最大分数尺度；当前人生指标常缺少可信的界限，不能直接移植保证。

## Cherenson / Panagou，SI-OCP 2026

- 来源：[作者实验室页面](https://dasc-lab.github.io/papers/2026/2026-siocp/)、[代码仓库](https://github.com/dcherenson/staggered-integral-ocp/tree/25fd56283b37849a08c859ab5be9a345bb2bfcb2)。作者页标注IEEE CDC 2026，未独立核实正式会议出版状态。
- 阅读：作者摘要、仓库元数据；license=null。
- 方法：面向动态系统适应的积分分数与多步覆盖处理。
- 意义：新的多步研究候选。
- 限制：当前Q-One没有同等的连续动力学和控制器前提。未复制、运行或集成未声明许可的仓库代码，未借用其安全保证。

## 本轮决定

ACI候选在稳定合成场景中改善区间评分，突变与噪声增加场景未通过提前冻结的采用条件。因此只保留影子评测与延迟结果凭据，**不改变自动推荐使用的区间**。对照证据位于 `artifacts/calibration-evaluation/v1/`。没有因新技术名气或发布日期更近而替换内核。
