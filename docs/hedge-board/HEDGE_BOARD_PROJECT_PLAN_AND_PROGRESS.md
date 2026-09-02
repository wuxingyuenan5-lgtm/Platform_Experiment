# 对冲基金看板｜完整项目计划书与进度总表

> 状态：Project Baseline v1.1 / Phase 0 DONE / Phase 1 DONE / Macro V1 NEXT  
> 主仓库：`wuxingyuenan5-lgtm/Platform_Experiment`  
> 开发分支：`feature/hedge-board-online-optimization`  
> 数据仓库：`wuxingyuenan5-lgtm/platform-data`  
> 作用：作为 Hedge Board 当前范围、数据策略、实施路线、真实进度、风险与下一步工作的管理总览。  
> 说明：具体产品定义、数据源、rights / feasibility 与工程细节仍以对应权威子文档为准；本文负责把它们汇总成一份可直接查看的完整项目计划书。

---

## 1. 项目目标

Hedge Board V1 定位为：

> **面向日常交易与研究的跨资产扫盘、数据集中展示和盘后复盘工具。**

核心目标：

1. 将分散在 TradingView、宏观网站、交易所、数据网站和专业分析工具中的高价值信息集中到一个看板；
2. 核心、稳定、rights 清晰的数据尽量 Native 落地；
3. 不值得自建或许可复杂的专业模块，使用精准 External Reference Button 跳转原站；
4. 保留并保护现有 UI，不为了数据工程重新设计产品；
5. 逐步清理金融假数据、随机数和占位曲线；
6. 建立可追溯、可自动更新、可回滚的数据生产体系；
7. 为后续研究工作流与金融 AI 分析提供标准化数据基础。

当前阶段不建设：

- 自动投资观点；
- 自动市场状态判断；
- 自动交易建议；
- 组合暴露 / 风控决策系统；
- 自动交易；
- tick / order book / 秒级高频数据库。

---

## 2. 项目范围

### 2.1 Active V1

当前正式推进：

- Macro / 宏观；
- Commodity / 商品；
- Crypto / 加密。

### 2.2 Deferred

当前暂停新增开发：

- US Equity / 美股；
- A-Share / A股；
- Global / 全球；
- Trading Tools / 交易工具。

Deferred 不代表删除页面，只代表：

- 不新增开发；
- 不重构；
- 不顺手真实化；
- 不因公共组件修改而改变这些页面。

### 2.3 Trading Tools 特殊角色

Trading Tools 当前继续 Deferred，但可被**只读**作为参考网站目录。

规则：

- 不维护其元数据生成逻辑；
- 不改 Trading Tools UI；
- 不建立第二套 Reference Links；
- Active V1 需要外链时，优先复用其中已经整理的精确 URL；
- Active V1 完成后，子页过去整块重复展示 Trading Tools 分类的模块不再需要；该清理动作等待对应 V1 完成并线下验收后执行。

---

## 3. 最高产品与 UI 约束

### 3.1 Additive Only

除非用户明确批准，不得：

- 删除现有内容；
- 移动现有模块；
- 改变现有顺序；
- 重命名现有模块；
- 用新设计替换现有设计；
- 重构整体页面；
- 改导航；
- 因“统一 / 清理 / 去硬编码”改变视觉表现。

### 3.2 默认保护组件

除最小兼容修改外，不主动重构：

- `HedgeResearchModule.vue`
- `MarketTerminalPage.vue`
- `TerminalDetailPanel.vue`
- `HedgeBoardSubnav.vue`
- `hedgeBoard.less`
- `strategy-theme.less`

### 3.3 硬编码处理

- 视觉组件硬编码：保留；
- 页面配置硬编码：当前允许；
- 金融数据硬编码：逐步退出。

---

## 4. 最终数据交付模式

Phase F 已冻结为三种正式交付模式。

### 4.1 NATIVE

适用于：

- 免费 / 合规；
- 数据长期稳定；
- 可自动化；
- 维护成本合理；
- 历史与口径满足产品需要。

链路：

```text
Official / approved source
        ↓
platform-data
        ↓
canonical data + validation + LKG
        ↓
platform-api
        ↓
Platform Web
```

### 4.2 EXTERNAL_LINK

适用于：

- 原站已经有成熟专业模块；
- 自建数据链投入产出比低；
- rights / redistribution 复杂；
- 免费历史不足；
- 维护风险高。

链路：

