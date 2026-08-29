# 对冲基金看板｜统一实施计划（Implementation Plan）

> 状态：Implementation Planning Baseline v0.2 / NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 数据可行性文档：`docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`  
> 适用分支：`feature/hedge-board-online-optimization`  
> 数据仓库：`wuxingyuenan5-lgtm/platform-data`  
> 说明：本文只定义实施顺序、共享基础设施、Phase 边界与验收标准；当前不代表已经开始工程实施。

---

## 1. 实施总原则【冻结】

所有实际开发必须同时遵守 Master Plan、Data Feasibility & Maintenance、对应模块 Spec / Data Source Map。

最高约束：

- Additive Only；
- 不删除、移动、重排、重命名或替换用户现有设计，除非用户明确要求；
- UI 与现有平台保持一致；
- 视觉组件硬编码不因数据工程而重构；
- 金融数据硬编码、随机数据、占位曲线逐步真实化；
- 前端原则上只消费 Platform API，不直接拼接多个外部金融数据源；
- TradingView 只作为展示 / 大图入口，不作为通用数据抓取源；
- 免费数据源优先；
- 无可靠免费源时 `not_configured`，不得伪造；
- 网站上“能看到”的图表 / 子模块不自动等于可嵌入或可抓取的数据源；
- 数据源进入开发前必须先通过 Data Feasibility Gate；
- GitHub / `platform-data` 是 V1 的版本化数据生产与分发层，不作为分钟级 / tick 高频数据库；
- 美股、A股、全球、交易工具保持 Deferred，不允许顺手修改。

当前实际实施范围只包括：

1. Macro V1
2. Commodity V1
3. Crypto V1

---

## 2. 统一目标架构【冻结】

```text
External free/public sources
        ↓
Data Feasibility Gate
        ↓
platform-data
  providers / normalize / derive / validate / LKG
        ↓
versioned canonical data / JSON + partitioned history
        ↓
platform-api
  cache / status / stale / fallback visibility
        ↓
Platform Web
  existing UI + additive sections
```

两个仓库职责严格分离：

### `platform-data`

负责：

- Provider adapter；
- 抓取；
- canonical identity；
- 单位 / 时区 / 交易日标准化；
- 派生指标；
- 历史序列；
- Last Known Good；
- quality flags；
- GitHub Actions 定时更新；
- 版本化 JSON 发布；
- 较长历史的 CSV / Parquet 分区（适用时）。

### `Platform_Experiment`

负责：

- 读取 `platform-data` 发布数据；
- API contract；
- cache；
- stale / degraded / error 展示语义；
- 前端状态与图表展示；
- 不改变现有视觉基线。

### V1 存储边界

适合 GitHub / 文件化保存：

- 宏观日 / 周 / 月 / 季频；
- Market Detail 日频历史；
- ETF Flow；
- CFTC；
- 库存；
- 日频 On-chain / Stablecoin；
- Polymarket 适度采样概率；
- Crypto Funding / OI / Basis 页面所需的快照与适度聚合历史。

不在 V1 用 GitHub 保存：

- tick；
- order book；
- 秒级；
- 每分钟全市场衍生品 raw feed；
- 高频实时交易流。

如果未来确实需要分钟级长期历史或复杂 SQL 查询，再在 canonical contract 不变的前提下升级到真正的时序 / 分析存储。

---

## 3. Phase F — Data Feasibility & Website Module Audit【实施前置硬门槛】

这是 Phase 0 之前必须完成的可行性阶段。

目标：

> 不写业务页面，先证明每个准备实现的数据源“真实可拿、免费、可自动更新、能维护”。

### 3.1 Data Source live validation

对三个 Data Source Map 的 Primary / Fallback 逐项检查：

- 实际请求是否成功；
- 是否需要免费 key；
- 免费额度 / 限制；
- 最新 observation 日期；
- 历史区间；
- 数据字段；
- frequency / publish timing；
- unit / currency / timezone / trading day；
- stale threshold；
- rights_scope；
- parser / schema 风险；
- 预计维护复杂度；
- 是否可稳定运行在 GitHub Actions；
- 是否需要 fallback；
- 是否适合 GitHub 文件化存储。

