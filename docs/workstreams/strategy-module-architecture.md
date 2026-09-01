# 策略模块架构工作流

状态：执行框架收敛完成，等待 Owner 最小实盘验收

Owner：Founder CEO

更新日期：2026-09-01

## 当前范围与结果

Cross 与 Funding 现在共用唯一执行主链：`Strategy Action → StrategyInstruction → immutable ExecutionPlan → ExecutionBatch / TradeCommand → VenueGateway → authoritative Order / Fill → Position → Reconciliation → 页面状态`。Platform 继续拥有策略、账户绑定、计划、风险和产品交互；Execution Runtime 继续独占 Venue SDK、账户连接和订单副作用。没有新增微服务、消息总线、工作流引擎或第二套订单状态机。

`VenueGateway` 是项目现有 Runtime 合同的统一命名和薄适配，覆盖 account、positions、open orders、order、place、cancel、history 和 readiness；它不是对 vn.py 的直接依赖或移植。旧 `ExecutionGateway` 仅保留导入兼容别名，Runtime 路由与恢复代码不再依赖旧名。Bybit/MT5 Order 状态归一共用底层安全规则；`canonical_fills` 当前只用于 Runtime recovery 的重复、乱序、冲突身份和累计 overfill 防护，恢复只查询和对账，禁止重发不确定命令。

Cross Market、FOK 与 PostOnly 入口已停止直接创建 Batch。两腿账户、symbol、权限和 readiness 全部通过后，入口必须使用稳定 `idempotencyKey` 创建同一 StrategyInstruction；reduce-only、MT5 Position Ticket、执行策略与限价固化进不可变计划，再交给共享执行器。MT5 未准备好时不会创建 Instruction、Batch 或先发送 Bybit 腿。Bybit live 账户的 BTC Spot/Perp、XAUT Perp 映射和 Cross 当前固定账户的 `XAUUSD.s` 映射已补齐，避免用泛化 instrument type 误选品种。

Funding 继续由平台侧特有状态机编排 PostOnly chase 和增量 Spot release；Runtime 每次只接受 `post_only_single_attempt`，Perpetual 权威累计成交决定 Spot residual。Funding 与 Cross 共享底层命令/订单合同、result_unknown 与对账安全规则，并调用同一资源 claim/余额预约实现；不宣称两个策略共用 Funding 的增量释放状态机。

Instruction 预创建的 pending Batch 现在必须在同一个 `BEGIN IMMEDIATE` 事务内先取得完整 resource claims 和 balance reservations，再 CAS 为 executing。权威 claim 函数会精确校验已有租约，完整重放不重复预约，部分或不一致租约 fail-closed；余额不足或 account-wide transfer claim 冲突时事务整体回滚，不创建 TradeCommand。Cross 与 Funding 在同一 UTA、同 venue/instrument/symbol 上互斥，不同 symbol 在余额充足时可以并行；result_unknown、manual_intervention 与 Funding reconciling 的资源保留规则未改变。

MT5 主模型保持“一账户一固定 Terminal/Worker 实例”：Router 只按逻辑 `account_id` 选择实例，启动时验证 Login/Server，终端路径不得复用，一个实例失败不影响其他实例，重启后的 unresolved command 继续冻结该账户写入。Cross 使用 `mt5-live-main`，Short A 使用独立实例且仅监控，Short B 未绑定。Native Worker 暂作生产兼容与 fallback；没有增加第二条 HTTP 下单链，也没有在同一 Python MT5 会话中切换账户。

## 代码级采用结论

