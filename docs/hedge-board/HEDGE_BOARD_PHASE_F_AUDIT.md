# 对冲基金看板｜Phase F 数据与参考入口审计

> 状态：Initial Audit v0.2 / Engineering NOT STARTED  
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

### Macro 结论

Macro V1 的核心新增指标大部分可以 Native，数据可行性风险最低。

第一批 Native Provider 可优先固定：

1. FRED；
2. U.S. Treasury；
3. New York Fed；
4. Polymarket official public APIs；
5. 各地区 Global M2 官方源 / AKShare 适用封装。

---

# 4. Commodity 初步审计

| 数据/模块 | 初步状态 | Native 来源 | Trading Tools / 参考入口 | 维护判断 |
|---|---|---|---|---|
| EIA crude / Cushing / gasoline / distillate inventories | `NATIVE_READY` | EIA API v2（免费 key） | EIA 原站可作辅助 | 低 |
| CFTC Gold / Silver / Copper / WTI / NatGas positioning | `NATIVE_READY` | CFTC Public Reporting Environment API | Trading Tools 已有 CME COT 页面 | 低 |
| Gold ETF weekly/monthly regional flow | `NATIVE_CANDIDATE` | World Gold Council weekly web data + monthly XLSX；现有 public endpoint 需 live validate | WGC Gold ETF 原页 | 中 |
| SPDR holdings / daily flow | `NATIVE_CANDIDATE` | SPDR historical archive / fund disclosure | SPDR 原页 | 中低 |
| CME Gold / Silver / Copper warehouse stocks | `NATIVE_CANDIDATE` | CME Warehouse & Depository Stocks reports | CME Registrar Reports | 中，需验证文件地址稳定性 |
| LME copper warehouse stocks | `NATIVE_CANDIDATE` | LME public delayed stock reports / Excel；官方说明 daily stock breakdown 为两日延迟 | LME Stocks Summary / Warehouse reports | 中，需验证 Actions 无登录取文件能力 |
| LME historical price / full prompt curve | `EXTERNAL_LINK` | V1 不强行自建 | LME Copper；Trading Tools 中 SMM / 奇货可查等 | 高，官方历史/实时价格存在注册/授权边界 |
| WTI / Brent current futures curve | `OPEN → EXTERNAL_LINK优先` | 继续找低维护 current chain；无则不自建 | Trading Tools 中 1qh跨期价差、奇货可查等入口 | 中高 |
| COMEX-LME / SHFE-LME copper structure | `OPEN` | 只有在 LME leg 可稳定自动化时 Native | Trading Tools SMM进口盈亏 / 奇货可查 | 高 |
| 国内期货跨期/库存/仓单 | `NATIVE_CANDIDATE` | AKShare + SHFE/INE等 upstream | Trading Tools 奇货可查 / 1qh | 中 |
| GVZ / OVX | `NATIVE_CANDIDATE` | Cboe historical index data | Cboe/CME相关页面 | 低中 |
| CVOL / 高级金属期权分析 | `EXTERNAL_LINK` | V1 不必复制完整模块 | Trading Tools 已有 CME CVOL / option volume | 低 |

### Commodity 结论

商品页采用混合模式：

- EIA库存、CFTC、核心黄金资金流等高价值且好维护数据 Native；
- LME完整历史价格、复杂期限结构、进口盈亏等高维护数据优先使用 Trading Tools 精确入口；
- LME延迟库存本身存在公开报表，值得继续验证 Native，而不是直接放弃。

---

# 5. Crypto 初步审计

