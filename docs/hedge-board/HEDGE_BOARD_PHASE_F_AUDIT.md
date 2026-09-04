# 对冲基金看板｜Phase F 数据与参考入口审计

> 状态：Feasibility Frozen v1.0 / Engineering NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 可行性原则：`docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`  
> 实施计划：`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`

---

## 1. Phase F 结论【冻结】

Phase F 的目标不是把所有第三方数据都抓进本地，而是给 Macro / Commodity / Crypto V1 的每个重点模块确定长期可维护的交付方式。

统一判定：

- `NATIVE_READY`：技术、维护、使用边界已有清晰低风险路径；
- `NATIVE_CANDIDATE`：技术可行，但实施时仍需 live request / rights / schema 检查；
- `EXTERNAL_LINK`：不值得或不适合自建，直接跳转成熟原站；
- `OFFICIAL_EMBED`：官方 Widget / Embed 明显优于自建；
- `OPEN`：仍需研究；
- `NOT_CONFIGURED`：既无合理 Native 链，也无合适参考入口。

核心产品原则：

> **好落地的自己落地；不好落地的直接给参考网站按钮。**

Phase F v1.0 冻结后，不再因为“网页上能看到”而继续逆向第三方网站。

---

## 2. Trading Tools 角色【冻结】

`/hedge-board/trading-tools/*` 继续保持 Deferred：

- 不开发；
- 不改 UI；
- 不处理元数据；
- 不调整现有收藏与分类。

但 Phase F 与后续业务页允许**只读** Trading Tools 中已经整理好的 `name / url / description / domain / tags`，作为 External Reference Button 的候选库。

不建设第二套 Reference Links 数据库。

Macro / Commodity / Crypto V1 完善后，子页过去整块读取 Trading Tools 的“本页工具”模块不再需要；最终由 Native 内容 + 少量精准 External Link 取代。当前不删除，待对应 V1 完成并线下验收后处理。

---

## 3. Rights Gate【冻结】

> **免费访问 / public API / 可下载，不等于可以直接复制进组织内部或公开生产看板。**

必须区分：

- automated extraction；
- internal organizational use；
- redistribution / public display；
- derived-data use；
- attribution；
- third-party copyright；
- permission requirement。

商业数据源对组织、专业投资机构、商业展示存在明确限制时，V1 默认 `EXTERNAL_LINK`；只有许可清晰或找到权利更清晰的 Source of Record 才 Native。

---

# 4. Macro Feasibility Baseline【冻结】

## 4.1 Source-of-Record Native

| 指标 | 状态 | 首选 Source |
|---|---|---|
| CPI / Core CPI | `NATIVE_READY` | BLS Public Data API |
| PPI | `NATIVE_READY` | BLS Public Data API |
| Unemployment / labor | `NATIVE_READY` | BLS Public Data API |
| Real GDP | `NATIVE_READY` | BEA API / NIPA |
| PCE / Core PCE | `NATIVE_READY` | BEA API / NIPA |
| Industrial Production | `NATIVE_READY` | Federal Reserve G.17 |
| US M2 | `NATIVE_READY` | Federal Reserve H.6 |
| CFNAI / CFNAIMA3 | `NATIVE_READY` | Chicago Fed |
| Initial Claims / 4W MA | `NATIVE_READY` | DOL ETA |
| UST 3M / 2Y / 10Y / 30Y | `NATIVE_READY` | U.S. Treasury |
| 5Y / 10Y real yield | `NATIVE_READY` | U.S. Treasury real curve |
| 5Y / 10Y Breakeven | `NATIVE_READY` | nominal - real，本地计算 |
| 5Y5Y Forward Inflation | `NATIVE_READY` | Treasury 5Y/10Y nominal+real，本地计算 |
| SOFR / EFFR | `NATIVE_READY` | New York Fed |
| Fed Target / IORB / ON RRP Award | `NATIVE_READY` | Fed / NY Fed |

FRED 可用于便利分发、核验和 fallback，但 Source-of-Record 能直接使用时优先官方源。

## 4.2 Global M2

固定公式仍按 `MACRO_V1_SPEC.md`：

```text
globalM2 =
  cnm2 * cnyusd
+ usm2
+ eum2 * eurusd
+ jpm2 * jpyusd
+ gbm2 * gbpusd
```

| 组成 | 状态 | Source |
|---|---|---|
| US M2 | `NATIVE_READY` | Federal Reserve H.6 |
| Euro Area M2 | `NATIVE_READY` | ECB SDMX |
| Japan M2 | `NATIVE_READY` | BOJ API |
| UK M2 | `NATIVE_READY` | BoE IADB |
| China M2 | `NATIVE_READY_WITH_VALIDATION` | AKShare adapter + PBOC official release validation |
| FX | `NATIVE_READY` | ECB reference FX |

### China M2 规则【冻结】

AKShare `macro_china_money_supply` / 同类货币供应接口只作为接入适配层；AKShare 文档明确其上游属于东方财富等公开分发层，不视为 PBOC Source of Record。