最终逐项标记：

- `READY`
- `FALLBACK`
- `OPEN`
- `EMBED_ONLY`
- `REFERENCE_ONLY`
- `NOT_CONFIGURED`

### 3.2 用户已有网站 / 子模块审计

用户整理的现成网站图表、资金流、期限结构、排名等子模块不得直接假定可复用。

逐项分类：

```text
官方 API
→ canonical_api

官方 Widget / Embed
→ official_embed（只展示，不反向取数）

公开但非文档化 JSON endpoint
→ public_endpoint_with_lkg（只有合规、稳定时）

只有网页 / JS 图表
→ 尝试找到 upstream source 后自行重画

iframe / CSP / X-Frame-Options / 登录受限
→ reference_only / not_configured
```

禁止：

- 绕 CAPTCHA / WAF；
- 绕登录；
- 从 iframe 跨域读取内部 DOM；
- 把浏览器自动化当成长期数据生产主链；
- 因复制第三方模块视觉而破坏现有平台 UI。

### 3.3 Phase F 输出

必须输出：

- Data Feasibility Matrix；
- Website Module Reuse Matrix；
- READY Source List；
- OPEN / NOT_CONFIGURED List；
- Storage Class（JSON / CSV / Parquet / snapshot-only）；
- 建议更新频率；
- 维护风险等级。

Phase F 不改业务页面。

### 3.4 Phase F 完成标准

只有当核心 V1 指标具备足够 READY 数据链后才进入 Phase 0。

如果某些非核心指标未通过：

- 保留 `not_configured`；
- 不阻塞整个 V1；
- 不自行删除产品规格；
- 是否最终删减由用户线下验收后决定。

---

## 4. Phase 0 — Shared Data Foundation

目标：只建立后续三个看板共用的数据基础设施，不提前实现任何具体大页面重构。

### 4.1 `platform-data` 最小共用骨架

建议形成：

```text
config/
schemas/
src/platform_data/
  providers/
  transforms/
  pipelines/
  storage/
public/v1/
history/
tests/
.github/workflows/
```

### 4.2 共用 canonical contract

至少支持：

- `series_id`
- `label`
- `observations`
- `latest_value`
- `unit`
- `currency`
- `frequency`
- `timezone`
- `source`
- `upstream_source`
- `source_id`
- `as_of`
- `retrieved_at`
- `status`
- `is_stale`
- `methodology_version`
- `quality_flags`
- `rights_scope`

### 4.3 共用运行机制

必须建立：

- finite timeout；
- transient retry；
- Primary / Fallback；
- Last Known Good；
- stale detection；
- schema validation；
- no-change no-commit；
- failed fetch 不覆盖上一份有效数据；
- provider failure 与 genuine no-data 分离；
- schema drift / latest-date / abnormal-scale checks。

### 4.4 存储实现基线

最新发布数据优先 JSON。

长历史：

- 小数据量：CSV；
- 较大 / 多列数据：Parquet；
- 按年或按月稳定分区；
- 不频繁 commit SQLite / DuckDB 二进制数据库；
- 不为每日数据建立海量细碎 snapshot 文件。

### 4.5 Phase 0 完成标准

不能只创建 README / schema 即宣布完成。

必须至少有一个真实免费数据源贯通：

```text
Provider
→ canonical series
→ validation
→ published JSON
→ history storage
→ automated workflow or reproducible pipeline
```

测试环境不可用时可标 `not_verified`，但不得伪造执行结果。

---

## 5. Phase 1 — Shared Market Detail Data Layer

目标：为 Macro / Commodity / Crypto 共用的 Market Detail 建立统一数据模型，但不重构 `MarketTerminalPage.vue` / `TerminalDetailPanel.vue` 的视觉结构。

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

规则：

