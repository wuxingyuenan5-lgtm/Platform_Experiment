# 对冲基金看板｜完整项目计划书与进度总表

> 状态：Project Baseline v1.6 / Phase 0 DONE / Phase 1 DONE / Macro V1 DONE / Commodity V1 DONE / Crypto V1 DONE / Unified QA NEXT
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
| Macro V1 Engineering | DONE | 100% | Market Detail 23 行；Growth / Inflation / Rates / Risk / Global M2 全部验收 |
| Commodity V1 Engineering | DONE | 100% | CFTC / EIA Native、受限模块官方 Link、母表 fail-closed 与 QA 全部完成 |
| Crypto V1 Engineering | DONE | 100% | Binance Native、links、fail-closed、本地数据库与本地调度已验收 |
| Unified QA + Offline Acceptance | IN PROGRESS | 95% | 隔离本地验收站已就绪；Owner 页面验收与是否合并待决定 |

**工程主阶段完成：5 / 6 = 83.3%。**

该比例只表示主阶段 Gate，不代表工作量严格等权；后续项目管理以阶段状态和实际交付为主，不使用该比例推算工期。

### 8.3 当前模块工程状态

| 模块 | Product | Feasibility | Data Foundation | Business Engineering | QA |
|---|---|---|---|---|---|
| Macro | Frozen | Frozen | Shared Phase 0 / 1 Done | Done | Done |
| Commodity | Frozen | Frozen | Shared Phase 0 Done | Done | Done |
| Crypto | Frozen | Frozen | Shared Phase 0 Done | Done | Done |
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

## 10. Macro V1 验收结果

### M1 — Macro Market Detail

Native 优先：BLS / BEA / Fed / Treasury / NY Fed 等。

截至 2026-09-02，M1 前三批已完成：

- Treasury 2Y / 10Y / 30Y 使用官方 CSV，并保留上一年度历史以支持 YTD / 1Y / 52W；
- FRED core 已覆盖 DFF、SOFR、10Y real yield、10Y breakeven、CPI、PCE、UNRATE、M2、WALCL、TGA、RRP；
- Net Dollar Liquidity 按 `WALCL - WDTGAL - RRPONTSYD × 1000`、同日对齐派生；
- VIX 使用 FRED/Cboe 分发；DXY、USDCNH、TLT、HYG 使用已批准的 Yahoo Chart 两年历史并标记 public-web / no-SLA 权利状态；
- `platform-data` commits：`774dccacebbd6f1fdca02f47071c0f74dc9fe07b`、`02bdfef35f803ef18e1f379598ba85abf001383c`、`183e99db29e44d7b6a9e490840b430e23c41f537`；
- workflow run `33596176092`：`success`；应用 commits `cca0a46685f86dc17271f9d46216646fa0ada6f1`、`482c636fca46833d6ab0a77ea17df922c2f457ea` 已启用全部 15 行。
- 第三批数据 commit `997adb4871bbfbd3d5c089c8761344433bd0e77c`、应用 commit `913d7df85e88bd3d2881c37a8750da3b3562df0d` 将覆盖扩大到 20 行。

Market Detail 尚未完成中国国债行；MOVE / DSPX 按 Source Map 保持 `not_configured`，不抓 TradingView。

### M2 — Macro V1 专题模块进展（2026-09-02）

- Growth：Real GDP YoY、Industrial Production YoY、Initial Claims 4W MA、CFNAI、CFNAIMA3；
- Inflation：CPI / Core CPI / PCE / Core PCE YoY、PPI YoY、5Y / 10Y Breakeven、5Y5Y Forward；
- Rates：Fed Target Lower / Upper、IORB、ON RRP Award、EFFR、SOFR；
- Risk Appetite：US HY OAS、HYG/LQD exact-date adjusted-close ratio；
- Global M2：五区官方/强校验广义货币、共同月份、ECB 同日交叉汇率月均、USD 总量与 YoY；132 个月端到端刷新通过，最新共同月份 2026-07；
- Market Expectations 继续复用已有白名单 Polymarket 面板；
- 聚合合约按规格窗口裁剪，并对日频展示序列周度抽样；完整 canonical history 保留在单序列文件中。

