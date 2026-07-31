# 参考代码采用矩阵

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6 Simplified  
文档层级：执行前参考代码吸收规则  
更新日期：2026-07-19

## 1. 结论

当前主项目不推翻，不整体迁移任何参考库。

第一阶段继续保留：

```text
platform-web
+
platform-backend
+
execution-runtime
```

参考代码只用于吸收成熟字段、流程、状态和工程经验。订单、成交、持仓、PnL、净值、风控和对账的业务权威必须保留在 `platform-backend`。

## 2. 采用原则

| 原则 | 要求 |
|---|---|
| 不整库搬迁 | Django、量化框架、交易机器人和数据站项目都不能直接替代当前主架构 |
| 不形成第二套权威 | 外部 Order、Position、PnL、NAV、Risk 对象只能经 Adapter 转换 |
| 先字段后实现 | 先借对象字段和状态流，再决定是否复用代码 |
| 先模拟盘后 Live | Fake Gateway 只做工程验证，V1 必须继续进入真实 API 模拟盘、测试盘或 Demo |
| 密钥不进代码 | API key、MT5 密码、交易账户凭证必须走环境变量或 SecretReference |
| 金额不用浮点数 | 正式金额、价格、数量、费用、PnL 使用 Decimal |
| 缺失不当零 | 缺失数据必须带质量状态，不自动填 0 |
| 前端不裁决交易事实 | 前端可预览、可展示，不保存正式交易事实 |

## 3. 参考库采用矩阵

| 参考库 | 可采用内容 | 不采用内容 | V1 作用 |
|---|---|---|---|
| `数据站后端：data_center-main` | FastAPI 分层、行情任务、Redis、调度、数据查询接口、MT5 行情同步经验 | 交易权威逻辑、前端直接依赖的浮点净值、硬编码凭证、自由拼接 SQL | 作为 Market Data / Read API / Scheduler 参考 |
| `数据站前端data-main` | Vben 后台结构、行情页面、图表、`localPreview` 预览兜底 | 把预览数据混入真实交易链路、前端计算正式净值 | 作为行情和分析页面参考 |
| `platform-web` 参考前端 | 风控页面、账户/产品视图、表格、弹窗、通知、权限守卫、平仓交互样式 | 前端直连交易系统、前端保存订单事实 | 作为当前前端改造的组件和页面范式 |
| `MT5-main` | 官方 MetaTrader5 Python 包封装、Order / Deal / Position / Account 字段、Magic / Comment / 历史成交查询 | 整体迁移 Django、明文存储 MT5 密码、让 MT5 服务成为 PnL 权威 | MT5 Worker PoC 的主要参考 |
| `PyTrader...` | 远程 MT4/MT5、EA Bridge、跨机器连接思路、instrument mapping | 作为 V1 主 MT5 接入、依赖授权不清的 EA 作为核心链路 | 官方 MT5 包不可行时的备选 |
| `risk-main` | RiskRecord、ExecutionTask、ExecutionOrder、ExecutionLog、Notification、HealthCheck、TransferRequest、风控阈值配置 | 完整用户权限系统、Django 迁移、乱码字段直接复用、浮点金额 | 风控、审计、通知、执行日志字段参考 |
| `future-main` | 策略指令、海内外价差字段、TQ/期货账户、TQ 订单/成交记录、策略绩效字段 | V1 CTP 闭环、国内真实期货交易、复杂海内外四层 PnL | 海内外价差和 CTP 后续阶段参考 |
| `freqtrade-develop` | Crypto dry-run / live 隔离、交易所适配、Funding/Market 经验、策略运行状态、回测/绩效理念 | 嵌入整套交易机器人、采用其 Strategy / Trade / PnL 作为平台权威 | Crypto Adapter 和 Paper Trading 思路参考 |
| `nautilus_trader-develop` | 事件驱动、幂等、状态机、缓存、恢复、研究到实盘一致性理念 | 引入完整高复杂交易引擎 | 长期架构参考，不进 V1 主路径 |
| `vnpy-master` | CTP Gateway、EventEngine、OmsEngine、RiskManager、SpreadTrading、AlgoTrading | V1 直接接 CTP、把 vn.py 作为平台主架构 | CTP 和多腿算法后续 PoC 参考 |

## 4. V1 可吸收对象

优先吸收这些对象和字段：

| 来源 | 对象/字段 | 进入平台对象 |
|---|---|---|
| `risk-main` | ExecutionTask、ExecutionOrder、ExecutionLog | TradeCommand、ExecutionBatch、Order、RuntimeEventLog |
| `risk-main` | RiskRecord、RiskConfig、NotificationMessage、HealthCheckRecord | RiskDecision、RiskEvent、Notification、ServiceHealth |
| `MT5-main` | Order、Deal、Position、AccountInfo、SymbolInfo | Order、Deal、PositionSnapshot、BalanceSnapshot、InstrumentMapping |
| `future-main` | StrategyInstruction、StrategyPerformance、TqOrderRecords、TqTradeRecords | StrategyInstance、StrategyRun、EconomicEvent、ExternalExecutionRecord |
| `data_center-main` | Market data task、Redis manager、scheduler、price diff query | MarketDataJob、QuoteSnapshot、ReadModel API |
| `freqtrade` | dry-run/live mode、exchange config、trade lifecycle | TradingMode、GatewayCapability、StrategyRunStatus |
| `vn.py` | Gateway / Order / Trade / Position 状态思想 | GatewayAdapter、ExternalOrderStatus、ReconciliationResult |

## 5. V1 禁止照搬清单

- 不把参考项目里的 API key、密码、账号凭证复制到主项目。
- 不用参考项目的 FloatField / float 作为正式金额、数量、净值、PnL。
- 不让数据站或前端页面成为订单、成交、持仓、PnL 权威。
- 不在服务启动时自动运行真实下单任务。
- 不把 `result_unknown` 当成失败后直接重试。
- 不让 CCXT、MT5、vn.py、Freqtrade 的对象直接穿透到前端或领域模型。
- 不因为存在 `localPreview` 就把预览数据当成真实数据。
- 不在 V1 做 CTP、完整基金 NAV、投资人份额、申赎和金融 AI 分析。

## 6. 第一批 PoC 顺序

```text
1. Fake Gateway 工程闭环
2. Crypto API 模拟盘／测试盘 PoC
3. 资费套利完整闭环
4. MT5 Demo / Worker PoC
5. 跨所价差 Crypto + MT5 完整闭环
6. 基础风险、对账、通知和审计
```

## 7. 采用门槛

任何参考代码进入主项目之前，必须回答：

- 是否会影响平台领域模型。
- 是否会形成第二套订单、成交、持仓、PnL 或净值权威。
- 是否支持幂等、恢复、对账和结果未知处理。
- 是否能脱敏日志和保护凭证。
- 是否有模拟盘、测试盘或 Demo 验证结果。
- 是否能在失败时退出或替换。

没有通过这些问题的内容，只能留在参考层，不能进入 V1 主路径。