- 同一行尽量使用同一 canonical history 计算当前值、收益率与 Sparkline；
- 30D 继续用现有 SVG；
- 不使用 placeholder / random spark；
- 低频宏观数据 frequency-aware；
- Crypto 7×24 与美股 ETF / 币股交易日历严格区分；
- 技术状态箭头不在本 Phase 重构。

Phase 1 先完成数据层和适配能力；具体哪些行正式接通，由后续各模块 Phase 逐步完成。

---

# 6. Macro V1 实施路线

权威产品文档：

- `specs/MACRO_V1_SPEC.md`
- `specs/MACRO_DATA_SOURCE_MAP.md`

## M1 — Market Expectations / Polymarket

端到端完成：

```text
platform-data whitelist
→ Polymarket metadata
→ token / probability history
→ canonical expectations JSON
→ platform-api
→ MacroExpectationPanel.vue
```

要求：

- 不再自动扫描大量市场并按标题关键词直接发布；
- 使用显式白名单；
- 当前概率 + 真实历史概率曲线；
- 1D / 7D change；
- liquidity / volume / expiry / updated_at；
- provider error 与 no configured events 分开。

## M2 — Macro Market Detail 真实化

处理现有 Macro Market Detail：

- 日频市场数据完整真实化；
- DFF / SOFR 等利率变化按 bp 语义；
- CPI / PCE / UNRATE / M2 等低频数据 frequency-aware；
- 真实 30D Sparkline；
- MOVE / DSPX 等无稳定免费源时允许 `not_configured`。

## M3 — Growth

新增：

- Real GDP YoY；
- Industrial Production YoY；
- Initial Claims 4W MA；
- CFNAI + CFNAIMA3。

## M4 — Inflation

新增：

- CPI / Core CPI；
- PCE / Core PCE；
- PPI；
- 5Y / 10Y Breakeven；
- 5Y5Y；
- Actual vs Market-Implied Inflation 曲线；
- Inflation Pricing Gap 只作状态比较，不标预测误差。

## M5 — Rates

新增：

- Short-End Rate Corridor：Target Lower / Upper、IORB、ON RRP、EFFR、SOFR；
- Treasury：3M / 2Y / 10Y / 30Y。

## M6 — Global M2

固定：

```text
globalM2 =
  cnm2 * cnyusd
+ usm2
+ eum2 * eurusd
+ jpm2 * jpyusd
+ gbm2 * gbpusd
```

必须：

- 最近共同月份；
- 月平均 FX；
- USD 统一单位；
- Global M2 Level + YoY；
- 成分贡献可在 tooltip / detail 中查看；
- methodology version。

## M7 — Risk Appetite

仅新增：

- US High Yield OAS；
- HYG / LQD Ratio。

## M8 — Macro QA / Offline Acceptance Prep

检查：

- 现有内容未被删除 / 重排；
- 新 Section UI 一致；
- freshness / previous value / frequency-aware time range；
- 数据状态正确；
- Source Map 与实际实现一致；
- 输出线下验收清单。

---

# 7. Commodity V1 实施路线

权威产品文档：

- `specs/COMMODITY_V1_SPEC.md`
- `specs/COMMODITY_DATA_SOURCE_MAP.md`

## C1 — Existing Gold Data Realization

先保护并真实化既有核心：

- Global gold ETF weekly flows；
- YTD ETF summary；
- SPDR daily flow；
- SPDR holdings vs gold；
- central-bank holdings / buyers；
- GVZ；
- gold macro-driver charts。

不得重做现有视觉。

## C2 — Commodity Market Detail 真实化

真实化现有：

- 贵金属；
- 铜；
- 商品指数（可合法免费时）；
- WTI / Brent / Natural Gas；
- 矿股；
- 相对比价；
- 30D Sparkline。

无稳定免费源的行允许 `not_configured`。

## C3 — Futures Curve / Term Structure

优先：

1. WTI
2. Brent
3. Copper
4. Gold（低优先级）

展示：

- current curve；
- M1-M2；
- M1-M3 / near-far spread。

