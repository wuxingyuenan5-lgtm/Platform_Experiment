# Cross-Spread Execution Contract

状态：`active contract`

产品范围：[跨所黄金价差](../product/strategies/跨所黄金价差.md)；受控实盘规则：[Live Acceptance Runbook](../operations/LIVE_ACCEPTANCE_RUNBOOK.md)。

## 1. 权威模型

跨所价差订单由三个正交维度组成：

```text
业务动作（做什么）
+ 执行方式（怎么成交）
+ 触发来源（为什么下达）
```

业务动作：

- `OPEN_LONG_SPREAD`：买 Bybit，卖 MT5。
- `CLOSE_LONG_SPREAD`：卖 Bybit，买 MT5。
- `OPEN_SHORT_SPREAD`：卖 Bybit，买 MT5。
- `CLOSE_SHORT_SPREAD`：买 Bybit，卖 MT5。

执行方式：

- `MARKET`：保护型市价生命周期。
- `LIMIT`：统一限价入口；内部策略包括 `fok` 和 `post_only_chase`。

触发来源：

- `MANUAL`
- `STRATEGY`
- `TAKE_PROFIT`
- `STOP_LOSS`
- `KILL_SWITCH`
- `RISK_REDUCTION`

止盈和止损不是新的订单类型。它们触发普通 Close Action。

## 2. 命令与结果恢复边界

- 每个被接受的 Cross 业务动作先按稳定 `idempotencyKey` 创建或复用 `StrategyInstruction`；完整双腿预校验通过后，持久化不可变 `ExecutionPlan`。
- `ExecutionPlan` 固化账户、instrument/symbol、方向、数量、执行策略、reduce-only 语义及平仓所需 MT5 Position Ticket；执行期不得静默改写这些业务事实。
- 计划获准执行后才创建 `ExecutionBatch`，每条 Leg 生成独立 `TradeCommand`。兼容入口必须路由到同一 Instruction/Plan 主链，不得直接建立第二套 Batch 权威。
- `idempotencyKey` 是原子业务身份；同一键载荷不同必须返回 409，不能生成第二个 Order、Batch 或 Runtime Command。
- 创建 Batch 前完成 Strategy、Account Binding、Instrument 与 ContractSpecification 的双腿预校验。
- Instrument 查询只使用该标的最新的完整 ContractSpecification；历史版本仍可保留，但不能与当前版本一起被当成多个有效映射。
- `result_unknown` 只能通过 Runtime Journal 与后续 Venue 对账恢复；恢复流程重放已持久化事件，绝不重新提交订单。
- Runtime 事件身份不匹配、事件缺失或上游不可用时继续保持未知并阻止重复副作用。
- 浏览器刷新按原 `idempotencyKey` 精确只读查询该策略的 Instruction 和 Batch，不加载整份历史指令，也不调用开平仓提交入口。精确查询返回 404 才表示该键下无指令；认证失败、超时或其他读取错误必须保留锁定。未知或暂未查到的指令保留身份；连续两次权威读取确认服务端没有该 Instruction 后，用户点击平仓可在最终再核验原键仍不存在时解除旧平仓草稿并进入原确认流程，亦可使用独立解除按钮；解除只清浏览器草稿、不下单，最终核验失败则继续锁定。只有明确 HTTP 拒绝且只读核实原指令不存在或已终止，才能释放待确认草稿。批量平仓中尚未派发的组不随恢复自动提交。跨所预检虽使用 POST 传入平仓组和数量，但仅计算准入证据，按平台读取权限认证，不具有交易写入权限。
- 当前自动化交易写入仍限于 Simulation / Fake Gateway；外部 Venue 主动恢复与真实资金启用受独立生产门禁约束。

## 2. 两类可成交方向

### 2.1 买 Bybit、卖 MT5

适用：`OPEN_LONG_SPREAD`、`CLOSE_SHORT_SPREAD`。

```text
Executable Spread = Bybit Ask - MT5 Bid
Raw Bybit Buy Limit = MT5 Bid + Limit Spread - Hedge Reserve
Submitted Buy Limit = floor(Raw Price / Tick Size) × Tick Size
```

用户限制是最大允许价差；Bybit 买价向下取 Tick，不能因舍入放宽限制。

### 2.2 卖 Bybit、买 MT5

适用：`OPEN_SHORT_SPREAD`、`CLOSE_LONG_SPREAD`。

