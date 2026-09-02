# 对冲基金看板优化总方案（Master Plan）

> 状态：Planning Baseline v1.4 / Phase F FROZEN / Phase 0 DONE / Phase 1 DONE / Macro V1 IN PROGRESS  
> 项目总览：`docs/hedge-board/HEDGE_BOARD_PROJECT_PLAN_AND_PROGRESS.md`  
> 适用分支：`feature/hedge-board-online-optimization`  
> 用途：作为 Hedge Board 后续产品、数据、工程与验收的最高约束来源。  
> 原则：总文件只维护全局规则与当前状态；完整项目计划与进度进入 `HEDGE_BOARD_PROJECT_PLAN_AND_PROGRESS.md`；模块产品细节进入 `specs/*_V1_SPEC.md`；数据源进入 `*_DATA_SOURCE_MAP.md`；可行性结论进入 `HEDGE_BOARD_PHASE_F_AUDIT.md`；工程顺序进入 `HEDGE_BOARD_IMPLEMENTATION_PLAN.md`。

---

## 1. 产品定位【冻结】

Hedge Board 定位为：

> **面向日常交易与研究的跨资产扫盘、数据集中展示和盘后复盘工具。**

主要解决：

- 将分散在网站、TradingView、数据工具中的核心市场数据集中展示；
- 快速查看当前值、历史走势、横截面与关键市场结构；
- 支持日常扫盘与盘后复盘；
- 为未来信息整理与金融 AI 分析提供标准化数据基础。

当前不承担：

- 自动生成投资观点；
- 自动市场状态判断；
- 自动宏观传导；
- 组合暴露分析；
- 买卖 / 仓位 / 风险建议；
- 自动交易。

---

## 2. 一级结构与当前范围【冻结】

现有一级结构保持：

1. 宏观
2. 商品
3. 加密
4. 美股
5. A股
6. 全球
7. 交易工具

当前 active V1：

- Macro；
- Commodity；
- Crypto。

当前 Deferred：

- US Equity；
- A-Share；
- Global；
- Trading Tools。

Deferred 含义：不新增开发、不重构、不顺手真实化。

但 Trading Tools 有一个特殊角色：

> **继续 Deferred，但允许被只读作为参考网站目录。**

不处理 Trading Tools 元数据，不改其 UI，不新建第二套书签库。

---

## 3. UI 最高原则【冻结】

### Additive Only

除非用户明确批准，不得：

- 删除现有内容；
- 移动现有模块；
- 改变原顺序；
- 重命名现有模块；
- 用新模块替换旧模块；
- 重构整体页面；
- 改导航；
- 因“清理 / 统一 / 去硬编码”改变视觉设计。

新增内容必须继承现有 UI 语言。

### 默认冻结组件

除非最小接口兼容，不主动重构：

- `HedgeResearchModule.vue`
- `MarketTerminalPage.vue`
- `TerminalDetailPanel.vue`
- `HedgeBoardSubnav.vue`
- `hedgeBoard.less`
- `strategy-theme.less`

### 硬编码定义

- 视觉组件硬编码：保留；
- 页面配置硬编码：当前允许；
- 金融数据硬编码：逐步退出。

---

## 4. 最终数据交付模式【冻结】

Phase F 已确认不追求“所有数据都本地化”。

每个指标 / 子模块最终只选以下模式：

### `NATIVE`

适合长期、低维护、rights 清晰的数据：

```text
Source
→ platform-data
→ canonical data
→ platform-api
→ existing UI / additive chart
```

### `EXTERNAL_LINK`

如果数据：

- 免费链不稳定；
- 商业许可复杂；
- 维护成本高；
- 原站已经提供成熟专业模块；

则使用：

```text
Trading Tools / Official Website exact URL
→ External Reference Button
→ new tab
```

External Link 是正式产品能力，不是失败占位。

### `OFFICIAL_EMBED`

仅当官方明确支持、体验明显优于外链且不会破坏当前 UI 时使用。

### `NOT_CONFIGURED`

仅当既无合理 Native，也没有合适参考入口时使用。

---

## 5. 数据架构【冻结】

### Native

```text
Official / approved public source
        ↓
platform-data
  fetch / normalize / derive / validate / LKG
        ↓
canonical JSON + partitioned history
        ↓
platform-api
        ↓
Platform Web
```

### External Link

```text
Trading Tools existing catalog / official site
        ↓
read-only exact URL
        ↓
Platform Web button
```

前端原则上不直接连接多个外部金融 API。

TradingView 主要用于图表展示 / 大图入口，不作为通用抓取源。

---

## 6. `platform-data` 定位【冻结】

数据仓库：`wuxingyuenan5-lgtm/platform-data`

负责：

- Provider adapter；
- 抓取；
- canonical identity；
- 单位 / 时区 / 交易日标准化；
- 派生指标；
- 历史序列；
- LKG；
- stale / degraded / error；
- quality flags；
- GitHub Actions；
- versioned output。

它是：

> **版本化数据生产与分发仓库**

不是：

