# 商品看板数据源图

本文件保留商品研究的专项来源、许可边界与交付选择；不维护产品范围、阶段进度或通用数据合同。通用规则见 [Research Data Contract](../../contracts/RESEARCH_DATA.md)，用户结果见 [对冲基金看板](../../product/modules/对冲基金看板.md)。

## Native 来源

| 主题 | 来源 | 说明 |
|---|---|---|
| 原油、库欣、汽油、馏分油库存 | U.S. EIA | 官方周度库存；按原始观察日管理时效。 |
| 黄金、白银、铜、WTI、天然气持仓 | CFTC PRE Disaggregated Futures Only | 合约市场代码固定；展示 Managed Money、Producer/Merchant 与历史分位时保留方法口径。 |
| 可公开且已验证的价格历史 | 明确标注的公开来源 | 只用于已接通 Market Detail 行；缺少可靠历史的字段不可用。 |
| 黄金 Seasonal Chart | TradingView，symbol=`XAUUSD` | “商品补充分析”中的轻量外部跳转按钮；点击后在新标签页打开 Seasonal Chart，数据与交互由 TradingView 页面负责，本地看板不挂载图表组件。 |
| 黄金分时累计波动与价格叠加（拥有数据集） | 策略研究共享 Bybit 高精度闭合成交 K 线（`XAUTUSDT:linear:trade`） | 策略模块独占原始高精度行情归档；对冲看板后端从共享投影提取并采样为 15 分钟/1 小时/4 小时输出，按 UTC 亚洲/欧洲/美洲盘口计算带符号累计相对波动，并以每日首个美洲盘有效收盘价生成价格线。只持久化小型派生读模型，不重复存储原始行情；不与 Seasonal Chart 卡混用。 |
| CFTC 持仓报告 | CFTC PRE Disaggregated Futures Only | 金属看板中的 CFTC 卡片只读平台已落库的周度序列，支持黄金、白银、铜、WTI、天然气切换，展示 Managed Money、Producer/Merchant 净头寸、历史分位与历史曲线；页面不直接访问 CFTC。 |

## 外部研究入口

| 主题 | 原始来源 | 交付原因 |
|---|---|---|
| 全球分地区黄金 ETF 周流入、各国央行净购买与储备 | World Gold Council / IMF | 尚未接通：2026-10-02 官方 XLSX 下载返回 403；央行页面标注受限导出。保持缺口，不能用 SPDR 单基金冒充全球总量。 |
| WTI、Brent、金属期限结构和部分库存 | CME、ICE、LME、交易所 | 期限结构、库存及合约口径以原站为准。 |
| 其他商品波动率 | Cboe / 官方产品页 | GVZ 已接 FRED；未接通的其他专有数据仍保留原站入口。 |
| 补充对照图 | MacroMicro | 仅在口径相符时作为参考入口，不替代官方来源。 |

## 口径与限制

- 跨市场价差只有在两个 leg 的许可、币种、合约月份和时间戳都可验证时才本地计算；否则提供原站入口。
- Market Detail 的价格、收益率与小趋势图必须来自同一可追溯历史；没有可靠历史时显示不可用。
- 不新增农产品或把受限商业数据转换为静态快照。
- CFTC 报告按官方报告日显示并标注周度滞后；缺失或过期序列保留来源与状态，不以零值替代。CFTC 数据与商品价格、执行或风险输入保持隔离。

## 本地公开数据补充

- SPDR 官方 historical-archive XLSX：黄金持仓吨数、连续有效交易日持仓差、GLD 股价；节假日不填零，持仓差不标成美元净流入。
- 金价比较采用 Yahoo `GC=F` 近月黄金期货，和 SPDR 持仓、FRED `DFII10` 分别使用双轴；不冒充现货黄金或 LBMA fixing。
- GVZ 使用 FRED `GVZCLS`。
- COMEX 库存直接读取 CME `Gold_Stocks.xls`，保留注册/合格/总量与活动日、报告日；历史从首次采集积累，Pledged 不再次计入合计。
- GLD 借券读取 ChartExchange 公开的 Interactive Brokers 最新快照，保留来源时间、百分比费率及可借股数；只代表单一券商，未购买旧历史。
- 各交易所黄金期货总 OI、沪金期限/期权、跨所价差、原站 QuikStrike 等仍未实现本地完整数据/交互，不因保留链接就判定已完成。
