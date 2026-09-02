# 对冲基金看板｜统一实施计划（Implementation Plan）

> 状态：Implementation Plan v1.4 / PHASE 0 DONE / PHASE 1 DONE / MACRO V1 IN PROGRESS  
> 项目总览：`docs/hedge-board/HEDGE_BOARD_PROJECT_PLAN_AND_PROGRESS.md`  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 数据可行性：`docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`  
> Phase F 审计：`docs/hedge-board/HEDGE_BOARD_PHASE_F_AUDIT.md`  
> 适用分支：`feature/hedge-board-online-optimization`  
> 数据仓库：`wuxingyuenan5-lgtm/platform-data`

---

## 1. 当前状态【冻结】

Phase F 已完成并冻结；Phase 0、Phase 1、Macro V1 已完成并通过真实 GitHub Actions 与应用验证。

当前：

```text
Phase F Data Feasibility & Rights Audit
→ DONE / FROZEN

Phase 0 Shared Data Foundation
→ DONE

Phase 1 Shared Market Detail Data Layer【DONE】
→ DONE

Macro V1 Engineering
→ IN PROGRESS
```

当前管理口径：

- 规划准备度：`100%`；
- 工程主阶段：`3 / 6 = 50%`；
- 六个工程主阶段：Phase 0、Phase 1、Macro V1、Commodity V1、Crypto V1、Unified QA / Offline Acceptance；
- 百分比仅用于阶段 Gate 管理，不代表工作量严格等权，不用于推算工期。

完整阶段状态与项目进度表统一维护在：

`docs/hedge-board/HEDGE_BOARD_PROJECT_PLAN_AND_PROGRESS.md`

所有工程实现必须同时遵守：

1. Project Plan & Progress；
2. Master Plan；
3. Data Feasibility & Maintenance；
4. Phase F Audit；
5. 对应模块 V1 Spec；
6. 对应模块 Data Source Map。

当旧 Spec / Source Map 与较新的 Phase F rights / feasibility 判定冲突时：

> **产品范围以 Spec 为准；实际数据交付方式以 Phase F Audit 为准。**

即：产品需求不擅自删除，但某项数据无法合法、低维护 Native 时，改用 External Reference Button / Official Embed，不使用假数据。

---

## 2. 全局实施原则【冻结】

- Additive Only；
- 不删除、移动、重排、重命名用户现有设计，除非用户明确批准；
- UI 与现有平台保持一致；
- 视觉组件不因数据工程被大规模重构；
- 假金融数据、静态随机值、占位曲线必须逐步退出；
- TradingView 主要作为展示 / 大图入口，不作为通用抓取源；
- Native 数据统一通过 `platform-data → platform-api → frontend`；
- `EXTERNAL_LINK` 直接复用 Trading Tools 已整理的精确 URL，不建第二套书签库；
- Trading Tools 本身继续 Deferred，不开发、不改 UI、不处理元数据；
- 美股、A股、全球继续 Deferred；
- rights / licensing 优先于“技术上能抓”；
- Provider 失败不得用空数组覆盖 LKG；
- GitHub / `platform-data` 不是 tick / 秒级 / 全量分钟数据库。

当前实际开发范围只包括：

1. Macro V1；
2. Commodity V1；
3. Crypto V1。

---

## 3. 统一目标架构【冻结】

### 3.1 Native 数据

```text
Official / approved public source
        ↓
platform-data
  provider / normalize / derive / validate / LKG
        ↓
canonical JSON + partitioned history
        ↓
platform-api
        ↓
existing UI / additive section
```

### 3.2 External 数据入口

```text
Trading Tools existing catalog / official site
        ↓
read-only exact URL
        ↓
External Reference Button
        ↓
new browser tab
```

External Link 是正式产品交付方式，不是“加载失败占位”。

### 3.3 Official Embed

仅在官方明确允许、体验明显优于外链、且不会破坏当前 UI 时采用。

---

## 4. V1 存储边界【冻结】

### 适合 GitHub / 文件化

- 宏观日 / 周 / 月 / 季频；
- Market Detail 日频历史；
- EIA；
- CFTC；
- Binance Funding / OI / Basis 页面所需采样；
- 本地派生指标；
- 30D Sparkline 历史；
- latest snapshots。