> tick / 秒级 / 高频实时数据库。

V1 不提前建设传统数据库。

Phase 0 已基于现有仓库完成共享 runtime 基线，包括 retry、freshness、material-change/no-change 处理，并以 Treasury 10Y 真实数据链通过 GitHub Actions 验证。

---

## 7. 存储基线【冻结】

### 最新数据

JSON：

```text
public/v1/<module>/manifest.json
public/v1/<module>/dashboard.json
public/v1/<module>/market-detail.json
public/v1/<module>/series/*.json
```

### 长历史

- 小型：CSV；
- 较大 / 多列：Parquet；
- 按年 / 月稳定分区。

避免：

- 巨型 JSON 每天整体重写；
- 海量小文件；
- SQLite / DuckDB 二进制文件频繁 commit。

Crypto Funding / OI / Basis 只存页面需要的采样 / 聚合历史，不存全市场分钟 raw feed。

---

## 8. 通用数据合同【冻结】

Native series 尽可能包含：

- `series_id`
- `label`
- `value`
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
- `delivery_mode`

状态：

- `ready`
- `partial`
- `degraded`
- `stale`
- `no_data`
- `not_configured`
- `error`

规则：

- 0 ≠ 无数据；
- [] ≠ Provider failure；
- stale 不得伪装 fresh；
- fallback 必须可见；
- 派生指标保留方法版本；
- fetch failure 不覆盖 LKG。

---

## 9. Market Detail【冻结方向】

保留现有视觉与列结构，逐步真实化：

- latest / close；
- 1D；
- 1W；
- 1M；
- QTD；
- YTD；
- 1Y；
- 52W High；
- 30D Sparkline。

30D继续用现有 SVG。

禁止 random / placeholder spark。

不同资产保留各自交易日历；Crypto 7×24 与 US ETF / equities 不强行统一。

技术箭头 / 技术状态算法暂不扩展。

---

## 10. 当前模块状态【冻结】

### Macro V1

权威文档：

- `specs/MACRO_V1_SPEC.md`
- `specs/MACRO_DATA_SOURCE_MAP.md`

状态：Product Scope Frozen / Feasibility Frozen。

Phase F 结论：

- BLS / BEA / Fed / Treasury / NY Fed / ECB / BOJ / BoE 等核心数据 Native；
- China M2 = AKShare adapter + PBOC mandatory validation；
- HY OAS External Link；
- HYG/LQD Official Embed；
- Polymarket External Link / permission required；
- CME FedWatch External Link。

### Commodity V1

权威文档：

- `specs/COMMODITY_V1_SPEC.md`
- `specs/COMMODITY_DATA_SOURCE_MAP.md`

状态：Product Scope Frozen / Feasibility Frozen。

Phase F 结论：

- EIA / CFTC Native；
- WGC / SPDR / CME / ICE / LME / Cboe index 等商业或许可复杂数据采用 Embed / External Link；
- Central Bank Gold V1 采用 IMF/WGC External Link；
- 不纳入农产品。

### Crypto V1

权威文档：

- `specs/CRYPTO_V1_SPEC.md`
- `specs/CRYPTO_DATA_SOURCE_MAP.md`

状态：Product Scope Frozen / Feasibility Frozen。

Phase F 结论：

- Binance 为 V1 第一 Native Venue；
- BTC Funding / OI / Basis 与 ETH Funding 已 smoke test；
- Coinglass / Bybit / OKX / Deribit 作为多 Venue / advanced derivatives External Link；
- Farside ETF Flow External Link；
- BitcoinTreasuries External Link；
- DefiLlama Stablecoin External Link；
- Checkonchain / Glassnode / CryptoQuant / Arkham 等承担复杂 On-chain External Link。

---

## 11. Trading Tools 后续关系【冻结】

Trading Tools 本身当前不开发。

Phase F / active V1 可以读取它的参考网址。

当 Macro / Commodity / Crypto 子页完成后：

- Native数据直接在子页展示；
- 不适合 Native 的项目使用精准 External Reference Button；
- 子页过去整块重复展示 Trading Tools 分类的模块不再需要。

当前不删除该旧模块；待对应 V1 完成并线下验收后处理。

---

## 12. 权威文档索引【冻结】

### 总体

- `HEDGE_BOARD_PROJECT_PLAN_AND_PROGRESS.md` — 完整项目计划、管理总览和进度表；
- `HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md` — 本文件，最高产品 / Change Control 约束；
- `HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`；
- `HEDGE_BOARD_PHASE_F_AUDIT.md`；
- `HEDGE_BOARD_IMPLEMENTATION_PLAN.md`。

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

## 13. 当前执行状态【Current】

```text
Product Scope Design       DONE
Data Source Baselines      DONE
Data Feasibility Phase F   DONE / FROZEN
Engineering Phase 0        DONE
Implementation Plan        v1.2 / Macro V1 Gate
Engineering Phase 1        DONE
```

当前统一进度口径：

