# 对冲基金看板｜Phase F 数据与参考入口审计

> 状态：Initial Audit v0.3 / Engineering NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 可行性原则：`docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`  
> 实施计划：`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`

---

## 1. 本轮确认的产品边界【冻结】

### 1.1 Trading Tools 的角色

`/hedge-board/trading-tools/*` 当前继续保持 Deferred：

- 不开发；
- 不重构；
- 不改 UI；
- 不调整其元数据生成逻辑；
- 不要求为了本轮 Hedge Board 优化去维护 Trading Tools 本身。

但 Trading Tools 中已经整理好的 `name / url / description / domain / tags` 可以被 Phase F **只读使用**，作为 Macro / Commodity / Crypto 的参考网站目录。

```text
Trading Tools
= 现成参考网站库
= Phase F 可读取
≠ 当前要开发的业务模块
```

### 1.2 不再建设第二套 Reference Links

不新建重复的参考网站书签库。

当某数据不值得 Native 落地时，优先从 Trading Tools 对应分类中选择最合适的精确 URL，供业务看板生成 `External Reference Button`。

### 1.3 子页内部“交易工具”模块的后续处理

Macro / Commodity / Crypto 子页此前存在从 Trading Tools 读取并展示“本页工具”的能力。

当对应业务子页 V1 数据和参考入口完善后，这种“把整个交易工具分类再次嵌入子页”的模块**不再需要**。

最终目标：

- 子页直接展示 Native 数据；
- Native 不合适的具体指标，在对应 Section / Card 上给出精确 External Reference Button；
- 不再在子页重复展示一整块通用 Trading Tools 目录。

注意：当前只冻结这一方向，**本轮不修改 Trading Tools 或现有子页工具代码**；实际删除/隐藏旧子页工具模块需等对应 V1 完成并线下验收后执行。

---

## 2. Phase F 最终判定状态【冻结】

每个数据/子模块最终优先判为：

- `NATIVE_READY`：已有明确、低维护、可自动化数据链，可进入实施；
- `NATIVE_CANDIDATE`：技术路线可行，但还需 live request / 权限 / schema / 历史覆盖验证；
- `EXTERNAL_LINK`：不值得自建，直接复用 Trading Tools 中的成熟原站入口；
- `OFFICIAL_EMBED`：仅官方 Widget 明显优于 Native / Link 时使用；
- `OPEN`：还需研究；
- `NOT_CONFIGURED`：既没有合理 Native 链路，也没有合适参考入口。

---

# 3. Macro 初步审计

| 数据/模块 | 初步状态 | Native 来源 | Trading Tools / 参考入口 | 维护判断 |
|---|---|---|---|---|
| GDP / CPI / PCE / PPI / UNRATE / M2 / Breakeven / HY OAS 等 FRED 序列 | `NATIVE_READY` | FRED REST API | Trading Tools 已有 FRED / MacroMicro 等入口 | 低 |
| UST 3M / 2Y / 10Y / 30Y | `NATIVE_READY` | U.S. Treasury XML / CSV | Treasury 官方页面 | 低 |
| 10Y real yield | `NATIVE_READY` | Treasury real yield XML / FRED fallback | FRED DFII10 | 低 |
| SOFR / EFFR | `NATIVE_READY` | New York Fed Markets Data / FRED fallback | Trading Tools 已有 NY Fed、FRED SOFR | 低 |
| Fed target / IORB / ON RRP award | `NATIVE_READY` | Fed / FRED | Trading Tools 宏观工具 | 低 |
| Polymarket event probability + history | `NATIVE_READY` | Gamma metadata + CLOB `prices-history` | Trading Tools 综合工具已有 Polymarket | 中，主要复杂度在 whitelist / token mapping |
| CME FedWatch | `EXTERNAL_LINK` | 不作为 Macro V1 主数据链 | Trading Tools 已有 CME FedWatch 精确页面 | 低 |
| MacroMicro 复杂宏观交叉图 | `EXTERNAL_LINK` | 不逆向抓取 | Trading Tools 已有大量 MacroMicro 精确子页面 | 低 |
| TradingEconomics / 金十 / 奇货可查宏观总览 | `EXTERNAL_LINK` | 不作为核心官方数据源 | Trading Tools 已整理 | 低 |

## 3.1 Global M2 组成审计

