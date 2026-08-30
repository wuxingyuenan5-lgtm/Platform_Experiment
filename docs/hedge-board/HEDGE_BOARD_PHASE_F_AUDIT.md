# 对冲基金看板｜Phase F 数据与参考入口审计

> 状态：Initial Audit v0.7 / Engineering NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 可行性原则：`docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`  
> 实施计划：`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`

---

## 1. Phase F 边界【冻结】

Trading Tools 继续 Deferred：不开发、不改 UI、不处理元数据。Phase F 只读其现有链接，作为 External Reference Button 候选。

Macro / Commodity / Crypto V1 完成后，子页此前整块读取 Trading Tools 的模块不再需要；最终由 Native 内容 + 少量精准 External Link 取代。当前不删除，待线下验收后处理。

### 判定状态

- `NATIVE_READY`：技术、维护、rights 均已具备清晰低风险路径；
- `NATIVE_CANDIDATE`：技术路线可行，但仍需 live request / rights / schema 验证；
- `EXTERNAL_LINK`：不值得或不适合自建，跳转成熟原站；
- `OFFICIAL_EMBED`：官方 Widget 明显更合适；
- `OPEN`：仍需研究；
- `NOT_CONFIGURED`：既无合理 Native 链，也无合适参考入口。

---

## 2. Rights Gate【本轮重要修正】

本轮确认：

> **免费访问 / 能下载 / 有 API，不等于可以系统化抓取并进入组织内部或对外看板。**

因此 Phase F 必须分别判断：

- access cost；
- automated extraction；
- internal organizational use；
- redistribution / public display；
- derived-data use；
- attribution；
- third-party copyright。

商业数据源明确限制抓取、复制、再分发、公开展示或派生使用时，默认 `EXTERNAL_LINK`，除非取得许可或找到权利更清晰的替代 Source of Record。

### FRED 角色修正

FRED 免费 API 并不会覆盖数据所有者版权。第三方版权序列用于非个人场景时必须遵守原数据方限制。

因此生产链原则改为：

```text
Source of Record official API/data
→ Native

FRED
→ research / cross-check / rights-allowed fallback
```

不再默认把所有宏观数据从 FRED 直接进入生产链。

---

# 3. Macro 审计 v0.7

## 3.1 Growth / Inflation / Labor

| 指标 | 状态 | 首选 Native Source | 备注 |
|---|---|---|---|
| CPI / Core CPI | `NATIVE_READY` | BLS Public Data API | 官方公开 API，适合应用开发 |
| PPI | `NATIVE_READY` | BLS Public Data API | 官方公开 API |
| UNRATE / labor series | `NATIVE_READY` | BLS Public Data API | 官方公开 API |
| Real GDP | `NATIVE_READY` | BEA API / NIPA | 官方 API，支持应用/可视化 |
| PCE / Core PCE | `NATIVE_READY` | BEA API / NIPA | 官方 API |
| Industrial Production | `NATIVE_READY` | Federal Reserve Board G.17 DDP / text files | 官方 CSV/XML/文本 |
| US M2 | `NATIVE_READY` | Federal Reserve Board H.6 DDP | 官方 monthly/weekly CSV/XML |
| CFNAI / CFNAIMA3 | `NATIVE_READY` | Chicago Fed XLSX | 官方下载中心 |
| Initial Claims 4W MA | `NATIVE_CANDIDATE → 高概率Native` | U.S. Department of Labor weekly claims | 官方每周发布和历史入口明确；实施时冻结机器可读历史链 |

### 3.2 Rates / Inflation Expectations

| 指标 | 状态 | Source | 备注 |
|---|---|---|---|
| UST 3M / 2Y / 10Y / 30Y | `NATIVE_READY` | U.S. Treasury | 官方 |
| 5Y / 10Y real yield | `NATIVE_READY` | U.S. Treasury real yield curve | 官方 |
| 5Y / 10Y Breakeven | `NATIVE_READY` | Treasury nominal - real，本地计算 | 不依赖第三方派生序列 |
| 5Y5Y Forward Inflation | `NATIVE_READY` | Treasury 5Y/10Y nominal+real，本地按公开公式计算 | 方法版本固定 |
| SOFR / EFFR | `NATIVE_READY` | New York Fed | 官方 |
| Fed Target / IORB / ON RRP Award | `NATIVE_READY` | Federal Reserve / NY Fed | 官方 |

5Y5Y 采用公开公式思想，本地基于 Treasury Source of Record 重算并保存 methodology version；FRED T5YIFR 仅作核验，不作为生产依赖。

### 3.3 Risk Appetite

| 指标 | 状态 | 结论 |
|---|---|---|
| US High Yield OAS | `EXTERNAL_LINK` | ICE BofA 数据明确有版权和 internal-use / redistribution限制；不进入自有生产链 |
| HYG / LQD Ratio | `NATIVE_CANDIDATE` | 公式简单，但 ETF price provider 的 rights_scope 需单独审计；不可直接假定 Yahoo/FRED 可再分发 |

HY OAS 产品需求保留，但交付方式改为精准外链 FRED/ICE 参考页面，不删指标。

