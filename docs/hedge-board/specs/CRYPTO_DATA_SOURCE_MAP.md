# 加密看板数据源图

本文件保留加密研究的专项来源、聚合口径与交付选择；不维护产品范围、工程阶段或历史验收。通用规则见 [Research Data Contract](../../contracts/RESEARCH_DATA.md)，用户结果见 [对冲基金看板](../../product/modules/对冲基金看板.md)。

## Native 来源

| 主题 | 来源 | 说明 |
|---|---|---|
| BTC / ETH 现货、资金费率、未平仓量、永续基差 | Binance | 单一 Venue 观察，必须明确标识为 Binance 而非全市场 Aggregate。现货采用已收盘 UTC 日线；衍生品保留各自结算语义。 |
| 已接通的加密 Market Detail 历史 | 明确标注的公开来源 | 与当前值使用同一可追溯口径；总市值或市占率缺可靠历史时不可用。 |

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