```text
Executable Spread = Bybit Bid - MT5 Ask
Raw Bybit Sell Limit = MT5 Ask + Limit Spread + Hedge Reserve
Submitted Sell Limit = ceil(Raw Price / Tick Size) × Tick Size
```

用户限制是最小允许价差；Bybit 卖价向上取 Tick，不能因舍入放宽限制。

成交判断、TP/SL 触发和 Limit 换算必须使用可成交 Bid/Ask，不能用中间价替代。

## 3. 永久执行不变量

- Bybit 是第一腿／主腿。
- MT5 是跟随对冲腿。
- ACK 不等于 Fill。
- Bybit 主腿确认真实成交后，才能提交 MT5。
- MT5 数量依据实际 Bybit Fill 与当前 Contract Size、Minimum、Step 计算。
- 执行热路径按净额账户的方向增量语义处理，不在下单前遍历历史仓位或 Fill。组合平仓先只读核验 Bybit 当前原生净仓：反向数量确实减少该净仓时使用交易所 `reduceOnly`，并免除该衍生品腿的新开仓保证金预留；原生仓位在提交前变化时，交易所减仓校验必须拒绝可能反向开仓的订单。若逻辑组合平仓会穿越净仓，则保留普通反向增量及资金预留，不因“平仓”名称绕过开仓约束。原生持仓证据不可用或歧义时拒绝执行。
- MT5 hedging 账户必须对该计划开仓产生的 Position Ticket 做 `reduceOnly` 精确平仓。绕过 Exit Plan 的底层 Close 仍必须使用双边 `reduceOnly` 并提供 MT5 Position Ticket。批次资源锁与幂等约束对两种平仓方式均生效。
- ExecutionBatch 必须以双腿 canonical Fill 确认完成；外部净仓差异由独立对账边界发现并冻结后续写入，不进入每笔订单的同步热路径。
- 明确失败、已受理、处理中、结果未知和外部仓位不一致使用不同处置。
- `result_unknown` 不允许盲目重试、回滚或生成第二个业务意图。
- Platform 与 Runtime Live Write、退出监控和单指令／单批次生命周期限制保持独立且默认关闭／受限。数量由 CEO 指令明确给定，双腿累计外部成交不得超过各自指令数量。

## 4. FOK Limit 合同

Limit 请求显式提供 `limitSpread`，`limitStrategy` 缺省为 `fok`。

Platform 在创建 ExecutionBatch 前读取当前双边可成交报价、应用 Hedge Reserve、按 Tick 保守取整并生成 Bybit `Limit + FOK` 价格。当前价差不满足限制时返回 `409`，不创建 Batch，不提交任何 Venue 订单。

只有 Bybit 终态 `Filled`、累计成交量等于请求量且平均价格有效，才生成正常 Fill 并允许 MT5。

| Bybit FOK 结果 | MT5 | Exit Plan |
|---|---|---|
| 精确全部成交 | 按实际 Fill 对冲 | 正常继续 |
| 零成交取消 | 不提交 | Open 不建计划；Close 释放 Claim 回 `active` |
| 部分成交／数量不一致 | 不提交 | 对账／人工介入 |
| 超时／Query 或 Place 未知 | 不提交 | 对账／人工介入 |

## 5. Exit Plan 与统一 Close Action

Exit Plan 存储于业务数据库，由 Platform API lifespan 启动的后台监控读取和原子领取。浏览器刷新、关闭、退出登录或 Session 过期不删除计划，也不停止该后台任务；应用重启从原库继续读取 `active` 计划，已领取及未知结果保持原防重边界。编辑和人工平仓仍需有效 CEO 会话。

这是平台管理的合成价差退出条件，未作为原生双边止损单预挂到 Venue。API/Runtime 停止、电脑休眠或断电时无法继续本地监控；行情不可用、交易开关关闭、账户权限或风险门禁不满足时不能保证派单。重启后仍需监控开启、双交易开关及新鲜可成交报价；不回溯停机期间曾经越过但恢复后已离开的阈值。保存参数和监控启动日志均不能单独证明持续保护有效。

每个 Exit Plan 持久化：

```text
takeProfitExecutionMode = market | limit
stopLossExecutionMode   = market | limit
takeProfitLimitStrategy = fok | post_only_chase
stopLossLimitStrategy   = fok | post_only_chase
```

