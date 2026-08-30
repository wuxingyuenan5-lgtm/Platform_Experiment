# 对冲基金看板｜Phase F 数据与参考入口审计

> 状态：Initial Audit v0.5 / Engineering NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 可行性原则：`docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`  
> 实施计划：`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`

---

## 1. 产品边界【冻结】

### Trading Tools

Trading Tools 继续 Deferred：不开发、不改 UI、不处理元数据。Phase F 只读其 `name / url / description / domain / tags`，把它当现成参考网站库。

不建设第二套 Reference Links。

Macro / Commodity / Crypto V1 完善后，子页此前“整块读取交易工具目录”的旧模块不再需要；最终形态是：

```text
Native 数据 / 图表
+
少量精准 External Reference Button
```

当前不删除旧模块，等各 V1 完成并线下验收后再处理。

---

## 2. 判定状态【冻结】

- `NATIVE_READY`：明确、低维护、可自动化；
- `NATIVE_CANDIDATE`：路线可行，仍需 live request / rights / schema 验证；
- `EXTERNAL_LINK`：不值得自建，跳转成熟原站；
- `OFFICIAL_EMBED`：官方 Widget 明显优于 Native / Link 时使用；
- `OPEN`：仍需研究；
- `NOT_CONFIGURED`：既无合理 Native 链路，也无合适参考入口。

核心原则：**好落地的自己落地；不好落地的直接给参考网站按钮。**

---

# 3. Macro

| 数据/模块 | 状态 | Native 来源 | 备注 |
|---|---|---|---|
| GDP / CPI / Core CPI / PCE / Core PCE / PPI / UNRATE / M2 / Breakeven / HY OAS | `NATIVE_READY` | FRED / 官方上游 | 低维护 |
| UST 3M / 2Y / 10Y / 30Y | `NATIVE_READY` | U.S. Treasury | 官方 |
| 10Y Real Yield | `NATIVE_READY` | Treasury / FRED fallback | 官方 |
| SOFR / EFFR | `NATIVE_READY` | NY Fed / FRED fallback | 官方 |
| Fed Target / IORB / ON RRP Award | `NATIVE_READY` | Fed / FRED | 官方 |
| CFNAI / CFNAIMA3 | `NATIVE_READY` | FRED / Chicago Fed | 低维护 |
| Polymarket概率+历史 | `NATIVE_READY` | Gamma + CLOB `prices-history` | 中等复杂度，主要在 whitelist/token mapping |
| CME FedWatch | `EXTERNAL_LINK` | — | Trading Tools已有精确页面 |
| MacroMicro复杂交叉图 | `EXTERNAL_LINK` | — | 不逆向抓取 |
| TradingEconomics / 金十 / 奇货可查总览 | `EXTERNAL_LINK` | — | 作为参考入口 |

## Global M2

| 组成 | 状态 | 来源 | 结论 |
|---|---|---|---|
| US M2 | `NATIVE_READY` | FRED / Fed | 成熟 |
| Euro Area M2 | `NATIVE_READY` | ECB SDMX API | JSON/CSV |
| Japan M2 | `NATIVE_READY` | BOJ Time-Series API | JSON/CSV |
| UK M2 | `NATIVE_READY` | BoE IADB CSV | 实施时复核最终series口径 |
| China M2 | `NATIVE_CANDIDATE` | AKShare `macro_china_money_supply` + PBOC核验 | 防 stale / upstream停更 |
| FX | `NATIVE_READY` | ECB reference FX | 月均本地计算 |

China M2 必须执行：

```text
AKShare adapter
+ upstream provenance
+ latest month check
+ PBOC date/value cross-check
+ stale gate
```

AKShare函数调用成功不代表数据最新。

---

# 4. Commodity

| 数据/模块 | 状态 | Native 来源 | 备注 |
|---|---|---|---|
| EIA crude / Cushing / gasoline / distillate | `NATIVE_READY` | EIA API v2 | 免费key |
| CFTC Gold / Silver / Copper / WTI / NatGas | `NATIVE_READY` | CFTC PRE API | 低维护 |
| Gold ETF monthly regional/fund flow | `NATIVE_CANDIDATE + EXTERNAL_LINK fallback` | WGC monthly XLSX / page | 当前直接XLSX下载测试返回403，不升级Ready |
| Gold ETF weekly flow | `NATIVE_CANDIDATE + EXTERNAL_LINK fallback` | WGC weekly page/data chain | 周度页面公开，但无人值守接口仍需验证 |
| SPDR holdings / daily flow | `NATIVE_READY` | SPDR Historical Archive API/XLSX | 官方页面直连 `api.spdrgoldshares.com` 返回XLSX |
| CME Gold / Silver / Copper warehouse stocks | `NATIVE_CANDIDATE` | CME warehouse/depository reports | 仍需文件下载稳定性测试 |
| LME monthly warehouse stocks/queue | `NATIVE_READY` | LME公开月度XLSX | 链接可直接返回XLSX，历史覆盖长 |
| LME daily 2-day delayed stock breakdown | `EXTERNAL_LINK优先` | 官方页面涉及登录/注册 | 不做登录自动化 |
| LME historical price / full prompt curve | `EXTERNAL_LINK` | — | 权限/维护复杂 |
| WTI current futures curve | `NATIVE_CANDIDATE / EXTERNAL_LINK fallback` | CME公开product settlement table | 网站午夜后可免费查看；DataMine flat files当前存在费用，不能假设免费自动文件链 |
| Brent current futures curve | `NATIVE_CANDIDATE / EXTERNAL_LINK fallback` | ICE公开多到期月延迟报价 | 自动读取稳定性/rights仍需确认 |
| COMEX-LME / SHFE-LME | `EXTERNAL_LINK优先` | — | LME leg复杂，SMM/奇货可查入口更合适 |
| 国内跨期/库存/仓单 | `NATIVE_CANDIDATE` | AKShare + SHFE/INE | 可落地但需upstream health check |
| GVZ | `NATIVE_READY` | Cboe | 官方历史 |
| OVX | `NATIVE_READY` | Cboe | 官方历史 |
| CVOL / 高级金属期权 | `EXTERNAL_LINK` | — | Trading Tools已有CME页面 |