```text
Trading Tools / Official site exact URL
        ↓
External Reference Button
        ↓
new browser tab
```

External Link 是正式产品能力，不是失败占位。

### 4.3 OFFICIAL_EMBED

只有官方明确支持、体验明显优于外链且不破坏现有 UI 时使用。

### 4.4 NOT_CONFIGURED

只有同时满足：

1. 无合理 Native 链；
2. 无合适 External Link / Official Embed；

才使用。

---

## 5. 数据与存储架构

### 5.1 `platform-data`

定位：

> **版本化数据生产与分发仓库。**

负责：

- Provider adapter；
- fetch；
- normalize；
- derive；
- canonical identity；
- data quality；
- stale / degraded / error；
- Last Known Good；
- history；
- GitHub Actions；
- versioned JSON / CSV / Parquet output。

### 5.2 `Platform_Experiment`

负责：

- Platform API；
- cache；
- status / stale / fallback 语义；
- 前端展示；
- External Link / Embed；
- 现有 UI 交互。

前端原则上不直接连接多个外部金融 API。

### 5.3 存储

最新消费：

```text
public/v1/<module>/manifest.json
public/v1/<module>/dashboard.json
public/v1/<module>/market-detail.json
public/v1/<module>/series/*.json
```

历史：

- 小型长历史 → CSV；
- 较大 / 多列 → Parquet；
- 按年 / 月稳定分区。

不做：

- tick；
- order book；
- 秒级长期数据库；
- 全市场分钟 raw feed；
- SQLite / DuckDB 二进制文件频繁 commit。

---

## 6. 通用数据合同

Native series 基线：

- `series_id`
- `label`
- `value / latest_value`
- `observations`
- `unit`
- `currency`
- `source`
- `upstream_source`
- `source_id`
- `source_url`
- `observation_date`
- `as_of`
- `retrieved_at`
- `frequency`
- `timezone`
- `status`
- `is_stale`
- `methodology_version`
- `quality_flags`
- `rights_scope`

统一状态：

- `ready`
- `partial`
- `degraded`
- `stale`
- `no_data`
- `not_configured`
- `error`

基本规则：

- `0` 不代表 no data；
- `[]` 不代表 Provider failure；
- stale 不伪装 fresh；
- fetch failed 不覆盖 LKG；
- fallback 必须可见；
- derived metric 保留 methodology version；
- 无 materially new data 时不制造无意义 Git commit。

---

## 7. 已完成阶段

### 7.1 Product Scope Design — DONE

已冻结：

- `MACRO_V1_SPEC.md`
- `COMMODITY_V1_SPEC.md`
- `CRYPTO_V1_SPEC.md`

### 7.2 Data Source Baselines — DONE

已建立：

- `MACRO_DATA_SOURCE_MAP.md`
- `COMMODITY_DATA_SOURCE_MAP.md`
- `CRYPTO_DATA_SOURCE_MAP.md`

### 7.3 Phase F — Data Feasibility & Rights Audit — DONE / FROZEN

已完成：

- 数据真实可获取性审计；
- API / 免费条件 / history / maintenance 审计；
- rights / redistribution gate；
- Native / External Link / Embed 路由；
- Trading Tools 只读复用原则；
- Binance Funding / OI / Basis smoke test；
- External Link 高价值入口识别。

权威结果：

`HEDGE_BOARD_PHASE_F_AUDIT.md`

### 7.4 Phase 0 — Shared Data Foundation — DONE

实际完成：

- 复用 `platform-data` 既有目录结构；
- `CanonicalSeries` 基线；
- finite timeout / transient retry；
- stale detection；
- quality validation；
- deterministic JSON / CSV；
- material-change / no-change no-commit；
- LKG 保护基线；
- Treasury 10Y 真实数据链；
- 共享 runtime tests；
- GitHub Actions 真实验证。

Phase 0 `platform-data` commits：

- `0677b2f1dbe12fd7fa38b83927ea0a965471f2e8`
- `bce33d6d33fc105068488e7ec8855e0b3e197dfa`
- `95ca27f6587fe37e1109876e85d7703d4a6659ed`
- `2a1428ccfc02b9f096f7f3397eb9183f972acdc2`

真实数据 refresh：

- `62cb4d213caf8dd82082726dfeb2e464fb964c52` — U.S. Treasury 10Y data refresh。

GitHub Actions：

