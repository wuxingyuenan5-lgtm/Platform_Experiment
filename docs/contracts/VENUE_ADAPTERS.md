# Controlled Venue Adapter Contract

状态：`active contract`

## 1. 设计原则

- Live Query 与 Live Command 分离。
- 查询失败不等于零仓位或零余额。
- 同步 ACK 不等于最终成交。
- 明确拒绝与结果未知必须区分。
- Route Store 用于补充 Platform 身份，不得成为读取真实订单的前提。
- MT5 Order Ticket、Deal Ticket 和 Position Ticket 是不同身份，不得互相替代。
- 实盘数量必须由 Venue 当前规格证明，不以数据库 Seed 作为写入依据。
- 所有外部副作用必须位于 Platform 幂等、Kill Switch、Runtime 幂等和 Live Gate 之后。
- 凭证、密码、API Secret 不进入数据库响应、日志或审计 JSON。

### 1.1 合同边界与统一命名

- Platform 拥有 `StrategyInstruction`、不可变 `ExecutionPlan`、账户绑定、风险控制和策略编排，不导入 Venue SDK，也不直接产生 Venue 副作用。
- Execution Runtime 独占 Venue SDK、账户连接、查询与订单副作用，并通过版本化合同向 Platform 提供能力。
- Runtime 的统一边界命名为 `VenueGateway`；`ExecutionGateway` 只保留为旧代码的导入兼容别名，不得成为新依赖或第二套执行合同。

## 2. Runtime 模块

`GET /venue/account-snapshot` accepts `includeHistory` (default `true`) and optional timezone-aware `historyStart`. Current-only reads skip order, fill and economic-history SDK calls and return empty historical lists with null history bounds and `economicEventsQuality=not_requested`; consumers must preserve prior history rather than treat those lists as proof of zero. A supplied history start must fall within the supported venue window; naive, future or out-of-range input is rejected. Full/default callers retain their existing behavior. Incremental executions/economic events and order-status windows are distinguished under the [account observation contract](LIVE_ACCOUNT_OBSERVABILITY.md).

| 模块 | 职责 |
|---|---|
| `bybit_connection.py` | 每个逻辑账户持有一个 pybit HTTP 客户端、时钟校验、CCXT 账户/IP 请求预算及关闭责任 |
| `bybit_market_data.py` | CCXT 4.5.78 标准市场/报价/资金费率解析；复用现有账户读取通道，保留原生扩展 |
| `bybit_live_adapter.py` | Bybit V5 基础 Query、受控 Submit/Cancel、Funding/Fee 映射 |
| `bybit_fill_confirming_adapter.py` | Market 提交、reduce-only close、bounded terminal-fill confirmation |
| `bybit_acceptance_adapter.py` | 无 Route Order／Fill 读取、bounded order list、实时规格和 API Key readiness |
| `mt5_live_adapter.py` | MT5 Terminal 基础 Query、受控 order_check/order_send、Swap/Fee 映射 |
| `mt5_position_closing_adapter.py` | Position Ticket 绑定的 reduce-only close |
| `mt5_acceptance_adapter.py` | 无 Route Order／Deal 读取、Order/Deal Ticket 纠错、实时 Symbol/Terminal 规格 |
| `strict_live_acceptance_adapters.py` | 正常交易前的场所数量规格、账户与终端交易权限校验；旧数量/持仓数量 cap 已移除 |
| `bybit_mt5_gateway.py` | 根据 Account 确定性选择适配器，并提供跨 Adapter 只读查询 |
| `cross_spread_market.py` | 从统一 Gateway 并行聚合固定 Bybit/MT5 账户的行情与持仓，不再直接创建 SDK 或登录 MT5 |
| `live_safety.py` | Environment、真实写开关、可交易账户范围、命令身份及原子幂等认领 |
| `live_route_store.py` | 外部 client identity、Order Route、日累计名义金额幂等认领 |
| `secret_resolver.py` | 从 `secret://...` 映射的环境变量读取凭证 |

## 3. Bybit 映射

### 3.1 外部身份

```text
Platform Order ID
→ SHA-256 派生 orderLinkId
→ Bybit orderId
→ Execution execId
```

