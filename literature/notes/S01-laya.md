# S01 · Laya: typed System 1 decision engine

- 来源：[Laya: typed System 1 decision engine](https://github.com/NandhaKishorM/laya)
- 类型：software；核查日期：2026-10-23
- 阅读范围：README及固定commit的许可证；全文与代码复现均未完成。
- 原来源内容概述：通过封闭问题返回 choice、score、noul 类型结果；README 描述了 checkpoint 路由。
- 本项目拟借鉴（设计判断）：为重复的局部判断提供可替换的本地 provider。
- 局限与适用条件：官方宣称的速度、精度和校准性质需要在中文个人任务中复验；分数不能直接解释为行动成功概率。
- 落点与状态：agent；计划新增 providers/laya.py；接入前固定代码与权重 revision。
- 项目结果：尚未评测；不转录外部性能数值作为本项目结果。
- 采用决策：P1 / 采用候选
- 引用键：`qone_laya`；关联假设：待建立可检验的独立假设。
- 代码快照：`0a05a45052e23ae0b887a490fe8d6d9c8cff2ab5`。
- 许可观察：固定commit的代码许可证Apache-2.0；HF模型卡标注Apache-2.0；各checkpoint及数据仍需分别核查。