对仍处于 `active` 的 Exit Plan，CEO 可在持仓总览中补充或修改 `takeProfitSpread`、`stopLossSpread`，以及各自的 `market | limit` 执行方式和 Limit 策略。更新只改变该计划后续触发的设置，不创建 Close Action、不改变已持久化的开仓事实，也不会立即向 Venue 提交订单；`triggered`、`closing`、`manual_intervention` 与 `closed` 计划不可编辑。两项阈值同时存在时，Long 的 TP 必须高于 SL，Short 的 TP 必须低于 SL。触发平仓针对计划的当前剩余数量；人工部分平仓后，原计划以剩余数量继续保持 `active` 并沿用该设置。

多个活动组的持仓总览按 Exit Plan 身份分别显示数量与 TP/SL，不以账户净仓合并组，也不把共享账户成本或损益复制给每个组。MT5 明细按该组的 Position Ticket 关联；未能归属的单腿事实显示待复核，缺失的组合损益保持缺失。总览的当前价差采用该方向的可成交平仓 Bid/Ask 组合。

存在活动组合时仍须展示未归属的原生 MT5 Ticket，以及 Bybit 原生净数量与已归属组合净数量的差额；差额由后端 Decimal 计算，不分配共享账户成本或假定两条未归属腿属于同一组合。经原生订单/成交核验恢复的误单沿既有指令、批次和 Exit Plan 显示，状态标注来自恢复审计，保留原始误单来源；持仓和单组平仓入口显示 MT5 Ticket。

持仓总览的损益是各组剩余数量的浮动盈亏，不含已平仓损益、手续费、资金费或库存费。Platform 的统一财务读取按开仓批次、TradeCommand 归属与冻结计划验证双腿完整成交，复用原生成交/确认回执的去重规则计算加权入场成本。Bybit 按该组方向、剩余盎司和可成交平仓价计算；单向账户的反向组即使净仓抵消为零，也保留各自逻辑持仓估值，该值不等于交易所账户未实现损益。MT5 只取同一账户、合约、Ticket 且方向、剩余数量与入场价匹配的原生浮盈亏。USD 使用本次 USDT/USD 换算，USDT 直接保留；其他币种、缺失汇率或过期报价不猜测。

单边汇总须覆盖所有活动组，双边汇总须覆盖所有组的两条腿，任一所需金额缺失时相应汇总为空，不能跳过缺失项。后端用 Decimal 求和，前端只格式化，不从带符号/千分位的展示文本反算。估值携带计划版本和剩余数量，前端仅与当前 Exit Plan 匹配时显示，避免部分平仓或退出后的旧估值复现。该估值仅用于只读持仓展示，不推进订单、结算、对账或 TP/SL 判定。

页面可见时随既有只读轮询更新退出计划，恢复可见时重新读取；迟到的旧查询不能覆盖较新的保存或查询结果。自动退出完成后，`closed` 计划保留本次触发原因、触发价差及触发时间；部分退出后仍需继续运行的计划释放本次触发字段，保留原阈值。

迁移规则：

- 旧计划保留 `market / market`；
- 旧 Limit 策略默认 `fok`；
- TP 与 SL 可独立选择执行方式和 Limit 策略；
- Stop Loss 默认 Market；
- 人工平仓、自动 TP 和自动 SL 调用同一个 claimed-plan Close Action。
- 人工平仓可提供不超过计划剩余量的 `quantityOz`；成功后以一次原子更新扣减剩余量，剩余量大于零时计划回到 `active`，等于零时才进入 `closed`。

自动 Limit 使用原子 Claim 保存的 `triggerSpread` 作为价差限制，不静默回退到 Market。干净零成交或下单前行情失效可以释放 Claim；部分成交、数量不一致、提交后超时或结果未知不能释放 Claim。