| 组成 | 状态 | 推荐来源 | 审计结论 |
|---|---|---|---|
| US M2 | `NATIVE_READY` | FRED / Federal Reserve | 官方序列成熟 |
| Euro Area M2 | `NATIVE_READY` | ECB Data Portal SDMX 2.1 REST API | 官方 API 支持 JSON/CSV、历史/修订查询 |
| Japan M2 | `NATIVE_READY` | BOJ Time-Series Data Search API | BOJ 2026-02-18 正式上线 API，任何人可用，支持 JSON/CSV |
| UK M2 | `NATIVE_READY` | Bank of England IADB CSV download | 官方数据库支持 series code 自动 CSV 下载；`LPMVWYH` 等系列需实施时最终复核口径 |
| China M2 level | `NATIVE_CANDIDATE` | AKShare `macro_china_money_supply` / 上游东方财富，PBOC官方发布作核验 | AKShare接口明确提供M2数量，但上游不是PBOC API；必须做最新日期与stale health check |
| FX conversion | `NATIVE_READY` | ECB reference FX / official FX series | ECB SDMX API适合统一月均汇率 |

### Global M2 结论

Global M2 **整体可 Native 实现**，不需要降级为外链。

真正需要重点防守的只有 China M2：

- AKShare可作为便捷主适配器；
- 必须记录其 upstream；
- 每次抓取检查最新月份；
- 与PBOC官方发布做日期/数值核验；
- AKShare/上游陈旧时不得继续把旧值当最新值。

### Macro 总结

Macro V1 的核心新增指标大部分可以 Native，数据可行性风险最低。

第一批 Native Provider 优先：

1. FRED；
2. U.S. Treasury；
3. New York Fed；
4. ECB；
5. BOJ；
6. Bank of England；
7. Polymarket official public APIs；
8. China M2 使用 AKShare + 官方核验策略。

---

# 4. Commodity 初步审计

| 数据/模块 | 初步状态 | Native 来源 | Trading Tools / 参考入口 | 维护判断 |
|---|---|---|---|---|
| EIA crude / Cushing / gasoline / distillate inventories | `NATIVE_READY` | EIA API v2（免费 key） | EIA 原站可作辅助 | 低 |
| CFTC Gold / Silver / Copper / WTI / NatGas positioning | `NATIVE_READY` | CFTC Public Reporting Environment API | Trading Tools 已有 CME COT 页面 | 低 |
| Gold ETF monthly regional/fund flow | `NATIVE_CANDIDATE → 高概率Native` | World Gold Council monthly XLSX | WGC Gold ETF 原页 | 中低，月频下载路径清晰 |
| Gold ETF weekly web flow | `NATIVE_CANDIDATE` | WGC weekly website / existing page data chain需 live validate | WGC Gold ETF 原页 | 中，部分页面可能涉及登录/网页接口 |
| SPDR holdings / daily flow | `NATIVE_CANDIDATE → 高概率Native` | SPDR official Historical Archive XLSX + current fund disclosures | SPDR GLD 原页 | 中低 |
| CME Gold / Silver / Copper warehouse stocks | `NATIVE_CANDIDATE` | CME Warehouse & Depository Stocks reports | CME Registrar Reports | 中，需验证文件地址稳定性 |
| LME monthly copper warehouse stock | `NATIVE_CANDIDATE` | LME Stocks Summary monthly Excel | LME Stocks Summary | 中 |
| LME daily two-day delayed stock breakdown | `OPEN / EXTERNAL_LINK优先` | LME Stock Breakdown XLS；官方页面提示登录/注册访问全部报告 | LME Warehouse Reports | 中高，不为日频库存维持登录自动化 |
| LME historical price / full prompt curve | `EXTERNAL_LINK` | V1 不强行自建 | LME Copper；Trading Tools 中 SMM / 奇货可查等 | 高，官方历史/实时价格存在注册/授权边界 |
| WTI / Brent current futures curve | `OPEN → EXTERNAL_LINK优先` | 继续找低维护 current chain；无则不自建 | Trading Tools 中 1qh跨期价差、奇货可查等入口 | 中高 |
| COMEX-LME / SHFE-LME copper structure | `OPEN / EXTERNAL_LINK优先` | 只有在 LME leg 可稳定自动化时 Native | Trading Tools SMM进口盈亏 / 奇货可查 | 高 |
| 国内期货跨期/库存/仓单 | `NATIVE_CANDIDATE` | AKShare + SHFE/INE等 upstream | Trading Tools 奇货可查 / 1qh | 中 |
| GVZ | `NATIVE_READY` | Cboe official historical volatility index data | Cboe index page | 低 |
| OVX | `NATIVE_READY` | Cboe official historical volatility index data | Cboe index page | 低 |
| CVOL / 高级金属期权分析 | `EXTERNAL_LINK` | V1 不必复制完整模块 | Trading Tools 已有 CME CVOL / option volume | 低 |

### Commodity 结论

商品页采用混合模式：