### 不在 V1 保存

- tick；
- order book；
- 秒级数据；
- 每分钟全市场 raw feed；
- 受限商业数据的本地历史副本。

### 文件格式

- 最新前端消费：JSON；
- 小型长历史：CSV；
- 较大 / 多列：Parquet；
- 按年或按月分区；
- 不把 SQLite / DuckDB 二进制文件频繁 commit 到 Git。

---

# 5. Phase 0 — Shared Data Foundation【DONE】

目标：建立三个 active V1 共用的数据基础设施，不提前改页面。

## 5.1 `platform-data` 骨架【已存在并复用】

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

没有为 Phase 0 另建平行框架；直接复用并增强现有 `platform-data`。

## 5.2 Canonical Contract【DONE】

现有 Pydantic `CanonicalSeries` 已覆盖：

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
- `source_url`
- `as_of`
- `retrieved_at`
- `status`
- `is_stale`
- `methodology_version`
- `quality_flags`
- `rights_scope`

`delivery_mode` 属于产品交付路由，不强制塞进每个纯 Native time-series payload；在业务 manifest / route config 层表达即可。

## 5.3 共用运行机制【DONE / 基线】

已具备：

- finite timeout；
- finite transient retry；
- LKG 保留（fetch/validation失败时不覆盖上一份有效数据）；
- stale detection；
- Pydantic schema validation；
- latest/future-date / duplicate / numeric range 等质量检查；
- no-change no-commit；
- material payload 不变时保留旧 `retrievedAt`，避免 Git 噪音；
- deterministic JSON / CSV history output。

Primary / Fallback 仍按具体 Provider 在后续业务 Phase 中逐源配置，不为 Phase 0 强造无业务意义的 fallback。

## 5.4 External Link Registry【设计完成，按需实施】

不复制 Trading Tools 全库。

只在业务模块需要时，通过现有 Trading Tools catalog 读取选定链接，并形成业务页所需轻量配置：

- `tool_id`；
- `label`；
- `url`；
- `provider`；
- `purpose`；
- `last_checked_at`；
- `status`。

来源仍以 Trading Tools 为准；Phase 0 不修改 Trading Tools。

## 5.5 Phase 0 真实验收链【DONE】

已存在并增强的真实链路：

```text
U.S. Treasury official CSV
→ Treasury provider
→ CanonicalSeries
→ quality validation / stale detection
→ public/v1/macro/series/us_treasury_10y.json
→ history/us_treasury_10y/<year>.csv
→ GitHub Actions scheduled / push pipeline
```

Phase 0 本轮新增 / 修改的 `platform-data` commits：

- `0677b2f1dbe12fd7fa38b83927ea0a965471f2e8` — shared runtime helpers；
- `bce33d6d33fc105068488e7ec8855e0b3e197dfa` — Treasury provider 使用共享 retry session；
- `95ca27f6587fe37e1109876e85d7703d4a6659ed` — Treasury pipeline 使用共享 freshness / material-change helpers；
- `2a1428ccfc02b9f096f7f3397eb9183f972acdc2` — shared runtime tests。

真实 GitHub Actions：

- workflow: `macro-data`；
- run id: `33295430507`；
- head SHA: `2a1428ccfc02b9f096f7f3397eb9183f972acdc2`；
- conclusion: `success`；
- completed: 2026-08-30。

因此 Phase 0 完成标准已经满足。

---

# 6. Phase 1 — Shared Market Detail Data Layer【DONE】

保留现有 Market Terminal 视觉和列结构。

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

- 同一行尽量使用同一 canonical history；
- 30D 继续用现有 SVG；
- 不使用 random / placeholder spark；
- 低频数据 frequency-aware；
- Crypto 7×24 与 US ETF / equities 日历分离；
- 技术状态箭头不在本 Phase 重构。