Close Action 在领取 Exit Plan 或建立执行意图前检查交易开关，开关拒绝不得改变计划状态。抛错时按该次幂等键、策略、方向、数量与 MT5 Ticket 找回已持久化的平仓批次，并关联到原 Exit Plan；不丢弃实际批次或创建旁路恢复状态。若拒绝发生在 StrategyInstruction/ExecutionBatch 持久化之前，且原幂等键下没有已持久化指令，则该次请求没有到达 Runtime，领取状态必须释放回 `active`，不能伪装成待人工对账。人工恢复继续验证前次批次，未知/可能已派单不得重试。对于没有关联批次的旧人工处理计划，仅在同一事务证明该策略与 Ticket 没有任何平仓指令后，允许用户从既有平仓入口重新领取当前剩余数量；无法识别 Ticket 的平仓指令也阻止恢复，不自动激活计划或后台重试。已证明指令准入拒绝、双腿均 pending 且没有订单或命令时，组内数量未变，可继续显示经过原生 Ticket 校验的浮盈亏；其他人工处理状态保持数量待核对。客户端关闭动作的幂等键在市价和限价下均保留，并识别统一指令所派生的 `instruction:` 批次键，避免重复扣减。

平仓曾进入人工介入后，若权威 Venue 对账证明两条 Close Leg 均已完整成交且双边仓位归零，Platform 必须在同一恢复边界将 Batch 置为 `hedged`、Instruction 置为 `completed`、Exit Plan 置为 `closed`，并释放该 Batch 的资源 claim 与余额 reservation；证据不完整时不得释放。

用户在场所端直接平仓时，成交不属于原平台失败批次，不能把该批次改成成功或补造平台 Fill。账户同步在 Live Write 关闭时也对账：原开仓腿冻结的账户/标的范围内，两个账户同步均为 ready、完整持仓快照不超过 120 秒、成交历史观测不超过 600 秒，双边仓位归零、无未决订单/命令/批次，且同向未关闭组的 Bybit reduce-only 成交总量与剩余量一致、各 MT5 Ticket 的原生退出 Deal 数量完整时，原子关闭这些 Exit Plan 并写入审计。既有正式接受的 missing_external 处置沿用原证据；其他 result_unknown 继续阻止对账关闭。Bybit 净额成交仅保留组集合层面的证据，不推算每组的成交分配或利润；原失败批次、原生身份/时间及关闭前计划保留。`closed_at` 为平台确认时间，场所成交时间保留在审计凭据。部分退出、混合方向、过期或不完整证据不自动关闭。

确认前的只读平仓预检必须指定仓位组，拒绝已关闭、正在处理或请求量超出剩余量的计划，并校验原生仓位；已成交 Bybit 的单腿恢复仍走原恢复检查。正常人工平仓与 TP/SL 在派出 Bybit 第一腿前，必须校验开仓时冻结的账户仍与当前绑定一致、指定 MT5 Ticket 的方向/剩余量准确，以及 Bybit 当前净仓等于未关闭组的净额。校验失败转人工处理且不发单；同一次原生净仓观测决定是否使用 reduce-only，不以过期计划推断可增仓。已完成的平台平仓再次查询直接返回原批次结果，不依赖当前行情或写入开关；已被场所端平仓对账关闭的计划拒绝再次平仓，不把原失败批次作为成功结果返回。

## 5.1 正常交易准入

用户处理已完成 Bybit、未派出 MT5 的市价平仓时，必须沿用原 Instruction、Batch、MT5 Command 和幂等键，只领取原来 `rejected` 且不存在任何 Order 的 MT5 Command。领取前校验原冻结数量、角色、账户、方向、成交总量和原生 Ticket 剩余量，事务内再次校验状态；存在未关联命令、未知订单或其他处置动作时拒绝。完成后核对成交量与 Ticket 余量，再同步计划、指令、批次及风险资源；不重置旧成交、不自动重试、不重新提交 Bybit。

异常展示由原计划、批次和已确认成交投影，不另建仓位账本。正常组合浮盈亏和一键全平排除异常项；未完成平仓扣除已成交腿后再比较账户净仓，不能将已归属的平仓成交显示成未归属持仓。浏览器仅在回执身份明确且各腿已结束或确认未派单时，将本地草稿交接到异常区；结果未知继续保留原请求身份。Bybit 单腿开仓残留可使用既有 `flatten_filled_legs` 风险处置，受原生成交核对与数量限制约束。

2026-09-09 起，CEO 有效登录与 CSRF、活动账户交易绑定、双层 Live Gate、余额/保证金、Venue 数量规格、MT5 原生交易权限和风险检查构成正常准入。市价和限价开平仓均不需要 LiveTradingSession、临时验收窗口、固定一盎司/名义额度或单组持仓限制。已完成开仓的持仓组不阻止新增独立组；未解决的执行批次仍阻止不安全的新开仓。平仓继续绑定目标组和 MT5 Position Ticket，累计成交不能超过指令数量。

