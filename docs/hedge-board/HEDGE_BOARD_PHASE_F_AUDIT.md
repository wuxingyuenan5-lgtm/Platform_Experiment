# 对冲基金看板｜Phase F 数据与参考入口审计

> 状态：Initial Audit v0.4 / Engineering NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 可行性原则：`docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`  
> 实施计划：`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`

---

## 1. 产品边界【冻结】

### 1.1 Trading Tools 只读

`/hedge-board/trading-tools/*` 继续保持 Deferred：

- 不开发；
- 不重构；
- 不改 UI；
- 不处理其元数据生成逻辑；
- 不要求为了本轮 Hedge Board 优化去维护 Trading Tools 本身。

但其现有 `name / url / description / domain / tags` 可被 Phase F **只读使用**，作为 Macro / Commodity / Crypto 的参考网站目录。

```text
Trading Tools
= 现成参考网站库
= Phase F 可读取
≠ 当前要开发的业务模块
```

### 1.2 不建设第二套 Reference Links

不新建重复书签库。

某项数据不值得 Native 落地时，优先从 Trading Tools 对应分类中选精确 URL，给业务看板生成 `External Reference Button`。

### 1.3 子页旧“交易工具”模块未来退出

Macro / Commodity / Crypto 子页此前存在把对应 Trading Tools 分类再次嵌入子页的能力。

对应 V1 完成后，目标是：

- Native 数据直接展示；
- 不适合 Native 的具体指标，在对应 Section / Card 上提供精确 External Reference Button；
- 不再重复展示整块 Trading Tools 目录。

当前只冻结方向，**本轮不修改 Trading Tools，也不删除现有子页工具模块**；实际删除/隐藏必须等对应 V1 完成并线下验收后处理。

---

## 2. Phase F 判定状态【冻结】

- `NATIVE_READY`：已有明确、低维护、可自动化的数据链；
- `NATIVE_CANDIDATE`：路线可行，但仍需 live request / 权限 / schema / history 验证；
- `EXTERNAL_LINK`：不值得自建，直接复用成熟原站；
- `OFFICIAL_EMBED`：官方 Widget 明显优于 Native / Link 时使用；
- `OPEN`：仍需研究；
- `NOT_CONFIGURED`：既无合理 Native 链路，也无合适参考入口。

核心原则：

> **好落地的自己落地；不好落地的直接给参考网站按钮。**

---

# 3. Macro 审计

| 数据/模块 | 状态 | Native 来源 | 参考入口 | 维护 |
|---|---|---|---|---|
| GDP / CPI / Core CPI / PCE / Core PCE / PPI / UNRATE / M2 / Breakeven / HY OAS 等 | `NATIVE_READY` | FRED REST API / 官方上游 | FRED / MacroMicro | 低 |
| UST 3M / 2Y / 10Y / 30Y | `NATIVE_READY` | U.S. Treasury | Treasury 官方 | 低 |
| 10Y Real Yield | `NATIVE_READY` | Treasury / FRED fallback | FRED DFII10 | 低 |
| SOFR / EFFR | `NATIVE_READY` | New York Fed / FRED fallback | NY Fed / FRED | 低 |
| Fed Target / IORB / ON RRP Award | `NATIVE_READY` | Fed / FRED | Fed / FRED | 低 |
| CFNAI / CFNAIMA3 | `NATIVE_READY` | FRED / Chicago Fed | FRED | 低 |
| Polymarket概率+历史曲线 | `NATIVE_READY` | Gamma metadata + CLOB `prices-history` | Polymarket | 中，复杂点在 whitelist/token mapping |
| CME FedWatch | `EXTERNAL_LINK` | 不作为 Macro V1 主数据链 | Trading Tools 已有 CME FedWatch | 低 |
| MacroMicro 复杂交叉图 | `EXTERNAL_LINK` | 不逆向抓取 | Trading Tools 已整理 | 低 |
| TradingEconomics / 金十 / 奇货可查总览 | `EXTERNAL_LINK` | 不作为核心官方数据源 | Trading Tools 已整理 | 低 |

## 3.1 Global M2

| 组成 | 状态 | 推荐来源 | 结论 |
|---|---|---|---|
| US M2 | `NATIVE_READY` | FRED / Federal Reserve | 官方成熟 |
| Euro Area M2 | `NATIVE_READY` | ECB SDMX REST API | JSON/CSV，历史/修订可查 |
| Japan M2 | `NATIVE_READY` | BOJ Time-Series API | 2026-02正式上线，JSON/CSV |
| UK M2 | `NATIVE_READY` | Bank of England IADB CSV | series code自动下载，实施时复核最终口径 |
| China M2 | `NATIVE_CANDIDATE` | AKShare `macro_china_money_supply` + PBOC官方核验 | 重点防 stale/upstream停更 |
| FX Conversion | `NATIVE_READY` | ECB reference FX | 月均汇率可本地计算 |