- EIA库存、CFTC、GVZ/OVX、核心黄金ETF/SPDR数据优先 Native；
- LME月度库存值得 Native 验证；
- LME日频完整库存、历史价格、复杂期限结构、进口盈亏等高维护数据优先使用 Trading Tools 精确入口；
- WTI/Brent current futures curve 在没有低维护免费 current chain 前不强行实现。

---

# 5. Crypto 初步审计

| 数据/模块 | 初步状态 | Native 来源 | Trading Tools / 参考入口 | 维护判断 |
|---|---|---|---|---|
| BTC / ETH spot | `NATIVE_READY` | Binance / Coinbase等官方 public API | TradingView现有大图 | 低 |
| Binance Funding | `NATIVE_READY` | Binance `fundingRate` / mark price APIs | Trading Tools 已有 Coinglass Funding Rate | 低 |
| Binance OI | `NATIVE_READY` | Binance current OI + `openInterestHist` | Trading Tools 已有 Coinglass OI | 低 |
| Bybit Funding / OI | `NATIVE_READY` | Bybit V5 `market/funding/history` + `market/open-interest` | Coinglass作参考 | 低 |
| OKX Funding / OI | `NATIVE_READY` | OKX public funding history + open interest APIs | Coinglass作参考 | 低 |
| Deribit Funding / OI | `NATIVE_READY` | Deribit public market data | Trading Tools Deribit / Greeks.live | 低 |
| BTC DVOL | `NATIVE_READY` | Deribit `get_volatility_index_data` | Deribit statistics | 低 |
| BTC/ETH options snapshot / mark IV | `NATIVE_READY` | Deribit option book summary / instruments | Trading Tools Deribit / Greeks.live | 中 |
| IV Term Structure / 25D Skew | `NATIVE_CANDIDATE` | Deribit option chain + local interpolation / calculation | Greeks.live / Deribit statistics | 中高；若维护成本过高可转外链 |
| Stablecoin total / USDT / USDC supply | `NATIVE_READY` | DefiLlama stablecoin endpoints | Trading Tools 可保留专业稳定币站点 | 低 |
| BTC ETF Daily Flow | `NATIVE_CANDIDATE → 高概率Native` | Farside公开完整 daily flow 表；持续自动更新 | Trading Tools Coinglass / SoSoValue 可作参考 | 中低，需确认rights_scope与parser稳定性 |
| ETH ETF Daily Flow | `NATIVE_CANDIDATE → 高概率Native` | Farside公开 daily flow 表；持续自动更新 | Trading Tools相关ETF入口 | 中低，需确认rights_scope与parser稳定性 |
| Bitcoin Treasuries holdings | `EXTERNAL_LINK优先 / Native仍OPEN` | 当前未确认正式公共 API；网页数据丰富但名单维护成本高 | BitcoinTreasuries专业页面 | 高 |
| MVRV / Realized Cap | `NATIVE_CANDIDATE` | Coin Metrics metric IDs明确；Community API entitlement需实际请求测试 | Checkonchain / Glassnode | 中 |
| NUPL / SOPR | `NATIVE_CANDIDATE` | Coin Metrics方法学/metric IDs明确；Community entitlement待测 | Checkonchain / Glassnode | 中 |
| Exchange Balance / Netflow | `EXTERNAL_LINK优先` | 不自建 exchange entity labels | Trading Tools CryptoQuant / Glassnode / Checkonchain / Arkham | 高 |
| LTH / STH Supply / Cost Basis | `EXTERNAL_LINK优先` | 除非找到稳定免费统一方法源 | Checkonchain / Glassnode | 高 |
| Liquidation Heatmap | `EXTERNAL_LINK` | 不自建全市场 liquidation map | Trading Tools 已有 Coinglass Liquidation HeatMap | 很高，外链更合理 |
| 全市场 Funding / OI | `NATIVE_READY（第一版3 Venue） + EXTERNAL_LINK` | Binance + Bybit + OKX；后续可增加Deribit | Coinglass Funding / OI | 中 |
| BTC期限结构专业图 | `NATIVE_CANDIDATE / EXTERNAL_LINK` | Deribit/CME等可构建简版；复杂版不强求 | Trading Tools 已有 Checkonchain BTC期限结构 | 中高 |
| Crypto complex analytics / whales | `EXTERNAL_LINK` | 不建设地址标签系统 | CryptoQuant / Arkham / BGeometrics 等 | 高 |

### Coin Metrics rights_scope 特别说明

Coin Metrics Community API：

- 无需 API key；
- 官方文档明确为 Community free tier；
- 官方文档同时明确 Community 数据为 **non-commercial use** 的 Creative Commons 数据。

因此在 Phase F 中：

- 技术可获取性与指标 entitlement 可以继续验证；
- `rights_scope` 必须明确标记；
- 若未来使用场景超出允许范围，不得因为“接口免费”就默认可以继续 Native 分发；
- 对受限指标可直接回退为 Trading Tools 中的 Checkonchain / Glassnode 等 External Link。