正常 Cross 开仓、人工双腿平仓和自动 TP/SL 必须在创建指令或原子领取 Exit Plan 前，取得两腿当前可执行证据。行情可见不等于可交易：Runtime 保留报价供价差和账户风险监控，同时以 Venue 原生报价更新证据、品种交易模式、账户/终端/EA/Python 权限及真实合约规格分别给出 `openAllowed`、`closeAllowed`。任一腿报价超过 30 秒未更新、原生时间缺失、品种休市/禁用或权限不满足时，快照进入 `monitor_only`；价差仍可展示，但不得参与正常开平仓或 TP/SL 触发，也不得领取 Exit Plan。MT5 券商原生时间保留不校正；新鲜度采用账户观测合同规定的连续 Tick 递增证据，首次读取和重连后未确认更新时仅监控。异常批次已形成的单腿暴露仍沿原 Instruction、Ticket、幂等与对账合同处置，不能因正常双腿市场门而失去恢复路径。

策略页的交易规则保留原有五行表格，只把可确认的用户规则接到当前绑定账户的 Runtime 原生 Instrument Specification 与当前会话状态：交易时间显示 Bybit 24H 和 MT5 配置的服务器时区、周一至周五开市窗口，以及 MT5 当前休市或边界缓冲状态；当前 `00:00-23:00` 服务器窗口对应北京时间每日 04:00-05:00（UTC+03:00，夏令时）或 05:00-06:00（UTC+02:00，冬令时）休市。正常时不追加“正常执行”字样，休市显示“休市”，并始终注明“开收盘前后 N 分钟不自动交易（仅暂停后台自动止盈止损，手动开平仓可用）”；处于边界时再显示当前“不自动执行”状态。N 由 `VG_RUNTIME_CROSS_SPREAD_AUTO_EXIT_GUARD_MINUTES` 配置，不能在页面或执行逻辑中写死。Bybit MT5 默认时区为 Runtime 的 `Bybit/MT5`：UTC+2，并按 Bybit 公布的 3 月第二个周日到 11 月第一个周日切换 UTC+3；不能把北京时间或 `Europe/Athens` 当作服务器时钟。

边界缓冲只暂停后台自动 TP/SL，不撤销人工意图：缓冲期间仍允许用户自行提交开平仓指令；完整休市或时段证据未知时，正常开平及自动 TP/SL 均 fail-closed。MT5 周期性维护、夏冬令时和日期级节假日/临时维护通过 Runtime 的 `VG_RUNTIME_CROSS_SPREAD_MT5_TRADING_SCHEDULE`、`VG_RUNTIME_CROSS_SPREAD_MT5_SCHEDULE_TIMEZONE` 与 `VG_RUNTIME_CROSS_SPREAD_MT5_SESSION_OVERRIDES` 维护，状态随每次快照重新计算。

报价时间、交易模式、权限和来源时间仅作为后台准入证据，不在普通交易规则表中展开。没有 Venue 证据的手续费、杠杆上限或每日回撤不得以硬编码、Catalog Seed 或 UI Fixture 冒充真实规则，保持 `—`。

## 6. PostOnly Chase 合同

PostOnly Chase 是 `LIMIT` 的内部策略：

```text
executionType = LIMIT
limitStrategy = post_only_chase
Runtime executionPolicy = post_only_chase
```

它不是新的业务动作，也不会改变四类合成指令。

### 6.1 默认状态

- PostOnly 为正常限价执行方式，不再要求验收专用 Chase 开关；
- Live Write 仍由 Platform 与 Runtime 双重控制；
- 单指令／单批次生命周期与累计成交数量上限不变；固定仓位、名义金额、日成交量、批次数和亏损 cap 不属于该受控合同；
- 不自动启用退出监控；
- 不支持 IOC；
- 不静默改成 FOK 或 Market。

### 6.2 Bybit 原生追逐限价

跨所 `post_only_chase` 使用 Bybit `/v5/strategy/create` 的 `chaseOrder`，取代本地 Amend / Cancel-Repost。保留原业务指令、数量、TTL、Live Write、Kill Switch 和未知结果保护，不自动回退到其他执行方式。Funding 的独立追价实现不受此替换影响。

Cross 适配器中已无入口的旧本地追价动作、旧子单创建及私有流工厂接线已移除；原生 Chase 是此路径唯一追价实现。此清理不改变终态累计成交确认后放行 MT5 的规则，也不删除历史 Journal/Route 证据。