### Global M2 结论

整体可以 Native，不需要外链降级。

China M2 采用：

```text
AKShare adapter
+ upstream provenance
+ latest month check
+ PBOC official date/value verification
+ stale gate
```

AKShare 调用成功不等于数据最新。

---

# 4. Commodity 审计

| 数据/模块 | 状态 | Native 来源 | 参考入口 | 维护 |
|---|---|---|---|---|
| EIA crude / Cushing / gasoline / distillate inventories | `NATIVE_READY` | EIA API v2（免费 key） | EIA | 低 |
| CFTC Gold / Silver / Copper / WTI / NatGas | `NATIVE_READY` | CFTC PRE API | CME COT页面 | 低 |
| Gold ETF monthly regional/fund flow | `NATIVE_CANDIDATE → 高概率Native` | WGC monthly XLSX | WGC Gold ETF | 中低 |
| Gold ETF weekly web flow | `NATIVE_CANDIDATE` | WGC weekly website/data chain | WGC Gold ETF | 中 |
| SPDR holdings / daily flow | `NATIVE_CANDIDATE → 高概率Native` | SPDR Historical Archive XLSX + current disclosure | SPDR GLD | 中低 |
| CME Gold / Silver / Copper warehouse stocks | `NATIVE_CANDIDATE` | CME warehouse/depository reports | CME Registrar Reports | 中 |
| LME monthly copper stocks | `NATIVE_CANDIDATE` | LME monthly XLSX | LME warehouse reports | 中 |
| LME daily 2-day delayed stock breakdown | `EXTERNAL_LINK优先` | 官方日度XLS页面涉及登录/注册 | LME Stock Breakdown | 中高 |
| LME historical price / full prompt curve | `EXTERNAL_LINK` | V1 不强行自建 | LME / SMM / 奇货可查 | 高 |
| WTI current futures curve | `NATIVE_CANDIDATE → 高概率Native` | CME free midnight settlement files / product settlements | CME WTI settlements | 中低 |
| Brent current futures curve | `NATIVE_CANDIDATE / EXTERNAL_LINK fallback` | ICE官网公开多到期月延迟报价，自动化稳定性/rights仍需确认 | ICE Brent futures page | 中 |
| COMEX-LME / SHFE-LME copper structure | `EXTERNAL_LINK优先` | LME leg长期自动化/授权复杂 | SMM进口盈亏 / 奇货可查 | 高 |
| 国内跨期/库存/仓单 | `NATIVE_CANDIDATE` | AKShare + SHFE/INE upstream | 奇货可查 / 1qh | 中 |
| GVZ | `NATIVE_READY` | Cboe historical data | Cboe | 低 |
| OVX | `NATIVE_READY` | Cboe historical data | Cboe | 低 |
| CVOL / 高级金属期权 | `EXTERNAL_LINK` | V1 不复制完整模块 | Trading Tools已有CME CVOL | 低 |

## 4.1 WTI Curve 新结论

CME 已明确：

- daily settlement report覆盖当日所有可交易合约；
- Settlement Files 自 2024 年起通过 CME DataMine 提供；
- **midnight CT 的 Settlements File 继续免费**；
- NYMEX settlement 文件包含多月份合约，足以形成日终 WTI curve、M1-M2、M1-M3。

因此 WTI curve 不再默认外链，优先验证免费 midnight settlement 文件自动下载。

目标数据口径应使用：

```text
Daily settlement
not intraday last price
```

这与本看板“日常扫盘 + 盘后复盘”定位一致。

## 4.2 Brent Curve 新结论

ICE Brent页面公开多到期月 delayed quotes，说明数据展示本身存在；但尚未确认适合作为长期无人值守数据接口。

因此：

- 若找到稳定、允许自动访问的数据接口 → `NATIVE`；
- 否则直接 `EXTERNAL_LINK` 到 ICE Brent futures data page。

不为做曲线长期依赖脆弱网页逆向。

---

# 5. Crypto 审计

