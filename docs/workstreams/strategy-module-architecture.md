# 策略模块架构工作流

状态：Cross 首个最小实盘及策略管理读模型已闭环；执行底层已离线收口，维持现有对冲仓位并等待 MT5 开市后的受控验收

更新日期：2026-09-06

## 阶段目标与范围

本阶段把 Cross 与 Funding 收敛到一套简洁、统一且可恢复的策略执行框架，并以真实账户最小开仓、双腿核对、平仓和对账闭环作为阶段验收。Platform 负责策略意图、账户绑定、不可变计划、风险编排和页面状态；Execution Runtime 独占 Venue SDK、账户连接与订单副作用。

阶段不授权真实交易、资金划转、外部部署或凭据变更，也不扩展海内外价差、抄底、短线交易员 BL 等产品范围。Live Write 继续默认关闭，任何真实写入仍需 Owner 提供新的、操作明确且有时限的授权。

## 当前已经成立

- Cross 与 Funding 共用主链：`Strategy Action → StrategyInstruction → immutable ExecutionPlan → ExecutionBatch / TradeCommand → VenueGateway → authoritative Order / Fill → Position → Reconciliation → 页面状态`。
- Cross 的新旧入口均进入同一 Instruction/Plan 路径；两腿账户、品种、权限和 readiness 必须在创建执行意图前通过，MT5 不可执行时不得先开 Bybit 腿。
- Funding 保留平台侧有界 PostOnly 编排，Runtime 每次只执行一个 PostOnly attempt；两种策略共用订单身份、累计成交、恢复、对账及账户资源保护。
- Funding 与 Cross 可绑定同一逻辑 Bybit UTA；资源 claim 与余额 reservation 在 dispatch 前原子取得。同一账户同一市场资源互斥，不同 symbol 仅在权威可用余额足够时并行。
- MT5 使用“一逻辑账户一固定 Terminal/Worker”；Cross 使用独立固定实例，禁止在同一 Python 会话中切换账户；短线交易员 WW 绑定 `account_mt5_short_term_a` 只读监控，BL 保持未绑定。
- `result_unknown`、人工介入和 Funding 对账中状态继续保留相应写入冻结、资源与余额预约；恢复只查询和对账，不重发不确定命令。
- 历史 Cross orphan 已在保留原始事实的前提下完成责任处置，当前没有遗留 unknown 计数；该结论不构成新的交易授权。
- 2026-09-04 只读预检确认 Bybit `XAUTUSDT` 与 MT5 `XAUUSD.s` 的账户身份、品种和交易权限可用，双端均无该策略持仓或挂单；标准持久配置默认 `Live Write=false`，当前仅在 Owner 授权窗口内临时启用。
- Owner 已给出截至北京时间 2026-09-07 00:00 的新窗口；该窗口不自动开启写入，且不得超出本阶段 Cross → Funding 最小闭环范围。
- Cross 已按 Owner 指定的 `market`、1 盎司完成过一轮真实双腿开仓、持仓核对、双腿平仓、归零与权威对账；随后进行的反方向延迟测试目前仍有一组已对冲真实持仓，尚未平仓。
- Owner 要求在既有授权期内连续测试实际操作，不再每完成一笔就人工重启整套门控。当前为 Cross 两腿及 Funding 共享账户建立了短时、品种限定的受控会话并开启双层 Live Write；自动到期、Kill Switch、幂等、防重复、数量上限和异常 fail-closed 继续生效。
- 本次闭环暴露两个恢复缺口：MT5 平仓成功时可能返回不含成交量/价格的稀疏 `DONE`，以及终态聚合 Fill 与后续 component execution 可能重复投影。两项均已按订单身份和累计数量上限修复。
- 策略管理的 Cross 订单按 Batch/TradeCommand 身份归属，开平仓四张真实订单均可读取；损益按 canonical Fill 与合约乘数计算，账户净值曲线来自双腿权威余额快照。共享账户不再依靠账户与 symbol 猜测策略归属。
- 策略管理的账户资金与净值曲线读取账户级 `account_risk_snapshots`；抄底账户使用 Bybit `asset overview.totalEquity` 的 USD 全账户估值，纳入 Unified Trading、Earn/RWA、Alpha、TradFi 等账户结构；Cross/Funding 的 Bybit 账户继续使用 Unified Trading `wallet-balance` 的 USDT 站内交易口径。Cross 的 MT5 账户独立读取，禁止从 Bybit 全账户汇总中重复计入。BYUSDT、XPL 等资产明细不作为账户净值。同步非 `ready` 时不展示旧快照，避免把过期 MT5 资金当作当前资金；净值曲线仅返回最近 1000 个展示点，原始快照保留。
- Platform API 已具备后台只读同步：每 30 秒从 Runtime 采集已绑定账户，账户间并发、单次同步互斥，页面只读取数据库投影；后台同步失败不会触发任何订单或资金写入。本地 Runtime 所需的 Cross/WW MT5 终端保持运行但由 `scripts/dev-platform.ps1` 自动隐藏窗口；WW 使用独立 portable 副本和 MCP `22347`，Cross 使用 `22346`，不得重新切回原共享终端实例。
- 策略管理首屏不再预加载 Cross 的订单审计模块；订单/成交/批次及 audit 观测仅在进入“订单信息”子页时加载，避免与损益/账户资金首屏重复读取。
- Cross 订单与成交列表现在由 Platform API 按 `strategyInstanceId` 在数据库查询阶段过滤，保留无参数全量接口兼容；`trade_commands(strategy_instance_id, created_at)`、`orders(command_id, created_at)` 与 `fills(order_id, occurred_at)` 已补齐查询索引，页面不再为 Cross 拉取全局历史后本地筛选。
- 管理概览的同步表结构检查已收敛为每个数据库进程/路径一次；本地实测首个请求约 235ms，后续请求约 13–19ms。剩余首请求耗时主要来自少数可交易策略的 readiness 组装，后续可在不改变交易门禁的前提下改为后台只读投影。
- Cross 市场数据已增加独立的低频后台采集：默认每 60 秒写入价差、资金费率输入及买卖两侧库存费输入，页面访问不再是记录这些数据的前提；已结算的 funding/swap/fee 仍走经济事件与 financial fact 链路，不能由行情快照代替。
- 前端行为保持不变但降低资源占用：Vite Windows 文件轮询默认关闭（网络盘/Docker 场景可用 `VITE_USE_FILE_POLLING=true` 且 1 秒间隔显式启用）；Cross 展示页隐藏时暂停 15 秒展示刷新、恢复可见立即补拉；订单、成交、最新账户余额和权益历史同时请求时按策略/账户键做请求去重。TradingView 组件原已有可视区域懒加载，本轮不重复改造。
- Cross 策略管理按子页拆分读取：进入“账户资金”只读取绑定、账户风险、当前行情和资金历史；进入“策略损益”后才读取成交、订单、批次、品种和策略 PnL；“订单信息”继续由订单模块按需读取。交易数据口径不变，只减少首屏无关读取。
- 开仓和平仓端到端各约 10 秒，主要由双腿顺序执行、Venue 终态确认及预检构成；顺序对冲不并行，后续只优化无副作用读取和页面阶段反馈。
- 最新 Cross 反向开仓实测约 11.3 秒，其中真实 Venue 提交/确认不足 1 秒，主要延迟来自指令后的重复规格、报价、保证金读取以及 Bybit/MT5 冷启动。代码已将两腿只读 admission 移到最终确认前并行完成，Runtime 在 live ready 前预热 Bybit 与固定 MT5 Worker，短时复用规格/报价/保证金结果；真实持仓尚未归零，因此新版本只完成离线验证，未重启部署。
- 2026-09-05 只读现场复核仍确认 Bybit `XAUTUSDT` 空 1 与 MT5 `XAUUSD.S` 多 0.01 lot 的对冲仓位存在；未发现活动 resource claim、余额 reservation 或 Runtime `result_unknown`。Platform Live Write 与 Founder local self-approval 均为 `false`，但运行中的 Runtime 早于 admission/预热提交启动且 Live Write 仍为 `true`；两条持久化 Cross session 已越过到期时间但状态尚未被惰性过期处理。持仓未归零前不得重启、部署或改变门控，须由 Owner 明确授权具体平仓操作。
- 2026-09-06 WW 的 MT5 终端底层问题已修复：原桌面终端、Cross Bybit 终端和 Runtime worker 争用 MT5 MCP `22346`，且 portable 终端首次编译超过 worker 固定 15 秒启动窗口，造成 `(-10005, IPC timeout)`/`runtime_unavailable`。已为 WW 创建独立 portable 终端副本，改用 MCP `22347`，并将 worker 启动等待改为动态窗口；当前 `account_mt5_short_term_a` 已恢复 `ready`，只读快照已返回 `233089709 / Exness-MT5Real5`、USD 资金、订单和成交。
- 2026-09-05 已将多仓执行收敛为常数时间的方向增量热路径：受控生命周期支持任意多空交错与按计划剩余量部分／全部平仓，下单前不遍历历史仓位或 Fill。当前 MT5 账户只读快照确认 `marginMode=2`，因此 Bybit 使用净额方向增量，MT5 使用本地已确认开仓订单的外部 Ticket 做精确平仓。Fake Runtime 已验证 `多1 → 空1 → 多1` 及按不同计划依次平仓的双端净仓变化并最终归零；核心市价、FOK/Limit、统一 TP/SL Close Action 与部分平仓测试共 37 项通过。该离线证据不代表已部署或取得新实盘授权。
- 交易平台不设置 1 盎司产品上限；`cross_spread_acceptance_max_quantity_oz=0` 表示不施加平台旧验收上限，实际数量继续受 Venue 最小量、步长、保证金和既有风险门控约束。页面已将单笔操作拆为“全平／部分平仓”，底部统一为“全部平仓”；部分数量沿用同一预检、确认、幂等草稿和恢复链路。本地浏览器仅验证展开与取消，未提交任何真实交易。
- 已为既有 Cross 持仓组补齐 Exit Plan 编辑：持仓总览的 TP/SL 单元格只绑定其匹配的 `active` Exit Plan，CEO 可补充或修改阈值、TP/SL 的市价／限价执行方式及限价策略；该 PATCH 只更新 Platform 内的计划，不会立即平仓或触发外部写入。自动触发使用该计划当前剩余数量；既有人工部分平仓会原子扣减剩余数量并沿用设置。页面不再将全局第一条 Exit Plan 错投影到其他持仓行；有 MT5 Ticket 时优先按 Ticket 绑定，多个同向／同量候选仍无法唯一确认时不显示可编辑计划，避免将其他订单错误关联到 TP/SL。
- Cross 持仓概览现按每一行实际价差决定颜色；多持仓组时顶部爆仓价不再误取第一行，改为提示查看各持仓行；Bybit 与 MT5 单边损益分别显示正负颜色。
- 受控 Cross/Funding 公开旁路已在路由边界封堵：通用 TradeCommand、ExecutionBatch、旧 Strategy Run、通用 StrategyInstruction 对两条受控策略直接返回 403；无策略身份的 deprecated raw Order 对任一有效受控交易账户返回 403。专用 lifecycle/instruction 仍走同一 StrategyInstruction → ExecutionPlan → ExecutionBatch 链与 CEO 权限边界。该源码变更尚待 Platform API 重启加载，未触碰 Runtime。

## 尚未满足的验收

- 本地运行中的 Platform API 尚未加载 ExitPlan 编辑及公开旁路封堵路由；需在不重启 Runtime 的前提下重启 API 后，以 OpenAPI 与拒绝测试复核。兼容 Cross market-command 已收敛到 Instruction 主链，不在封堵范围。
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