创建前持久化原 command 与路由，成功后绑定唯一 `strategyId` 及全部真实子 `orderId`。创建超时不重复创建，也不按相同品种、数量或时间猜测归属；缺少 strategyId 时保持 `result_unknown`，需要核对原外部结果。

### 6.3 动态价差与终态核验

原计划冻结目标价差、非负 `maxAdverseSpread`（默认 0）及真实 MT5 账户、品种、最小数量、步长和合约乘数。创建前及等待成交期间读取双边原生报价时间与可交易权限。买 Bybit / 卖 MT5 使用 `BY Ask - MT5 Bid <= target + tolerance`；卖 Bybit / 买 MT5 使用 `BY Bid - MT5 Ask >= target - tolerance`。

价差越界、单边不可交易、TTL 到期，或累计量已足够精确对冲时，停止策略并取消剩余量。`maxChasePrice` 仅是额外单边价格边界，不能代替动态价差保护或撤单确认。止盈止损和人工平仓同样受双边可交易检查约束；休市保留监控和风险提示。

通过有界 REST 读取策略、全部分页子单和真实 executions；按 `execId` 去重并按实际成交价加权，不把子限价当成交价。只有策略及所有子单均终态，且策略、子单、executions 的累计量一致，才输出一次带 `terminal=true` 的累计成交。停止确认失败或证据冲突保持未知，不放行 MT5。取消只能阻止未成交余量，无法取消已经发生的成交。

### 6.4 Fill 与 MT5

MT5 沿现有市价执行链按 Bybit 终态实际成交量对冲。原生 Chase 允许终态部分成交：保存已取消余量的订单状态和独立终态证据，按实际数量调整 MT5，不把请求数量当成交量。数量不足 MT5 最小量或不符合步长时保留敞口并进入人工介入。未终态部分成交不放行；FOK 仍要求全成交。

这是终态后单次对冲，不是逐笔增量 MT5 子单。REST 轮询、撤余单与核验会带来延迟，不能保证两边同时成交或最终价差无滑点。恢复仅查询原策略并复用相同事件身份，不重建策略或重复对冲。

Funding carry 的增量 Spot 对冲是独立策略语义，不改变上述跨 Venue 合同：每个去重后的永续累计成交增量只释放按 CEO 双腿指令比例、向下量化到 Spot Step 的新增数量；量化余数显式保留，子指令留在同一 Batch 并使用确定性身份。重复 `execId`、累计量回退或超量、断线、身份不一致、未知订单状态或 `result_unknown` 均停止新副作用并进入对账。跨 Venue FOK 仍只有终态累计全成交才允许 MT5 第二腿；原生 Chase 按本节终态实际量规则执行。

Funding 平仓绑定原开仓 Instruction，永续腿使用 reduce-only；实际可卖现货须扣除原生币手续费，按剩余永续比例向下取 Spot Step，不自动追加买币。实际已对冲、已平数量只来自 canonical Fill，Spot release 预约不能作为成交。剩余、待平与结果未知预约分别保留；请求数量不能越过原计划和剩余额度。建议开仓量取两腿共同数量步长并向下取整，预算不足最低成交量时返回不可用，不抬高数量。

已持久化的 Funding 指令由 Platform 生命周期中的有界状态机继续推进与对账，不依赖浏览器持续在线。它只执行原不可变 Plan，继续遵守原 TTL、mutation、claim、余额、门禁及未知结果规则。页面刷新或超时按原 identity 查询恢复，不创建新业务意图。浏览器交易请求使用当前 CEO Session 和 CSRF；确认时冻结动作和数量，取消确认不下单。

Funding 页面保留并展示服务端失败原因；人工介入或结果未知时明确提示保留原指令、等待核对，不暗示正在自动重新执行。账户上下文不可用时，无法读取的资金预约显示缺失，不能显示为零。

增量 MT5 对冲属于后续可单独讨论的策略扩展；当前实现优先保证不会重复对冲或错误放行第二腿。

### 6.5 当前边界

页面保留“追逐限价”和“触发后市价”两个选择；历史 FOK 配置可继续读取。普通限价开仓先持久化目标价差，未到价时保持 pending，不提交任何 Venue 订单；后台监控达到目标价差后，按选择触发市价或追逐限价。已保存的 TP/SL 由原后台监控触发。每次新指令及 TP/SL 分别保存允许不利偏移。