| 数据/模块 | 状态 | Native 来源 | 参考入口 | 维护 |
|---|---|---|---|---|
| BTC / ETH spot | `NATIVE_READY` | Binance / Coinbase官方API | TradingView大图 | 低 |
| Binance Funding / OI | `NATIVE_READY` | Binance Futures API | Coinglass | 低 |
| Bybit Funding / OI | `NATIVE_READY` | Bybit V5 | Coinglass | 低 |
| OKX Funding / OI | `NATIVE_READY` | OKX API v5 | Coinglass | 低 |
| Deribit Funding / OI | `NATIVE_READY` | Deribit public API | Deribit / Greeks.live | 低 |
| BTC DVOL | `NATIVE_READY` | Deribit | Deribit statistics | 低 |
| BTC/ETH option snapshot / mark IV | `NATIVE_READY` | Deribit | Deribit / Greeks.live | 中 |
| IV Term Structure / 25D Skew | `NATIVE_CANDIDATE` | Deribit option chain + 本地插值计算 | Greeks.live / Deribit | 中高，可随时回退外链 |
| Stablecoin total / USDT / USDC | `NATIVE_READY` | DefiLlama stablecoin endpoints | 专业稳定币站点 | 低 |
| BTC ETF Daily Flow | `NATIVE_CANDIDATE → 高概率Native` | Farside完整公开daily table | Coinglass / SoSoValue | 中低 |
| ETH ETF Daily Flow | `NATIVE_CANDIDATE → 高概率Native` | Farside完整公开daily table | 对应ETF页面 | 中低 |
| Bitcoin Treasuries | `EXTERNAL_LINK优先` | 当前未确认稳定公开API；网页聚合丰富 | BitcoinTreasuries | 高 |
| MVRV / Realized Cap | `NATIVE_CANDIDATE` | Coin Metrics metric IDs明确 | Checkonchain / Glassnode | 中 |
| NUPL / SOPR | `NATIVE_CANDIDATE` | Coin Metrics metric IDs/方法学明确 | Checkonchain / Glassnode | 中 |
| Exchange Balance / Netflow | `EXTERNAL_LINK优先` | 不自建entity labels | CryptoQuant / Glassnode / Arkham | 高 |
| LTH / STH Supply / Cost Basis | `EXTERNAL_LINK优先` | 除非找到稳定免费统一方法源 | Checkonchain / Glassnode | 高 |
| Liquidation Heatmap | `EXTERNAL_LINK` | 不自建全市场heatmap | Coinglass | 很高 |
| Aggregate Funding / OI | `NATIVE_READY（首批3 Venue） + EXTERNAL_LINK` | Binance + Bybit + OKX | Coinglass | 中 |
| BTC期限结构专业图 | `NATIVE_CANDIDATE / EXTERNAL_LINK` | 可做简版；复杂版不强求 | Checkonchain | 中高 |
| Whale / Wallet Intelligence | `EXTERNAL_LINK` | 不建设地址标签系统 | Arkham / CryptoQuant / BGeometrics | 高 |

## 5.1 Multi-Venue 第一版【基本确认】

第一版 Aggregate：

```text
Binance + Bybit + OKX
```

Deribit主要承担 Options / DVOL，并可补充 derivatives venue。

### Funding 归一化

各 venue funding interval 不一定一致。

Canonical至少记录：

- raw funding rate；
- funding interval hours；
- timestamp；
- annualized / normalized rate（如展示需要）；
- venue；
- contract type。

Aggregate前必须先把 funding interval 统一，再按 OI weighted。

### OI 归一化

Bybit官方明确：

- inverse合约 OI 可为 USD；
- linear合约 OI 可为 coin amount。

因此统一策略：

```text
venue raw OI
→ identify contract type
→ convert to USD notional
→ aggregate
```

不得直接对不同单位的原始 OI 求和。

### OKX 方法学版本

OKX funding API 已存在 formula type 等字段变化历史，Provider必须保留 `methodology_version / quality_flags`，避免上游算法变化后历史被静默混用。

## 5.2 Coin Metrics【技术可行，rights需保留】

官方文档确认：

- Community API root：`https://community-api.coinmetrics.io/v4`；
- Community endpoint 无需 API key；
- 免费范围为 **non-commercial use**，Creative Commons条款；
- MVRV：`CapMVRVCur`；
- Realized Cap：`CapRealUSD`；
- NUPL：`NUPL`；
- SOPR：`SOPR`；
- 均为标准日频 asset metrics。

目前尚未用实际 Community 请求逐个证明四个 metric 都对 BTC 返回 200；因此状态仍保留 `NATIVE_CANDIDATE`，而不是直接升级 `READY`。

即使技术可取，未来用途若超出 Community license，也应改用其他来源或 External Link，不因“无API key”就默认具备任意再分发权。

## 5.3 ETF Flow

Farside目前：

- BTC ETF完整daily flow table公开；
- ETH ETF daily flow table公开；
- 页面标明自动更新。