- vn.py 4.4.0（MIT）：采用 `BaseGateway`、`OrderRequest/CancelRequest`、`OrderData/TradeData/PositionData/AccountData` 的窄 Gateway/Data 边界和状态词汇；本项目保留 Decimal、Pydantic 合同和现有路由，不直接依赖其 float、EventEngine、GUI 与完整交易框架。
- NautilusTrader 本地快照（Python 1.231.0 / Rust workspace 0.61.0，LGPL-3.0）：仅采用 client/venue order identity、duplicate/out-of-order fill、cumulative overfill、restart recovery 与 reconciliation 的安全规则和测试场景；不引入 Rust 核心、事件总线、缓存或完整订单系统。
- mt5-httpapi 4.3.0（WTFPL-2.0）：采用一个 Terminal/API 实例固定一个登录、上层按 account 路由，以及 account/positions/orders/history/place/query/cancel/health 的协议形状。现有独立 Worker 已实现同一隔离模型，因此没有并行引入第二个生产 Gateway。
- MetaTrader5-Docker（MIT）与 mt5-docker-api（MIT）：只采用 Terminal/容器故障隔离、健康检查的部署边界；本轮不部署容器或服务器。
- DWX Connect（BSD-3-Clause）：只参考 Order/Deal/Position Ticket 与查询/关闭语义，不采用文件桥作为生产主路径。
- Freqtrade 2026.7-dev（GPL-3.0）：只参考 dry/live、恢复和运维状态表达；不移植代码。
- RQAlpha 本地快照（非商业 Apache 2.0、商业另行授权）：仅完成源码/API/许可证排除判断，不进入实盘链。
- XAU-60 只保留账户×策略监控和页面交互参考，不进入订单执行链。

没有复制上述项目源码。自行实现部分仅限现有 Platform/Runtime 合同适配、Decimal/时区/幂等安全边界，以及当前 Cross/Funding 业务计划；这些无法由任一候选项目在不引入其完整框架的前提下直接提供。

## 验收与剩余阻断

已由 FakeGateway、离线 fixture 和本地 stub 验证：双腿预检、稳定身份/重复点击、partial/duplicate/out-of-order fill、overfill、ACK 丢失查询恢复、result_unknown fail-closed、重启恢复、权威平仓数量、Funding 单次 attempt/cancel terminal/residual/TTL/maxMutations/Spot release，以及 MT5 固定实例路由、身份不一致拒绝、故障隔离和 unresolved 写冻结。Runtime 全量、Platform 相关纵向套件、Ruff、Pyright、前端类型检查、Cross/账户页面检查和生产构建通过。

历史 8 条 Bybit `XAUTUSDT` Runtime orphan 已通过受控 operator disposition 处置：逐条要求 exact order 不存在、命令时间窗口内 closed Order/Fill 无身份匹配、当前空仓空单及 Owner 明确确认，随后仅追加不可变审计并将 Journal 命令标记为 `resolved_absent`。原命令、payload 和历史状态保留，未删除、未标记 filled、未伪造 external order identity，处置路径不含 Venue 写操作；对应账户的旧 unknown readiness 阻断已解除。

当前没有已知代码缺陷阻止 Owner 请求新的最小手动实盘验收窗口。Platform 与 Runtime 持久配置及标准启动进程均已恢复 Live Write=false；Bybit `XAUTUSDT` 与 Cross MT5 `XAUUSD.s` 已只读确认空仓空单、账户与 symbol 数据可用。当前外部人工前置项只剩 Cross Terminal 的 Algo/Expert Trading 开关；开启后仍须在新授权窗口内完成写前复核。Short A 外部 Python API 一次性授权只影响其独立监控，不是 Cross 前置条件。本阶段记录不构成任何真实交易授权。

`docs/PROJECT.md` 当前存在并行全局文档改动，本轮不覆盖。文档 Owner 仍需收口两项冲突事实：2026-08-25 实盘授权窗口已经过期，不构成当前授权；其中“Cross/Short A 共用单 Terminal 切换”的旧表述与当前一账户一固定实例模型冲突。

## 下一动作

Owner 开启 Cross Terminal Algo/Expert Trading 后，可请求新的、操作明确且有时限的最小实盘窗口；获批后按 `docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md` 手动完成 Cross 最小开仓、双腿核对、平仓与对账，通过后再以共享 UTA 最小仓位验收 Funding。任何身份不一致、查询不可用、累计成交冲突或 result_unknown 都立即停止扩展。

长期权威仍为 `docs/PROJECT.md`、`docs/contracts/VENUE_ADAPTERS.md`、`docs/contracts/CROSS_SPREAD_EXECUTION.md`、`docs/contracts/LIVE_ACCOUNT_OBSERVABILITY.md`、`docs/contracts/EOD_RECONCILIATION.md` 与 `docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md`。