发布规则：

```text
AKShare fetch
→ normalize
→ latest month/value
→ 与 PBOC 最新金融统计发布核验
→ 一致：publish
→ 不一致 / 日期落后：保留 LKG + degraded/stale
```

2026-07 PBOC 核验基准：M2 余额 355.51 万亿元，同比增长 7.7%，发布于 2026-08-14。

## 4.3 Risk Appetite

| 指标 | 状态 | 产品处理 |
|---|---|---|
| US High Yield OAS | `EXTERNAL_LINK` | ICE BofA / FRED 页面 |
| HYG / LQD Ratio | `OFFICIAL_EMBED` | 现有 TradingView expression |

不为这两项额外建设 ETF / ICE 历史数据库。

## 4.4 Market Expectations

### Polymarket

技术 API 完整，但专业 / capital markets entities 的数据使用涉及单独商业数据安排。

因此：

```text
Polymarket Market Expectations
→ EXTERNAL_LINK / permission_required
```

原产品需求不删除；未来如取得许可，再恢复 whitelist + historical probability Native 方案。

### CME FedWatch

`EXTERNAL_LINK`，直接使用 Trading Tools 中精确入口。

### Macro 结论

Macro V1 的核心 Source-of-Record 数据最稳定，后续最适合作为第一个实际业务 V1 开发对象。

---

# 5. Commodity Feasibility Baseline【冻结】

## 5.1 Native

| 数据 | 状态 | Source |
|---|---|---|
| EIA crude / Cushing / gasoline / distillate | `NATIVE_READY` | EIA API v2 |
| CFTC Gold / Silver / Copper / WTI / NatGas | `NATIVE_READY` | CFTC PRE API |

## 5.2 Central Bank Gold

IMF International Liquidity (`IL`) dataset 确认包含官方黄金储备相关统计概念；技术上有 IMF Data API / SDMX 入口。

但 IMF API portal 当前需要账号登录，且 IMF 条款对潜在 commercial reuse 要求额外联系确认。

因此 V1 决策：

```text
Central Bank Gold
→ EXTERNAL_LINK / permission_required
```

保留 WGC / IMF 等原站作为参考入口；不在 V1 为此继续投入复杂 API / rights 工作。

如未来取得 IMF / 数据权利确认，可重新评估 Native。

## 5.3 Commercial / Licensed Data

| 数据/模块 | 状态 | 原因 |
|---|---|---|
| WGC Global Gold ETF flows | `EXTERNAL_LINK` | 使用/复制/分发边界较严格 |
| SPDR GLD holdings / daily flow | `EXTERNAL_LINK` | archive 数据再利用边界受限 |
| CME Gold/Silver/Copper warehouse stocks | `EXTERNAL_LINK` | CME市场数据许可边界 |
| WTI futures curve | `EXTERNAL_LINK` | CME市场数据许可边界 |
| Brent futures curve | `EXTERNAL_LINK` | ICE market-data licensing |
| LME stocks / prices / prompt curve | `EXTERNAL_LINK` | LME数据许可与自动化限制 |
| COMEX-LME / SHFE-LME | `EXTERNAL_LINK` | 关键 leg 使用权受限 |
| CVOL | `EXTERNAL_LINK` | CME专业市场数据 |

## 5.4 GVZ / OVX

Cboe 指数存在独立 licensing 体系。

- GVZ：保留当前 TradingView / 现有展示入口；
- OVX：`OFFICIAL_EMBED / EXTERNAL_LINK`；
- 不建设自有 Cboe index history 数据库。

## 5.5 Commodity 结论

```text
EIA / CFTC
→ NATIVE

WGC / SPDR / CME / ICE / LME / Cboe index / complex spreads
→ OFFICIAL_EMBED or EXTERNAL_LINK
```

Commodity V1 应接受混合模式，不再追求每个图都由本地数据库维护。

---

# 6. Crypto Feasibility Baseline【冻结】

## 6.1 Binance Core Market Data【NATIVE_READY】

Binance 官方开发者文档明确支持：

- real-time / historical market data；
- internal services；
- dashboards / analytics / reporting systems；
- institutional workflows。

2026-08 Phase F smoke test 已实际验证：

### BTCUSDT

- Funding history：成功返回；
- 1H Open Interest Statistics：成功返回；
- Basis：成功返回；
- OI 响应直接包含 `sumOpenInterestValue`，可作为统一 USD notional 基础；
- Basis 响应包含 `indexPrice / futuresPrice / basis / basisRate / annualizedBasisRate` 等结构化字段。

### ETHUSDT

- Funding history：成功返回。

因此 V1 第一 Native Venue 固定为 Binance。

### Binance 数据粒度规则

官方历史端点存在窗口限制，例如 Basis / OI statistics 只提供近约 30 天。

因此 `platform-data` 必须从启用后持续增量保存自己的采样历史：

```text
Binance public API
→ periodic fetch
→ canonical snapshot/history
→ GitHub partitioned history
```

不能等几年后再依赖 Binance API 回补完整高频历史。

