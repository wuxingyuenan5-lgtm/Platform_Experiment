# 策略模块架构工作流

状态：`in_progress`  
Owner：Founder CEO  
更新时间：2026-08-25  
当前基线：Platform `0.11.2` 候选；已包含 Funding 收口、CEO 会话候选和本工作流 MT5 协调修正

本文件是“策略模块架构”活跃阶段的唯一接续入口。它只维护当前范围、验收门、阻断和下一动作；稳定产品、合同和运维事实仍归属下方列出的长期权威文档。

## 当前目标与范围

把创始人本地策略平台收敛为可恢复、可审计的真实账户闭环。本阶段把 Cross 与 Funding 作为同一个实盘测试工作流：二者共用逻辑账户 `bybit-live-main`，Cross 的另一腿使用 `mt5-live-main`。策略管理继续统一展示六个策略；Bottom 和 Short A 只读，Short B 暂不绑定，海内外价差暂停。

Cross 保留开仓、平仓、移动双边资金三个模板；MT5 Transfer API 未验证时继续使用辅助模式。Funding 不使用生产 mock，开平仓必须进入 StrategyInstruction、immutable Plan、单一 Batch、权威成交、恢复和对账路径。共享账户通过 claim、余额预约和稳定业务身份避免两个 Alpha 策略互相干扰。

当前不建设通用组合引擎、消息队列或新增服务，不开放 Bottom/Short 的交易，不做自动选币、自动定仓、无人值守 Live Write、未验证的自动资金划转或海内外价差实盘。

长期边界保持不变：Venue SDK 与外部副作用只在 Runtime；ACK 不等于 Fill；`result_unknown`、身份不一致和查询不可用均 fail-closed；FinancialFact 才是正式金融事实入口。任何真实订单仍需要 Owner 对具体策略、账户、Symbol、数量、执行政策和绝对过期时间作本次授权。

## 当前快照

本地代码门已经通过。三服务常驻和登录链路可用；共享 UTA、Bottom、Cross MT5、Short A 均完成真实账户只读预检，Short A 切换后能恢复主 MT5 账号。Cross 开/单平/批平和三模板、Funding Spot/Perp context、开平仓、自动轮询、幂等恢复、权威已平量和 active/history 均有本地回归证据。

CEO 面板现在按真实 binding 建立会话：Funding 单选 1 个 Bybit 会话，Cross 单选 1 个 Bybit 加 1 个 MT5 会话，两者同选共 3 个 strategy/account 会话。Funding Symbol 来自 execution context；Cross Bybit 与实际 MT5 Broker Symbol 来自只读 observability。缺少权威 Symbol、账户会话、双 Live Write、Kill Switch 条件或存在 unresolved `result_unknown` 时继续显示 blocked；approved 不等于 armed/ready。

最近验证包括 Platform 相关 53 tests、Runtime MT5 相关 17 tests，以及 Platform/Runtime Pyright、相关 Ruff、前端 typecheck、行为测试和 production build。当前只读事实为 Funding `BTCUSDT` Spot/Perp、Cross Bybit `XAUTUSDT`、Cross MT5 `XAUUSD.s`；approved session 为 0，Funding/Cross unresolved `result_unknown` 为 0。

尚未完成的是外部实盘证据：没有真实开仓、平仓、Funding Settlement、差异核对或 EOD。普通启动器会强制 Platform Live Write、Runtime Live Write 和 founder-demo CEO 自审批为 `false`，因此当前运行中的服务仍是安全只读状态；页面只显示这些门，不自行开启它们。

## 下一动作与 Owner 决策

下一步不是继续泛化优化，而是由 Owner 定义一次受控实盘窗口：选择 Funding Pair、Cross/Funding 每腿最大数量与执行政策、窗口开始和绝对过期，并决定首次在同一窗口内顺序发起还是实际并行。若仍由同一个 CEO 申请并审批，还需明确授权仅在该本地最小测试窗口启用现有 `founder_demo_live_acceptance_enabled` 例外；默认继续关闭。

获得本次明确授权后，运维应以受控方式启动双 Live Write，在页面创建并审批对应的 3 个账户会话，先确认 Cross/Funding 分别 ready，再执行最小真实开仓、核对、对应平仓、Venue reconciliation、EOD 和强制复位。任何一步出现 unknown、账户或 Symbol 不一致、会话缺失或查询不可用都停止新副作用。

## 关联长期权威文档

- 产品总边界：`docs/product/modules/策略.md`
- Funding 产品合同：`docs/product/strategies/资金费率套利.md`
- Cross 产品合同：`docs/product/strategies/跨所黄金价差.md`
- 系统边界：`docs/architecture/SYSTEM_MAP.md`
- Platform/Runtime API：`docs/contracts/API.md`
- Cross 执行合同：`docs/contracts/CROSS_SPREAD_EXECUTION.md`
- Venue 与只读查询：`docs/contracts/VENUE_ADAPTERS.md`、`docs/contracts/LIVE_ACCOUNT_OBSERVABILITY.md`
- 金融事实与对账：`docs/contracts/FINANCIAL_FACTS.md`、`docs/contracts/EOD_RECONCILIATION.md`
- 受控实盘操作：`docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md`
- 稳定工程基线：`docs/BASELINE.md`

## 阶段结束时的归并清单

全部验收门满足后才执行：

- 将稳定的 Funding 开平仓、组合、恢复和 shared-account 语义归并到对应产品与合同文档。
- 将最终 Runtime spot/perp、MT5 session/write lock 和 capability 语义归并到 Venue/API 合同。
- 将受控会话审批、页面操作、强制复位和联合测试顺序归并到 Live Acceptance Runbook。
- 将真实 Funding Settlement、关闭、EOD 与差异处置保留到批准的 operator evidence 位置，不写入项目驾驶舱过程记录。
- 根据最终证据只更新 `docs/PROJECT.md` 的结果、阻断和下一动作，不改变其结构。
- 删除本文件；不建立阶段 archive，历史由 Git 保留。
