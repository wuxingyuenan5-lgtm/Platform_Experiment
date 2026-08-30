# 对冲基金看板｜Phase F 数据与参考入口审计

> 状态：Audit Baseline v0.9 / Engineering NOT STARTED  
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

核心原则：**好落地的自己落地；不好落地的直接给参考网站按钮。**

---

## 2. Rights Gate【冻结】

> **免费访问 / 能下载 / public API 不等于可进入组织内部或对外生产看板。**

必须分别判断：

- automated extraction；
- internal organizational use；
- redistribution / public display；
- derived-data use；
- third-party copyright；
- attribution / permission。

商业数据源明确限制上述用途时，默认 External Link；只有取得许可或找到权利更清晰的替代 Source of Record 才 Native。

FRED、聚合站、第三方网页不会覆盖原数据所有者的版权限制。

---

# 3. Macro Audit Baseline

## 3.1 Source-of-Record Native

| 指标 | 状态 | 首选 Source |
|---|---|---|
| CPI / Core CPI | `NATIVE_READY` | BLS Public Data API |
| PPI | `NATIVE_READY` | BLS Public Data API |
| Unemployment / labor series | `NATIVE_READY` | BLS Public Data API |
| Real GDP | `NATIVE_READY` | BEA API / NIPA |
| PCE / Core PCE | `NATIVE_READY` | BEA API / NIPA |
| Industrial Production | `NATIVE_READY` | Federal Reserve G.17 |
| US M2 | `NATIVE_READY` | Federal Reserve H.6 |
| CFNAI / CFNAIMA3 | `NATIVE_READY` | Chicago Fed XLSX |
| Initial Claims / 4W MA | `NATIVE_READY` | DOL ETA Weekly Claims Spreadsheet/XML + raw downloads |

BLS 官方 API 明确面向开发者/第三方组织构建应用；BEA API 明确支持开发者搜索、展示、分析和构建新服务。

## 3.2 Rates / Inflation Expectations

| 指标 | 状态 | Source |
|---|---|---|
| UST 3M / 2Y / 10Y / 30Y | `NATIVE_READY` | U.S. Treasury |
| 5Y / 10Y real yield | `NATIVE_READY` | U.S. Treasury real curve |
| 5Y / 10Y Breakeven | `NATIVE_READY` | nominal - real，本地计算 |
| 5Y5Y Forward Inflation | `NATIVE_READY` | Treasury 5Y/10Y nominal+real，本地计算 |
| SOFR / EFFR | `NATIVE_READY` | New York Fed |
| Fed Target / IORB / ON RRP Award | `NATIVE_READY` | Fed / NY Fed |

5Y5Y 本地使用公开公式计算并版本化；FRED仅作核验。

## 3.3 Risk Appetite

| 指标 | 状态 | 产品处理 |
|---|---|---|
| US High Yield OAS | `EXTERNAL_LINK` | ICE BofA数据明确有版权/internal-use/redistribution限制；链接 FRED/ICE |
| HYG / LQD Ratio | `OFFICIAL_EMBED` | 优先利用现有 TradingView expression 展示，不建立 ETF 行情数据库 |

## 3.4 Market Expectations / Polymarket【重要修正】

Polymarket public CLOB API 技术上完整，`prices-history` 等 endpoint 也有明确 rate limits。

但 Polymarket Institutional 当前明确：

- Capital Markets Entities 若消费 Polymarket data，需要与 Polymarket 和 ICE 协商；
- 其定义明确包含 hedge funds、investment managers、proprietary trading firms、banks 等；
- 约束覆盖 API、on-chain、raw/derived/aggregated/anonymized data。

因此针对当前 Hedge Board 使用场景：

```text
Polymarket Market Expectations
→ EXTERNAL_LINK / permission_required
```

V1 产品需求不删除，但不能在未取得许可前建立公司内部概率历史数据库。

Trading Tools / 页面可提供 Polymarket 精确入口；若未来完成数据许可，再恢复原冻结的 whitelist + historical curve Native 方案。