数据 commits：`c62dbb299efaa1dcc21d95bd26612be262535d7e`、`34cb72f7d28539ca25360234e175c654ee418106`、`36ba32b78d8ce037dc9c75d2bfe0f00dd97fbbc6`、`9ce61a1f29d781dfa015085a94771e7405014fec`。应用 commits：`e294e75398005b3efa040f575e3a0ff37954278e`、`ecbb20a9463fd0da237566eee3bdf4a4668182cb`、`88e94bd53f6a51b02b2cef9a2cb1a83ef5d4bf11`。`platform-data` 17 tests、API targeted tests、Ruff、Pyright、前端 type check 与 production build 已通过。

中国国债 2Y / 10Y / 30Y 已使用财政部—中国国债收益率曲线官方 `historyQuery` 精确字段 `twoYear / tenYear / thirtyYear` 接入。2026-09-01 实测分别为 1.24% / 1.68% / 2.14%，Market Detail 扩展至 23 行；远端数据 commit `5dac2e68c7664824e0dc8423531f9819f5307bfc`，增量刷新修复 `d5fc17f6248baaffcb1878cadfd9043542047b9f`。

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

DONE（2026-09-02）：

- Native / Link 边界与 Source / freshness 元数据复核通过；MOVE / DSPX 保持 `not_configured`；
- 中国债券旧静态样例在 Native API 返回前已统一清空为不可用，不再短暂泄漏假值；
- `platform-data` 21 tests、目标 API tests、Ruff、前端 type check、targeted ESLint 与 5683-module production build 通过；
- Global M2 API 实测返回 6 条 level/component series 与 1 条 YoY；ChinaBond API 实测返回 23 行母表和三条官方曲线；
- 应用 commits `ee8dd4d0`、`97eff694`，文档 commit `4f04349d`；数据 workflow runs `33601155026`、`33601543904` 成功，后者同时验证并发生成数据 push 的 rebase 修复。

---

## 11. Commodity V1 实施进度

### C1 — Native Commodity Core

- EIA crude / Cushing / gasoline / distillate；
- CFTC Gold / Silver / Copper / WTI / NatGas positioning。【DONE】

CFTC 已使用官方 PRE Disaggregated Futures Only 数据集，按 Contract Market Code 显式绑定五个品种，发布 Managed Money Net、Producer/Merchant Net 与滚动 260 周 Managed Money 历史分位，共 15 条 canonical series。数据 commits `7dc7646`、`d01e038`、CI 修复 `c771318`；应用/API commit `fac747c2`；workflow runs `33603224576`、`33604442977` success，后者验证完整 dashboard 路径触发。

EIA Native 已完成：工程 commit `4a317da`，真实数据 commit `a0e42a8`，应用图表 commit `8ec3ce7e`。四条官方 series identity、API v2 provider、canonical pipeline、CLI、Commodity dashboard groups、周三/周六条件式 CI 与密钥不落盘测试均已验收。workflow run `33631637867` success，EIA refresh step 实际执行；API 返回两组四序列。最新观测为 2026-08-21，按 10 天阈值正确标记 `stale`，未 forward-fill。

2026-09-03 商品页补充 MacroMicro 二级参考入口：仅挂接与现有卡片口径明确对应的黄金 ETF、央行黄金、黄金利率关系、CFTC 持仓、EIA 库存、原油期限结构/波动率及 Brent-WTI 价差页面；官方或一手来源继续作为“原始网页”，MacroMicro 不替代数据权威来源。

2026-09-03 市场明细纠偏：商品 14 行与加密已接通 13 行的 90 日 sparkline 改由实时 Yahoo Chart 日线生成；所有静态样例 sparkline 在渲染前清空，暂无可靠公开历史的加密总市值/市占率行明确显示“—”。黄金 ETF 四张卡片已核验并改挂 MacroMicro 具体周度、月度、GLD 流量及持仓页面；补充工具中的“黄金与全球 M2”“全球央行净购金”“Owner 黄金复盘模板”已按 Owner 要求移除。

Owner 随后确认将 Chrome 三个研究标签组全部接入：商品页新增“黄金与商品补充研究工具”13 个入口；加密页新增 ETF/稳定币/财库公司 7 个、杠杆/清算/期权 8 个、链上/周期/研究 6 个入口。新增卡片采用轻量外链组件，不加载第三方 iframe、不共享浏览器账号，且既有图表和默认折叠工具目录保持不变。

