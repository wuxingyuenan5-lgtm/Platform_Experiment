# 对冲基金看板｜Phase F 数据与参考入口审计

> 状态：Initial Audit v0.8 / Engineering NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 可行性原则：`docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`  
> 实施计划：`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`

---

## 1. Phase F 边界【冻结】

Trading Tools 继续 Deferred：不开发、不改 UI、不处理元数据。Phase F 只读其现有链接，作为 External Reference Button 候选。

Macro / Commodity / Crypto V1 完成后，子页此前整块读取 Trading Tools 的模块不再需要；最终由 Native 内容 + 少量精准 External Link 取代。当前不删除，待线下验收后处理。

### 判定状态

- `NATIVE_READY`：技术、维护、rights 均有清晰低风险路径；
- `NATIVE_CANDIDATE`：技术可行，但仍需 live request / rights / schema 验证；
- `EXTERNAL_LINK`：不值得或不适合自建，跳转成熟原站；
- `OFFICIAL_EMBED`：官方 Widget 明显更合适；
- `OPEN`：仍需研究；
- `NOT_CONFIGURED`：既无合理 Native 链，也无合适参考入口。

---

## 2. Rights Gate【冻结】

Phase F 当前最重要的修正：

> **免费访问 / 能下载 / 有 public API，不等于可以系统化抓取并进入组织内部或对外看板。**

必须分别判断：

- automated extraction；
- internal organizational use；
- redistribution / public display；
- derived-data use；
- third-party copyright；
- attribution / permission。

商业数据源明确限制这些用途时，默认 External Link；只有取得许可或找到权利更清晰的替代 Source of Record 才 Native。

FRED、聚合站和第三方页面不覆盖原数据所有者的版权限制。

---

# 3. Macro 审计 v0.8

## 3.1 Native Source of Record

| 指标 | 状态 | 首选 Source |
|---|---|---|
| CPI / Core CPI | `NATIVE_READY` | BLS Public Data API |
| PPI | `NATIVE_READY` | BLS Public Data API |
| Unemployment / labor series | `NATIVE_READY` | BLS Public Data API |
| Real GDP | `NATIVE_READY` | BEA API / NIPA |
| PCE / Core PCE | `NATIVE_READY` | BEA API / NIPA |
| Industrial Production | `NATIVE_READY` | Federal Reserve G.17 data files / DDP |
| US M2 | `NATIVE_READY` | Federal Reserve H.6 monthly/weekly CSV/XML |
| CFNAI / CFNAIMA3 | `NATIVE_READY` | Chicago Fed XLSX |
| Initial Claims / 4W MA | `NATIVE_READY` | DOL ETA Weekly Claims Data / Spreadsheet/XML / raw comma-delimited downloads |

### Initial Claims 新结论

DOL ETA 官方 Weekly Claims Data 页面：

- National / State 可选；
- 支持 Spreadsheet / XML；
- 数据页持续更新；
- Data Downloads 提供 raw comma-delimited files；
- ETA 539 明确为 weekly claims data。

因此不需要再依赖 FRED 作为生产主源。

## 3.2 Rates / Inflation Expectations

| 指标 | 状态 | Source |
|---|---|---|
| UST 3M / 2Y / 10Y / 30Y | `NATIVE_READY` | U.S. Treasury |
| 5Y / 10Y real yield | `NATIVE_READY` | U.S. Treasury real curve |
| 5Y / 10Y Breakeven | `NATIVE_READY` | nominal - real，本地计算 |
| 5Y5Y Forward Inflation | `NATIVE_READY` | Treasury 5Y/10Y nominal+real，本地计算 |
| SOFR / EFFR | `NATIVE_READY` | New York Fed |
| Fed Target / IORB / ON RRP Award | `NATIVE_READY` | Federal Reserve / NY Fed |

5Y5Y 使用公开公式思路本地计算；FRED T5YIFR 只作交叉核验。

## 3.3 Risk Appetite

| 指标 | 状态 | 产品处理 |
|---|---|---|
| US High Yield OAS | `EXTERNAL_LINK` | ICE BofA数据明确禁止未经许可复制/再分发；保留FRED/ICE参考入口 |
| HYG / LQD Ratio | `OFFICIAL_EMBED` | 优先用现有 TradingView 展示能力表达 `HYG/LQD`，不自己长期存储商业ETF行情 |

这样保留用户冻结的两个 Risk Appetite 指标，同时避免新增商业行情数据库依赖。

## 3.4 Market Expectations

- Polymarket whitelist probability/history：`NATIVE_CANDIDATE → 高概率Native`，正式实施前再做 API terms / usage scope 复核；
- CME FedWatch：`EXTERNAL_LINK`；
- MacroMicro / TradingEconomics / 金十等复杂图：`EXTERNAL_LINK`。

## 3.5 Global M2

