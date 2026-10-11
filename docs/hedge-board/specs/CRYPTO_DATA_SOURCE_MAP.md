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
| 尚未接通的链上估值与资金流 | Checkonchain、Glassnode、CryptoQuant、Arkham、BGeometrics | 稳定币、URPD 与六档 BTC 地址分布已本地采集；其余未接通指标保留明确缺口。 |
| 多 Venue 衍生品、清算、期权与波动率 | CoinGlass、Deribit、Greeks.live、Bybit、OKX | 不将单一来源误标为聚合数据。 |
| 公开研究布局 | TradingView 及明确原始网页 | 仅新标签页跳转，不依赖用户登录态或私有模板。 |

## 口径与限制

- 聚合 funding、OI、basis 仅在 constituents、权重、时间和失败处理可验证时提供；否则按单 Venue 或外部入口呈现。
- 加密资产使用 7×24 日历；ETF、上市公司和跨资产比率按对应市场日历对齐。
- 理财信息属于加密研究的观察材料，不代表收益承诺、申购入口或交易授权。
- ETF、IV 和 DVOL 数据按各自来源的市场日历与时间戳展示；刷新失败保留上次有效数据并标记状态，不以零值替代缺失。
- BTC / ETH ETF 日流量卡位于“加密资金面”，默认展示后端生成的日流量与价格双轴图，资金流使用左轴、Bybit 策略归档参考收盘价使用右轴；每日流量柱使用独立视觉比例，价格覆盖不足时保持不可用，不渲染零散断线；图表下方复用策略模块的日期标签、概览线、双滑块和范围按钮，可切换近 90 日、近 1 年或全部历史；卡片不重复展示抓取日期、单位和覆盖天数摘要，视图切换仅保留图标按钮；点击表格图标切换到最新日期倒序表格；BTC 的 30 日均线与各 ETF 细节继续作为卡片参考链接，ETH 保留 SoSoValue 参考入口。Greeks.live BTC Data Lab（含 BTC ATM IV 期限结构本地交互）位于“期权分析”，其参考网页链接保留。

## 本地公开数据补充

- 稳定币：DefiLlama `stablecoincharts/all`，汇总 `totalCirculatingUSD`，保留每日原值。
- 恐惧贪婪：Alternative.me 官方 API，0–100，页面紧邻数据注明来源。
- Deribit：BTC option book summary 的 Call/Put OI 与 Put/Call 比率；单一交易所快照，历史从接入日积累，ATM IV 原链路保留。
- BTC DVOL 主图读取独立生产端的完整 UTC 日收盘历史；按官方 OHLC 第五项取 close，逐页处理 continuation，排除未闭合当日，保留缺失值和原始响应。[Deribit 字段定义](https://docs.deribit.com/api-reference/market-data/public-get_volatility_index_data)。原小时历史接口同步修正 close 字段、分页及不必要的两位小数截断。
- BitcoinTreasuries：可公开读取的上市公司持仓样本及 Strategy；采集日不冒充统一披露日，不能由样本余额变化推成财库周净流入。
- Strategic ETH Reserve：只纳入 ACTIVE 实体，排除未审/停用记录；保留原始更新时间与 PUBLIC_REPORT / SELF_REPORTED / WALLET_TRACKING 标识。旧披露仍可 stale，抓取成功不代表所有实体当日披露。
- BGeometrics URPD：UTXO 最后移动价格分桶及 BTC 数量；这是链上价格分布，非已证实的投资者成本。生产端校验全部区间后发布，priceLower / priceUpper 原生数值边界贯穿 JSON、DuckDB 和 API；页面按价格比例绘制柱状图，保留键盘查看与数据表，缺失量不画作零。
- STRC：Yahoo 交易所日线价格，不冒充实时 ATM 发行额或收益率；最新交易日可能未收盘。
- Coinbase/Binance 日线溢价：闭合 UTC 日线精确日期相交，并用 Coinbase USDT/USD 调整计价币，公式和输入版本由生产端保留。
- 保证金借贷：Bybit USDT 公开 VIP 0 小时费率；非用户账户实际成本。Binance 资金费率单独接入原有历史组，不冒充全市场聚合。
- 加密明细参与度：BTC/ETH/SOL/BNB/XRP/DOGE/HYPE 固定观察池，排除 UTC 当前日期，用同日且历史足够的币种计算高于 20/50/200 日均线的比例；覆盖数与日期同步展示。HYPE 来源缺失时保留 6/7 partial，不用同名代币替换，也不混入上市公司或 ETF。

财库周净流入、全市场合约 OI/清算热力、CoinGlass CDRI、STRC ATM 实际发行尚未形成可靠的本地数据链；这些缺口与文章、作者、Seasonal Chart 等明确外部研究工具分开对待。

- BTC 地址分布：使用 BGeometrics 公开 HTML 日报的六档 Today 地址数，保留原始余额分桶、报表日期和未指定时区；核对分桶合计与 Total，地址不等于人数/实体。原报表历史变化列合计不一致，未纳入；本地历史从接入日积累。

- Bitcoin 减半周期：Blockchain.com 跨交易所日度 USD 市场均价，保存未抽样历史与四次减半日=100 的派生序列；按 2012-11-28 / 2016-07-09 / 2020-05-11 / 2024-04-20 UTC 日期归一。来源：[市场价格方法](https://www.blockchain.com/explorer/charts/market-price)、[区块 210000](https://www.blockchain.com/explorer/blocks/btc/210000)、[420000](https://www.blockchain.com/explorer/blocks/btc/420000)、[630000](https://www.blockchain.com/explorer/blocks/btc/630000)、[840000](https://www.blockchain.com/explorer/blocks/btc/840000)。排除未闭合 UTC 当日，零报价作缺失；周期截止下一次减半前一日，无插值、无后续预测。页面按距减半日的天数对齐，可切换范围、对数/线性及查看对应日期。
- 减半图展示参考 CoinGlass 的多周期叠线与顶部图例，默认展示完整周期，支持显隐且至少保留一条；价格指数仍以减半日=100，累计涨跌另列。参考站包含首次减半前的 Epoch 1，本地没有相应可验证基准，仍只展示四次已落库的减半周期。
- 未接通的 CDRI、全市场 OI/清算、ATM 发行及交易所链上资金流卡片明确显示缺口，保留参考入口。

- BTC ETF 折溢价覆盖 IBIT、BITB、HODL。IBIT：从 iShares 产品页公开图表取得逐日序列，并与页面最新日期/数值核对；沿用发行方展示的小数精度，原始高精度字段和页面保留在归档。真实历史目前从 2025-01-02 开始，未补造更早记录；当前日以后不发布。该指标为收盘价相对 NAV 的百分比，NAV 的比特币定价窗口与收盘时点不同，不能当作无风险套利空间或全市场 ETF 聚合。

- BITB：Bitwise 公开产品页 premiumDiscount 图表；采用折溢价自身日期，比例与百分数交叉核对。HODL：VanEck 官方 historical-prices XLSX 的 `% Premium/Discount`，保留公布百分数，不以舍入后的 NAV/价格重算；排除上市前及空成交量日期，保留源站零成交量日期。三只基金独立展示，不合成全市场值。
- GEX：Deribit public instrument/book summary 推导远期 Gamma；Cboe IBIT 公开延迟期权链使用公布 Gamma、标准 100 股乘数。Call 正 / Put 负仅为 OI 敞口代理；显示纳入合约和 OI 覆盖，缺失隐波合约排除，报价/OI 日期未知时明确标识。支持到期日、近价/全行权价和数据表；完整方法、保存路径及刷新时效见 RESEARCH_DATA 合同。
