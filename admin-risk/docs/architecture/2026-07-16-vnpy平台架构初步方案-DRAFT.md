# vn.py 平台架构初步方案（已被替代）

状态：`superseded`  
原文日期：2026-07-16  
替代日期：2026-07-17  
适用分支：`refactor/frontend-architecture-v6`

## 1. 状态说明

本文原用于讨论 Variable-Global 与 vn.py 的结合方式，但文件标题和部分表述容易造成以下误解：

- 平台总体架构由 vn.py 主导。
- 需要先决定某个项目是不是“唯一运行时”。
- 其他开源项目只能围绕 vn.py 进行选择。
- 平台业务模型需要适配外部框架对象。

这些都不是当前正确前提。

Variable-Global 是自行设计和运行的完整平台。vn.py、aiomql、Freqtrade、rotki、NautilusTrader、PyTrader、官方 SDK 和其他项目，只是能力参考或组件候选。

## 2. 替代文档

后续讨论以以下两份 DRAFT 为准：

1. `2026-07-17-Variable-Global交易平台总体架构方案-DRAFT.md`
   - 从平台真实需求出发定义总体分层、业务领域、执行基础设施、数据账本和运行保障。
   - 允许讨论结果反向调整现有 active 架构。

2. `2026-07-17-开源与外部能力采用矩阵-DRAFT.md`
   - 按能力分别评估自建、直接复用、封装复用、Fork、设计参考或暂缓。
   - 不再按项目整体决定平台架构。

## 3. 历史内容说明

原文中的以下研究方向仍有参考价值，但已在新文档中重新组织：

- vn.py EventEngine、MainEngine、Gateway、OMS、RiskManager、SpreadTrading 和 AlgoTrading。
- aiomql 的 MT5 初始化、异步、重试和 Session 设计。
- Freqtrade 的策略实例和运行控制思想。
- rotki 的经济事件、账本、数据缺失和报告版本思想。
- NautilusTrader 的状态机、幂等、恢复、对账和降级思想。
- PyTrader 的远程 MT4／MT5 和 EA 桥接思路。
- MT5 多账户 Worker、Crypto、CTP、执行、风控、恢复和损益等讨论。

如需追溯原始完整内容，请通过 Git 历史查看本文件在替代前的版本。

## 4. 使用规则

- 本文件不再作为架构讨论和实施依据。
- 不从本文复制旧领域对象、旧状态枚举、旧策略名称或旧路由。
- 新结论先进入新 DRAFT 讨论，确认后再通过 active 架构文档和 ADR 生效。
