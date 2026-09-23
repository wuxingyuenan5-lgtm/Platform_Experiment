# 加密看板数据源图

本文件保留加密研究的专项来源、聚合口径与交付选择；不维护产品范围、工程阶段或历史验收。通用规则见 [Research Data Contract](../../contracts/RESEARCH_DATA.md)，用户结果见 [对冲基金看板](../../product/modules/对冲基金看板.md)。

## Native 来源

| 主题 | 来源 | 说明 |
|---|---|---|
| BTC / ETH 现货、资金费率、未平仓量、永续基差 | Binance | 单一 Venue 观察，必须明确标识为 Binance 而非全市场 Aggregate。现货采用已收盘 UTC 日线；衍生品保留各自结算语义。 |
| 已接通的加密 Market Detail 历史 | 明确标注的公开来源 | 与当前值使用同一可追溯口径；总市值或市占率缺可靠历史时不可用。 |
| BTC / ETH 现货 ETF 资金流 | Farside UK（`/btc/`、`/eth/`；直连受上游 403 时经 Jina Reader 读取同一公开页面）+ Bybit 日线收盘价 | 后端日度抓取 Farside 美元流量并按同日 Bybit 收盘价换算为 BTC/ETH 币本位落库；原始美元流量、换算价格和币本位流量同时保留。BTC 使用 `crypto_etf_flow`，ETH 使用 `crypto_eth_etf_flow`；不是全市场资金流。价格源暂不可用时保留美元原值并在下一次刷新补换算，不以零值替代缺失。|
| BTC ATM IV 期限结构与历史 | Deribit | 使用 BTC ATM IV、指数价及 DVOL；按到期日和抓取时间保留历史，缺失时不可用。 |
| BTC Seasonal Chart | TradingView，symbol=`BTCUSD` | “链上成本、周期与研究跟踪”中的轻量外部跳转按钮；点击后在新标签页打开 Seasonal Chart，数据与交互由 TradingView 页面负责，本地看板不挂载图表组件。 |
| BTC 分时累计波动与价格叠加（拥有数据集） | 策略研究共享 Bybit 高精度闭合成交 K 线（`BTCUSDT:linear:trade`） | 策略模块独占原始高精度行情归档；对冲看板后端从共享投影提取并采样为 15 分钟/1 小时/4 小时输出，按 UTC 亚洲/欧洲/美洲盘口计算带符号累计相对波动，并以每日首个美洲盘有效收盘价生成价格线。只持久化小型派生读模型，不重复存储原始行情；不与 Seasonal Chart 卡混用。 |

## 外部研究入口

| 主题 | 原始来源 | 交付原因 |
|---|---|---|
| BTC / ETH ETF 流量、企业财库周度流入 | SoSoValue | 原站维护证券流量与财库分类。 |
| 稳定币、链上估值与资金流 | DefiLlama、Checkonchain、Glassnode、CryptoQuant、Arkham | 许可、定义或完整历史不适合本地复制时保留研究入口。 |
| 多 Venue 衍生品、清算、期权与波动率 | CoinGlass、Deribit、Greeks.live、Bybit、OKX | 不将单一来源误标为聚合数据。 |
| 公开研究布局 | TradingView 及明确原始网页 | 仅新标签页跳转，不依赖用户登录态或私有模板。 |

## 口径与限制

- 聚合 funding、OI、basis 仅在 constituents、权重、时间和失败处理可验证时提供；否则按单 Venue 或外部入口呈现。
- 加密资产使用 7×24 日历；ETF、上市公司和跨资产比率按对应市场日历对齐。
- 理财信息属于加密研究的观察材料，不代表收益承诺、申购入口或交易授权。
- ETF、IV 和 DVOL 数据按各自来源的市场日历与时间戳展示；刷新失败保留上次有效数据并标记状态，不以零值替代缺失。
- BTC / ETH ETF 日流量卡位于“加密资金面”，默认展示后端生成的日流量与价格双轴图，资金流使用左轴、Bybit 策略归档参考收盘价使用右轴；每日流量柱使用独立视觉比例，价格覆盖不足时保持不可用，不渲染零散断线；图表下方复用策略模块的日期标签、概览线、双滑块和范围按钮，可切换近 90 日、近 1 年或全部历史；卡片不重复展示抓取日期、单位和覆盖天数摘要，视图切换仅保留图标按钮；点击表格图标切换到最新日期倒序表格；BTC 的 30 日均线与各 ETF 细节继续作为卡片参考链接，ETH 保留 SoSoValue 参考入口。Greeks.live BTC Data Lab（含 BTC ATM IV 期限结构本地交互）位于“期权分析”，其参考网页链接保留。