### Crypto 结论

Crypto V1 Native 可行性比最初预估更好。

第一版多 Venue 聚合建议：

```text
Binance + Bybit + OKX
```

三者均存在公开 Funding / OI 数据接口；Deribit更适合作为期权/DVOL核心和补充 derivatives venue。

因此：

- Funding：先归一 funding interval / timestamp，再按 OI 加权；
- OI：根据 linear/inverse 合约单位统一为 USD notional；
- Venue 模式可切 Binance / Bybit / OKX；
- Deribit按指标性质加入；
- Coinglass继续作为全市场专业参考入口，而不是生产主源。

真正应主动放弃自建的主要仍是：

- entity-labelled exchange flows；
- LTH/STH 高级口径（免费稳定源不足时）；
- liquidation heatmap；
- whale / wallet intelligence；
- 专业完整 options analytics 页面。

---

## 6. 已核验的核心公开 API / 数据入口

### Macro

- FRED API：`https://api.stlouisfed.org/fred/`
- U.S. Treasury daily interest rate XML：`https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml`
- New York Fed reference rates / Markets Data APIs：`https://www.newyorkfed.org/markets/reference-rates`
- ECB SDMX API：`https://data-api.ecb.europa.eu/service/`
- BOJ Time-Series API：`https://www.stat-search.boj.or.jp/api/v1/`
- Bank of England automatic CSV database download：`https://www.bankofengland.co.uk/boeapps/database/`
- Polymarket CLOB price history：`https://clob.polymarket.com/prices-history`

### Commodity

- EIA API v2：`https://api.eia.gov/v2/`
- CFTC Public Reporting Environment：`https://publicreporting.cftc.gov/`
- World Gold Council Gold ETF data：`https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows`
- SPDR GLD official Historical Archive：`https://www.spdrgoldshares.com/usa/gld/`
- CME Registrar / warehouse reports：`https://www.cmegroup.com/clearing/operations-and-deliveries/registrar-reports.html`
- LME warehouse reports：`https://www.lme.com/Market-data/Reports-and-data/Warehouse-and-stocks-reports`
- Cboe volatility historical data：`https://www.cboe.com/tradable_products/vix/vix_historical_data`

### Crypto

- Binance Developer Docs：`https://developers.binance.com/docs/derivatives/`
- Bybit V5 Market API docs：`https://bybit-exchange.github.io/docs/v5/market/`
- OKX API v5 docs：`https://www.okx.com/docs-v5/`
- Deribit API docs：`https://docs.deribit.com/`
- DefiLlama stablecoins API host：`https://stablecoins.llama.fi/`
- Coin Metrics Community API：`https://community-api.coinmetrics.io/v4/`
- Farside BTC ETF Flow：`https://farside.co.uk/btc/`
- Farside ETH ETF Flow：`https://farside.co.uk/eth/`
- Bitcoin Treasuries：`https://bitcointreasuries.net/`

---

## 7. Trading Tools 已确认可直接复用的高价值 External Link 候选

### Macro

- CME FedWatch；
- MacroMicro各类宏观交叉图；
- TradingEconomics / 金十 / 奇货可查宏观总览。

### Commodity

- CME CVOL / options metrics；
- 奇货可查国内商品数据；
- 1qh跨期价差；
- SMM有色金属进口盈亏；
- LME官方Copper / warehouse pages。

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

这些链接当前只读，不修改 Trading Tools 本体。

---

## 8. 当前剩余高价值 OPEN 项

下一轮不扩产品范围，只继续 live validation：

1. China M2：AKShare当前最新月份与PBOC官方值一致性；
2. WGC weekly flow：现有网页数据接口是否无需会话并适合长期自动化；
3. SPDR Historical Archive XLSX 的实际下载URL与schema稳定性；
4. CME warehouse report文件地址与历史下载稳定性；
5. LME monthly Stocks Summary 是否可无登录稳定自动下载；
6. WTI/Brent current contract chain是否存在维护成本合理的免费Native方案；
7. Farside BTC/ETH ETF Flow 的rights_scope与长期parser稳定性；
8. Coin Metrics Community 对 MVRV/NUPL/SOPR/Realized Cap 的实际免费 entitlement；
9. Bitcoin Treasuries 是否存在正式/稳定数据接口；若无则固定 `EXTERNAL_LINK`；
10. Binance / Bybit / OKX Funding interval、OI单位、linear/inverse contract mapping的最终归一化公式；
11. Trading Tools 中最终被选为按钮的精确URL可达性、登录要求与迁移风险。

本文件是 Phase F 审计，不代表对应业务 Phase 已经开始实施。