- workflow：`macro-data`
- run id：`33295430507`
- head SHA：`2a1428ccfc02b9f096f7f3397eb9183f972acdc2`
- conclusion：`success`
- date：2026-08-30

---

## 8. 当前项目进度表

### 8.1 规划 / 准备度

| 工作流 | 状态 | 完成度 | 说明 |
|---|---|---:|---|
| 产品定位与 Change Control | DONE | 100% | 已冻结 |
| Macro V1 产品规格 | DONE | 100% | 已冻结 |
| Commodity V1 产品规格 | DONE | 100% | 已冻结 |
| Crypto V1 产品规格 | DONE | 100% | 已冻结 |
| 三模块 Data Source Map | DONE | 100% | baseline 已建立 |
| Phase F 可行性 / rights 审计 | DONE | 100% | v1.0 frozen |
| Unified Implementation Plan | DONE | 100% | Phase 1 Gate 已通过 |

**规划准备度：100%。**

含义：当前不再缺“应该做什么 / 数据从哪里来 / 哪些必须外链 / 怎么实施”的核心计划输入。

### 8.2 工程实施主阶段

工程交付采用 6 个主阶段口径，不将前置规划混入工程完成率：

| 工程阶段 | 状态 | 完成度 | 当前说明 |
|---|---|---:|---|
| Phase 0 — Shared Data Foundation | DONE | 100% | CI success |
| Phase 1 — Shared Market Detail | DONE | 100% | 真实 Treasury 10Y 垂直样板已验收 |
| Macro V1 Engineering | NEXT | 0% | 下一阶段 |
| Commodity V1 Engineering | NOT STARTED | 0% | 等 Phase 1 / Macro |
| Crypto V1 Engineering | NOT STARTED | 0% | 等共享层稳定 |
| Unified QA + Offline Acceptance | NOT STARTED | 0% | 三模块后执行 |

**工程主阶段完成：2 / 6 = 33.3%。**

该比例只表示主阶段 Gate，不代表工作量严格等权；后续项目管理以阶段状态和实际交付为主，不使用该比例推算工期。

### 8.3 当前模块工程状态

| 模块 | Product | Feasibility | Data Foundation | Business Engineering | QA |
|---|---|---|---|---|---|
| Macro | Frozen | Frozen | Shared Phase 0 / 1 Done | Next | Not Started |
| Commodity | Frozen | Frozen | Shared Phase 0 Done | Not Started | Not Started |
| Crypto | Frozen | Frozen | Shared Phase 0 Done | Not Started | Not Started |
| US Equity | Existing / Deferred | Deferred | N/A | Deferred | N/A |
| A-Share | Existing / Deferred | Deferred | N/A | Deferred | N/A |
| Global | Existing / Deferred | Deferred | N/A | Deferred | N/A |
| Trading Tools | Existing / Deferred | Read-only reference | N/A | Deferred | N/A |

---

## 9. 已完成：Phase 1 — Shared Market Detail Data Layer

### 9.1 目标

在不改变现有 Market Terminal UI 的前提下，建立统一 Market Detail 数据计算与适配能力。

统一支持：

- latest / close；
- 1D；
- 1W；
- 1M；
- QTD；
- YTD；
- 1Y；
- 52W High；
- 30D Sparkline。

### 9.2 Phase 1 规则

- 同一行尽量从同一 canonical history 计算当前值、returns、52W high、sparkline；
- 继续使用现有 SVG Sparkline；
- 不使用 random / placeholder history；
- low-frequency macro series 必须 frequency-aware；
- Crypto 7×24 与 US ETF / equities calendar 分离；
- cross-asset ratio 明确 timestamp alignment；
- 技术箭头 / technical-state algorithm 不在本 Phase 扩展；
- 不重构 `MarketTerminalPage.vue` / `TerminalDetailPanel.vue` 视觉。

### 9.3 Phase 1 完成标准

必须至少形成一个可复用的真实 Market Detail 垂直样板：

```text
canonical history
→ market-detail calculation
→ platform-api contract
→ existing frontend row
→ real 30D sparkline
→ validation
```

并证明：

- current value / returns / sparkline 一致；
- provider / frequency / stale 状态可追溯；
- 假数据退出；
- UI 不被改坏。

### 9.4 Phase 1 验收结果（2026-09-02）

