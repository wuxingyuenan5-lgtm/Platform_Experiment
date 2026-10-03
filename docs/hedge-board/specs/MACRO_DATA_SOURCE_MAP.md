# 宏观看板数据源图

本文件是宏观看板的专项来源与交付参考，不定义产品范围、工程阶段、分支状态或通用研究数据合同。通用 identity、freshness、rights、LKG 与交付规则见 [Research Data Contract](../../contracts/RESEARCH_DATA.md)；用户结果见 [对冲基金看板](../../product/modules/对冲基金看板.md)。

## Native 来源

| 研究主题 | 来源 | 说明 |
|---|---|---|
| 美国国债曲线 | U.S. Treasury | 3M、2Y、10Y、30Y 等官方期限收益率。 |
| 美国增长与通胀 | BLS、BEA、Chicago Fed、FRED | CPI、PCE、PPI、GDP、工业生产、初请、CFNAI 等按发布频率呈现。 |
| 政策利率与美元流动性 | Federal Reserve、New York Fed、FRED | 政策区间、IORB、EFFR、SOFR、ON RRP、资产负债表、TGA 与 RRP。 |
| 全球 M2 | Federal Reserve、ECB、BOJ、BoE、PBOC 验证口径 | 只在各分项具有可比共同月份及有效汇率转换时汇总。 |
| 汇率换算 | ECB | Global M2 使用与共同月份一致的汇率处理。 |
| 中国国债曲线 | 中国财政部国债收益率曲线 | 2Y、10Y、30Y 使用官方字段。 |
| 部分跨资产市场序列 | 明确标注的公开网页数据 | 仅用于获准的低维护展示；无 SLA、历史或权利不充分时降级为入口或不可用。 |

## 补齐的公开采集

- GDPNow：FRED `GDPNOW`，季度最新估计，SAAR；不冒充季度内预测路径。
- 通胀 Nowcast：Cleveland Fed 官方 `nowcast_year.json`，目标月份与预测更新日期分开保留，空值保留。
- 消费者通胀预期：NY Fed `frbny-sce-data.xlsx` 的 1/3/5 年中位数，不与 Cleveland Fed 模型预期互换。
- 信贷标准：FRED `DRTSCILM`、`DRTSCIS`。
- Fed 结构：WALCL 总资产周三值、WDTGAL/WRESBAL/WCURCIR 周均值分别绘制；不把不同日期口径作会计分项求和。
- 美国国债总发行额：Fiscal Data 拍卖 `total_accepted` 按 `issue_date` 月份汇总，含滚动续发；当月不完整。
- 美元净流动性、VIX、NFCI 改用已有/新增本地序列；来源、观察日期和质量随 API 返回。

## 交付映射

| 主题 | 默认交付 | 限制 |
|---|---|---|
| 市场明细、增长、通胀、短端利率走廊、美元流动性、全球 M2 | Native | 低频数据保持原观察日期；缺历史不补齐。 |
| VIX、信用/跨资产风险观察 | Native 或明确来源的研究入口 | 来源不足时不生成本地替代曲线。 |
| CME FedWatch、预测市场利率路径 | Native read-only snapshot | 概率由 CME 30-Day Fed Funds Futures 结算价与 FRED EFFR 计算；缺少结算价时保持不可用，不填充为零。 |
| TradingView 布局、MacroMicro、金十、美元流动性网站 | External link | 仅提供精确研究入口，不依赖个人登录态。 |

## 特别口径

- 全球 M2 是方法论明确的月度研究指标，不等同于即时全球流动性报价。
- 美元净流动性按已披露的资产负债表组成计算；输入日期无法对齐时结果不可用。
- 通胀预期、实际通胀和市场隐含指标不得混用单位或发布日期。
- 宏观日历属于宏观看板；事件的观察、修订和缺失不构成交易授权。

- 美债收益率原 TradingView 嵌入在实际页面返回权限拒绝，现使用本地 3M/2Y/10Y/30Y 历史组；3M 为 FRED DGS3MO，其他期限复用 Treasury 官方日度序列，保留各来源日期。