### 3.4 Market Expectations

| 模块 | 状态 | Source |
|---|---|---|
| Polymarket whitelist probability/history | `NATIVE_READY` | Gamma + CLOB public APIs |
| CME FedWatch | `EXTERNAL_LINK` | Trading Tools 现有 CME 精确入口 |
| MacroMicro / TradingEconomics / 金十复杂图 | `EXTERNAL_LINK` | Trading Tools |

### 3.5 Global M2

| 组成 | 状态 | Source | 备注 |
|---|---|---|---|
| US M2 | `NATIVE_READY` | Federal Reserve H.6 | Source of Record |
| Euro Area M2 | `NATIVE_READY` | ECB SDMX API | 官方 |
| Japan M2 | `NATIVE_READY` | BOJ Time-Series API | 官方 |
| UK M2 | `NATIVE_READY` | Bank of England IADB | 最终 series 语义实施时复核 |
| China M2 | `NATIVE_CANDIDATE → 高概率Native` | AKShare adapter + PBOC monthly official validation | 防 stale |
| FX | `NATIVE_READY` | ECB reference FX | 月均本地计算 |

China M2 当前官方核验基准：2026-07 M2 余额 355.51 万亿元、同比 7.7%，官方报告日期 2026-08-14。实际实施必须确认 AKShare 最新一行同步到同一月份和数量级。

### Macro 总结

Macro 是三个 V1 中权利和技术风险最低的模块。生产链尽量绕过第三方聚合，直接对接 BLS / BEA / Fed / Treasury / NY Fed / Chicago Fed / ECB / BOJ / BoE / PBOC核验链。

---

# 4. Commodity 审计 v0.7

## 4.1 可明确 Native 的政府/公共统计

| 数据 | 状态 | Source |
|---|---|---|
| EIA crude / Cushing / gasoline / distillate inventories | `NATIVE_READY` | EIA API v2 |
| CFTC Gold / Silver / Copper / WTI / NatGas positioning | `NATIVE_READY` | CFTC PRE API |

## 4.2 商业数据权利修正

| 数据/模块 | v0.7 状态 | 原因 / 处理 |
|---|---|---|
| WGC Global Gold ETF weekly/monthly flows | `EXTERNAL_LINK` | WGC条款限制复制、抓取、分发、衍生使用；不建立生产 scraper |
| SPDR GLD holdings / daily flow | `EXTERNAL_LINK` | Historical Archive明确禁止未经书面同意复制/再分发 |
| CME Gold/Silver/Copper warehouse stocks | `EXTERNAL_LINK` | 虽然Excel可直连，但CME网站数据条款禁止系统化提取/编译/内部转移等未授权用途 |
| WTI current futures curve | `EXTERNAL_LINK` | CME结算网页/数据属于受许可市场数据，不以网页抓取做生产链 |
| Brent current futures curve | `EXTERNAL_LINK` | ICE delayed/public display及derived use需许可/审批 |
| LME monthly/daily warehouse stocks | `EXTERNAL_LINK` | LME条款限制归档、派生、分发及API/自动机制抓取 |
| LME historical price / prompt curve | `EXTERNAL_LINK` | 数据许可边界明确 |
| COMEX-LME / SHFE-LME complex spread | `EXTERNAL_LINK优先` | 受限 leg 太多；优先 SMM/奇货可查等专业入口 |
| GVZ / OVX | `NATIVE_CANDIDATE / rights_review_required` | Cboe指数数据有专门 licensing；技术有历史数据但不能只凭可下载判 Native |
| CVOL / advanced options | `EXTERNAL_LINK` | CME 专业页面 |

这次修正的原则是：**技术 Ready 不等于 Product Native Ready。**

## 4.3 Central Bank Gold：更干净的 Native 替代候选

WGC 央行储备/增持页面继续作为 External Link；Native 候选改为 IMF 官方统计：

- IMF International Liquidity / former IFS；
- IRFCL 等月度官方储备模板包含 monetary gold volume（fine troy ounces）；
- IMF Published Statistical Data 的复用条款明显比 WGC/SPDR 清晰，并要求正确 attribution。

状态：`NATIVE_CANDIDATE`。

限制：

- IMF 与 WGC 的覆盖和修订口径并不完全相同；
- IRFCL 属自愿报送，不能宣称 100% 复刻 WGC Top Holders；
- 优先研究更广覆盖的 International Liquidity / IFS gold series；
- WGC 继续作为外链/人工交叉验证。

## 4.4 Commodity 结论

Commodity V1 采用更克制的混合模式：

```text
EIA / CFTC / 权利清晰官方统计 → NATIVE
商业交易所 / 指数 / WGC / SPDR → EXTERNAL_LINK / rights review
央行黄金 → IMF official Native candidate + WGC external reference
```

这会显著降低长期授权和维护风险。

---

# 5. Crypto 审计 v0.7

## 5.1 Exchange / Derivatives