- `platform-data` commit `9c5eb80f056bcbf2896fd85d321abb2c67bde01c` 已发布共享窗口计算、frequency-aware 缺失规则、52 周覆盖检查、30D sparkline 和 exact-date ratio alignment；
- `macro-data` 初始 workflow run `33588457408` 对该 SHA 结论为 `success`；官方日更到 `4.79%` 后，动态数据一致性测试修复 commit `8203a727923215bec573ced2db11858d3fd2c936` 的 run `33589428430` 再次为 `success`；
- 应用 commit `14fda8c4b1cf79013ca38396753f197ff17d7806` 已接入 `platform-api` Decimal 合约和现有宏观母表；
- 真实远端验收读取 `macro-us10y`：as-of `2026-09-01`、收盘 `4.79%`、1D `+4bp`；
- 完整历史不足的 YTD / 1Y / 52W 指标保持 `—`，不 forward-fill、不生成 placeholder；
- `TerminalDetailPanel.vue`、现有 SVG sparkline、列顺序和视觉结构未改；US Equity、A-Share、Global、Trading Tools 未改。

验证：`platform-data` 11 tests passed；新增 API/provider 6 tests passed；Ruff、Pyright、前端 type check、targeted ESLint、production Vite build 均通过。API 全量测试曾启动，但因既有慢速套件出现多项非本阶段失败且未在合理时限内完成，未将其伪报为全绿。

---

## 10. Macro V1 后续计划

### M1 — Macro Market Detail

Native 优先：BLS / BEA / Fed / Treasury / NY Fed 等。

### M2 — Growth

- Real GDP YoY；
- Industrial Production YoY；
- Initial Claims 4W MA；
- CFNAI + CFNAIMA3。

### M3 — Inflation

- CPI / Core CPI；
- PCE / Core PCE；
- PPI；
- Treasury nominal / real；
- 5Y / 10Y BE；
- 5Y5Y；
- Inflation Pricing Gap。

### M4 — Rates

- Target Lower / Upper；
- IORB；
- ON RRP Award；
- EFFR；
- SOFR；
- Treasury 3M / 2Y / 10Y / 30Y。

### M5 — Global M2

- US Fed；
- ECB；
- BOJ；
- BoE；
- China AKShare adapter + PBOC mandatory validation；
- ECB FX；
- latest common month；
- monthly-average FX；
- methodology version。

### M6 — Risk Appetite

- HY OAS → External Link；
- HYG/LQD → Official Embed / existing TradingView expression。

### M7 — Market Expectations

- Polymarket → External Link / permission required；
- CME FedWatch → External Link。

### M8 — Macro QA

完成后单独 QA，不自动进入 Commodity。

---

## 11. Commodity V1 后续计划

### C1 — Native Commodity Core

- EIA crude / Cushing / gasoline / distillate；
- CFTC Gold / Silver / Copper / WTI / NatGas positioning。

### C2 — Existing Gold Modules 去假数据

- WGC ETF Flow → External Link；
- SPDR → External Link；
- Central Bank Gold → IMF/WGC External Link；
- rights-clear macro driver → Native/Embed；
- GVZ 保留既有展示入口。

### C3 — Commodity Market Detail

逐行按 rights / feasibility 路由 Native / Embed / Link。

### C4 — Term Structure

- WTI → CME link；
- Brent → ICE link；
- LME complex curve → link；
- 中国公开期货结构仅在 rights-clear 时 Native。

### C5 — Inventory

- EIA Native；
- CME/LME受限库存 Link；
- SHFE/INE rights-clear 数据按需 Native。

### C6 — CFTC Positioning

核心五品种 Native。

### C7 — Cross-Market Spreads

受限 commercial legs 默认 Link。

### C8 — Volatility

- GVZ existing；
- OVX Embed / Link；
- CVOL Link。

### C9 — Commodity QA

确保不新增农产品、不显示假数据。

---

## 12. Crypto V1 后续计划

### X1 — Binance Native Core

BTC / ETH：

- Spot；
- Funding；
- Open Interest；
- Basis。

已完成 smoke test：BTC Funding / OI / Basis、ETH Funding。

Binance 部分历史接口窗口有限，因此启用后必须持续保存自有历史。

### X2 — Multi-Venue / Advanced Derivatives

- Coinglass → External Link；
- Bybit → Link / permission required；
- OKX → Link / permission required；
- Deribit → Link / permission required。

### X3 — ETF / Treasury Flow

现有静态数组退出：

- BTC ETF → Farside Link；
- ETH ETF → Farside Link；
- Bitcoin Treasuries → BitcoinTreasuries Link。

### X4 — Stablecoin