| 数据/模块 | 初步状态 | Native 来源 | Trading Tools / 参考入口 | 维护判断 |
|---|---|---|---|---|
| BTC / ETH spot | `NATIVE_READY` | Binance / Coinbase等官方 public API | TradingView现有大图 | 低 |
| Binance Funding | `NATIVE_READY` | Binance `fundingRate` / mark price APIs | Trading Tools 已有 Coinglass Funding Rate | 低 |
| Binance OI | `NATIVE_READY` | Binance current OI + `openInterestHist` | Trading Tools 已有 Coinglass OI | 低 |
| Bybit Funding / OI | `NATIVE_READY` | Bybit V5 `market/funding/history` + `market/open-interest` | Coinglass作参考 | 低 |
| OKX Funding / OI | `NATIVE_READY` | OKX public market funding history + open interest APIs | Coinglass作参考 | 低 |
| Deribit Funding / OI | `NATIVE_READY` | Deribit public market data | Trading Tools Deribit / Greeks.live | 低 |
| BTC DVOL | `NATIVE_READY` | Deribit `get_volatility_index_data` | Deribit statistics | 低 |
| BTC/ETH options snapshot / mark IV | `NATIVE_READY` | Deribit option book summary / instruments | Trading Tools Deribit / Greeks.live | 中 |
| IV Term Structure / 25D Skew | `NATIVE_CANDIDATE` | Deribit option chain + local interpolation / calculation | Greeks.live / Deribit statistics | 中高；若维护成本过高可转外链 |
| Stablecoin total / USDT / USDC supply | `NATIVE_READY` | DefiLlama `/stablecoins`、`/stablecoincharts/all`、单资产历史 endpoints | Trading Tools 可保留专业稳定币站点 | 低 |
| BTC ETF Daily Flow | `NATIVE_CANDIDATE → 高概率Native` | Farside公开完整 daily flow 表；需验证稳定解析/使用边界 | Trading Tools Coinglass / SoSoValue 可作参考 | 中低 |
| ETH ETF Daily Flow | `NATIVE_CANDIDATE → 高概率Native` | Farside公开 daily flow 表且持续更新 | Trading Tools相关ETF入口 | 中低 |
| Bitcoin Treasuries holdings | `EXTERNAL_LINK优先 / Native仍OPEN` | 当前未确认正式公共 API；网页数据丰富但名单维护成本高 | BitcoinTreasuries专业页面 | 高 |
| MVRV / Realized Cap | `NATIVE_CANDIDATE` | Coin Metrics metric IDs明确，Community API是否开放需实际 entitlement test | Checkonchain / Glassnode | 中 |
| NUPL / SOPR | `NATIVE_CANDIDATE` | Coin Metrics有明确方法学/metric family；Community entitlement待测 | Checkonchain / Glassnode | 中 |
| Exchange Balance / Netflow | `EXTERNAL_LINK优先` | 不自建 exchange entity labels | Trading Tools CryptoQuant / Glassnode / Checkonchain / Arkham | 高 |
| LTH / STH Supply / Cost Basis | `EXTERNAL_LINK优先` | 除非找到稳定免费统一方法源 | Checkonchain / Glassnode | 高 |
| Liquidation Heatmap | `EXTERNAL_LINK` | 不自建全市场 liquidation map | Trading Tools 已有 Coinglass Liquidation HeatMap | 很高，外链更合理 |
| 全市场 Funding / OI | `NATIVE_READY（第一版3 Venue） + EXTERNAL_LINK` | Binance + Bybit + OKX；后续可增加Deribit | Coinglass Funding / OI | 中 |
| BTC期限结构专业图 | `NATIVE_CANDIDATE / EXTERNAL_LINK` | Deribit/CME等可构建简版；复杂版不强求 | Trading Tools 已有 Checkonchain BTC期限结构 | 中高 |
| Crypto complex analytics / whales | `EXTERNAL_LINK` | 不建设地址标签系统 | CryptoQuant / Arkham / BGeometrics 等 | 高 |

### Crypto 结论

Crypto V1 Native 可行性比最初预估更好。

第一版多 Venue 聚合建议直接从：

```text
Binance + Bybit + OKX
```

开始，原因是三者均存在公开 Funding / OI 数据接口，足够代表主要永续市场；Deribit 更适合作为期权/DVOL核心和补充 derivatives venue。

因此：

- Funding：三 Venue 统一到同一时间窗口后做 OI-weighted aggregate；
- OI：先换算统一 USD notional 再求和；
- Venue 模式可切 Binance / Bybit / OKX，Deribit视指标性质加入；
- Coinglass继续作为全市场参考入口，而不是生产主源。

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
- Polymarket CLOB price history：`https://clob.polymarket.com/prices-history`

### Commodity

- EIA API v2：`https://api.eia.gov/v2/`
- CFTC Public Reporting Environment：`https://publicreporting.cftc.gov/`
- World Gold Council Gold ETF data：`https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows`
- CME Registrar / warehouse reports：`https://www.cmegroup.com/clearing/operations-and-deliveries/registrar-reports.html`
- LME warehouse reports：`https://www.lme.com/Market-data/Reports-and-data/Warehouse-and-stocks-reports`

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

## 8. 下一轮 Phase F 审计重点【OPEN】

下一轮不扩产品范围，只继续做 live validation：

1. Global M2 五地区官方源/AKShare实际请求；
2. WGC/SPDR 当前自动化接口是否无需会话即可长期运行；
3. CME warehouse report文件地址与历史下载稳定性；
4. LME公开延迟库存Excel能否在GitHub Actions无会话稳定下载；
5. WTI/Brent current contract chain是否存在维护成本合理的免费Native方案；
6. Coin Metrics Community 对 MVRV/NUPL/SOPR/Realized Cap 的实际免费 entitlement；
7. Farside BTC/ETH ETF Flow 是否允许长期稳定自动解析及rights_scope；
8. Bitcoin Treasuries 是否存在正式/稳定数据接口；若无则固定 `EXTERNAL_LINK`；
9. Binance / Bybit / OKX 的 Funding interval、OI单位、linear/inverse contract mapping归一化；
10. Trading Tools 中最终被选为按钮的精确URL可达性、登录要求和页面迁移风险。

本文件是 Phase F 审计，不代表对应业务 Phase 已经开始实施。