| 数据 | 状态 | Source |
|---|---|---|
| BTC / ETH spot | `NATIVE_CANDIDATE → 高概率Native` | Binance/Coinbase official public APIs；实施前最终复核API ToS |
| Binance Funding / OI | `NATIVE_CANDIDATE → 高概率Native` | Binance official API |
| Bybit Funding / OI | `NATIVE_CANDIDATE → 高概率Native` | Bybit V5 |
| OKX Funding / OI | `NATIVE_CANDIDATE → 高概率Native` | OKX API v5 |
| Deribit Funding / OI / DVOL / option snapshot | `NATIVE_CANDIDATE → 高概率Native` | Deribit public API |
| IV Term Structure / 25D Skew | `NATIVE_CANDIDATE` | Deribit chain + local calculation；复杂时外链 |

技术链已经明确，但 rights-aware 标准下，正式工程前还要把各交易所 API ToS 的 internal display / derived use 做一次轻量复核。

### Multi-Venue 第一版

```text
Aggregate = Binance + Bybit + OKX
Venue = Binance / Bybit / OKX
Deribit = Options/DVOL核心 + 可选derivatives补充
```

Funding 必须先统一 interval，再按 OI weighted。OI 必须按 contract type / multiplier / price 转成 USD notional 后聚合。

## 5.2 Stablecoin

DefiLlama 技术接口简单，但本轮尚未完成其数据 reuse/redistribution 条款审计。

状态由原 `NATIVE_READY` 调整为：`NATIVE_CANDIDATE / rights_review_required`。

## 5.3 ETF Flow

Farside BTC/ETH ETF daily tables：

- 公开可访问；
- 表结构清晰；
- 技术解析容易；
- 页面保留 `All rights reserved`，未发现明确允许系统化再利用/再分发的许可。

因此默认：

```text
EXTERNAL_LINK / rights_review_required
```

不再把“技术好解析”当作高概率 Native。

## 5.4 On-chain

| 数据 | 状态 | 处理 |
|---|---|---|
| MVRV / NUPL / SOPR / Realized Cap | `NATIVE_CANDIDATE` | Coin Metrics Community无key，但明确 non-commercial use；用途不匹配时外链 |
| Exchange Balance / Netflow | `EXTERNAL_LINK` | CryptoQuant / Glassnode / Arkham；不自建entity labels |
| LTH / STH Supply / Cost Basis | `EXTERNAL_LINK优先` | Checkonchain / Glassnode |
| Liquidation Heatmap | `EXTERNAL_LINK` | Coinglass |
| Whale / Wallet Intelligence | `EXTERNAL_LINK` | Arkham / CryptoQuant / BGeometrics |
| Bitcoin Treasuries | `EXTERNAL_LINK` | 专业名单维护成本高，未确认正式稳定公共API |

### Coin Metrics

已确认 metric IDs：`CapMVRVCur`、`CapRealUSD`、`NUPL`、`SOPR`。Community API 无需 key，但免费层为 non-commercial use，必须保留 `rights_scope`。

在当前工具环境尚未完成四指标逐项 Community endpoint smoke test，因此仍是 Candidate。

---

# 6. External Link 高价值候选【当前可用】

### Macro
- CME FedWatch
- MacroMicro复杂宏观交叉图
- FRED / ICE HY OAS参考页
- TradingEconomics / 金十 / 奇货可查

### Commodity
- WGC Gold ETF Holdings & Flows
- SPDR GLD Historical Data
- CME WTI Settlements / warehouse pages
- ICE Brent Futures Data
- LME warehouse / price pages
- CME CVOL / options metrics
- SMM进口盈亏
- 1qh跨期价差

### Crypto
- Coinglass Funding / OI / Liquidation HeatMap
- Checkonchain BTC期限结构 / 图表库
- Deribit Options Metrics
- Greeks.live Data Lab
- Glassnode
- CryptoQuant
- Arkham（使用当前 `https://arkm.com/`）
- BGeometrics
- Farside BTC / ETH ETF Flow
- BitcoinTreasuries

Trading Tools 本体仍只读。

---

# 7. 当前剩余真正高价值 Live Validation

Phase F 现在只剩少量值得继续压缩的问题：

1. China M2：真实运行环境调用 AKShare，核到 2026-07 与 PBOC 官方值一致；
2. Initial Claims：冻结 DOL 机器可读历史数据路径；
3. HYG/LQD：确定一个 rights_scope 清晰的价格数据源，或降级外链；
4. IMF Central Bank Gold：冻结 International Liquidity / IRFCL 的 exact API/series mapping；
5. Cboe GVZ/OVX：确认当前内部展示场景需要的具体 license；不合适即外链；
6. Binance/Bybit/OKX/Deribit：轻量复核 API ToS + 实际字段级 Funding/OI normalization smoke test；
7. DefiLlama：完成 stablecoin data rights_scope 审计；
8. Coin Metrics：实际 Community endpoint smoke test + 使用场景 rights 判断。

WGC、SPDR、CME/LME/ICE市场数据、Farside不再作为“只要技术跑通就 Native”的 OPEN 项；默认已转 External Link / rights review 路线。

本文件仍属于 Phase F 审计，不代表任何业务 Phase 已开始实施。