DefiLlama → External Link / permission required。

### X5 — Options & Volatility

- BTC DVOL 保留现有展示 / Deribit入口；
- IV Term / 25D Skew → Deribit / Greeks.live links。

### X6 — On-chain

- valuation → Checkonchain / Glassnode；
- exchange flow → CryptoQuant / Glassnode / Arkham；
- LTH/STH → Checkonchain / Glassnode；
- liquidation heatmap → Coinglass；
- whale intelligence → Arkham / CryptoQuant / BGeometrics。

### X7 — Crypto Market Detail

Native Binance / rights-clear data；严格区分 7×24 与 US securities calendars。

### X8 — Crypto QA

确保：

- 不再用 BTC ETF / Treasury fake arrays；
- Binance data 可追溯；
- Venue / Aggregate 标签正确；
- External Link 指向精确子页面。

---

## 13. 主要风险与处理原则

| 风险 | 当前等级 | 处理 |
|---|---|---|
| 数据 rights / redistribution | 高 | Phase F 已将大量商业数据改为 External Link |
| 第三方 endpoint schema drift | 中 | Native只采用批准源；parser check + LKG |
| Git 数据膨胀 | 中低 | 日/小时级必要数据；CSV/Parquet分区；不存raw高频 |
| Crypto历史窗口有限 | 中 | 启用后持续增量保存自己的历史 |
| 中国 M2上游延迟 | 中 | AKShare adapter + PBOC mandatory validation |
| UI 被数据工程误改 | 高 | Additive Only + protected components |
| 旧假数据残留 | 高 | 各业务 Phase 明确退出静态金融数据 |
| External Link失效 | 中 | 精确URL + 后续低频health/manual check |
| Deferred模块被顺手修改 | 高 | Change Control RED |

---

## 14. 阶段 Gate 与完成定义

### Phase 1 Gate

必须先完成 Shared Market Detail 样板，才开始大规模逐模块真实化。

### Module Gate

每个 Macro / Commodity / Crypto V1：

- Native data chain 可追溯；
- External Link 精确；
- no fake data；
- data status 正确；
- existing UI protected；
- 对应模块 QA 完成。

### Final Gate

三个 V1 完成后：

- 统一数据 QA；
- UI QA；
- Deferred regression check；
- local build / test / browser QA；
- 用户人工验收；
- 决定是否合并。

---

## 15. 仓库与分支纪律

### `Platform_Experiment`

- 开发分支：`feature/hedge-board-online-optimization`；
- 不直接修改 `main`；
- 不未经授权 merge。

### `platform-data`

- 当前生产数据仓库工作分支：`main`；
- Phase 0 已在该仓库产生真实 commit / Actions；
- 后续只按批准的数据 Phase 修改。

---

## 16. 当前下一步

当前唯一下一工程阶段：

> **Macro V1 Engineering**

建议执行顺序：

```text
Macro V1
↓
Macro QA
↓
Commodity V1
↓
Commodity QA
↓
Crypto V1
↓
Crypto QA
↓
Unified Offline Acceptance
```

除非用户明确调整优先级，执行 Agent 不得自行重排。

---

## 17. 权威文档索引

### 总控

- `HEDGE_BOARD_PROJECT_PLAN_AND_PROGRESS.md` — 本文件，完整计划与项目进度总览；
- `HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md` — 最高产品 / Change Control 约束；
- `HEDGE_BOARD_IMPLEMENTATION_PLAN.md` — 工程 Phase 与完成标准；
- `HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md` — 数据维护原则；
- `HEDGE_BOARD_PHASE_F_AUDIT.md` — 数据可行性 / rights 冻结结论。

### Macro

- `specs/MACRO_V1_SPEC.md`
- `specs/MACRO_DATA_SOURCE_MAP.md`

### Commodity

- `specs/COMMODITY_V1_SPEC.md`
- `specs/COMMODITY_DATA_SOURCE_MAP.md`

### Crypto

- `specs/CRYPTO_V1_SPEC.md`
- `specs/CRYPTO_DATA_SOURCE_MAP.md`

---

## 18. 更新规则

以后每完成一个正式 Phase：

1. 更新本文件进度表；
2. 更新 Implementation Plan 当前 Gate；
3. 更新 Master Plan 当前执行状态；
4. 记录真实 commit / workflow / test 结果；
5. 未验证内容必须写 `not_verified`；
6. 不因进度更新改变已冻结产品范围。