原生 API 依据：[Create](https://bybit-exchange.github.io/docs/v5/strategy/create-strategy)、[Strategy List](https://bybit-exchange.github.io/docs/v5/strategy/strategy-list)、[Order List](https://bybit-exchange.github.io/docs/v5/strategy/order-list)。本地测试不代表真实账户的原生策略写权限或成交验收。停止策略与成交发生竞争时，60062/60074 仅允许继续查询原策略及子单，不作为终态或成交证据；其他拒绝仍失败关闭。

## 7. API 与页面

Open、人工 Close 与 TP/SL 计划支持：

```json
{
  "executionMode": "limit",
  "limitStrategy": "post_only_chase",
  "limitSpread": "-0.8",
  "maxAdverseSpread": "0"
}
```

页面继续沿用现有交易执行区结构，仅增加 Limit 策略选择和清晰风险提示：

- 市价；
- FOK 限价；
- PostOnly Chase；
- TP/SL 各自的执行方式和 Limit 策略；
- 当前限制价差和派生 Bybit 硬价格边界。

本批不加入事后订单分析面板，也不改变侧边栏、页面结构或视觉体系。

### 7.1 Bybit 杠杆与保证金占用

执行区通过 Platform 的 `GET/POST /api/v1/trading/cross-spread/leverage` 读取与修改当前绑定 Bybit 账户的 XAUTUSDT 杠杆。浏览器使用当前会话与 CSRF，只提交 Decimal 杠杆值；账户和合约由服务端绑定决定。修改要求 CEO、Platform Live Write、Kill Switch 校验以及 Runtime Live Write 和账户写权限全部通过。最终范围由交易所合约规则裁决。

杠杆输入默认 50x，当前杠杆独立显示交易所回读值；默认输入不触发写入。应用按钮独立于输入框，通过页面内确认框提交。执行区账户可用资金与保证金占用并列显示。

提交前确认该共享账户合约已有仓位的保证金也可能受到影响。Runtime 设置后回读交易所当前值，确认一致才报告成功，并使该账户原有保证金读取缓存失效。拒绝保留交易所原因；超时、身份差异或回读不一致均不自动重放。账户保证金占用使用权威账户风险快照，读取耗时不作为下单延迟。

## 8. 分批状态

### Batch 1：统一合成指令模型——已完成

### Batch 2：FOK 价差限价——已完成

### Batch 3：TP/SL 执行方式与统一 Close Action——已完成

### Batch 4：PostOnly Chase——Issue #113 / PR #114

- 状态机、私有事件、Runtime 策略、Platform 合同、数据库迁移和页面选择已实现；
- 当前正在完成最终回归、文档与 CI；
- 未通过最终门禁前保持未合并状态。

### 原 Batch 5：事后订单分析／执行复盘——仅保留待讨论项

该范围当前不属于交易执行界面计划，也不预设最终产品位置。只在 Markdown 中记录候选内容：

- Quote Age 与跨 Venue 时间差；
- Bid/Ask 宽度；
- MT5 Deviation；
- 未对冲时长；
- 真实价差偏差；
- Maker/Taker、手续费、Commission、Swap、Funding 和执行成本拆分。

用户后续将单独决定：是否开发、哪些属于下单前保护、哪些属于事后分析，以及应放在订单详情、复盘页面、风险页面或其他位置。在明确决定前，不创建 Issue，不新增前端区域，不混入交易执行界面。

## 9. 本地实盘边界

CI 只能证明类型、迁移、状态机、映射和安全分支，不能证明真实 Bybit／MT5 权限、Private WebSocket、Broker 字段、Terminal 稳定性、流动性、Tick 一致性或成交质量。

Issue #39 仍需依次验证：

1. Live Write 全关闭的只读核对；
2. 当前／历史 Order、Fill／Deal、Position 和 Account Risk；
3. 真实 Bybit Tick、数量 Step 与 Platform Contract Specification；
4. MT5 Hedge Reserve；
5. CEO 指令数量限定的受控 Market；
6. CEO 指令数量限定的受控 FOK；
7. 自动 TP/SL 的 Market/FOK 行为；
8. PostOnly Private Stream、TTL、Amend、Cancel/Repost、断线和异常结果；
9. 多轮干净 EOD 后才复审临时限制。