Phase 1 已于 2026-09-02 完成。数据 commit 为 `9c5eb80f056bcbf2896fd85d321abb2c67bde01c`，workflow run `33588457408` 为 `success`；官方日更后的动态一致性测试 commit `8203a727923215bec573ced2db11858d3fd2c936` / run `33589428430` 再次为 `success`。应用纵切片 commit 为 `14fda8c4b1cf79013ca38396753f197ff17d7806`。真实样本 `macro-us10y` 已通过统一窗口层、API Decimal 合约接回现有母表，最新远端验收 as-of `2026-09-01`、收盘 `4.79%`、1D `+4bp`。缺少足够历史的窗口显式返回 unavailable；没有 forward-fill 或 placeholder。

---

# 7. Macro V1 实施路线

权威产品：

- `specs/MACRO_V1_SPEC.md`
- `specs/MACRO_DATA_SOURCE_MAP.md`

## M1 — Macro Market Detail 真实化

优先使用 BLS / BEA / Fed / Treasury / NY Fed 等 Phase F `NATIVE_READY` Source of Record。

Native core 最终完成 23 行：原 20 行 Treasury / FRED / Yahoo core，加财政部—中国国债收益率曲线 2Y / 10Y / 30Y。既有数据 commits 为 `774dccacebbd6f1fdca02f47071c0f74dc9fe07b`、`02bdfef35f803ef18e1f379598ba85abf001383c`、`183e99db29e44d7b6a9e490840b430e23c41f537`、`997adb4871bbfbd3d5c089c8761344433bd0e77c`；中国曲线 commit `5dac2e68c7664824e0dc8423531f9819f5307bfc`。应用 commits 为 `cca0a46685f86dc17271f9d46216646fa0ada6f1`、`482c636fca46833d6ab0a77ea17df922c2f457ea`、`913d7df85e88bd3d2881c37a8750da3b3562df0d`、`97eff694`；workflow run `33601155026` success。

Macro 专题已交付 Growth、Actual / Upstream / Market-Implied Inflation、Short-End Rate Corridor、Risk Appetite，并完成 Global M2 五区共同月份、ECB 日汇率月均折算、总量/YoY/component/share canonical 输出与双图展示。既有数据 commits `c62dbb299efaa1dcc21d95bd26612be262535d7e`、`34cb72f7d28539ca25360234e175c654ee418106`、`36ba32b78d8ce037dc9c75d2bfe0f00dd97fbbc6`、`9ce61a1f29d781dfa015085a94771e7405014fec`；应用 commits `e294e75398005b3efa040f575e3a0ff37954278e`、`ecbb20a9463fd0da237566eee3bdf4a4668182cb`、`88e94bd53f6a51b02b2cef9a2cb1a83ef5d4bf11`。当前仅剩中国国债 mapping，未确认部分保持 unavailable。

处理：

- 日频市场/利率数据；
- 低频 CPI/PCE/UNRATE/M2 frequency-aware；
- 利率变化以 bp；
- 真实 30D Sparkline；
- 无 rights-clear Native 的项目使用 Embed / Link，不造假。

## M2 — Growth

Native：

- Real GDP YoY；
- Industrial Production YoY；
- Initial Claims 4W MA；
- CFNAI + CFNAIMA3。

## M3 — Inflation

Native：

- CPI / Core CPI；
- PCE / Core PCE；
- PPI；
- Treasury nominal / real；
- 本地计算 5Y / 10Y Breakeven；
- 本地计算 5Y5Y；
- Inflation Pricing Gap。

## M4 — Rates

Native：

- Target Lower / Upper；
- IORB；
- ON RRP Award；
- EFFR；
- SOFR；
- Treasury 3M / 2Y / 10Y / 30Y。

## M5 — Global M2

Native：

- US：Fed；
- Euro Area：ECB；
- Japan：BOJ；
- UK：BoE；
- China：AKShare adapter + PBOC mandatory validation；
- FX：ECB。

固定：最近共同月份 + 月平均 FX + methodology version。

## M6 — Risk Appetite

- HY OAS：`EXTERNAL_LINK`；
- HYG/LQD：`OFFICIAL_EMBED` / 现有 TradingView expression。

## M7 — Market Expectations

### Polymarket

默认 V1：`EXTERNAL_LINK / permission_required`。

保留原产品模块位置，但未取得许可前不建立本地概率历史数据库。

### CME FedWatch