## 4.1 WGC / SPDR / LME 实测结论

### WGC

WGC官网明确：

- ETF holdings/flows网页周度更新；
- 月度提供Excel下载。

但本轮直接点击月度 XLSX 链路得到 403，因此目前不能把其下载链视为无人值守稳定接口。

策略：

```text
优先继续寻找已有公开data endpoint / 稳定下载方式
失败 → WGC External Link
```

### SPDR

SPDR GLD官网 Historical Archive 的下载目标实际为：

```text
api.spdrgoldshares.com/api/v1/historical-archive?... 
```

测试返回 XLSX content-type，说明数据链明显优于网页逆向，升级 `NATIVE_READY`。

### LME 月度库存

LME Warehouse Company Stocks and Queue Data：

- 月度；
- 页面列出长期历史；
- XLSX直接下载可返回文件。

因此月度库存可以 Native。

日度两日延迟 Stock Breakdown 页面仍提示登录/注册，不建立登录抓取链。

## 4.2 WTI 修正

CME当前FAQ明确区分：

- product website settlement values：午夜CT后免费查看；
- DataMine flat-file delivery：当前存在DataMine/licensing费用。

因此不能把 `nymex.settle.YYYYMMDD.csv` 当成已确认免费的自动化文件源。

WTI curve 只有满足下列之一才 Native：

1. 公开 product settlement table 存在稳定可读取接口；
2. 发现明确免费、允许自动化的官方替代链。

否则直接外链 CME WTI settlements / 参考网站。

## 4.3 Brent

ICE Brent futures data page公开多个到期月 delayed quotes，数据展示真实存在。

但尚未证明存在适合 GitHub Actions 长期调用的公开接口。

所以保留：

```text
NATIVE_CANDIDATE
with EXTERNAL_LINK fallback
```

---

# 5. Crypto

| 数据/模块 | 状态 | Native 来源 | 备注 |
|---|---|---|---|
| BTC / ETH spot | `NATIVE_READY` | Binance / Coinbase | 低维护 |
| Binance Funding / OI | `NATIVE_READY` | Binance Futures API | 官方 |
| Bybit Funding / OI | `NATIVE_READY` | Bybit V5 | 官方 |
| OKX Funding / OI | `NATIVE_READY` | OKX API v5 | 官方 |
| Deribit Funding / OI | `NATIVE_READY` | Deribit | 官方 |
| BTC DVOL | `NATIVE_READY` | Deribit | 官方 |
| BTC/ETH option snapshot / mark IV | `NATIVE_READY` | Deribit | 中 |
| IV Term Structure / 25D Skew | `NATIVE_CANDIDATE` | Deribit chain + 本地计算 | 复杂时可外链 Greeks.live/Deribit |
| Stablecoin total / USDT / USDC | `NATIVE_READY` | DefiLlama | 低维护 |
| BTC ETF Daily Flow | `NATIVE_CANDIDATE → 高概率Native` | Farside daily table | rights/parser待核 |
| ETH ETF Daily Flow | `NATIVE_CANDIDATE → 高概率Native` | Farside daily table | rights/parser待核 |
| Bitcoin Treasuries | `EXTERNAL_LINK优先` | 未确认正式公开API | 专业聚合名单维护成本高 |
| MVRV / Realized Cap | `NATIVE_CANDIDATE` | Coin Metrics Community候选 | metric ID明确，entitlement待实测 |
| NUPL / SOPR | `NATIVE_CANDIDATE` | Coin Metrics Community候选 | metric ID明确，entitlement待实测 |
| Exchange Balance / Netflow | `EXTERNAL_LINK优先` | — | 不自建entity labels |
| LTH / STH Supply / Cost Basis | `EXTERNAL_LINK优先` | — | 除非找到统一免费源 |
| Liquidation Heatmap | `EXTERNAL_LINK` | — | Coinglass |
| Aggregate Funding / OI | `NATIVE_READY（首批3 Venue）` | Binance + Bybit + OKX | Coinglass作专业参考 |
| BTC专业期限结构 | `NATIVE_CANDIDATE / EXTERNAL_LINK` | 可做简版 | Checkonchain已有成熟入口 |
| Whale / Wallet Intelligence | `EXTERNAL_LINK` | — | Arkham / CryptoQuant / BGeometrics |

