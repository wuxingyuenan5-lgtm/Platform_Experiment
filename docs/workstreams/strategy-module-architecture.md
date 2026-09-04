# 策略模块架构工作流

状态：执行框架已收敛，等待新的最小实盘授权与 Cross Terminal 外部条件

更新日期：2026-09-04

## 阶段目标与范围

本阶段把 Cross 与 Funding 收敛到一套简洁、统一且可恢复的策略执行框架，并以真实账户最小开仓、双腿核对、平仓和对账闭环作为阶段验收。Platform 负责策略意图、账户绑定、不可变计划、风险编排和页面状态；Execution Runtime 独占 Venue SDK、账户连接与订单副作用。

阶段不授权真实交易、资金划转、外部部署或凭据变更，也不扩展海内外价差、抄底、短线交易员 B 等产品范围。Live Write 继续默认关闭，任何真实写入仍需 Owner 提供新的、操作明确且有时限的授权。

## 当前已经成立

- Cross 与 Funding 共用主链：`Strategy Action → StrategyInstruction → immutable ExecutionPlan → ExecutionBatch / TradeCommand → VenueGateway → authoritative Order / Fill → Position → Reconciliation → 页面状态`。
- Cross 的新旧入口均进入同一 Instruction/Plan 路径；两腿账户、品种、权限和 readiness 必须在创建执行意图前通过，MT5 不可执行时不得先开 Bybit 腿。
- Funding 保留平台侧有界 PostOnly 编排，Runtime 每次只执行一个 PostOnly attempt；两种策略共用订单身份、累计成交、恢复、对账及账户资源保护。
- Funding 与 Cross 可绑定同一逻辑 Bybit UTA；资源 claim 与余额 reservation 在 dispatch 前原子取得。同一账户同一市场资源互斥，不同 symbol 仅在权威可用余额足够时并行。
- MT5 使用“一逻辑账户一固定 Terminal/Worker”；Cross 与 Short A 使用独立固定实例，禁止在同一 Python 会话中切换账户，Short B 保持未绑定。
- `result_unknown`、人工介入和 Funding 对账中状态继续保留相应写入冻结、资源与余额预约；恢复只查询和对账，不重发不确定命令。
- 历史 Cross orphan 已在保留原始事实的前提下完成责任处置，当前没有遗留 unknown 计数；该结论不构成新的交易授权。
- Platform 与 Runtime 的标准持久配置及运行默认均为 `Live Write=false`，当前没有有效实盘窗口。

## 尚未满足的验收

- Owner 尚未提供新的、操作明确且有时限的 Cross/Funding 最小实盘授权。
- Cross 固定 Terminal 的 Algo/Expert Trading 外部开关仍需 Owner 确认已启用；只读可用不等于执行 ready。
- Cross 尚需在新授权窗口内完成最小开仓、Bybit/MT5 双腿权威成交与持仓核对、平仓、归零和对账。
- Cross 通过后，Funding 尚需使用共享 UTA 的最小可成交数量完成开仓、双腿对冲、平仓和对账。
- 任一身份不一致、查询不可用、累计成交冲突、外部持仓差异或 `result_unknown` 都会停止扩展并保持 fail-closed。

## 下一动作

1. Owner 确认 Cross 固定 Terminal 的 Algo/Expert Trading 已开启。
2. Owner 决定是否签发新的 Cross → Funding 最小实盘窗口；旧窗口已经过期，不能复用。
3. 获得授权后，操作方按受控实盘 Runbook 先完成 Cross 全闭环，再完成 Funding 最小闭环，并在结束、失败或超时后强制恢复只读。
4. 两个闭环取得外部权威证据后，将最终状态回填 `docs/PROJECT.md` 与对应长期权威，完成本阶段并删除本文件。

## 长期权威

- 项目状态与下一步：[项目驾驶舱](../PROJECT.md)
- Platform/Runtime、VenueGateway、账户路由与 `result_unknown` 边界：[Venue Adapter Contract](../contracts/VENUE_ADAPTERS.md)
- Cross 指令、不可变计划与双腿执行语义：[Cross-Spread Execution Contract](../contracts/CROSS_SPREAD_EXECUTION.md)
- 真实账户只读观测：[Live Account Observability Contract](../contracts/LIVE_ACCOUNT_OBSERVABILITY.md)
- 恢复与日终对账：[EOD Reconciliation Contract](../contracts/EOD_RECONCILIATION.md)
- 授权、共享账户资源与受控验收：[Live Acceptance Runbook](../operations/LIVE_ACCEPTANCE_RUNBOOK.md)
