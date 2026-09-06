# 策略模块架构工作流

状态：Cross 首个最小实盘及策略管理读模型已闭环；执行底层已离线收口，维持现有对冲仓位并等待 MT5 开市后的受控验收

更新日期：2026-09-05

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
- 2026-09-04 只读预检确认 Bybit `XAUTUSDT` 与 MT5 `XAUUSD.s` 的账户身份、品种和交易权限可用，双端均无该策略持仓或挂单；标准持久配置默认 `Live Write=false`，当前仅在 Owner 授权窗口内临时启用。
- Owner 已给出截至北京时间 2026-09-07 00:00 的新窗口；该窗口不自动开启写入，且不得超出本阶段 Cross → Funding 最小闭环范围。
- Cross 已按 Owner 指定的 `market`、1 盎司完成过一轮真实双腿开仓、持仓核对、双腿平仓、归零与权威对账；随后进行的反方向延迟测试目前仍有一组已对冲真实持仓，尚未平仓。
- Owner 要求在既有授权期内连续测试实际操作，不再每完成一笔就人工重启整套门控。当前为 Cross 两腿及 Funding 共享账户建立了短时、品种限定的受控会话并开启双层 Live Write；自动到期、Kill Switch、幂等、防重复、数量上限和异常 fail-closed 继续生效。
- 本次闭环暴露两个恢复缺口：MT5 平仓成功时可能返回不含成交量/价格的稀疏 `DONE`，以及终态聚合 Fill 与后续 component execution 可能重复投影。两项均已按订单身份和累计数量上限修复。
- 策略管理的 Cross 订单按 Batch/TradeCommand 身份归属，开平仓四张真实订单均可读取；损益按 canonical Fill 与合约乘数计算，账户净值曲线来自双腿权威余额快照。共享账户不再依靠账户与 symbol 猜测策略归属。
- 开仓和平仓端到端各约 10 秒，主要由双腿顺序执行、Venue 终态确认及预检构成；顺序对冲不并行，后续只优化无副作用读取和页面阶段反馈。
- 最新 Cross 反向开仓实测约 11.3 秒，其中真实 Venue 提交/确认不足 1 秒，主要延迟来自指令后的重复规格、报价、保证金读取以及 Bybit/MT5 冷启动。代码已将两腿只读 admission 移到最终确认前并行完成，Runtime 在 live ready 前预热 Bybit 与固定 MT5 Worker，短时复用规格/报价/保证金结果；真实持仓尚未归零，因此新版本只完成离线验证，未重启部署。
- 2026-09-05 只读现场复核仍确认 Bybit `XAUTUSDT` 空 1 与 MT5 `XAUUSD.S` 多 0.01 lot 的对冲仓位存在；未发现活动 resource claim、余额 reservation 或 Runtime `result_unknown`。Platform Live Write 与 Founder local self-approval 均为 `false`，但运行中的 Runtime 早于 admission/预热提交启动且 Live Write 仍为 `true`；两条持久化 Cross session 已越过到期时间但状态尚未被惰性过期处理。持仓未归零前不得重启、部署或改变门控，须由 Owner 明确授权具体平仓操作。
- 2026-09-05 已将多仓执行收敛为常数时间的方向增量热路径：受控生命周期支持任意多空交错与按计划剩余量部分／全部平仓，下单前不遍历历史仓位或 Fill。当前 MT5 账户只读快照确认 `marginMode=2`，因此 Bybit 使用净额方向增量，MT5 使用本地已确认开仓订单的外部 Ticket 做精确平仓。Fake Runtime 已验证 `多1 → 空1 → 多1` 及按不同计划依次平仓的双端净仓变化并最终归零；核心市价、FOK/Limit、统一 TP/SL Close Action 与部分平仓测试共 37 项通过。该离线证据不代表已部署或取得新实盘授权。
- 交易平台不设置 1 盎司产品上限；`cross_spread_acceptance_max_quantity_oz=0` 表示不施加平台旧验收上限，实际数量继续受 Venue 最小量、步长、保证金和既有风险门控约束。页面已将单笔操作拆为“全平／部分平仓”，底部统一为“全部平仓”；部分数量沿用同一预检、确认、幂等草稿和恢复链路。本地浏览器仅验证展开与取消，未提交任何真实交易。

## 尚未满足的验收

- Platform 仍保留通用 ExecutionBatch、旧 Strategy Run、单腿 TradeCommand 和 deprecated Order 写入口；受控 Cross/Funding 实例必须在下一次部署前拒绝这些旁路，并让 lifecycle open/close 使用与正式 market-command 相同的 CEO 权限硬门。兼容 Cross market-command 已收敛到 Instruction 主链，不在封堵范围。
- Cross 通过后，Funding 尚需使用共享 UTA 的最小可成交数量完成开仓、双腿对冲、平仓和对账。
- 任一身份不一致、查询不可用、累计成交冲突、外部持仓差异或 `result_unknown` 都会停止扩展并保持 fail-closed。

## 下一动作

1. Owner 已决定在 MT5 休市期间维持现有 Cross 对冲仓位；持仓期间不得重启 Runtime、部署或改变门控，也不自动平仓。
2. 在只读与本地 Fake Gateway 下继续收口现有执行主链：对受控 Cross/Funding 实例封堵通用及旧写入旁路并补拒绝测试；限价开平仓、TP/SL、部分平仓、恢复和对账均复用同一 Instruction/Plan/Batch 合同；保持方向增量热路径，不新增同步仓位遍历或平行执行架构。
3. MT5 开市且 Owner 对具体实盘操作另行授权后，再决定现有仓位处置与包含 admission/预热优化版本的部署；其后按既有顺序验收限价与多分组真实闭环。
4. Funding 继续在 Cross 限价、多分组、恢复与对账取得外部权威证据后进行；异常、未知结果或会话到期时停止继续下单并核对外部权威状态。

## 长期权威

- 项目状态与下一步：[项目驾驶舱](../PROJECT.md)
- Platform/Runtime、VenueGateway、账户路由与 `result_unknown` 边界：[Venue Adapter Contract](../contracts/VENUE_ADAPTERS.md)
- Cross 指令、不可变计划与双腿执行语义：[Cross-Spread Execution Contract](../contracts/CROSS_SPREAD_EXECUTION.md)
- 真实账户只读观测：[Live Account Observability Contract](../contracts/LIVE_ACCOUNT_OBSERVABILITY.md)
- 恢复与日终对账：[EOD Reconciliation Contract](../contracts/EOD_RECONCILIATION.md)
- 授权、共享账户资源与受控验收：[Live Acceptance Runbook](../operations/LIVE_ACCEPTANCE_RUNBOOK.md)