## 5.1 Multi-Venue 第一版

```text
Aggregate = Binance + Bybit + OKX
Venue = Binance / Bybit / OKX
Deribit = Options/DVOL核心 + 可选derivatives补充
```

### Funding

Canonical至少记录：

- raw rate；
- funding interval hours；
- timestamp；
- venue；
- contract type；
- normalized/annualized rate（仅展示需要时）。

先统一interval，再按 OI weighted aggregate。

### OI

不同 venue / contract type 的 OI 单位不同。

Bybit官方明确 linear 和 inverse 的单位不同，因此：

```text
raw OI
→ contract type
→ mark/index price + multiplier
→ USD notional
→ aggregate
```

不能直接相加原始 OI。

OKX funding formula曾发生版本变化，provider必须保存 methodology version / quality flag。

## 5.2 Coin Metrics

已确认：

- Community API 无需 key；
- Community free tier限 **non-commercial use**；
- MVRV metric：`CapMVRVCur`；
- Realized Cap：`CapRealUSD`；
- NUPL：`NUPL`；
- SOPR：`SOPR`；
- 均为1D asset metrics。

尚未直接对 Community endpoint逐个请求验证四项对 BTC 是否均返回 200，因此仍为 `NATIVE_CANDIDATE`。

即便技术可取，rights_scope 仍必须保留；未来用途不符合Community条款时转其他源或 External Link。

## 5.3 ETF Flow

Farside BTC/ETH ETF flow table当前公开、自动更新，技术解析简单。

仍需核：

- rights_scope；
- table schema变化；
- parser health check；
- LKG。

## 5.4 Bitcoin Treasuries

网页数据丰富，但未发现正式稳定公开API。

当前默认 `EXTERNAL_LINK`，除非后续发现正式接口。

---

## 6. 已核验的核心入口

### Macro
- FRED `https://api.stlouisfed.org/fred/`
- U.S. Treasury `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml`
- NY Fed `https://www.newyorkfed.org/markets/reference-rates`
- ECB `https://data-api.ecb.europa.eu/service/`
- BOJ `https://www.stat-search.boj.or.jp/api/v1/`
- BoE `https://www.bankofengland.co.uk/boeapps/database/`
- Polymarket `https://clob.polymarket.com/prices-history`

### Commodity
- EIA `https://api.eia.gov/v2/`
- CFTC `https://publicreporting.cftc.gov/`
- WGC `https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows`
- SPDR `https://www.spdrgoldshares.com/usa/gld/`
- CME Registrar `https://www.cmegroup.com/clearing/operations-and-deliveries/registrar-reports.html`
- CME WTI settlements `https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.settlements.html`
- LME warehouse `https://www.lme.com/Market-data/Reports-and-data/Warehouse-and-stocks-reports`
- Cboe history `https://www.cboe.com/tradable_products/vix/vix_historical_data`
- ICE Brent `https://www.ice.com/products/219/Brent-Crude-Futures/data`

### Crypto
- Binance `https://developers.binance.com/docs/derivatives/`
- Bybit `https://bybit-exchange.github.io/docs/v5/market/`
- OKX `https://www.okx.com/docs-v5/`
- Deribit `https://docs.deribit.com/`
- DefiLlama `https://stablecoins.llama.fi/`
- Coin Metrics Community `https://community-api.coinmetrics.io/v4/`
- Farside BTC `https://farside.co.uk/btc/`
- Farside ETH `https://farside.co.uk/eth/`
- Bitcoin Treasuries `https://bitcointreasuries.net/`

---

## 7. Trading Tools 高价值外链候选

### Macro
- CME FedWatch
- MacroMicro交叉图
- TradingEconomics / 金十 / 奇货可查

### Commodity
- CME CVOL / option metrics
- 奇货可查
- 1qh跨期价差
- SMM进口盈亏
- LME价格/warehouse

### Crypto
- Coinglass Funding / OI / Liquidation HeatMap
- Checkonchain BTC期限结构 / 图表库
- Deribit期权指标
- Greeks.live Data Lab
- Glassnode
- CryptoQuant
- Arkham
- BGeometrics

只读 Trading Tools，不修改其本体。

---

## 8. 当前剩余 Live Validation

1. China M2：AKShare最新月份 vs PBOC；
2. WGC：是否存在稳定、无需会话的周度/月度自动数据链；
3. CME warehouse reports：稳定下载方式；
4. WTI：公开 settlement table 是否有低维护自动读取方式；
5. Brent：ICE delayed contract table 是否适合自动读取；
6. Farside：rights_scope与parser稳定性；
7. Coin Metrics Community：直接请求 `CapMVRVCur,NUPL,SOPR,CapRealUSD`；
8. Binance / Bybit / OKX：实际字段级冻结 funding/OI归一化公式；
9. 最终 External Link 候选的精确URL可达性、登录要求和迁移风险。

本文件是 Phase F 审计，不代表任何业务 Phase 已开始实施。
