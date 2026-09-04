# 对冲基金看板｜加密看板数据源图（Crypto Data Source Map）

> 状态：Data Source Baseline v0.1 / Implementation OPEN  
> 上位产品规格：`docs/hedge-board/specs/CRYPTO_V1_SPEC.md`  
> 上位总计划：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`  
> 原则：V1 免费优先；交易所官方 public market API 优先；聚合指标必须透明记录 venue / methodology；链上数据只采用免费、可解释、可持续更新的数据；无可靠免费源时明确 `not_configured`。

---

## 1. 数据架构【冻结】

```text
Exchange / Public Data Source
        ↓
platform-data provider adapters
        ↓
canonical crypto series
        ↓
venue normalization / aggregation / derived metrics
        ↓
quality validation + LKG
        ↓
versioned JSON
        ↓
platform-api
        ↓
Crypto V1 existing UI / new additive sections
```

前端不直接拼接 Binance / Deribit / DefiLlama / Coin Metrics 等外部源。

---

## 2. Source Tier【冻结】

| Tier | 含义 | 例子 |
|---|---|---|
| A | 官方交易所 / 官方公共API | Binance, Deribit |
| A- | 权威公开数据服务，免费可用但需复核用途 | Coin Metrics Community |
| B | 免费聚合 / 公共网页数据，无正式 SLA | DefiLlama, Farside, BitcoinTreasuries |
| C | 免费可见但自动化 / 再分发条款需特别复核 | 某些公共聚合站 |
| D | 无可靠免费链路 | `not_configured` |

V1 允许 B-tier，但必须：

- cache；
- Last Known Good；
- parser / schema health check；
- rights_scope；
- source / retrieved_at。

---

## 3. Spot / Core Market Data【冻结】

### BTC / ETH / major crypto spot

Primary: Binance official public Spot API

Tier: A

用途：

- latest；
- OHLCV；
- 1D / 1W / 1M / QTD / YTD / 1Y；
- 30D Sparkline；
- BTC / ETH price reference for derivatives modules。

### Fallback

- independent exchange public API（实现时优先 Coinbase 或其他可稳定访问的官方交易所源）；
- 不以 TradingView 为 fallback 数据源。

### Canonical rules

- BTC reference spot 优先固定为一个 explicit pair，例如 `BTCUSDT` 或 `BTCUSD`；
- 不在同一历史序列中静默切换 USD 与 USDT；
- USDT-based reference 若用于 USD display，需要显式记录 quote asset 与 peg assumption。

---

## 4. Derivatives & Leverage【冻结】

### 4.1 Initial Venue Set

V1 初始优先支持：

1. Binance Futures；
2. Deribit。

产品架构必须允许后续新增：

- OKX；
- Bybit；
- 其他官方 public derivatives APIs。

但未 live validate 前不写死到实现。

### 4.2 Funding Rate

#### Binance

Primary endpoint family：Binance Futures public market data

可用信息包括：

- funding rate history；
- current / mark-price related funding info。

#### Deribit

Primary endpoints：

- `public/get_funding_rate_history`；
- `public/get_funding_chart_data`；
- ticker / book summary 中 current funding / funding_8h。

#### Canonical format

统一为：

- realized funding rate；
- native funding interval；
- normalized 8h rate（展示比较时）；
- annualized rate 仅作为派生显示，并保存 annualization methodology。

#### Aggregate

默认：OI-weighted funding。

```text
aggregate_funding = Σ(funding_i * OI_USD_i) / Σ(OI_USD_i)
```

必须只聚合可比 perpetual contracts。

### 4.3 Open Interest

Primary：各交易所官方 public derivatives API。

Canonical：

- `oi_native`；
- `oi_usd_notional`；
- venue；
- instrument；
- timestamp。

Aggregate：

```text
aggregate_oi_usd = Σ venue OI_USD
```

主页面优先 USD notional。

### 4.4 Basis

定义必须区分：

- perpetual premium / basis；
- dated futures annualized basis。

Dated futures 年化示例：

```text
basis_annualized = (future_price / spot_price - 1) * 365 / days_to_expiry
```

具体 day-count 与 mark/index price 选择在实现时冻结 methodology version。

Aggregate 仅聚合同期限 / 可比期限 bucket，不得把 PERP、季度、次季混成一个平均值。

### 4.5 Venue Selector

前端支持：

- Aggregate；
- Binance；
- Deribit；
- 后续已配置 Venue。

每次显示必须带当前 venue mode。

---

## 5. Options & Volatility【冻结】

Primary: Deribit official public API

Tier: A

### 5.1 DVOL

- endpoint: `public/get_volatility_index_data`
- currency: BTC / ETH（可用时）
- history: official volatility-index candles

现有 BTC DVOL 直接以 Deribit canonical series 真实化。

### 5.2 IV Term Structure

Source：Deribit active option instruments + public ticker / book summary。

Target tenor：

- 7D；
- 30D；
- 60D；
- 90D；
- 180D。

Method：

- 读取 active expiries；
- 对每个 target tenor 选择最近可比 expiry 或做显式插值；
- 若插值，必须 methodology version；
- 不把不同 moneyness 的单一 option IV 当成期限结构。

建议以 ATM / near-ATM mark IV 建 canonical term structure。

### 5.3 25 Delta Skew

Deribit ticker 可返回 option greeks delta 与 bid/ask/mark IV。

Canonical：

```text
25D Skew = Put IV - Call IV
```

Method：

- 每个目标 expiry 查找最接近 |delta|=0.25 的 put / call；
- 优先 mark IV；
- 必要时在相邻 strikes 间插值；
- 保存 strike selection / interpolation quality flag。

### 5.4 Historical IV structure / skew

官方历史 snapshot 若不足：

- 从 `platform-data` 上线之日起每日 / 定时保存 snapshot；
- 不伪造历史 backfill；
- 历史起点显式标记。

---

## 6. Stablecoin Liquidity【冻结】

### 6.1 Primary

DefiLlama stablecoin dataset / public data service

Tier: B

目标 canonical：

- total stablecoin market cap / supply；
- USDT market cap / supply；
- USDC market cap / supply；
- USDT share；
- USDC share；
- 7D / 30D change。

### 6.2 Cross-check

- Tether official transparency / supply disclosure；
- Circle official USDC transparency（可自动化程度在实现时核验）。

### 6.3 Definition

V1 页面用“Stablecoin Market Cap / Supply”时必须统一定义，避免把：

- issued supply；
- circulating supply；
- bridged supply；
- chain-level duplicate supply

混为一谈。

默认以 DefiLlama aggregate definition 作为 V1 canonical，并记录 methodology/source version。

### 6.4 Stablecoin vs BTC

BTC 价格从项目 Spot canonical series 读取，不从 DefiLlama 另取第二套价格。

---

## 7. BTC / ETH ETF Flows【当前基线】

### 7.1 BTC ETF Flow

Primary candidate: Farside Investors public daily Bitcoin ETF flow table

Tier: B/C

字段：

- date；
- per-fund flow；
- total flow；
- currency = USD million。

### 7.2 ETH ETF Flow

Primary candidate: Farside Investors public Ethereum ETF flow table

Tier: B/C

### 7.3 Rules

- Farside 是免费公开数据但不是交易所官方 API；
- 实现前复核自动化访问 / 使用条款；
- 保存原始表快照 / normalized output；
- parser schema change 触发 error，不静默返回 0；
- 0 flow 与 missing / not reported 必须区分；
- BTC/ETH price 从项目自身 spot canonical series 对齐。

### 7.4 Fallback

如果 Farside 无法稳定自动化：

- 研究 SoSoValue 等免费公开替代；
- 或根据 ETF issuer shares outstanding / NAV 构建更复杂官方派生链；
- 在 fallback 完成前保留 LKG / stale，不生成假 flow。

---

## 8. Bitcoin Treasuries【当前基线】

Primary candidate: BitcoinTreasuries.net public company holdings dataset

Tier: B/C

Use：

- listed-company BTC holdings；
- aggregate holdings；
- category totals；
- recent disclosed changes（只有时间口径明确时）。

Cross-check：

- company SEC filings / exchange announcements / investor relations；
- Strategy 等大型持有者优先做 independent sanity check。

### Flow caveat

“Bitcoin Treasuries Flow”只有在能从相邻披露快照准确计算增持 / 减持时才能称 flow。

否则应展示：

- holdings snapshot；
- disclosed change；

不得把页面抓取差异误判成真实交易流。

---

## 9. On-chain Core【冻结 / 免费可用性需逐项 live validate】

### 9.1 Primary candidate

Coin Metrics Community API

Tier: A-/C

Access：

- community endpoint 可无 API key 访问社区数据；
- 官方说明 Community 数据免费用于 non-commercial use；
- 因此当前项目如为内部研究可作为候选，外部商业分发前必须复核权利。

### 9.2 MVRV

Metric candidate: `CapMVRVCur`

Definition：Market Cap / Realized Cap。

Primary candidate: Coin Metrics Community if live catalog confirms BTC metric accessible。

### 9.3 NUPL

Metric candidate: `NUPL`

Definition：

```text
(CapMrktCurUSD - CapRealUSD) / CapMrktCurUSD
```

可直接取 source metric，或使用同一 Provider 的 market cap + realized cap deterministic derive。

### 9.4 SOPR

Metric candidate: `SOPR`

Frequency: daily

可增加 7D MA 作为图表平滑辅助，但原始 SOPR 保留。

### 9.5 Realized Cap / Realized Price

Realized Cap candidate: `CapRealUSD`

Realized Price：优先本地 derive：

```text
realized_price = CapRealUSD / SplyCur
```

前提：两者来自同一 Provider / same observation date。

### 9.6 MVRV / NUPL / SOPR / Realized metrics gating

实现前必须调用 Coin Metrics Community catalog 验证：

- BTC 是否可用；
- 1d frequency；
- historical min/max；
- Community entitlement。

如果某 metric 仅 Pro：该 metric `not_configured`，不得偷偷换成来源不明的二次转载。

---

## 10. Exchange Balance / Netflow【OPEN】

产品规格要求：

- BTC Exchange Balance / Reserve；
- BTC Exchange Netflow。

但该类指标依赖交易所地址标签集合，免费源长期稳定性和口径一致性较差。

### V1 source rule

- 优先寻找公开、免费、可自动更新且说明 wallet labeling methodology 的 Provider；
- 必须让 Balance 与 Netflow 来自同一 label universe；
- 不允许拼接 Glassnode / CryptoQuant 截图或二次转载；
- 若实施前无可靠免费源：`not_configured`。

该产品 Section 保留，但宁可空状态也不伪造。

---

## 11. LTH / STH Supply【OPEN】

产品规格要求：

- Long-Term Holder Supply；
- Short-Term Holder Supply。

基准阈值优先采用市场常用 155 days，但最终需按数据源 methodology 冻结。

Coin Metrics 文档提供 155-day LTH/STH SOPR metrics，但是否能免费获取“Supply”本身需 live catalog 验证。

### Rules

- 如果免费 source 提供统一 LTH / STH supply：接入；
- 如果只能获得 SOPR 而非 supply，不得用 SOPR 替代 supply；
- 不从图表图片反推数值；
- 无免费稳定 source → `not_configured`。

---

## 12. Crypto Market Detail【Source Policy】

### 12.1 Crypto assets

BTC / ETH / supported altcoins：

- Primary: Binance spot official API where symbol exists；
- Fallback: independent exchange official API。

### 12.2 Crypto equities / ETF

- IBIT / MSTR / COIN / CRCL / HOOD 等：Yahoo v8 Chart 可作为 B-tier research convenience；
- 后续若有稳定免费证券行情源可替换；
- close 与 adjusted close 必须区分。

### 12.3 Dominance / TOTAL / TOTAL2 / TOTAL3

TradingView 当前仅负责展示。

项目自有 canonical data：

- 需要独立免费 market-cap aggregator 或可重建 universe；
- Source 尚未冻结；
- 在无稳定源前不得从 TradingView 抓取；
- 对无法真实化的 row 使用 `not_configured` / existing visual-only state。

### 12.4 Relative ratios

ETH/BTC：优先同交易所直接 market pair。

BTC/XAU、BTC/SPY、MSTR/BTC 等跨资产 ratio：

- 读取各自 canonical series；
- 明确 7×24 vs securities calendar 对齐规则；
- 美股闭市日不 forward-fill 后伪装成同步 market move；
- ratio calculation methodology 在实现时冻结。

---

## 13. Refresh Baseline【初版】

| Dataset | Suggested refresh | Initial stale threshold |
|---|---|---|
| Spot BTC/ETH | 15m-1h snapshot / daily history | 2h intraday / 2d daily |
| Funding | 每 funding interval / 至少1h | 2 intervals |
| OI | 1h | 3h |
| Basis | 1h | 3h |
| DVOL | 1h / daily canonical | 3h |
| IV term / skew | 1h-4h snapshot | 6h |
| Stablecoin | daily | 3d |
| ETF flow | US trading day after data available | 2 business days |
| Treasury holdings | daily check / source cadence | 7d or source-specific |
| On-chain core | daily | 3d |

GitHub Actions 不适合作分钟级实时市场数据库。若最终只用 GitHub Actions，工程实现可以降低抓取频率为数小时级 / 日频并明确页面 freshness；未来实时化应迁移到常驻数据服务。

---

## 14. Aggregation Quality Rules【冻结】

### Funding

- only comparable perpetuals；
- normalize interval before compare；
- OI-weighted；
- missing venue 不按0处理。

### OI

- convert to USD notional；
- record native amount；
- aggregate only same underlying。

### Basis

- same underlying；
- same / comparable maturity bucket；
- explicit spot/index reference；
- OI-weighted only within comparable set。

### Venue failure

若一个 venue 失败：

- Aggregate 可继续使用其余 venue；
- status = `degraded`；
- `venues_included` / `venues_missing` 必须返回；
- 不把残缺聚合标 `ready`。

---

## 15. Last Known Good【冻结】

所有模块：

- fetch failure 不覆盖 LKG；
- parser schema change → error；
- stale 数据保留 observation_date；
- `retrieved_at` 更新不等于 observation 更新；
- fallback / venue degradation 必须显式。

---

## 16. Implementation Gate【冻结】

开始 Crypto 工程实施前再次 live validate：

1. Binance public funding / OI / futures market endpoints当前限制；
2. Deribit DVOL / funding / instrument / ticker endpoints；
3. DefiLlama stablecoin API exact endpoint与历史字段；
4. Coin Metrics Community 对 `CapMVRVCur`, `NUPL`, `SOPR`, `CapRealUSD`, `SplyCur` 的 BTC entitlement；
5. Exchange Balance / Netflow 免费来源；
6. LTH / STH Supply 免费来源；
7. Farside BTC / ETH ETF flow 自动化与权利范围；
8. BitcoinTreasuries data automation 与披露时点；
9. Crypto Market Detail dominance / TOTAL 系列的免费来源；
10. 每个跨资产 ratio 的 calendar alignment。

未通过 live validation 的 source 不得进入 `ready`。

---

## 17. Implementation Evidence（2026-09-02）

- Binance Spot `data-api.binance.vision` 与 USD-M Futures `fapi.binance.com` 已在本地 live validate；
- BTC / ETH spot、funding、OI、perpetual basis 共 8 条 series 已发布，`venue_binance` 与 `mode_venue_not_aggregate` 写入 quality flags；
- spot 使用已收盘 UTC 日线；funding 为当日已实现费率均值；OI 与 perpetual basis 为当日最后观测；
- 数据 commit：`1707668`；应用 commit：`9fa3d25b`；
- 2026-09-03 Owner 确认统一迁移至 `D:\自营数据库`，GitHub 仅保留代码；
- Binance Futures 本机系统 DNS 被污染至错误地址；实现限定 `fapi.binance.com` 的 Cloudflare DoH fallback，并继续依赖 TLS 主机名校验，不修改系统 DNS / hosts；
- 本地真实刷新通过，Crypto 8/8 series ready；DuckDB 与 JSON serving contract 同步；
- 数据 commit `ccc69cc`，应用本地读取 commit `05c37323`；GitHub code-only CI runs `33658157466`、`33658157488`、`33658157326` 均成功。