- **规划准备度：100%**；
- **工程主阶段：2 / 6 = 33.3%**；
- 工程主阶段口径：Phase 0、Phase 1、Macro V1、Commodity V1、Crypto V1、Unified QA / Offline Acceptance；
- 该比例只用于管理 Gate，不代表各阶段实际工作量等权，也不用于推算工期。

Phase 0 真实验收：

- `platform-data` 共享 runtime helper 已落库；
- Treasury provider / pipeline 已改为使用共享 retry / freshness / material-change 机制；
- 新增共享 runtime tests；
- GitHub Actions `macro-data` run `33295430507` 对 commit `2a1428ccfc02b9f096f7f3397eb9183f972acdc2` 结论为 `success`；
- Treasury 10Y 已存在真实 `Provider → canonical JSON → CSV history → workflow` 链路。

Phase 1 真实验收：

- `platform-data` commit `9c5eb80f056bcbf2896fd85d321abb2c67bde01c`；
- `macro-data` workflow run `33588457408`：`success`；日更后的动态一致性测试 commit `8203a727923215bec573ced2db11858d3fd2c936` / run `33589428430` 再次为 `success`；
- 应用 commit `14fda8c4b1cf79013ca38396753f197ff17d7806`；
- 已形成 `canonical Treasury history → shared metrics → platform-api → macro-us10y existing row → existing SVG sparkline` 的真实纵切片；
- 最新远端验收 as-of `2026-09-01`，美国 10Y `4.79%`，1D `+4bp`；缺历史窗口显式为 `—`。

当前阶段：

> `Macro V1 Engineering — IN PROGRESS`

Native core 已真实化 20 个既有 Macro Market Detail 行。Treasury curve 数据 commit `774dccacebbd6f1fdca02f47071c0f74dc9fe07b`，FRED core commit `183e99db29e44d7b6a9e490840b430e23c41f537`，VIX / DXY / USDCNH / TLT / HYG commit `997adb4871bbfbd3d5c089c8761344433bd0e77c`；workflow runs `33596176092`、`33596701735` 均为 `success`。该进度不代表 Macro V1 完成；专题模块及其余市场行仍按冻结范围继续。

Macro 专题模块已完成 Growth、Inflation、Short-End Rate Corridor 和 Risk Appetite 的真实数据/API/additive SVG 图表；既有 Polymarket 白名单面板继续作为 Market Expectations。数据 commits `c62dbb299efaa1dcc21d95bd26612be262535d7e`、`9ce61a1f29d781dfa015085a94771e7405014fec`；应用 commits `e294e75398005b3efa040f575e3a0ff37954278e`、`ecbb20a9463fd0da237566eee3bdf4a4668182cb`。当前 Macro V1 主要剩余 Global M2 与中国国债 mapping。

完整阶段状态、模块进度、风险和后续路线以 `HEDGE_BOARD_PROJECT_PLAN_AND_PROGRESS.md` 为管理总览。

---

## 14. Change Control【冻结】

### GREEN

在已开启 Phase 内：

- approved Native Provider；
- canonical data；
- API；
- data quality；
- fallback / LKG；
- approved External Link；
- tests；
- bug fixes。

### YELLOW

必须先讨论：

- 改现有 Section 顺序；
- 换主要图表形态；
- 修改指标定义；
- 新增二级主题；
- 显著改信息密度；
- 改公共视觉组件；
- External Link 升级 Native 且涉及新 rights；
- 重新开启 Deferred 模块。

### RED

未经明确授权不得：

- 删除 / 移动 / 替换现有设计；
- 整体 UI 重构；
- 改一级分类或导航；
- 修改 Deferred 模块；
- 绕 CAPTCHA / WAF / 登录 / CSP / 权限；
- 修改 `Platform_Experiment/main`；
- 未授权合并；
- 把看板改成 AI 自动投资决策系统。

说明：`platform-data/main` 是当前数据生产仓库的工作分支，Phase 0 已在该仓库产生真实 commit；禁止修改 main 的约束继续专指 `Platform_Experiment/main`。

---

## 15. GitHub 执行 Agent 规则【冻结】

后续 Agent 必须：

1. 读取 Project Plan & Progress；
2. 读取 Master Plan；
3. 读取 Phase F Audit；
4. 读取 Implementation Plan；
5. 读取当前模块 Spec / Source Map；
6. 只执行用户明确开启的 Phase；
7. 遵守 Additive Only；
8. 不用 README / schema 冒充业务 Phase 完成；
9. Native Phase 必须形成真实数据链；
10. 无法验证标 `not_verified`；
11. 不伪造 build / test / E2E；
12. External Link 不得重新变成未经批准的抓取链；
13. Phase 0 已完成，后续不得以“补基础设施”为名重复重构共享层。

---

## 16. 线下验收【冻结】

Platform Web / API 开发全部在：

`feature/hedge-board-online-optimization`

不直接改 `Platform_Experiment/main`。

最终由用户线下：

- pull；
- build；
- test；
- browser QA；
- 页面人工验收；
- 决定修复 / 合并。

网页 Agent 自报完成不等于最终发布完成。