| 组成 | 状态 | Source |
|---|---|---|
| US M2 | `NATIVE_READY` | Federal Reserve H.6 |
| Euro Area M2 | `NATIVE_READY` | ECB SDMX |
| Japan M2 | `NATIVE_READY` | BOJ API |
| UK M2 | `NATIVE_READY` | BoE IADB |
| China M2 | `NATIVE_CANDIDATE → 高概率Native` | AKShare adapter + PBOC核验 |
| FX | `NATIVE_READY` | ECB reference FX |

China M2 当前官方核验基准：2026-07 M2 余额 355.51 万亿元、同比 7.7%，报告日 2026-08-14。

### Macro 结论

Macro 核心数据基本可以直接走政府/央行 Source of Record，是 Phase 0 后最适合先做的业务 V1。

---

# 4. Commodity 审计 v0.8

## 4.1 明确 Native

| 数据 | 状态 | Source |
|---|---|---|
| EIA crude / Cushing / gasoline / distillate | `NATIVE_READY` | EIA API v2 |
| CFTC Gold / Silver / Copper / WTI / NatGas | `NATIVE_READY` | CFTC PRE API |

## 4.2 默认 External Link / Rights Review

| 数据/模块 | 状态 | 原因 |
|---|---|---|
| WGC Global Gold ETF flows | `EXTERNAL_LINK` | WGC条款限制复制、抓取、分发、衍生使用 |
| SPDR GLD holdings / daily flow | `EXTERNAL_LINK` | Historical Archive明确禁止未经书面同意复制/再分发 |
| CME Gold/Silver/Copper warehouse stocks | `EXTERNAL_LINK` | CME网站数据条款限制系统化提取/编译/内部转移等用途 |
| WTI futures curve | `EXTERNAL_LINK` | CME市场数据许可边界明确，不以网页/API逆向做生产链 |
| Brent futures curve | `EXTERNAL_LINK` | ICE delayed/public display/derived use需要审批或许可 |
| LME monthly/daily warehouse stocks | `EXTERNAL_LINK` | LME条款限制归档、派生、分发和自动化抓取 |
| LME prices / prompt curve | `EXTERNAL_LINK` | LME专门市场数据许可 |
| COMEX-LME / SHFE-LME | `EXTERNAL_LINK` | 多个受限数据 leg，专业原站更适合 |
| CVOL / advanced metal options | `EXTERNAL_LINK` | CME专业数据/工具 |

## 4.3 GVZ / OVX

Cboe指数数据有专门 licensing 体系，不能只因为历史 CSV 可下载就直接进入公司生产链。

产品处理：

```text
现有 GVZ → 保留 TradingView/现有展示
OVX → OFFICIAL_EMBED / Cboe External Link 优先
```

状态：`OFFICIAL_EMBED / EXTERNAL_LINK`，不建立自有长期 Cboe 指数数据库。

## 4.4 Central Bank Gold：IMF Native 候选

WGC央行黄金继续 External Link；Native 候选改为 IMF published statistical data。

官方 IMF Introductory Notes 已确认 International Liquidity 指标：

```text
RAFAGOLDV_OZT
= Gold (Million Fine Troy Ounces)
```

IRFCL 模板同样明确包含官方储备黄金 volume in fine troy ounces。

IMF统计数据条款允许下载、提取、复制、制作派生、发布和分发，并要求准确 attribution；潜在商业再利用仍应按条款请求许可。

状态：`NATIVE_CANDIDATE / rights_review_required`。

注意：IMF与WGC覆盖/修订不完全一致，不能宣称100%复刻WGC全球Top Holders。

### Commodity 结论

Commodity采用：

```text
EIA / CFTC → NATIVE
IMF central-bank gold → Native candidate
商业交易所 / WGC / SPDR / Cboe指数 → Embed / External Link
```

长期维护风险显著下降。

---

# 5. Crypto 审计 v0.8

这一轮最重要的结论是：多个交易所的 public API 虽然技术上适合做 Funding/OI，但市场数据使用条款对个人/非商业用途、再分发和分析平台有明显限制。

## 5.1 Binance

Binance官方开发者文档明确把以下场景列为 API 用途：

- market data；
- trading bots / automation；
- internal services；
- dashboards / analytics / reporting。

因此 Binance 是当前最有希望的 Native crypto venue。

状态：`NATIVE_CANDIDATE → 高概率Native`，实施前仍需记录最终 ToS / rights_scope。

## 5.2 OKX

2026 API Agreement 明确：

- public market data endpoint 仍受协议限制；
- market data 主要限个人、非商业交易/账户管理；
- 不得未经许可发布、展示、再分发或用于金融数据聚合/分析平台；
- 机构/商业大规模用途需单独数据许可。

因此：`EXTERNAL_LINK / permission_required`。

## 5.3 Deribit

