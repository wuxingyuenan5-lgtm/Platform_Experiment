# 策略模块架构工作流

状态：`in_progress`  
Owner：Founder CEO  
更新时间：2026-08-26  
当前基线：Platform `0.11.2` 候选；已包含 Funding 收口、CEO 会话候选和本工作流 MT5 协调修正

本文件是“策略模块架构”活跃阶段的唯一接续入口。它只维护当前范围、验收门、阻断和下一动作；稳定产品、合同和运维事实仍归属下方列出的长期权威文档。

## 当前目标与范围

把创始人本地策略平台收敛为可恢复、可审计的真实账户闭环。本阶段把 Cross 与 Funding 作为同一个实盘测试工作流：二者共用逻辑账户 `bybit-live-main`，Cross 的另一腿使用 `mt5-live-main`。策略管理继续统一展示六个策略；Bottom 和 Short A 只读，Short B 暂不绑定，海内外价差暂停。

Cross 保留开仓、平仓、移动双边资金三个模板；Owner 已明确官网手工操作不构成“移动双边资金”验收，第三模板必须最终接入可验证的 Bybit MT5/TradFi 正式划转能力。Funding 不使用生产 mock，开平仓必须进入 StrategyInstruction、immutable Plan、单一 Batch、权威成交、恢复和对账路径。共享账户通过 claim、余额预约和稳定业务身份避免两个 Alpha 策略互相干扰。

当前不建设通用组合引擎、消息队列或新增服务，不开放 Bottom/Short 的交易，不做自动选币、自动定仓、无人值守 Live Write、未验证的自动资金划转或海内外价差实盘。

长期边界保持不变：Venue SDK 与外部副作用只在 Runtime；ACK 不等于 Fill；`result_unknown`、身份不一致和查询不可用均 fail-closed；FinancialFact 才是正式金融事实入口。任何真实订单仍需要 Owner 对具体策略、账户、Symbol、数量、执行政策和绝对过期时间作本次授权。

## 当前快照

本地代码门已经通过。三服务常驻和登录链路可用；共享 UTA、Bottom、Cross MT5、Short A 均完成真实账户只读预检，Short A 切换后能恢复主 MT5 账号。Cross 开/单平/批平和三模板、Funding Spot/Perp context、开平仓、自动轮询、幂等恢复、权威已平量和 active/history 均有本地回归证据。

Funding 行情分析三组件已逐字恢复到 `731e21bb` 之前的 Owner 历史设计，继续使用原完整行情板、历史资金费率图、期现与借贷详情及其原筛选交互，不接入或改写实时执行数据；交易执行页单独使用真实 execution context、持仓组合与指令恢复链路，不再使用生产 mock。联调诊断卡和工程状态字段不再替代产品界面。策略管理中的“CEO 实盘测试会话”及其专用前端状态逻辑已移除。LiveTradingSession、Kill Switch、额度、幂等和 fail-closed 继续作为后台安全机制存在，但不构成策略产品页面或产品概念。

Cross 的辅助资金划转实验已经证明不能满足产品验收：真实账户路径只建立记录、claim 和余额预约，Runtime 明确不调用真实划转接口，仍要求 Owner 到 Bybit 官网操作。Owner 已否决把该模式视为可用产品能力。2026-08-25 的旧版 81 USDT 记录和 2026-08-26 的 300 USDT 实验记录均已在确认无外部副作用后审计关闭并释放资源；后者还暴露出可用余额小幅波动会误阻取消，不能用账户可用余额差额代替权威转账身份。

最近验证包括 Platform 相关 53 tests、Runtime MT5 相关 17 tests，以及 Platform/Runtime Pyright、相关 Ruff、前端 typecheck、行为测试和 production build。Funding 历史行情与真实执行页已通过聚焦浏览器验收；多 MT5 凭据引用分类和只读预检状态枚举已与 Runtime 合同对齐，Bybit/MT5 当前只读预检通过。当前只读事实为 Funding `BTCUSDT` Spot/Perp、Cross Bybit `XAUTUSDT`、Cross MT5 `XAUUSD.s`；approved session 为 0，Funding/Cross unresolved `result_unknown` 为 0。

尚未完成的是外部实盘证据：没有真实开仓、平仓、Funding Settlement、差异核对或 EOD。普通启动器会强制 Platform Live Write、Runtime Live Write 和 founder-demo CEO 自审批为 `false`，因此当前运行中的服务仍是安全只读状态；页面只显示这些门，不自行开启它们。2026-08-25 当前窗口的只读基线发现 Cross 的 `mt5-live-main` 没有可用资金且终端 `trade_allowed=false`，因此在 Owner 完成 MT5 入金并开启终端算法交易前，不得发送 Bybit 单边订单或开启写入门。

Owner 已授权 2026-08-25 16:55–24:00（北京时间）的 Cross + Funding 最小实盘窗口，并允许仅在该窗口临时启用双 Live Write 与 founder-demo CEO 本地自审批。执行必须串行：先以 Cross `XAUTUSDT` + `XAUUSD.s`、每腿 1 盎司完成开仓、核对、平仓和对账；由于共享 Bybit UTA 约 500 USDT、并行时资金不足，Cross 完全退出并复核余额后，Funding 才以 `BTCUSDT` Spot + Perpetual 和账户实际可用资金下的最小可开仓位执行 `post_only_chase`。完成后立即撤销会话并关闭全部写入门控。

## 下一动作与 Owner 决策

Funding 历史行情设计与真实交易执行页已经完成聚焦浏览器验收，Bybit/MT5 只读预检也已通过。下一动作不是继续官网辅助流程，而是取得并验证 Bybit 对该账户开放的 MT5/TradFi Transfer 正式接口、账户类型和权威查询合同，再由 Runtime 实现真实划转与对账；在此之前第三模板不得宣称可用。若 Bybit 未向该账户提供正式接口，该能力保持外部阻断，不能以网页自动化代替。MT5 入金完成后仍需 Owner 另行给出新的 Cross/Funding 实盘交易窗口；2026-08-25 的交易授权不顺延。

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
