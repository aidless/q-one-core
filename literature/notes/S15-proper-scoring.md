# S15 · Strictly Proper Scoring Rules, Prediction, and Estimation

- 来源：[Strictly Proper Scoring Rules, Prediction, and Estimation](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf)
- 类型：review_article；核查日期：2026-10-23
- 阅读范围：原文首页及选定段落；全文与代码复现均未完成。
- 原来源内容概述：讨论用于概率预测评估的适当评分规则。
- 本项目拟借鉴（设计判断）：将已定义预测事件的概率与同一事件结果配对。
- 局限与适用条件：Brier 不是完整的校准诊断；如果执行了另一个选项，原推荐选项结果可能未观测。
- 落点与状态：core；已修正 report.py 中 override 的预测与结果配对并通过7项开发测试（含合成CLI流程）；完整事件预测契约仍待补齐。
- 项目结果：尚未评测；不转录外部性能数值作为本项目结果。
- 采用决策：P0 / 采用方法
- 引用键：`qone_proper_scoring`；关联假设：待建立可检验的独立假设。