`EXTERNAL_LINK`。

## M8 — Macro QA

检查：

- Native / Embed / Link 标识准确；
- 不出现假数据；
- Source / freshness 正确；
- 现有 UI 未被擅自重排。

Macro V1 已于 2026-09-02 完成。Global M2 数据 commit `2e5812593a8a5a1e3ddba9d9402e5888d6d25331`；中国国债 2Y / 10Y / 30Y commit `5dac2e68c7664824e0dc8423531f9819f5307bfc`，增量刷新修复 `d5fc17f6248baaffcb1878cadfd9043542047b9f`；workflow runs `33601155026`、`33601543904` success。应用 Global M2 / cache consistency commit `ee8dd4d0`、中国债券 placeholder 清理 commit `97eff694`。Macro Market Detail 共 23 行，Global M2 level/component/YoY 与全部专题模块均通过真实 API 和 production build 验证。

---

# 8. Commodity V1 实施路线

权威产品：

- `specs/COMMODITY_V1_SPEC.md`
- `specs/COMMODITY_DATA_SOURCE_MAP.md`

## C1 — Native Commodity Core

Native：

- EIA crude / Cushing / gasoline / distillate；
- CFTC Gold / Silver / Copper / WTI / Natural Gas positioning。

## C2 — Existing Gold Modules 去假数据

现有视觉保护，但 Phase F 判定为商业/受限数据的模块不得继续依赖静态假值。

处理：

- WGC ETF Flow → External Link；
- SPDR holdings / flow → External Link；
- Central Bank Gold → IMF/WGC External Link（未来 permission cleared 再 Native）；
- Treasury / DXY 等 rights-clear 宏观驱动可继续 Native/Embed；
- GVZ 保留现有展示入口，不新建本地 Cboe history DB。

## C3 — Commodity Market Detail

逐行按 Phase F：

- rights-clear price/history → Native；
- 商业指数/受限市场数据 → Embed / External Link；
- 不再用假 current value / fake sparkline。

## C4 — Futures Curve / Term Structure

- WTI → CME External Link；
- Brent → ICE External Link；
- LME / complex prompt curve → External Link；
- 国内可稳定公开的期限结构再按 AKShare / exchange upstream 单独 Native。

## C5 — Inventory / Physical

- EIA → Native；
- CME / LME受限库存 → External Link；
- SHFE/INE rights-clear upstream 可评估 Native。

## C6 — Positioning

CFTC核心品种全部 Native。

## C7 — Cross-Market Spreads

涉及 CME/LME/ICE等受限 leg 的复杂 spread 默认 External Link；不为 V1 建受限数据历史库。

## C8 — Volatility

- GVZ：现有展示；
- OVX：Official Embed / External Link；
- CVOL：External Link。

## C9 — Commodity QA

检查：

- 原有黄金模块不显示假数据；
- Native/External Link清晰；
- 单位/合约/结算口径正确；
- 不新增农产品。

---

# 9. Crypto V1 实施路线

权威产品：

- `specs/CRYPTO_V1_SPEC.md`
- `specs/CRYPTO_DATA_SOURCE_MAP.md`

## X1 — Binance Native Core

V1 第一 Native Venue 固定 Binance。

Native BTC / ETH：

- spot；
- Funding；
- Open Interest；
- Basis。

Phase F 已实际 smoke test：BTC Funding / OI / Basis、ETH Funding均能返回结构化数据。

注意：Binance部分历史接口只保留近约30天，因此启用后 `platform-data` 必须持续增量保存自身历史。

## X2 — Multi-Venue / Advanced Derivatives

默认：

- Coinglass Funding / OI → External Link；
- Bybit → External Link / permission_required；
- OKX → External Link / permission_required；
- Deribit → External Link / permission_required。

产品未来仍可扩 Aggregate / Venue，但需 rights cleared 后再增加 Native Venue。

## X3 — ETF / Treasury Flow

现有静态数据必须退出。

- BTC ETF Flow → Farside External Link；
- ETH ETF Flow → Farside External Link；
- Bitcoin Treasuries → BitcoinTreasuries External Link。

保留现有卡片/Section语义，不用静态数组冒充真实数据。

