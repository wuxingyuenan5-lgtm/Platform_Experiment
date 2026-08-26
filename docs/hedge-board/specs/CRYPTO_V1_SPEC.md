# 对冲基金看板｜加密看板 V1 规格（Crypto V1 Spec）

> 状态：Product Scope Discussion v0.1 / Not Frozen  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`  
> 作用：定义“对冲基金看板 → 加密看板”的 V1 产品范围、既有内容保护、拟新增模块与后续数据源设计边界。  
> 说明：本文件只描述 Crypto V1，不替代整个 Hedge Board Master Plan；当前仍处于产品规格讨论阶段，未经用户确认不得自行升级为 Frozen。

---

## 1. 全局原则【冻结】

Crypto V1 严格遵守 Hedge Board 全局 Additive Only：

- 不删除现有内容；
- 不移动现有内容；
- 不改变现有顺序；
- 不重构现有整体 UI；
- 不改变视觉组件硬编码；
- 新增内容先统一追加在现有 Crypto 页面下方；
- 新增组件必须与现有平台视觉风格一致；
- 金融数据硬编码逐步真实化，但视觉组件不因“去硬编码”而被重写。

最终页面顺序、合并与删减，等 V1 完成并线下验收后再决定。

当前只完善产品规格，不进入工程实施。

---

## 2. 既有 Crypto 页面【受保护】

现有页面与结构全部保留，包括但不限于：

### 2.1 BTC Main

- BTCUSDT Main Chart；
- BTC IV / Deribit DVOL。

### 2.2 Crypto Market Detail

现有 Market Detail 已覆盖：

- BTC、ETH、SOL、BNB、XRP、DOGE、AAVE、UNI、CRV、HUMA、ONDO、PLUME、PEPE、SUI 等主流/重点币；
- IBIT；
- MSTR、CRCL、COIN、BMNR、HOOD 等币股；
- USDT/USD；
- MSTR/BTC、CRCL/BTC、COIN/BTC、ETH/BTC、BTC/XAU、BTC/SPY、ETH/SOL 等相对比价；
- BTC.D、USDT.D、USDC、TOTAL、TOTAL2、TOTAL3、OTHERS.D 等市场扩散与市占率指标。

现有内容先保留，不因 V1 新增 Section 而重复塞入同类指标。

### 2.3 BTC ETF Flow【受保护核心模块】

现有：

- BTC ETF 日净流量 vs BTC 价格。

当前数据层存在静态/硬编码问题，后续进入工程实施时必须真实化，但不重做现有视觉组件。

### 2.4 Bitcoin Treasuries Flow【受保护核心模块】

现有：

- 上市公司；
- 私营财库；
- 基金 / 信托；
- BTC Treasury Flow 图。

当前数据层存在静态/硬编码问题，后续真实化，但不重构现有视觉表现。

---

## 3. Crypto V1 产品目标【方向冻结】

Crypto V1 不以“继续增加币种”为核心，而是补齐加密市场特有的结构数据。

目标信息链：

```text
Price / Market Structure
    ↓
Institutional Flows
    ↓
Derivatives & Leverage
    ↓
Options & Volatility
    ↓
Stablecoin Liquidity
    ↓
On-chain State
    ↓
