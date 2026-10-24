# S13 · On Calibration of Modern Neural Networks

- 来源：[On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599)
- 类型：paper；核查日期：2026-10-23
- 阅读范围：摘要及元数据；全文与代码复现均未完成。
- 原来源内容概述：研究预测置信度与正确率的失配以及温度缩放等后处理方法。
- 本项目拟借鉴（设计判断）：校准分类概率，按任务、模型版本和数据窗口报告。
- 局限与适用条件：温度缩放需独立校准集；同一模型换领域、输入或版本后不能沿用结论。
- 落点与状态：core；计划扩展 report.py 与校准数据拆分协议。
- 项目结果：尚未评测；不转录外部性能数值作为本项目结果。
- 采用决策：P0 / 采用方法
- 引用键：`qone_calibration`；关联假设：待建立可检验的独立假设。