Deribit API 技术很成熟，但其公开市场数据条款/历史说明明确要求非个人用途取得批准。

因此：

- DVOL / options professional metrics：优先现有 TradingView / Deribit / Greeks.live External Link；
- 不默认建立自有 Deribit market-data database。

状态：`EXTERNAL_LINK / permission_required`。

## 5.4 Bybit

Bybit API Terms 明确禁止重新包装/转售 Service Data 和商业利用 API；内部组织使用边界不如 Binance 文档清晰。

状态：`NATIVE_CANDIDATE / rights_review_required`。

## 5.5 Multi-Venue Funding / OI / Basis

产品需求仍保留，但交付方式调整为：

```text
Venue Native
→ 优先 Binance（rights通过后）

Multi-Venue Aggregate
→ Coinglass External Link 为 V1 默认
→ 只有获得 Bybit/OKX/Deribit 等足够 rights 后再升级平台内聚合
```

因此当前不为了“多交易所聚合”引入授权不清晰的数据生产链。

## 5.6 Stablecoin

DefiLlama官方 Terms：

- Services 包含 official public APIs；
- 默认许可仍为 personal / non-commercial；
- 禁止未经许可 republish data / commercial scraping or exploitation。

因此：`EXTERNAL_LINK / permission_required`。

Stablecoin V1 产品需求保留，但默认按钮跳转 DefiLlama，除非后续取得许可或找到权利更清晰的替代源。

## 5.7 ETF Flow

Farside BTC/ETH tables 虽然公开、好解析，但页面保留 All rights reserved，未发现清晰再利用授权。

状态：`EXTERNAL_LINK / rights_review_required`。

## 5.8 On-chain

| 数据 | 状态 | 产品处理 |
|---|---|---|
| MVRV / NUPL / SOPR / Realized Cap | `EXTERNAL_LINK优先` | Coin Metrics Community仅 non-commercial；Checkonchain/Glassnode可作参考 |
| Exchange Balance / Netflow | `EXTERNAL_LINK` | CryptoQuant / Glassnode / Arkham |
| LTH / STH | `EXTERNAL_LINK` | Checkonchain / Glassnode |
| Liquidation Heatmap | `EXTERNAL_LINK` | Coinglass |
| Bitcoin Treasuries | `EXTERNAL_LINK` | BitcoinTreasuries |
| Whale / Wallet Intelligence | `EXTERNAL_LINK` | Arkham / CryptoQuant / BGeometrics |

如果未来明确取得可用 license，再将个别指标从 Link 升级 Native，不影响页面产品定义。

### Crypto 结论

Crypto V1 不再追求“大量免费 public API 全部本地化”。更稳妥的 V1 是：

```text
BTC/ETH核心价格 + 少量rights清晰的Native
+
TradingView现有展示
+
Coinglass / Deribit / DefiLlama / Checkonchain / Glassnode / CryptoQuant 等精准外链
```

这与用户的低维护原则一致。

---

# 6. External Link 高价值入口

### Macro
- CME FedWatch
- HY OAS FRED / ICE reference
- MacroMicro
- TradingEconomics / 金十 / 奇货可查

### Commodity
- WGC Gold ETF
- SPDR GLD Historical Data
- CME WTI / warehouse
- ICE Brent
- LME warehouse / price
- Cboe GVZ / OVX
- CME CVOL
- SMM / 1qh / 奇货可查

### Crypto
- Coinglass Funding / OI / Liquidation HeatMap
- Checkonchain
- Deribit Options Metrics
- Greeks.live
- DefiLlama Stablecoins
- Farside BTC / ETH ETF Flow
- Glassnode
- CryptoQuant
- Arkham (`https://arkm.com/`)
- BGeometrics
- BitcoinTreasuries

Trading Tools 本体仍只读。

---

# 7. Phase F 当前剩余事项

经过技术 + rights 双重审计，剩余真正需要继续验证的已经很少：

1. China M2：真实运行环境调用 AKShare，确认 2026-07 与 PBOC一致；
2. IMF Central Bank Gold：冻结最新 IMF Data API exact dataset/query 形式，并决定是否需要商业 reuse permission；
3. Binance：最终 API/market-data ToS 记录 + Funding/OI/Basis smoke test；
4. Bybit：确认内部组织 dashboard 是否允许当前 API/Service Data 使用；不清晰则 External Link；
5. Polymarket：补一次 public API rights_scope 审计；
6. 如用户坚持平台内 Stablecoin/On-chain/Multi-Venue aggregate，再单独寻找明确允许组织使用的替代免费/授权源；否则 V1 直接走现有 External Link。

Initial Claims、美国宏观 Source of Record、商品 EIA/CFTC、复杂商业市场数据的 External Link 路线已经基本定型。

本文件仍属于 Phase F 审计，不代表任何业务 Phase 已开始实施。