### C2 — Existing Gold Modules 去假数据

- WGC ETF Flow → External Link；
- SPDR → External Link；
- Central Bank Gold → IMF/WGC External Link；
- rights-clear macro driver → Native/Embed；
- GVZ 保留既有展示入口。

【DONE】原有 6 张黄金 ETF / SPDR / 央行储备卡片与 Section 顺序保持不变，旧静态快照已退出渲染，统一显示精确官方 External Link 与 `permission_required` 状态。

### C3 — Commodity Market Detail

【OWNER CORRECTION / 2026-09-03】Macro、Commodity、Crypto 三个市场明细表必须保留原有完整行、收益率、技术信号、sparkline 与轮动热图，Native 数据只覆盖已接通字段，不得以数据治理名义删减既有页面信息。未接入字段明确标为历史参考，不宣称实时；后续按逐行 source audit 慢慢替换为本地数据库数据。

【OWNER CONFIRMED / 2026-09-03】宏观页一级阅读顺序调整为：1 宏观市场明细、2 流动性、3 利率、4 经济、5 通胀、6 风险偏好。Global M2 Proxy、美元净流动性和美联储资产负债结构合并为流动性层，Global M2 YoY 已删除；利率层补齐美债期限走势、短期利率走廊、CME FedWatch 与 Polymarket 利率路径。通胀、经济、风险偏好增加交易工具母表中的关键领先指标，未采集来源明确保留为原始网页入口。

【OWNER CONFIRMED / 2026-09-03】三个研究子页的工具目录默认折叠、点击展开；商品与加密同步宏观的阅读规则，市场明细置于第一屏，主图及资金/结构专题随后。三个市场明细的 sparkline 统一为 90 日；前端和 API 合约优先使用 `spark90d`，同时兼容既有 `spark30d` 数据，以避免本地历史快照中断。

Owner 指定的 6 套 TradingView 研究布局已按语义接入对应卡片的“TradingView 模板”入口，同时保留各卡片原有官方/方法论来源：流动性、美联储负债结构、美债利率市场、美元短期利率监控、美国经济、VIX 期限结构。对外可访问性仍取决于 TradingView 逐布局共享权限，不共享账号登录态。

宏观研究入口继续按语义收拢：`美元流动性大全`归入美元净流动性卡片；金十美国经济数据、MacroMicro 美国宏观与中国宏观归入经济层的增长与生产卡片。所有入口均为新标签页跳转，不复刻第三方页面或依赖 Owner 登录态。

### C4 — Term Structure

- WTI → CME link；
- Brent → ICE link；
- LME complex curve → link；
- 中国公开期货结构仅在 rights-clear 时 Native。

【DONE】WTI / Brent / LME Copper 已增加精确官方 External Link 卡片，不复制受限期限结构数据。

### C5 — Inventory

- EIA Native；
- CME/LME受限库存 Link；
- SHFE/INE rights-clear 数据按需 Native。

【DONE】CME delivery / stocks 与 LME warehouse / stocks 已增加官方 External Link；EIA crude / Cushing / gasoline / distillate 已 Native。

### C6 — CFTC Positioning

核心五品种 Native。

### C7 — Cross-Market Spreads

受限 commercial legs 默认 Link。

【DONE】Copper cross-market 与 Brent-WTI 均按受限 leg 路由至官方入口，不在本地计算未经许可的价差历史。

### C8 — Volatility

- GVZ existing；
- OVX Embed / Link；
- CVOL Link。

【DONE】GVZ / OVX 使用 Cboe 官方入口，CVOL 使用 CME 官方入口；旧本地 SPDR gold proxy 与静态 GVZ 对比不再渲染。

### C9 — Commodity QA

DONE（2026-09-02）：