CME FedWatch 继续 `EXTERNAL_LINK`。

## 3.5 Global M2

| 组成 | 状态 | Source |
|---|---|---|
| US M2 | `NATIVE_READY` | Federal Reserve H.6 |
| Euro Area M2 | `NATIVE_READY` | ECB SDMX |
| Japan M2 | `NATIVE_READY` | BOJ API |
| UK M2 | `NATIVE_READY` | BoE IADB |
| China M2 | `NATIVE_CANDIDATE → 高概率Native` | AKShare adapter + PBOC核验 |
| FX | `NATIVE_READY` | ECB reference FX |

China M2 官方核验基准：2026-07 M2 余额 355.51 万亿元、同比 7.7%，报告日 2026-08-14。

### Macro 结论

除 Polymarket / HY OAS 等商业数据外，Macro 绝大多数可以直接走政府/央行 Source of Record，是后续最适合优先实施的 V1。

---

# 4. Commodity Audit Baseline

## 4.1 Native

| 数据 | 状态 | Source |
|---|---|---|
| EIA crude / Cushing / gasoline / distillate | `NATIVE_READY` | EIA API v2 |
| CFTC Gold / Silver / Copper / WTI / NatGas | `NATIVE_READY` | CFTC PRE API |

## 4.2 Commercial / Licensed Data → External Link

| 数据/模块 | 状态 | 原因 |
|---|---|---|
| WGC Global Gold ETF flows | `EXTERNAL_LINK` | WGC条款限制复制、抓取、分发、衍生使用 |
| SPDR GLD holdings / daily flow | `EXTERNAL_LINK` | Archive明确禁止未经书面同意复制/再分发 |
| CME Gold/Silver/Copper warehouse stocks | `EXTERNAL_LINK` | CME条款限制系统化提取/编译等用途 |
| WTI futures curve | `EXTERNAL_LINK` | CME市场数据许可边界明确 |
| Brent futures curve | `EXTERNAL_LINK` | ICE delayed/public display/derived use需许可 |
| LME stocks / prices / prompt curve | `EXTERNAL_LINK` | LME条款限制归档、派生、分发和自动化抓取 |
| COMEX-LME / SHFE-LME | `EXTERNAL_LINK` | 多受限 data leg，专业原站更适合 |
| CVOL | `EXTERNAL_LINK` | CME专业市场数据 |

## 4.3 GVZ / OVX

Cboe index data 有独立 licensing 体系，历史数据可见不等于可自建公司数据库。

产品处理：

- GVZ：保留现有 TradingView/展示方式；
- OVX：优先 `OFFICIAL_EMBED / EXTERNAL_LINK`。

不新增自有 Cboe index history 数据库。

## 4.4 Central Bank Gold → IMF Candidate

IMF 官方 International Liquidity (`IL`) dataset 已确认存在 API 入口。

官方 Introductory Notes 精确指标：

```text
RAFAGOLDV_OZT
= Gold (Million Fine Troy Ounces)
```

IRFCL 模板也明确包含官方储备 Gold volume in fine troy ounces。

IMF published statistical data 的一般条款允许下载、提取、复制、派生、发布和分发并要求 attribution；潜在 commercial reuse 仍应按 IMF 条款联系确认。

状态：`NATIVE_CANDIDATE / rights_review_required`。

不宣称 IMF 能 100% 复刻 WGC 的全球 Top Holders / 修订口径；WGC继续外链校验。

### Commodity 结论

```text
EIA / CFTC → NATIVE
IMF central-bank gold → Candidate
WGC / SPDR / CME / ICE / LME / Cboe index → Embed / External Link
```

---

# 5. Crypto Audit Baseline

## 5.1 Binance

Binance官方开发者文档明确列出：

- real-time / historical market data；
- trading bots / automation；
- internal services；
- dashboards / analytics / reporting systems；
- institutional workflows。

因此 Binance 是当前最清晰的 Native crypto provider 候选。

状态：`NATIVE_CANDIDATE → 高概率Native`，正式实现仍记录适用 ToS / rights_scope。

