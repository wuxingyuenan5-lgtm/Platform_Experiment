# 对冲基金看板｜商品看板数据源图（Commodity Data Source Map）

> 状态：Data Source Baseline v0.1 / Implementation OPEN  
> 上位产品规格：`docs/hedge-board/specs/COMMODITY_V1_SPEC.md`  
> 上位总计划：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`  
> 原则：V1 只采用免费数据源 / 免费公开接口；统一 canonical contract，优先稳定官方源，AKShare 可作为成熟统一接入层；无可靠免费源时明确 `not_configured`，不得伪造。

---

## 1. 总体原则【冻结】

### 1.1 免费优先

Commodity V1 不引入付费行情、付费基本面或付费衍生品数据。

### 1.2 统一口径优先于统一 Provider

统一：

- canonical id；
- 单位；
- currency；
- frequency；
- timestamp / trading day；
- adjustment / settlement definition；
- Primary / Fallback；
- freshness；
- status；
- rights_scope。

不要求所有商品数据来自同一个 Provider。

### 1.3 AKShare 定位

AKShare 在商品模块主要用于：

- 中国期货日线 / 合约数据；
- SHFE 库存 / 仓单等已成熟封装；
- 适合通过统一 Python 接口降低维护成本的数据。

但必须记录 `upstream_source`。如果 AKShare 上游停更或官方源更稳定，则直接改用官方源。

---

## 2. Source Tier【冻结】

| Tier | 含义 | 使用原则 |
|---|---|---|
| A | 官方、免费、结构化、稳定 | 优先 Primary |
| A- | 官方免费，但文件 / 网页结构需要适配或权利需复核 | 可 Primary，需监控 |
| B | 免费公共 Vendor / AKShare 上游公共接口，无 SLA | 可 V1 使用，必须 LKG / fallback |
| C | 可免费查看但再分发或自动化权利不清晰 | `review_required` |
| D | 暂无稳定免费链路 | `not_configured` |

---

## 3. Gold ETF / Official Sector【冻结】

### 3.1 全球黄金 ETF Flow

- canonical: `gold_etf_global_flow`
- Primary: World Gold Council Gold ETF holdings & flows
- Tier: A-/C
- Frequency: weekly / monthly（按上游发布）
- Unit: tonnes / USD
- Use:
  - global weekly flow；
  - regional flow；
  - YTD summary。
- Notes:
  - WGC 数据覆盖全球主要实物黄金 ETF；
  - 保留 methodology / source note；
  - 权利范围标 `review_required`，上线外部商业产品前复核。

### 3.2 SPDR Gold Shares

- canonical: `spdr_gold_holdings`
- Primary: SPDR Gold Shares official historical holdings / archive
- Tier: A-
- Frequency: trading day / upstream available frequency
- Fields:
  - holdings tonnes；
  - daily holdings change；
  - associated gold price field only if official archive includes clear definition。
- Use:
  - SPDR daily flow；
  - holdings vs gold price。

### 3.3 Central Bank Gold

- canonical: `central_bank_gold_reserves`
- Primary: World Gold Council official-sector data
- Secondary / Cross-check: IMF / central-bank publications when practical
- Tier: A-/C
- Frequency: monthly / official release schedule
- Use:
  - top holders；
  - rolling net buyers / strategic buyers。

---

## 4. Gold Macro Drivers【冻结】

沿用 Macro Source Map 的共享 canonical series，不重复维护第二套数据：

- US 10Y nominal yield → U.S. Treasury Primary / FRED fallback；
- US 10Y real yield → Treasury real curve / FRED distribution；
- 10Y breakeven → FRED / locally derived if source map specifies；
- DXY → 复用 Macro canonical DXY source；
- FX → 复用全局 canonical FX source。

Commodity 不自行建立另一套利率 / DXY 数据链。

---

## 5. CFTC Positioning【冻结】

V1 核心品种：

- Gold；
- Silver；
- Copper；
- WTI；
- Natural Gas。

### Source

- Primary: CFTC Commitments of Traders Public Reporting Environment / official compressed historical files
- Tier: A
- Frequency: weekly
- Report: Disaggregated Futures Only 优先作为商品仓位主口径

### Canonical calculations

Managed Money Net Position：

```text
M_Money_Positions_Long_All - M_Money_Positions_Short_All
```

Producer / Merchant Net Position：

```text
Prod_Merc_Positions_Long_All - Prod_Merc_Positions_Short_All
```

Historical Percentile：

- 本地 deterministic calculation；
- rolling window 已冻结为 260 周（5 年）；
- 不由前端临时计算。

### Implemented contract identities（2026-09-02）

| Commodity | CFTC Contract Market Code |
|---|---:|
| Gold | `088691` |
| Silver | `084691` |
| Copper | `085692` |
| WTI | `067651` |
| Natural Gas | `023651` |

正式实现使用 PRE Socrata dataset `72hh-3qpy`，保留完整 canonical 周频历史；供页面读取的 dashboard artifact 仅裁剪为最近 5 年，避免把文件分发层误用作无限历史数据库。

### Quality rules

- 必须通过 CFTC Contract Market Code 显式绑定合约；
- 不只依赖名称模糊匹配；
- 报告日期与发布时间分开保存；
- 周度数据不得伪装成日频。

---

## 6. Energy Inventory / Physical【冻结】

### 6.1 Crude / Products

Primary: U.S. EIA Open Data API v2

Tier: A

需要免费 EIA API key，放 GitHub Secret，不写入仓库。

V1 series：

- U.S. commercial crude oil stocks；
- Cushing crude oil stocks；
- gasoline stocks；
- distillate stocks。

Frequency: weekly

展示：

- latest level；
- WoW change；
- history curve。

### 6.2 Natural Gas Storage

Primary: EIA Open Data API

Tier: A

V1：

- U.S. working gas in underground storage；
- weekly change。

---

## 7. Copper Inventory【当前基线】

### 7.1 SHFE Copper Inventory / Warehouse Receipts

- Primary: AKShare mature SHFE inventory / warehouse-receipt adapter（实现前 live validate）
- upstream_source: SHFE
- Fallback: SHFE official data page / downloadable report
- Tier: A-/B
- Unit: 实现时统一成 tonnes

### 7.2 COMEX Copper Stocks

- Primary: CME Group NYMEX/COMEX Warehouse & Depository Stocks official reports
- Tier: A-
- Frequency: daily / report frequency
- Unit: 按官方报表原单位读取后 canonical 转换为 tonnes

### 7.3 LME Copper Stocks

- Source status: `OPEN / review_required`
- Preferred: LME official daily stocks if stable free automation and redistribution terms can be confirmed
- AKShare / public-web wrapper only作为候选，不在未核验前冻结为 Primary
- 若实施阶段无法确认稳定免费链路：`not_configured`

### 7.4 Inventory aggregation

不得直接把 SHFE / COMEX / LME 原始值混加，必须先统一：

- unit；
- report date；
- registered / eligible / on-warrant semantics。

V1 默认分别展示，不做“全球铜库存总和”除非三者口径完全冻结。

---

## 8. Futures Curve / Term Structure【部分 OPEN】

### 8.1 WTI

产品要求：当前 curve + M1-M2 + M1-M3。

Source state: `OPEN`。

Important constraint:

- EIA historical NYMEX futures series存在，但官方页面明确提示 2024-04-05 之后部分 futures prices 不再提供，因此不能作为 V1 当前期限结构 Primary。

候选优先级：

1. 官方 / 交易所免费 contract-chain endpoint（若实现时可验证）；
2. AKShare 可稳定返回真实单月合约链时使用，并记录 upstream；
3. Yahoo v8 individual futures contracts 仅作为 B-tier research fallback。

若无法得到稳定当前 contract chain：保持 Section，数据状态 `not_configured`，不得用连续合约模拟期限结构。

### 8.2 Brent

同 WTI：必须获得真实单月合约链。

不得用 Brent continuous price 伪造 M1-M2 / M1-M3。

### 8.3 Copper

优先两层：

- SHFE copper contract chain：AKShare / SHFE official；
- COMEX copper contract chain：免费稳定链路实现前验证。

不同交易所曲线不混成一条统一曲线。

### 8.4 Gold

Gold curve V1 priority 较低；仅在真实 contract-chain source 可稳定获得时上线。

---

## 9. Cross-Market Spreads【冻结 / 部分 OPEN】

### 9.1 Brent - WTI

V1 优先实现为：

```text
EIA Brent Europe Spot - EIA WTI Cushing Spot
```

- Primary: EIA
- Tier: A
- Frequency: daily
- Unit: USD/barrel

若未来需要 futures Brent-WTI spread，再单独新增明确的 contract alignment，不与 spot spread 混淆。

### 9.2 COMEX Copper vs LME Copper

Status: `OPEN`

必须冻结：

- COMEX contract / cash definition；
- LME cash / 3M / contract definition；
- USD/lb ↔ USD/tonne conversion；
- timestamp alignment。

LME 免费稳定价格源未确认前，不进入 ready。

### 9.3 SHFE Copper vs LME Copper

Status: `OPEN`

必须处理：

- CNY/tonne ↔ USD/tonne；
- VAT / tax semantics；
- FX；
- trading-hour mismatch；
- contract maturity alignment。

V1 初期可以只展示标准化 price spread / ratio，不直接称“进口利润”。

### 9.4 Shanghai Gold / Silver vs International

Status: optional / `OPEN`

若实现：

- 中国价格优先 SGE / SHFE official or AKShare official-wrapper；
- 国际 XAU/XAG 必须有与现有页面语义一致的免费 source；
- 汇率 / 单位 / 交易时点统一。

---

## 10. Commodity Volatility【冻结】

### GVZ

- Primary: Cboe historical volatility-index data
- Tier: A-
- Frequency: daily

### OVX

- Primary: Cboe Crude Oil ETF Volatility Index historical data
- Tier: A-
- Frequency: daily

Copper volatility 无稳定免费 source 时保持 `not_configured`，V1 不强制。

---

## 11. Commodity Market Detail【Source Policy】

### 11.1 China futures / A-share miners

- SHFE futures：AKShare official-wrapper 优先，SHFE官方 fallback；
- A-share miner equities：AKShare / exchange-derived public data，保持股票复权规则显式。

### 11.2 International metals / energy market prices

优先：

- 免费官方 spot / futures source；
- 若无官方结构化免费接口，可用 Yahoo v8 / AKShare public-web adapter 作为 B-tier research source；
- exact semantic 必须与页面 row 一致。

不得把 futures proxy 静默替换成 `XAUUSD spot` 或反向替换。

### 11.3 BCOM / SPGSCI

若无法确认稳定、免费、可自动化并适合内部使用的准确 index series：

- 保留现有行；
- canonical status = `not_configured`；
- TradingView 仍可作为已有展示入口；
- 不抓 TradingView 数据。

---

## 12. Refresh / Stale Baseline【初版】

| Dataset | Frequency | Suggested refresh | Initial stale threshold |
|---|---|---|---|
| Market prices | daily | daily | 3 calendar days / exchange-aware |
| Gold ETF weekly | weekly | daily check | 10 days |
| SPDR holdings | trading day | daily | 3 business days |
| Central bank gold | monthly | daily check | 45 days |
| CFTC | weekly | daily check | 10 days |
| EIA oil inventory | weekly | daily check | 10 days |
| EIA gas storage | weekly | daily check | 10 days |
| CME warehouse stocks | daily/report | daily | 5 business days |
| Cboe GVZ/OVX | daily | daily | 3 business days |

最终 threshold 在工程实现和实际发布节奏验证后冻结。

---

## 13. Last Known Good【冻结】

任何数据源失败：

- 不用空数组覆盖已有历史；
- 保留 LKG；
- 标 `stale` / `degraded` / `error`；
- 保存 `provider_error` / `fallbacks_used`；
- Primary 与 fallback 不能在历史中静默换口径。

---

## 14. Implementation Gate【冻结】

开始 Commodity 工程实施前必须再次 live validate：

1. AKShare 当前 SHFE inventory / contracts adapters；
2. WTI / Brent current futures chain 免费方案；
3. LME copper stocks / price 的免费自动化与使用权；
4. COMEX copper stocks report parser；
5. WGC / SPDR 当前文件/API结构；
6. Market Detail 中每一个国际 row 的 exact canonical identity。

未通过 live validation 的 source 不得标 `ready`。