- 未新增农产品；旧商品母表、黄金 ETF / SPDR / 央行储备及 GVZ 对比静态值均退出渲染；
- Native / External Link、周频频率、10 天 freshness 与 `stale` 状态正确；
- `platform-data` 28 tests、目标 Ruff、API provider 2 tests、目标 Pyright、前端 type check、ESLint、布局守护与 5681-module production build 通过；
- 完整 API Pyright 的 2 个既存 Macro `float → Decimal` 错误不属于 Commodity 变更，Commodity provider 单独为 0 error；
- 数据 commits `7dc7646`、`d01e038`、`4a317da`、`a0e42a8`；应用 commits `fac747c2`、`eebbde6b`、`4ff5b0e7`、`8ec3ce7e`；真实 workflow `33631637867` success。

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

> **Unified QA + Offline Acceptance**

已验证实现：

- `platform-data` commit `1707668`：Binance BTC / ETH spot、funding、OI、perpetual basis 共 8 条 canonical series 与 dashboard；
- 应用 commits `9fa3d25b`、`3dc7d676`、`b5ffe90f`：API、Native 图表、Crypto Market Detail fail-closed、ETF / Treasury / derivatives / stablecoin / options / on-chain 精确外链及静态假数据退出守卫；
- 本地真实刷新：8 条 series ready；spot 仅使用已收盘 UTC 日线，derivatives 明确为 Binance Venue / not Aggregate；
- QA：数据仓库 31 tests passed；API provider tests 2 passed、target Ruff / Pyright 通过；frontend ESLint、typecheck、layout verifier、production build（5677 modules）通过；
- Owner 已于 2026-09-03 确认统一迁移至 `D:\自营数据库`，GitHub 仅保留代码；数据 commit `ccc69cc`，应用 commit `05c37323`；
- 本地主库 `D:\自营数据库\hedge-board\hedge_board.duckdb` 已验收 82 条 series / 78,846 observations；Macro 55 ready、Crypto 8 ready，Commodity 15 ready + 4 stale（按真实 EIA observation date）；
- Windows 计划任务 `HedgeBoard-LocalData-Refresh` 已安装，每日 00:15 / 06:15 / 12:15 / 18:15 执行，GitHub 三个 workflow 仅运行代码测试且 runs `33658157466`、`33658157488`、`33658157326` 均为 success；
- Binance Futures 系统 DNS 污染通过限定主机的 Cloudflare DoH + TLS 校验 fallback 解决；不修改系统 DNS，不写 hosts；
- GitHub 中 EIA secret 已移除；本地用户环境保留刷新凭据。
- Unified QA 首轮：Hedge Board 专项 12 tests、Pyright 0 errors、frontend ESLint / typecheck / layout verifier、production build 均通过；全仓 API 套件 615 项中 592 passed、23 failed，失败均位于既有版本工具、上下文预算、数据库 seed、交易执行与 venue reconciliation 边界，未触及本次 Hedge Board 本地数据读取文件。不得将这些失败记为本阶段通过，最终验收保留为 IN PROGRESS；
- `platform-data` 仓库中历史已提交的数据快照仍存在。受根目录安全规则限制，AI 不批量删除；当前已停止一切 GitHub 数据刷新与提交，Owner 已确认后续手动批量删除旧快照并自行提交。
- 已使用隔离 E2E 数据库完成认证浏览器 QA：Macro / Commodity / Crypto 在 normal 与 blocked 两种网络模拟下共 6 组 chart/detail flow 全部通过；本地 API 实际请求 `/research/macro/dashboard-v1`、`/research/commodity/dashboard-v1`、`/research/crypto/dashboard-v1`、`/research/market-detail/macro` 均返回 HTTP 200。测试账户环境变量和临时数据库已清理；
- Owner 线下页面验收使用独立 `127.0.0.1:14373` Web 与 `127.0.0.1:18000` API，账号库隔离且 Live Write 关闭，数据只读 `D:\自营数据库\hedge-board`；默认平台 `4373/8000` 不受占用。启动与关闭入口分别为仓库根目录 `启动HedgeBoard验收站.bat`、`关闭HedgeBoard验收站.bat`；
- 当前最终 Gate 只保留 Owner 线下页面验收以及是否合并应用分支。AI 未合并 `Platform_Experiment/main`。
- Owner 线下反馈后已修正验收范围：恢复三个市场明细表原有信息密度与轮动热图；所有图表（Market Detail 表除外）右上角统一提供“原始网页 ↗”，当前无法完整 Native 展示的卡片以原网页作为初期可用入口，后续再逐图升级为正式采集与本地主库图表。

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