## 6.2 Bybit【EXTERNAL_LINK / permission_required】

Bybit V5 技术接口本身完整：

- Funding Rate History；
- Open Interest；
- 5min / 15min / 30min / 1h / 4h / 1d OI；
- linear / inverse；
- OI 单位会随合约类型不同。

但 Bybit API Terms 明确限制：

- repackage / resell Service Data；
- commercially exploit APIs；
- API 使用还受各具体文档额外条件约束。

对于当前组织内部投资研究 dashboard，V1 不再为第二 Venue 做许可边界投入。

决策：

```text
Bybit
→ EXTERNAL_LINK
```

未来如取得适用许可，再加入 Native Aggregate。

## 6.3 OKX / Deribit

- OKX：机构 / commercial market-data 用途需额外许可 → `EXTERNAL_LINK`；
- Deribit：非个人 market / derived data 使用需额外批准 → `EXTERNAL_LINK`。

Deribit DVOL / options 保留 TradingView + Deribit / Greeks.live 精准入口。

## 6.4 Funding / OI / Basis 最终 V1 方案【冻结】

```text
Native Venue
→ Binance

Multi-Venue Aggregate
→ Coinglass External Link

Additional Venue
→ permission / rights cleared 后再加入
```

产品层仍允许未来 Aggregate / Venue 切换，但 V1 不为了满足“多 Venue”而复制受限数据。

## 6.5 Stablecoin

DefiLlama API 技术好用，但其服务条款对 personal / non-commercial 与再发布存在限制。

V1：`EXTERNAL_LINK / permission_required`。

## 6.6 ETF Flow

Farside BTC / ETH ETF Flow 技术上易读取、历史表完整，但未确认适合组织内部系统化再利用的许可边界。

V1：`EXTERNAL_LINK / rights_review_required`。

## 6.7 On-chain

| 数据 | 状态 | 产品处理 |
|---|---|---|
| MVRV / NUPL / SOPR / Realized Cap | `EXTERNAL_LINK` | Coin Metrics Community 主要面向 non-commercial；Checkonchain / Glassnode |
| Exchange Balance / Netflow | `EXTERNAL_LINK` | CryptoQuant / Glassnode / Arkham |
| LTH / STH | `EXTERNAL_LINK` | Checkonchain / Glassnode |
| Liquidation Heatmap | `EXTERNAL_LINK` | Coinglass |
| Bitcoin Treasuries | `EXTERNAL_LINK` | BitcoinTreasuries |
| Whale / Wallet Intelligence | `EXTERNAL_LINK` | Arkham / CryptoQuant / BGeometrics |

### Crypto 结论

Crypto V1 的本地维护范围应主动收敛：

```text
Binance core market / derivatives data
+
existing TradingView
+
专业网站精准 External Link
```

这比复制大量“免费可见但组织使用权受限”的商业数据更稳定。

---

# 7. 高价值 External Link 候选【来自 Trading Tools / 官方原站】

## Macro

- CME FedWatch；
- Polymarket；
- HY OAS FRED / ICE；
- MacroMicro；
- TradingEconomics；
- 金十；
- 奇货可查。

## Commodity

- World Gold Council Gold ETF；
- SPDR GLD Historical Data；
- CME WTI / warehouse；
- ICE Brent；
- LME warehouse / price；
- Cboe GVZ / OVX；
- CME CVOL；
- SMM；
- 1qh；
- 奇货可查。

## Crypto

- Coinglass Funding / OI / Liquidation HeatMap；
- Checkonchain；
- Deribit Options Metrics；
- Greeks.live；
- DefiLlama Stablecoins；
- Farside BTC / ETH ETF Flow；
- Glassnode；
- CryptoQuant；
- Arkham；
- BGeometrics；
- BitcoinTreasuries。

Trading Tools 本体仍只读，不调整。

---

# 8. Phase F 实施交接清单【冻结】

Phase F v1.0 完成后，实施阶段只需继续做以下**运行级检查**，不再属于产品/数据源方案未知：

1. China M2：Phase 0/Global M2 provider 首次运行时执行 AKShare smoke test，并与 PBOC 最新发布值比较；
2. Binance：Phase 0/7 实现时把已验证 Funding / OI / Basis endpoint 固化进 provider tests；
3. External Links：实现按钮前做 HTTP 可达性 / 登录状态检查，并从 Trading Tools 只读选取精确 URL；
4. Rights：任何未来希望从 `EXTERNAL_LINK` 升级 `NATIVE` 的商业数据源，先取得适用许可，再修改 Data Source Map / Phase F 状态。

上述检查不阻塞 Phase F 冻结。

---

# 9. Phase F Gate Result

```text
Product Scope
    ↓
Data Feasibility / Rights / Maintenance Audit
    ↓
NATIVE_READY / EMBED / EXTERNAL_LINK
    ↓
Phase F FROZEN
    ↓
Phase 0 Shared Data Foundation（尚未启动）
```

**Phase F 已完成。当前仍不代表已开始工程实施。**