所以技术路径非常简单，但仍需验证：

- rights_scope；
- HTML/table schema长期稳定；
- 页面异常时parser health check与LKG。

V1高概率可以 Native。

## 5.4 Bitcoin Treasuries

当前网页数据丰富、分类完整，但未确认正式公开API，且名单维护本身属于专业数据聚合工作。

因此当前默认：

```text
EXTERNAL_LINK
```

除非后续发现正式、稳定、授权清晰的数据接口，否则不为这一项建立脆弱抓取链。

---

## 6. 已核验的核心数据入口

### Macro

- FRED：`https://api.stlouisfed.org/fred/`
- U.S. Treasury：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml`
- New York Fed：`https://www.newyorkfed.org/markets/reference-rates`
- ECB SDMX：`https://data-api.ecb.europa.eu/service/`
- BOJ API：`https://www.stat-search.boj.or.jp/api/v1/`
- Bank of England Database：`https://www.bankofengland.co.uk/boeapps/database/`
- Polymarket CLOB：`https://clob.polymarket.com/prices-history`

### Commodity

- EIA API v2：`https://api.eia.gov/v2/`
- CFTC PRE：`https://publicreporting.cftc.gov/`
- WGC ETF：`https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows`
- SPDR GLD：`https://www.spdrgoldshares.com/usa/gld/`
- CME Registrar：`https://www.cmegroup.com/clearing/operations-and-deliveries/registrar-reports.html`
- CME Daily Settlements：`https://www.cmegroup.com/market-data/daily-settlements.html`
- CME WTI Settlements：`https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.settlements.html`
- LME Warehouse Reports：`https://www.lme.com/Market-data/Reports-and-data/Warehouse-and-stocks-reports`
- Cboe Volatility History：`https://www.cboe.com/tradable_products/vix/vix_historical_data`
- ICE Brent Futures Data：`https://www.ice.com/products/219/Brent-Crude-Futures/data`

### Crypto

- Binance：`https://developers.binance.com/docs/derivatives/`
- Bybit：`https://bybit-exchange.github.io/docs/v5/market/`
- OKX：`https://www.okx.com/docs-v5/`
- Deribit：`https://docs.deribit.com/`
- DefiLlama Stablecoins：`https://stablecoins.llama.fi/`
- Coin Metrics Community：`https://community-api.coinmetrics.io/v4/`
- Farside BTC ETF：`https://farside.co.uk/btc/`
- Farside ETH ETF：`https://farside.co.uk/eth/`
- Bitcoin Treasuries：`https://bitcointreasuries.net/`

---

## 7. Trading Tools 高价值 External Link 候选

### Macro

- CME FedWatch；
- MacroMicro宏观交叉图；
- TradingEconomics / 金十 / 奇货可查总览。

### Commodity

- CME CVOL / option metrics；
- 奇货可查国内商品数据；
- 1qh跨期价差；
- SMM有色金属进口盈亏；
- LME官方价格/warehouse页面。

### Crypto

- Coinglass Funding Rate；
- Coinglass Open Interest；
- Coinglass Liquidation HeatMap；
- Checkonchain BTC期限结构；
- Checkonchain图表库；
- Deribit期权指标；
- Greeks.live BTC Data Lab；
- Glassnode；
- CryptoQuant；
- Arkham；
- BGeometrics。

这些链接只读，不修改 Trading Tools 本体。

---

## 8. 当前剩余高价值 OPEN / Live Validation 项

下一轮不扩产品范围，只做真实请求验证：

1. China M2：AKShare当前最新月份与PBOC官方发布一致性；
2. WGC weekly flow：是否能稳定无人值守读取周度数据；
3. SPDR Historical Archive XLSX：实际下载URL与schema稳定性；
4. CME warehouse report：文件地址与历史下载稳定性；
5. LME monthly stocks：月度XLSX能否无登录稳定自动下载；
6. CME DataMine免费 midnight settlement file：实际自动下载流程，确认 WTI curve 可无人值守；
7. ICE Brent delayed contract table：是否存在低维护、允许的自动读取方式；否则固定 External Link；
8. Farside BTC/ETH ETF Flow：rights_scope与parser稳定性；
9. Coin Metrics Community：直接请求 BTC `CapMVRVCur,NUPL,SOPR,CapRealUSD` 验证 entitlement；
10. Binance / Bybit / OKX：用实际返回字段冻结 funding interval / OI USD notional 归一化公式；
11. Trading Tools：最终按钮候选精确URL的可达性、登录要求、迁移风险。

本文件是 Phase F 审计，不代表对应业务 Phase 已开始实施。