## X4 — Stablecoin

DefiLlama → External Link / permission_required。

不把其 public API 技术可访问性误当成组织生产再利用许可。

## X5 — Options & Volatility

- BTC DVOL：保留现有 TradingView / Deribit入口；
- IV Term Structure / 25D Skew：Deribit / Greeks.live External Link；
- 未取得数据许可前不本地复制完整 option chain。

## X6 — On-chain

External Link 为 V1 默认交付：

- MVRV / NUPL / SOPR / Realized Cap → Checkonchain / Glassnode；
- Exchange Balance / Netflow → CryptoQuant / Glassnode / Arkham；
- LTH / STH → Checkonchain / Glassnode；
- Liquidation Heatmap → Coinglass；
- Whale / Wallet → Arkham / CryptoQuant / BGeometrics。

## X7 — Crypto Market Detail

Native Binance / rights-clear数据逐步真实化；其他币股/ETF等可继续使用现有展示能力或 rights-clear source。

必须区分：

- Crypto spot 7×24；
- derivatives funding/settlement；
- US ETF / equities交易日；
- cross-asset ratio对齐时间。

## X8 — Crypto QA

检查：

- 不再展示 BTC ETF / Treasury 静态假数据；
- Binance Native数值可追溯；
- External Link按钮精确到子页面；
- 不把单 Venue 标成全市场 Aggregate。

---

# 10. Shared Provider Reuse【冻结】

原则：

```text
one canonical series
→ many consumers
```

示例：

- Treasury / Fed / FX 可跨 Macro 与 Commodity 复用；
- Binance BTC/ETH spot 在 Crypto多个 Section 复用；
- CFTC 多商品使用同一 pipeline；
- External Link 使用 Trading Tools 现有 catalog，不重复建书签库。

---

# 11. GitHub Actions 分层【实施时冻结 cron】

建议：

### Macro Daily / Low Frequency
- BLS / BEA / Fed / Treasury / NY Fed / ECB / BOJ / BoE / PBOC validation；
- 每日检查，数据不变不 commit。

### Commodity Official
- EIA；
- CFTC；
- rights-clear中国交易所数据。

### Crypto Native
- Binance Funding / OI / Basis / spot；
- 只保存页面需要的采样与聚合历史。

### Link Health
- External Link 只做低频 HTTP / manual health check；
- 不抓取第三方内部数据。

---

# 12. Commit / Phase Discipline【冻结】

每个 Phase 必须是可验证垂直切片。

禁止：

- 只新增 README/schema 就宣布完成；
- 一个大 commit 混多个业务模块；
- 为 Macro 顺手改 Crypto；
- 为公共组件整洁性修改 Deferred 页面；
- 把 External Link 又变成未经批准的抓取器。

Native Phase 尽量：

```text
platform-data
→ platform-api
→ frontend
→ validation
→ commit
```

无法运行构建/测试时标 `not_verified`，不得伪造。

---

# 13. 当前推荐执行顺序【冻结基线】

```text
Phase F                         DONE
↓
Phase 0 Shared Data Foundation DONE
↓
Phase 1 Shared Market Detail   DONE
↓
Macro V1
↓
Commodity V1
↓
Crypto V1
↓
Offline Acceptance
```

业务内部建议：

1. Macro Native core + links；
2. Commodity EIA/CFTC + links；
3. Crypto Binance Native + links；
4. 三模块 QA；
5. 线下验收。

用户可明确改变优先级；执行 Agent 不得自行重排。

---

# 14. 下一阶段 Gate【冻结】

当前已经完成：

- Product Spec；
- Data Source Map；
- Data Feasibility / Maintenance；
- Phase F Audit v1.0；
- Phase 0 Shared Data Foundation；
- Phase 0 GitHub Actions 验证；
- Project Plan & Progress v1.0。

下一步是 **Commodity V1 Engineering**。

以后每完成一个正式 Phase，都必须同步更新：

1. `HEDGE_BOARD_PROJECT_PLAN_AND_PROGRESS.md`；
2. `HEDGE_BOARD_IMPLEMENTATION_PLAN.md`；
3. `HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`；
4. 真实 commit / workflow / test 结果。