- `orderLinkId` 不超过 Bybit 限制并保持确定性。
- place-order 返回后先生成 `order_acknowledged`。
- Market Order 通过 bounded polling 等待 terminal state。
- Execution `execId` 用作 Fill 与 FinancialFact 的自然身份。
- `VenueFillSnapshot.fee` 可空：Bybit 缺失或空 `execFee` 保持未知，显式 `0` 和负返佣保留原始 Decimal。测试 FakeGateway 的具名费用夹具同时生成同身份原币费用流水，重复命令与快照读取不能重复扣费；该夹具不证明外部场所账单覆盖。
- Route 缺失时仍可按 `orderId` 读取；结果标记 `external_only` 并使用合成 Platform Identity。
- 按 Platform Order / 原生 Order 查询成交时，Gateway 将已持久化 Route 的账户显式传入 Adapter；Adapter 也先解析 Route 再确定账户，拒绝调用方账户与 Route 冲突。多账户时没有 Route 或明确账户不能任选账户查询。
- 新命令携带 Platform 合约目录的 `instrument_type`，Runtime Journal 保留这一市场身份；下单规格、报价、提交、订单确认、成交查询及撤单使用同一市场。现货为 `spot`、现货市价数量明确采用 `marketUnit=baseCoin` 且 `isLeverage=0`；永续继续使用合约市场和 reduce-only 语义。现货检查 `SpotTrade`，不以合约 Order/Position 权限替代现货权限。参数依据 [Bybit 下单文档](https://bybit-exchange.github.io/docs/v5/order/create-order)及 [API 权限文档](https://bybit-exchange.github.io/docs/v5/user/apikey-info)。
- 无静态合约映射时，账户、原生 symbol 和持久化命令的市场共同解析唯一 Instrument ID，不能把同名现货与永续合并；多个不一致的已知映射拒绝解析，无已知映射继续返回完整市场身份的 monitor 标识。旧命令没有 `instrument_type` 时保留当时默认合约市场的读取语义，不改写原命令。

### 3.2 Query

标准市场读取使用 CCXT 的精确字符串模式，Spot 与 Perpetual 按市场类别、原生 symbol 和统一 market identity 分开缓存；规范对象同时保留 base/quote/settlement 币种和原始回执。市场目录分页有重复游标检测和最大页数边界。报价和资金费率使用原始来源时间，不能把获取时间当作交易所时间；Bybit 的下一次资金结算时间对应 CCXT `fundingTimestamp`。

CCXT 在当前实现中只负责标准解析、端点成本和限流时序。它的网络入口只允许已登记的公开市场 GET 并委托同一账户连接；私有订单、余额、历史成交和资金变动仍由已有官方 pybit 扩展负责，不并行启用 CCXT 私有写入。连接禁止 SDK 自动下单重试和重定向；显式只读网络失败最多在同一连接上重读一次，业务拒绝和格式错误不重试。

Spot 数量步长/最小名义金额与合约数量步长分别使用场所规格。CCXT 通用 `amount.max` 不能代替 Bybit 原生市价订单上限；平台继续保留 `maxMarketQuantity`。规范化不是丢弃 Venue 证据或降低 Decimal 精度的理由。

Runtime 的同账户、类别、标的和参数相同的并发报价读取合并为一次外部请求；报价缓存为 1 秒，仍保留交易所原始来源时间。不同读取键独立进行网络请求，CCXT 解析器锁只保护内存解析，不能覆盖网络等待。失败不写入缓存；账户杠杆变更后，变更前在途的保证金读取不得覆盖新代缓存。

双腿规格可共享同一账户正在进行的权限读取；完成或失败后立即移除共享结果，下一次校验重新查询，不能把权限改成定时缓存。

静态市场规格可由市场读取器缓存；含账户/终端交易权限的完整规格快照不能整体缓存。下发前重新读取当前权限，避免计划创建后撤销 Spot 权限仍被旧快照判为可交易。Platform 的实盘 Crypto 委托使用已确认的原生最小数量、步长和价格 tick，本地目录 Seed 不替代这些规则。

- `get_open_orders`
- `get_order_history`
- `get_executions`
- `get_positions`
- `get_wallet_balance`
- `get_transaction_log`
- `get_instruments_info`
- `get_api_key_information`

Funding 和 Fee 分别映射为带符号经济贡献。Fee 以负值写入。

Bybit 普通正手续费按收到的币种扣取：Spot Buy 扣基础币、Spot Sell 扣报价币。Funding 的 Spot 市价买入按已确认 0.1% 预估净币量，实际对账仍使用原生每笔手续费；卖出与永续的 USDT 费用不减少 BTC 数量。来源：[Bybit Spot Fee Currency](https://bybit-exchange.github.io/docs/v5/enum#spot-fee-currency-instruction)。

### 3.3 Market Fill 规则

```text
place_order ACK
→ Active Order / Order History polling
→ terminal Filled
   or terminal Canceled with confirmed partial fill
→ emit order_filled(actual quantity)
```

- `New` 或非终态 `PartiallyFilled` 到达超时后保持 unresolved，不提交 MT5。
- 终态部分成交只对冲实际成交量。
- 终态无成交取消或拒绝才属于 definitive failure。

## 4. MT5 映射

### 4.1 外部身份

```text
Platform Order ID
→ SHA-256 派生 Comment
+ 固定 Magic Number
→ Order Ticket
→ Deal Ticket
→ Position Ticket
```

- 下单前执行 `order_check`。
- 写入使用 `order_send`。
- Order 查询使用 `orders_get` 与 `history_orders_get`。
- Deal 查询使用 `history_deals_get`。
- Position 与账户查询使用 `positions_get`、`account_info`。
- Deal Ticket 用作 Fill、Swap、Commission/Fee 的自然身份。
- 市价成交若 `order_send` 主要返回 Deal Ticket，读取层必须通过 Deal 的 `order` 字段恢复 Order Ticket。
- Close 必须使用真实 Position Ticket；Deal Ticket 或 Order Ticket 不能充当 Position Ticket。
- MT5 reduce-only close 返回 `DONE` 但未携带成交量或价格时，Runtime 必须按目标 Position Ticket 查询历史 Deal，并用本次 Order/Deal 身份和方向精确匹配后才生成 Fill；无法唯一证明时保持 ACK／待对账，禁止猜测成交。

MT5 非 Windows、Terminal 未连接、登录账号不匹配或交易权限不足时必须 fail-closed。

Platform 将 Runtime 的终态聚合 Fill 与后续 Venue component execution 投影到同一 Order 时，累计数量不得超过指令数量；已经存在完整聚合 Fill 时不得再次计入其组成成交。

每个逻辑 `account_id` 必须确定性映射到一个固定 Terminal/Worker 及其 Terminal Path、Login 和 Server。Worker 不得在同一 Python 会话中切换账户，Terminal Path 不得被不同逻辑账户共享；身份不一致时 fail-closed，单个实例故障不得改变其他账户的路由或状态。Worker 启动时若终端已登录到配置的 Login/Server，直接复用连接，不重复调用登录；后续每次连接仍复核身份。平台不强制重开操作员关闭的算法交易开关。

固定账户 Worker 初次连接及只读 IPC 恢复时，必须把配置的完整 Terminal Path 和 portable 参数一次传给 MT5 SDK，由 SDK 负责该终端的一次启动/连接尝试；Runtime 不得先用 `Popen` 预启动同一终端再调用 SDK，否则会产生 `terminal process already started` 并放大断线恢复。SDK 初始化或恢复完成后，Runtime 仅隐藏匹配配置完整路径的可见顶层窗口（含其拥有者对话框），覆盖 MT5 启动期间恢复已保存窗口布局的行为。2026-09-10 Owner 明确要求两个配置终端持续在后台运行：重连已运行终端也执行隐藏，固定账户 Worker 每次处理请求前及空闲时检查并隐藏对应完整路径进程的可见顶层窗口。已隐藏窗口不重复操作，不切换焦点、不关闭进程、不重新登录、不影响其他路径终端。窗口维护失败记录日志，不中断交易/读取 IPC；portable 模式与账户路径绑定不变。Worker 启动失败时按指数退避（2 至 30 秒）拒绝重复拉起，避免每个读取请求重新启动终端。此规则替代此前“已运行窗口保持不变”的策略。

跨所行情也必须显式传入 `bybitAccountId` 与 `mt5AccountId` 并通过同一 Gateway/Worker 读取，不能选择任意“首个账户”。MT5 行情使用 `symbol_info.currency_profit` 作为报价币，账户现金与结算币来自账户证据；缺失报价币时标注 UNKNOWN/partial。Swap 字段、合约乘数及 Position Ticket 保留原生值，不能从 XAUUSD 名称推断账户现金币。

MT5 报价读取还须确认 `terminal_info.connected`：终端信息缺失或经纪商连接中断时，即使 SDK 留有账户信息和正数缓存 Tick，也不能生成可执行报价；后续读取确认连接恢复后才能继续。观察时间只证明本次读取时刻，不能用来证明经纪商缓存 Tick 的源时钟或停机期间行情。

MT5 账户风险与账户快照读取也必须确认 `terminal_info.connected`，断线时不得把缓存的账号资料和余额判为同步成功。账户快照的 `identity` 保留 SDK 返回的 `login`、`server` 和 `company`，实盘接入验收同时核对三者；经纪商服务器目录属于该 Terminal 的数据目录，单独配置 Server 名称不能证明对应服务商已装载。

MT5 Python SDK 不提供周历 `SymbolInfoSessionTrade` 窗口，Runtime 不得把 `trade_mode` 或正数缓存 Tick 当作周末/日内开市证据。跨所黄金使用 Runtime 的 `VG_RUNTIME_CROSS_SPREAD_MT5_TRADING_SCHEDULE` 与服务器时区计算周历，`VG_RUNTIME_CROSS_SPREAD_MT5_SESSION_OVERRIDES` 覆盖节假日和临时维护；Bybit 默认时区标识为 `Bybit/MT5`，按其公布的 UTC+2/UTC+3 切换日期计算，不能套用北京时间或 `Europe/Athens` 的夏令时日期。`VG_RUNTIME_CROSS_SPREAD_AUTO_EXIT_GUARD_MINUTES` 只作用于后台自动 TP/SL，边界期间人工开平仍按独立能力门处理。配置应以 [Bybit TradFi FAQ](https://www.cbybit.com/en/help-center/article/FAQ-TradFi-MT5)、[MT5 合约规格](https://www.bybitglobal.com/en/help-center/article/Contracts-Available-on-TradFi-MT5-and-Specifications) 及最新运营通知为准。

### 4.2 实时规格

Runtime 读取：

- `volume_min`
- `volume_step`
- `volume_max`
- `trade_contract_size`
- `trade_mode`
- `filling_mode`
- `account_info.login`
- Account `trade_allowed`
- Terminal `trade_allowed`

MT5 Command 数量单位是 Lot。Runtime 必须先计算：

```text
requestedOunces = requestedLots × trade_contract_size
```

再与 CEO 指令中的 MT5 腿数量上限比较。不能把 `1 lot` 误认为一个基础资产单位。

## 5. Route-independent Order Query

Runtime 提供：

```http
GET /venue/orders?accountId=...&symbol=...&limit=50
GET /venue/orders/by-platform/{platformOrderId}
GET /venue/orders/{externalOrderId}
GET /venue/fills?accountId=...&externalOrderId=...&platformOrderId=...
```

读取顺序：

1. 有 Platform Order ID 时优先使用 Route Store 确定 Adapter 和外部身份。
2. 有 External Order ID 且 Route 存在时使用对应 Adapter。
3. Route 不存在时直接查询 Venue：
   - 非纯数字 ID 优先 Bybit；
   - 纯数字 Ticket 查询 MT5；
   - Account-specific list 始终由 Account Route 确定 Adapter。
4. 无 Route 的结果标记 `dataQualityState=external_only`。
5. 查询不得创建、撤销或重发订单。

Platform 的监控持久化按账户、合约身份（含市场类别）和原生订单号解析旧、新内部别名；唯一的 TradeCommand 归属是策略依据，不按 symbol 或时间相近推断。不同 MT5 账户的同号 Ticket 不共用监控 Fill 主键。新成交记录来源和原生 Fill ID，旧记录来源不明时保持 legacy，不根据数量大小回填来源。账户快照保留原生成交证据，但不推进指令订单状态、执行数量或解除未知结果；详细投影规则由 [账户观察合同](LIVE_ACCOUNT_OBSERVABILITY.md) 唯一维护。

## 6. Instrument Specification Query

```http
GET /venue/instruments/{symbol}?accountId=...
```

返回：

- `minQuantity`
- `quantityStep`
- `minNotional`（Venue 有报告时保留最小名义金额，否则为 null）
- `maxMarketQuantity`
- `contractSize`
- `trade_mode`
- `filling_mode`
- `accessChecks`
- `asOf`

Platform 跨所价差写入前必须分别查询 Bybit 与 MT5；任一查询失败、规格无效或权限不满足时拒绝开仓。

Bybit 现货的数量步长来自 `lotSizeFilter.basePrecision`，合约来自 `qtyStep`；不得因套用合约字段而把现货步长返回为零。最小名义金额分别保留现货 `minOrderAmt` 与合约 `minNotionalValue`，供 Funding 的数量建议和金额校验使用。来源：[Bybit Instruments Info](https://bybit-exchange.github.io/docs/v5/market/instrument)。

## 6.1 Order Margin Estimate

```http
GET /venue/order-margin-estimate/{symbol}?accountId=...&side=...&quantity=...&referencePrice=...
```

衍生品余额预约不得用全额名义本金代替保证金。Runtime 在只读边界内返回 Venue 口径的初始保证金估算：Bybit 使用当前 Symbol 实际杠杆，MT5 使用 Terminal `order_calc_margin`。任一杠杆、品种、报价或保证金结果不可用时 fail-closed；Platform 只消费统一结果，不导入 Venue SDK 或自行猜测保证金率。

## 7. 原生数量、权限与执行边界

正常交易按不可变 CEO 指令数量、原生合约规格和执行状态约束每条腿；不再使用早期固定 1 盎司验收 cap。以下检查与第 8 节的正常 Live Safety Gate 共同生效。

### Bybit

- Command Quantity 与累计外部成交必须不超过 CEO 指令中的 Bybit 腿数量。
- Quantity 必须满足当前 `minOrderQty` 和 `qtyStep`。
- Symbol 必须处于 Trading／Available。
- API Key 不能是 read-only。
- API Key 必须绑定固定 IP。
- ContractTrade 必须包含 Order 与 Position 权限。
- 新执行批次必须通过全局序列化 claim；已持有的 funding pair 不授权并发开／平批次。

### MT5

- `lots × contractSize` 与累计外部成交必须不超过 CEO 指令中的 MT5／Spot 腿数量。
- Lot 必须满足当前 `volume_min`、`volume_step` 和 `volume_max`。
- Account Login 必须与配置一致。
- Account 与 Terminal 均必须允许交易；账户须允许自动交易，终端须允许外部 Python API 交易。
- 新执行批次必须通过全局序列化 claim。
- 跨 Venue Bybit 只有终态全成交才释放 MT5；funding carry 才允许按去重永续累计成交增量比例、向下量化到 Spot Step 后释放同 Batch Spot 子指令。
- Funding 显式 `executionPolicy=fok` 同样使用 Bybit 原生 `timeInForce=FOK`：仅终态精确全成交生成执行确认，零成交不释放现货，异常部分成交保持待核对。Funding 市价只提交一次，PostOnly 保留原有有界追价；关闭永续腿传递计划的 reduce-only。

## 8. Live Safety Gate

正常交易使用以下 Runtime 配置：

```text
VG_RUNTIME_ENVIRONMENT=live
VG_RUNTIME_LIVE_WRITE_ENABLED=false
VG_RUNTIME_LIVE_ACCOUNT_ALLOWLIST=已批准写入的逻辑账户集合
```

2026-09-09 起，旧 Strategy/Symbol 验收白名单、固定单笔/每日名义额度、数量/持仓数量 cap 及 PostOnly 专用启用开关退出正常执行链；旧配置项不会恢复这些限制。`LIVE_ACCOUNT_ALLOWLIST` 继续表示账户写权限范围，账户必须已配置且不得为只读账户。策略与品种由 Platform 的活动绑定、不可变执行计划和原生合约规格确定。

写命令依次验证 live 环境、独立 Runtime 写开关、账户写权限、StrategyInstance/Command 身份、正数参考价、原子幂等认领、Venue 实际规格与权限，然后调用 Venue。SQLite 仍保存名义金额供审计，但不据此消耗验收额度。相同 Command/载荷不重复发送，冲突载荷拒绝。

Platform 的登录权限、账户绑定、Live Gate、Kill Switch 和对账检查仍先行生效。PostOnly 仍必须有硬限价、健康私有流、有限追价时长和次数；取消验收开关不豁免它们。

## 9. 凭证

### Bybit

Credential Ref 示例：`secret://bybit-live-001`

对应环境变量：

```text
VG_SECRET_BYBIT_LIVE_001_API_KEY
VG_SECRET_BYBIT_LIVE_001_SECRET
```

### MT5

Credential Ref 示例：`secret://mt5-live-001`

对应环境变量：

```text
VG_SECRET_MT5_LIVE_001_LOGIN
VG_SECRET_MT5_LIVE_001_PASSWORD
VG_SECRET_MT5_LIVE_001_SERVER
```

`/gateway/capabilities` 和 Instrument Specification 只返回字段是否齐全、权限布尔值、适配器能力和缺失要求，不返回任何凭证值。Bybit 与 MT5 的 `accountStatuses` 按账户报告配置、运行和写入准入；单一账户缺少凭证或连接失败只影响该账户，适配器汇总状态表示至少一个账户可用。共享依赖故障仍影响所有账户，Runtime Live Write 与账户白名单继续分别控制写入。

## 10. Account 与 Instrument 路由

配置示例：

```text
VG_RUNTIME_BYBIT_ACCOUNT_IDS=account_bybit_live
VG_RUNTIME_MT5_ACCOUNT_IDS=account_mt5_live
VG_RUNTIME_BYBIT_INSTRUMENT_MAP=XAUTUSDT=instrument_xaut_usdt
VG_RUNTIME_MT5_INSTRUMENT_MAP=XAUUSD+=instrument_xauusd_mt5
```

约束：

- 一个 Account 只能属于一个 Adapter。
- 未映射 Account 拒绝查询和写入。
- 未映射 Symbol 的 Position、Deal 或 Economic Event 不进入 complete 事实。
- Instrument ID 必须与 Backend Catalog 一致。
- Route Store 丢失不阻止 External Order 只读查询，但会降低为 `external_only`。

## 11. Result Unknown

以下情况视为 `result_unknown`，不能视为拒绝：

- HTTP/Terminal 调用期间异常，无法证明请求未到 Venue。
- Bybit 返回成功但缺少 orderId。
- MT5 `order_send` 返回空结果或缺少 Order/Deal Ticket。
- 查询接口自身结果不确定。
- Bybit Market Order 在 bounded confirmation deadline 内仍处于 New／PartiallyFilled。

Runtime 返回 502，Platform 保留 Order 并标记 `result_unknown`，随后调用 Venue Reconcile。禁止以相同业务意图重新创建另一笔订单。

持久化的 unresolved command 必须冻结对应逻辑账户及可证明资源范围的后续写入；进程重启不得释放冻结。只有权威查询与对账完成，或形成明确且可追责的安全终态处置后，才允许解除。

对于跨所价差：

- MT5 definitive rejection／failure 才允许一次幂等 Bybit reduce-only rollback。
- MT5 `accepted`、`processing`、`acknowledged` 或 `result_unknown` 禁止自动 rollback。

## 12. Economic Event

Runtime：

```http
GET /venue/economic-events?accountId=...&instrumentId=...&eventType=...
```

Platform：

```http
POST /api/v1/ops/live-economic-events/import
```

支持 `funding`、`swap`、`fee`。导入操作本身和每条 FinancialFact 都具有独立幂等身份。

## 13. 验收边界

CI 可以证明：

- Route-independent Order／Fill 映射。
- MT5 Order／Deal Ticket 纠错。
- 当前规格模型和权限布尔值映射。
- 纯状态转换可证明 CEO 指令数量 ceiling；legacy acceptance adapter 的 instruction binding 和全局批次序列化仍需后续授权实现与验收。
- 跨 Venue 终态全成交边界与 funding carry 增量 Spot 释放边界互不混用。
- definitive failure 与 result_unknown 的不同处置。
- 路由、门禁、限额与幂等。
- 凭证不进入响应。
- 既有 Backend、Runtime 和 Frontend 回归不受破坏。

CI 不能证明：

- 真实 Bybit API Key 权限和 IP 白名单生效。
- 真实 Broker 的 `trade_contract_size`、最小手数和 filling mode。
- Windows MT5 Terminal 长时间稳定性。
- 实盘网络中断、滑点、部分成交和外部账单一致性。
- 真实 TP／SL exactly-once close。

真实账户运营验收按 [交易验收运行手册](../operations/LIVE_ACCEPTANCE_RUNBOOK.md) 独立记录。

## 14. 受控边界

固定仓位、名义金额、日成交量、批次数和亏损 cap 已从 founder-owned local test-account 合同移除。该决定不允许通过环境变量绕过 CEO 指令数量 ceiling、单指令／单 Batch 身份、全局执行序列化、bounded chase、Kill Switch、操作员停机与对账。ACK／Fill 区分、`result_unknown` 禁止盲重试、双重写门禁、Position Ticket close 和凭证隔离属于永久安全原则，不随数量变化删除。