Breadth / Rotation（利用现有 Market Detail）
```

页面本身只展示数据和结构，不自动生成交易观点、仓位建议或市场判断。

---

## 4. Institutional Flows【方向冻结】

### 4.1 BTC ETF

保留现有 BTC ETF 日净流量 vs BTC 价格，并在工程实施时接入真实数据。

可在不增加独立复杂模块的前提下增加轻量状态：

- 最新单日净流量；
- 5D / 7D rolling net flow；
- 30D rolling net flow；
- 累计净流入（数据口径稳定时）。

不在 V1 默认把每只 BTC ETF 拆成大量独立图表。

### 4.2 ETH ETF

新增：

- ETH ETF Daily Net Flow vs ETH Price；
- 最新单日净流量；
- 5D / 7D、30D rolling net flow（数据口径稳定时）。

### 4.3 Treasury / Institutional Holdings

保留并真实化现有 Bitcoin Treasuries Flow。

允许补充轻量 KPI：

- 总持币量；
- 总持币市值；
- 近期净增持。

V1 不建设大规模公司持币排行榜或公司基本面数据库。

---

## 5. Derivatives & Leverage【新增核心 / 方向冻结】

V1 重点覆盖 BTC 与 ETH，不扩展到大量 Altcoin。

### 5.1 Funding Rate

展示：

- BTC perpetual funding rate；
- ETH perpetual funding rate。

目标：观察永续合约杠杆多空成本与极端偏离。

### 5.2 Open Interest

展示：

- BTC Open Interest；
- ETH Open Interest；
- 与价格同图或同 Section 对照。

不在页面自动解释“上涨 + OI 上升”等交易结论，只提供数据。

### 5.3 Basis

展示：

- BTC futures / perpetual basis；
- ETH futures / perpetual basis；
- 优先提供标准化或年化口径。

必须明确：

- spot reference；
- futures / perpetual contract；
- annualization methodology；
- exchange / venue；
- timestamp alignment。

### 5.4 Liquidations

V1 暂不强制纳入。

只有找到稳定、免费、统计口径明确的全市场或主要交易所历史爆仓数据后再考虑加入；不得为补齐页面使用来源不明的聚合数据。

---

## 6. Options & Volatility【新增 / 方向冻结】

### 6.1 DVOL

现有 BTC DVOL 保留。

### 6.2 IV Term Structure

新增 BTC / ETH 隐含波动率期限结构。

优先期限：

- 7D；
- 30D；
- 60D；
- 90D；
- 180D。

目标：观察短端事件波动与中长期波动率定价结构。

### 6.3 25 Delta Skew

新增 BTC / ETH 25Δ skew。

建议统一方向定义并在数据源文档中固定，例如：

```text
25D Skew = Put IV - Call IV
```

如果最终使用的数据源采用不同符号方向，必须在 canonical transform 中统一，前端不得混用。

### 6.4 V1 边界

不在 V1 建设完整 Greeks、Vol Surface 或期权策略分析器。

---

## 7. Stablecoin Liquidity【新增核心 / 方向冻结】

目标：用稳定币供给观察 Crypto 体系内部美元流动性。

V1 重点：

- Total Stablecoin Market Cap / Supply；
- 7D change；
- 30D change；
- USDT Supply；
- USDC Supply；
- USDT Share；
- USDC Share。

建议展示：

### 7.1 Stablecoin Supply vs BTC

一张主要时间序列图：

- Total Stablecoin Supply；
- BTC Price。

### 7.2 Stablecoin Status

轻量状态区：

- Total Stablecoin；
- 7D Δ；
- 30D Δ；
- USDT Share；
- USDC Share。

V1 不拆分 Ethereum / Tron / Solana / Base 等链级稳定币供给模块。

---

## 8. On-chain Data【新增核心 / 已确认纳入 V1】

链上数据纳入 Crypto V1，但坚持“少量高信号、适合扫盘”的原则，不建设链上数据数据库大全。

优先围绕四类信息：

### 8.1 Valuation / Profitability

优先候选：

- MVRV；
- MVRV Z-Score（免费稳定源可得时）；
- SOPR；
- NUPL。

目标：观察链上持币者整体未实现盈亏、实现盈亏与估值状态。

V1 不要求四个指标全部强制上线；最终保留组合以后续免费数据源稳定性与页面信息密度为准。

### 8.2 Cost Basis / Realized Value

优先候选：

- Realized Price；
- Realized Cap。

展示优先考虑：

- BTC Price vs Realized Price；
- Realized Cap 单独趋势或轻量 KPI。

### 8.3 Exchange Flow / Exchange Balance

优先候选：

- BTC Exchange Balance / Reserve；
- Exchange Netflow；
- 7D / 30D change（数据口径稳定时）。

必须避免把不同数据商对“exchange wallet set”的定义混成一条连续历史序列。

### 8.4 Holder Structure

优先候选：

- Long-Term Holder Supply；
- Short-Term Holder Supply；
- LTH / STH 相关成本基础或供给占比（免费稳定源可得时）。

不在 V1 扩展到大量地址标签、鲸鱼榜单、矿工地址或复杂实体聚类。

### 8.5 On-chain V1 原则

- BTC 为主；
- ETH 链上数据暂不要求与 BTC 对称铺开；
- 数据源必须免费、口径可解释、可持续自动更新；
- 无可靠免费历史源的指标允许 `not_configured`；
- 不使用来源不明的截图、二次转载或不可验证指标；
- 同一 canonical on-chain series 不得在历史中静默更换不同钱包标签 / 口径算法。

具体指标最终选择、Primary/Fallback、方法学与更新频率进入后续 `CRYPTO_DATA_SOURCE_MAP.md`。

---

## 9. Breadth / Rotation【利用现有内容，不新增独立 Section】

Crypto V1 暂不新建大型 Altcoin Season / Breadth Dashboard。

优先利用现有 Market Detail 中：

- BTC.D；
- USDT.D；
- TOTAL / TOTAL2 / TOTAL3；
- OTHERS.D；
- ETH/BTC；
- ETH/SOL；
- 主流币横截面；
- 币股相对 BTC 表现。

先做数据真实化和正确性；线下验收后如果信息埋得过深，再讨论是否提炼成独立小型 Breadth Section。

---

## 10. Market Detail 真实化【方向冻结】

继续沿用现有视觉和列结构。

进入工程实施后，逐步把静态金融数据真实化：

- latest / close；
- 1D；
- 1W；
- 1M；
- QTD；
- YTD；
- 1Y；
- 52W High；
- 30D Sparkline。

30D Sparkline 继续使用现有 SVG，不嵌 TradingView Mini Chart。

### 10.1 交易日历特别规则

Crypto V1 必须明确区分：

- BTC / ETH / Crypto spot：7×24；
- Crypto perpetual / futures：7×24，但结算和 funding 时点依交易所；
- IBIT / ETF：美国证券交易日；
- MSTR / COIN / CRCL / HOOD 等币股：美国证券交易日。

不得把 7×24 Crypto 与美股 ETF / equities 强制使用同一交易日历计算 1D、1W、30D 或收益率窗口。

相对比价涉及 Crypto 与美股资产时，必须定义对齐时点和缺失日处理规则。

---

## 11. 数据新鲜度与展示规则【方向冻结】

所有新增 Crypto 数据应显示或保留：

- as_of；
- retrieved_at；
- frequency；
- source；
- status；
- stale / degraded flags。

不同模块更新频率不同：

- spot / funding / OI：高频或日内；
- ETF：交易日；
- Treasury holdings：取决于上游披露；
- stablecoin：日频或上游可用频率；
- on-chain：日频或源数据可用频率。

前端不得将不同频率数据伪装成同一实时级别。

---

## 12. 数据源原则【冻结】

Crypto V1 继续遵循 Hedge Board 全局免费优先：

- 免费公开数据优先；
- 交易所官方 API 优先用于 spot / derivatives；
- 可稳定免费获取的聚合源用于 stablecoin / ETF / on-chain 时必须记录 upstream provenance；
- TradingView 仅用于展示，不作为项目数据抓取源；
- Provider 失败不得使用假数据替代；
- 无可靠免费源时使用 `not_configured`；
- 数据源细节后续进入 `CRYPTO_DATA_SOURCE_MAP.md`。

---

## 13. V1 明确不做【当前方向】

Crypto V1 暂不建设：

- 大规模 Altcoin 新币列表；
- 完整链上数据库；
- ETH 与所有公链链上指标对称铺开；
- Whale 地址榜单；
- 矿工地址追踪；
- 复杂实体标签系统；
- 全量 liquidation 数据（除非后续确认稳定免费源）；
- 完整 Vol Surface / Greeks 分析器；
- Crypto 新闻流；
- 自动交易观点、风险建议或仓位建议。

---

## 14. 当前拟议开发优先级【OPEN】

若未来进入工程实施，当前建议优先级：

1. 既有 BTC ETF / Treasury 静态数据真实化；
2. Derivatives & Leverage；
3. Stablecoin Liquidity；
4. ETH ETF Flow；
5. On-chain Core Metrics；
6. Options Structure；
7. Crypto Market Detail 全量真实化与质量验收。

该顺序尚未冻结，最终在 Crypto V1 产品范围确认后决定。

---

## 15. 仍需讨论【OPEN】

1. On-chain V1 最终保留哪些核心指标；
2. MVRV / SOPR / NUPL / Realized Price 等免费稳定数据源；
3. Exchange Balance / Netflow 是否能获得长期稳定、免费且口径可解释的数据；
4. LTH / STH 数据是否进入 V1 最终验收范围；
5. BTC / ETH Funding 是否采用单一主交易所还是多交易所聚合；
6. OI 是否展示 USD notional、coin amount 或两者；
7. Basis 的标准合约与年化算法；
8. Deribit IV Term Structure / 25D Skew 的免费历史数据获取与本地计算；
9. BTC / ETH ETF Flow 免费稳定源；
10. Bitcoin Treasuries 免费稳定源；
11. Stablecoin Supply 免费稳定源与 canonical definition；
12. Crypto Market Detail 各行 Primary / Fallback；
13. V1 最终页面顺序与线下验收后删减。