只在获得稳定、免费 current contract chain 后实现；不得用停更历史接口冒充当前期限结构。

## C4 — Inventory / Physical

原油：

- EIA crude；
- Cushing；
- gasoline；
- distillate。

铜：

- LME；
- COMEX；
- SHFE inventory / warehouse receipts。

黄金：

- COMEX inventory 仅在免费稳定源可靠时加入。

## C5 — Positioning / CFTC

覆盖：

- Gold；
- Silver；
- Copper；
- WTI；
- Natural Gas。

展示：

- Managed Money Net；
- Commercial / Producer-Merchant Net；
- historical percentile。

## C6 — Cross-Market Spreads

新增：

- COMEX Copper vs LME Copper；
- SHFE Copper vs LME Copper；
- Brent - WTI；
- 沪金/国际金、沪银/国际银只在数据口径稳定时加入。

## C7 — Commodity Volatility

- GVZ：现有保留；
- OVX：新增；
- Copper IV 不强制。

## C8 — Commodity QA / Offline Acceptance Prep

重点检查：

- 合约单位 / 货币 / 汇率；
- trading day；
- settlement vs close；
- inventory units；
- CFTC contract mapping；
- 既有黄金模块未被改坏；
- 不出现农产品新增。

---

# 8. Crypto V1 实施路线

权威产品文档：

- `specs/CRYPTO_V1_SPEC.md`
- `specs/CRYPTO_DATA_SOURCE_MAP.md`

## X1 — Existing Flow Data Realization

先真实化既有静态模块：

- BTC ETF Daily Net Flow vs BTC；
- Bitcoin Treasuries Flow。

同时新增：

- ETH ETF Daily Net Flow vs ETH。

## X2 — Derivatives & Leverage

覆盖 BTC / ETH：

- Funding；
- Open Interest；
- Basis。

必须支持：

- Aggregate；
- Venue。

聚合原则：

- Funding：OI weighted；
- OI：USD notional sum；
- Basis：只聚合可比合约 / 期限，优先 OI weighted。

高频存储规则：

- 页面 latest 可按适当频率更新；
- Git 历史只保留页面需要的采样 / 聚合粒度；
- 不 commit 分钟级全市场 raw feed。

## X3 — Stablecoin Liquidity

新增：

- Total Stablecoin Supply；
- 7D / 30D change；
- USDT Supply / Share；
- USDC Supply / Share；
- Total Stablecoin vs BTC。

## X4 — Options & Volatility

保留：

- BTC DVOL。

新增：

- BTC / ETH IV Term Structure：7D / 30D / 60D / 90D / 180D；
- BTC / ETH 25D Skew；
- canonical 方向固定为 `Put IV - Call IV`。

不建设完整 Vol Surface / Greeks 平台。

## X5 — On-chain Core

BTC 为主，固定核心：

- MVRV；
- NUPL；
- SOPR；
- BTC Price vs Realized Price；
- Realized Cap；
- Exchange Balance / Reserve；
- Exchange Netflow；
- LTH Supply；
- STH Supply。

规则：

- 免费；
- 方法学可解释；
- 同一 canonical series 不静默切换实体标签 / 钱包集合；
- unavailable → `not_configured`；
- 不为补齐页面使用来源不明聚合数据。

## X6 — Crypto Market Detail 真实化

真实化现有：

- 主流币；
- 币股 / ETF；
- relative ratios；
- dominance / TOTAL series；
- 30D Sparkline。

特别规则：

- Crypto spot 7×24；
- derivatives 7×24但 funding / settlement 依 venue；
- ETF / US equities 使用美国证券交易日；
- cross-asset ratio 定义对齐时点。

## X7 — Crypto QA / Offline Acceptance Prep

重点检查：

- Aggregate / Venue 标签明确；
- 不同交易所 funding interval 正确归一化；
- OI notional 口径正确；
- Basis contract mapping 正确；
- ETF 与 7×24 Crypto 交易日历不混用；
- on-chain methodology 可追溯；
- 现有页面结构未被删除或重排。