## 5.2 Bybit

Bybit API Terms：

- 可开发 API Client；
- 不得 repackage / resell Service Data；
- 不得 commercially exploit APIs；
- 使用受个别 API 文档额外限制。

针对组织内部交易/研究 dashboard 的边界仍不够清晰。

状态：`NATIVE_CANDIDATE / rights_review_required`；若不确认，直接 External Link。

## 5.3 OKX

OKX 2026 API Agreement 明确：public Market Data 仍受限制，主要限个人、非商业交易/账户管理；机构/商业 market-data 用途需单独许可。

状态：`EXTERNAL_LINK / permission_required`。

## 5.4 Deribit

Deribit market data / derived data 的非个人用途需要明确批准。

状态：`EXTERNAL_LINK / permission_required`。

DVOL / options structure 用现有 TradingView + Deribit/Greeks.live 精准外链。

## 5.5 Multi-Venue Funding / OI / Basis

产品需求保留，但 V1 默认交付改为：

```text
Native Venue
→ Binance（rights最终通过后）

Multi-Venue Aggregate
→ Coinglass External Link

Additional Venue
→ Bybit only if rights cleared
```

不再为了聚合功能把 OKX / Deribit 受限数据复制进本地数据库。

## 5.6 Stablecoin

DefiLlama Terms 适用于其 Services（包括 official public APIs），默认 licence 为 personal/non-commercial，并限制未经许可的数据 republish / commercial exploitation。

因此：`EXTERNAL_LINK / permission_required`。

Stablecoin产品需求不删除，V1默认跳转 DefiLlama；若后续有权利清晰的替代源再 Native。

## 5.7 ETF Flow

Farside BTC/ETH tables 技术上容易解析，但未发现明确允许系统化再利用/组织展示的许可。

状态：`EXTERNAL_LINK / rights_review_required`。

## 5.8 On-chain

| 数据 | 状态 | 产品处理 |
|---|---|---|
| MVRV / NUPL / SOPR / Realized Cap | `EXTERNAL_LINK优先` | Coin Metrics Community仅 non-commercial；Checkonchain/Glassnode |
| Exchange Balance / Netflow | `EXTERNAL_LINK` | CryptoQuant / Glassnode / Arkham |
| LTH / STH | `EXTERNAL_LINK` | Checkonchain / Glassnode |
| Liquidation Heatmap | `EXTERNAL_LINK` | Coinglass |
| Bitcoin Treasuries | `EXTERNAL_LINK` | BitcoinTreasuries |
| Whale / Wallet Intelligence | `EXTERNAL_LINK` | Arkham / CryptoQuant / BGeometrics |

### Crypto 结论

Crypto 的低维护 V1 更适合：

```text
Binance核心数据（许可最终通过后）
+
现有 TradingView
+
Coinglass / Deribit / DefiLlama / Checkonchain / Glassnode / CryptoQuant / Farside / BitcoinTreasuries 精准外链
```

而不是复制大量“免费可见但使用权受限”的商业数据。

---

# 6. 高价值 External Link 候选

### Macro
- CME FedWatch
- Polymarket
- HY OAS FRED / ICE
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

# 7. Phase F 剩余事项【已显著收敛】

真正还值得继续验证的只剩：

1. **China M2**：真实运行环境执行 AKShare，确认最新月份与 PBOC一致；
2. **IMF Central Bank Gold**：用 IMF SDMX API 固定 `IL` dataset + `RAFAGOLDV_OZT` 的 exact query / country mapping，并按实际组织使用场景确认 commercial reuse；
3. **Binance**：记录最终适用 terms + Funding/OI/Basis smoke test；
4. **Bybit**：若用户希望 Native 第二 venue，再确认 internal organizational dashboard 是否允许；否则直接 Coinglass/Bybit External Link。

其它大部分目标已经有明确 `NATIVE_READY` / `OFFICIAL_EMBED` / `EXTERNAL_LINK` 路线。

**Phase F 已经接近可以冻结，不再建议扩展新的产品指标或新的数据网站。**