---

## 9. Shared Provider Reuse【冻结】

同一基础数据不得在三个模块重复抓取三次。

例如：

- Treasury / FRED：Macro 与 Gold macro drivers 共享 canonical series；
- DXY：Macro / Gold 共享；
- BTC / ETH spot：Crypto 多个 Section 共享；
- FX：Global M2、商品跨市场价差共享；
- CFTC：Commodity 多品种统一 pipeline；
- Yahoo / AKShare 等 public-web provider：统一 adapter、cache、retry、health rules。

原则：

```text
one canonical series
→ many consumers
```

不得：

```text
one page
→ one private copy of the same raw source
```

---

## 10. GitHub Actions 建议拆分【实施时再冻结具体 cron】

建议按数据变化速度分 workflow，而不是每指标一个 workflow：

### Core Market Daily

- Treasury / FRED；
- Market Detail daily histories；
- Commodity market data；
- ETF / equities daily。

### Macro Low Frequency

- CPI / PCE / GDP / M2 等；
- 每日检查，数据不变则不 commit。

### Commodity Weekly / Physical

- EIA inventory；
- CFTC；
- WGC / SPDR；
- exchange inventory。

### Crypto Frequent

- funding；
- OI；
- basis；
- DVOL / options；
- stablecoin；
- Polymarket（如继续与 Macro 共用独立任务）。

### Crypto Daily / Slow

- ETF Flow；
- Treasury Flow；
- on-chain；
- holder structure。

最终 cron 在实际实施前根据 API limit / update timing 冻结。

---

## 11. Commit / Phase Discipline【冻结】

每个 Phase 必须是可验证的垂直切片。

禁止：

- 只新增 contract / schema / README 就宣布 Phase 完成；
- 一个超大 commit 混合多个模块；
- 为修 Macro 顺手重构 Crypto；
- 为公共组件整洁性修改 Deferred 页面。

每个端到端 Phase 应尽量形成：

```text
platform-data
→ platform-api
→ frontend
→ validation
→ commit
```

无法运行本地构建时：

- 代码可以提交；
- 测试标 `not_verified`；
- 不得伪造 build / E2E 结果。

---

## 12. 推荐总体执行顺序【冻结为当前基线】

当前推荐：

1. **Phase F — Data Feasibility & Website Module Audit**
2. Phase 0 — Shared Data Foundation
3. Phase 1 — Shared Market Detail Data Layer
4. M1 — Macro Polymarket
5. M2 — Macro Market Detail
6. M3-M7 — Macro additive sections
7. M8 — Macro QA
8. C1-C2 — Existing Commodity real-data stabilization
9. C3-C7 — Commodity new structural modules
10. C8 — Commodity QA
11. X1 — Existing Crypto flow stabilization
12. X2-X5 — Crypto new structure / on-chain
13. X6 — Crypto Market Detail
14. X7 — Crypto QA
15. Hedge Board Phase 1 Offline Acceptance

用户可明确改变执行优先级；执行 Agent 不得自行重排业务优先级。

---

## 13. 最终阶段验收【冻结】

三个 V1 都完成后，用户线下验收前必须产出统一清单：

### 数据

- source / upstream source；
- freshness；
- fallback；
- quality flags；
- no fake data；
- no silent stale；
- no empty overwrite；
- no cross-frequency fake precision；
- website / internal endpoint 依赖已标风险等级；
- 高频数据没有被不合理塞入 Git。

### UI

- 现有设计未被擅自删除；
- 原顺序未被擅自改变；
- 新增 Section 与平台风格一致；
- 视觉组件未因数据工程被重构；
- Deferred 模块未受影响。

### 工程

- Platform main 未被修改；
- 所有开发仍在 `feature/hedge-board-online-optimization`；
- `platform-data` pipeline 有真实可追溯输出；
- 每个 Phase 有真实 commit；
- 未验证项目明确列 `not_verified`。

最终由用户在线下环境执行完整 build / test / browser QA 后，才决定是否修复或合并。
