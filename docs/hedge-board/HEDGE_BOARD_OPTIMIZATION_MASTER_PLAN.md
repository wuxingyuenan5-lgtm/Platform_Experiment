# 对冲基金看板优化总方案（Master Plan）

> 状态：Current Planning Baseline / v0.8  
> 适用分支：`feature/hedge-board-online-optimization`  
> 用途：作为对冲基金看板后续产品讨论、数据源设计、工程实施与线下验收的最高约束来源。  
> 原则：总文件只冻结全局规则与当前路线；各一级看板产品细节进入 `docs/hedge-board/specs/`；数据可行性与长期维护进入 `docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`；工程顺序进入 `docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`。任何执行 Agent 不得自行改变已冻结方向。

---

## 1. 产品定位【冻结】

对冲基金看板定位为：

**面向日常交易与研究的跨资产扫盘、数据集中展示和盘后复盘工具。**

主要解决：

- 将分散在多个网站、TradingView、数据工具中的核心市场数据集中展示；
- 快速查看当前值、历史走势、横截面对比与关键市场结构；
- 支持日常盘中扫盘和盘后复盘；
- 为后续信息整理与金融 AI 分析模块提供可靠、标准化的数据与图表基础。

当前阶段不承担：

- 自动生成投资观点；
- 市场状态自动判定；
- 自动宏观传导分析；
- 组合暴露分析；
- 买卖、仓位或风险建议；
- 自动交易。

---

## 2. 一级分类【冻结】

保持现有一级结构，不重新设计：

1. 宏观
2. 商品
3. 加密
4. 美股
5. A股
6. 全球
7. 交易工具

一级分类本身不因当前开发优先级变化而删除或调整。

---

## 3. 当前路线与模块状态【冻结】

### 3.1 宏观看板

状态：**Product Scope Frozen v1.0 / Data Source Baseline Ready / Implementation OPEN**

权威文档：

- `docs/hedge-board/specs/MACRO_V1_SPEC.md`
- `docs/hedge-board/specs/MACRO_DATA_SOURCE_MAP.md`

当前决定：

- 产品范围已冻结；
- Growth、Inflation、Rates、Global M2、Risk Appetite、Polymarket Market Expectations 等范围已确定；
- Data Source Map 已有初版；
- 当前不进入工程实施；
- 实施前对 OPEN / `not_configured` 数据源重新做 live validation。

### 3.2 商品看板

状态：**Product Scope Frozen v1.0 / Data Source Baseline Ready / Implementation OPEN**

权威文档：

- `docs/hedge-board/specs/COMMODITY_V1_SPEC.md`
- `docs/hedge-board/specs/COMMODITY_DATA_SOURCE_MAP.md`

当前决定：

- 产品范围已冻结；
- 不纳入农产品；
- 保留现有黄金 ETF / SPDR / 央行购金 / 黄金宏观驱动等核心内容；
- 新增期限结构、库存、CFTC、跨市场价差与精简商品波动率；
- Data Source Map 已建立免费数据源基线；
- EIA / CFTC / WGC / Cboe / CME 等官方免费源优先；
- SHFE 等中国数据可在口径稳定时复用 AKShare 并记录 upstream；
- 当前期限结构、LME 等无法确认稳定免费链路的项目保留 OPEN / `not_configured` gate；
- 当前不进入工程实施。

### 3.3 加密看板

状态：**Product Scope Frozen v1.0 / Data Source Baseline Ready / Implementation OPEN**

权威文档：

- `docs/hedge-board/specs/CRYPTO_V1_SPEC.md`
- `docs/hedge-board/specs/CRYPTO_DATA_SOURCE_MAP.md`

当前决定：

- 保留 BTC 主图、DVOL、Crypto Market Detail、BTC ETF Flow、Bitcoin Treasuries Flow 等既有内容；
- 新增 Institutional Flows；
- 新增 Derivatives & Leverage；
- 新增 Options & Volatility；
- 新增 Stablecoin Liquidity；
- On-chain Data 纳入 V1，并收敛为 MVRV、NUPL、SOPR、Realized Price/Cap、Exchange Balance/Netflow、LTH/STH 等主流核心；
- Funding / OI / Basis 同时支持 Aggregate 与 Venue 视角；
- Breadth / Rotation 优先利用现有 Market Detail；
- Binance / Deribit 等官方公共接口作为衍生品与期权核心候选源；
- Stablecoin / ETF / Treasury / On-chain 允许使用免费聚合或 Community 数据，但必须记录 provenance、方法学与 rights_scope；
- 无可靠免费源时保持 `not_configured`；
- 当前不进入工程实施。

### 3.4 暂缓开发模块【Deferred】

以下一级看板当前统一暂停新增开发：

- 美股；
- A股；
- 全球；
- 交易工具。

Deferred 的含义：

- 不删除现有页面；
- 不修改现有设计；
- 不新增 Phase；
- 不新增数据源工程；
- 不顺手真实化或重构；
- 不因公共组件开发而主动改变这些页面；
- 只有用户明确重新开启，才恢复产品讨论或工程开发。

---

## 4. UI 与现有设计保护原则【最高全局约束 / 冻结】

### 4.1 Additive Only

**默认只做增量添加和数据真实化，不允许擅自改动用户原有设计。**

除非用户明确提出，任何 Agent 不得：

- 删除现有内容；
- 移动现有内容；
- 改变现有顺序；
- 重命名现有模块；
- 用新模块替换现有模块；
- 重构现有页面；
- 改变导航；
- 改变整体视觉语言；
- 因“统一”“重构”“清理代码”而改变页面呈现。

### 4.2 UI 一致性

所有新增内容必须与现有平台保持一致，包括：

- 页面结构；
- 导航；
- 卡片；
- 表格；
- 字体；
- 颜色；
- 间距；
- 圆角；
- 阴影；
- 图表容器；
- Market Terminal 的整体视觉和交互方式。

### 4.3 默认冻结视觉组件

除非只是为接口兼容进行最小改动，不主动重构：

- `HedgeResearchModule.vue`
- `MarketTerminalPage.vue`
- `TerminalDetailPanel.vue`
- `HedgeBoardSubnav.vue`
- `hedgeBoard.less`
- `strategy-theme.less`

### 4.4 硬编码处理

必须区分：

- **视觉组件硬编码**：保留；
- **页面配置硬编码**：当前允许保留；
- **金融数据硬编码**：逐步替换为真实数据链。

“去硬编码”当前只针对金融数据和数据状态，不等于重写视觉组件。

---

## 5. 数据架构【冻结】

长期统一链路：

```text
External Source
    ↓
Data Feasibility Gate
    ↓
platform-data
    ↓
fetch / normalize / derive / validate / store
    ↓
versioned canonical data / JSON + partitioned history
    ↓
platform-api
    ↓
Research API
    ↓
Platform Web
    ↓
existing chart / table components
```

### 5.1 `platform-data`

数据仓库：`wuxingyuenan5-lgtm/platform-data`

长期负责：

- Provider 接入；
- 抓取；
- 标准化；
- 派生指标；
- 历史数据；
- GitHub Actions / 定时更新；
- 数据质量；
- Last Known Good；
- stale / degraded / error 状态；
- 标准化、版本化输出。

允许为了稳定完成数据抓取、存储、更新全流程而调整 `platform-data` 目录、脚本、配置和工作流，但不得伪造数据、绕过访问控制或未经确认改变金融指标定义。

V1 中 `platform-data` 定位为**版本化数据生产与分发仓库**，不是分钟级 / tick 高频实时数据库。低频与日频历史可文件化保存；Crypto 高频数据只保留页面需要的采样、聚合和最新 snapshot。未来若真实需要分钟级长期历史，再在 canonical contract 不变的前提下升级专业存储。

### 5.2 `Platform_Experiment`

负责：

- 消费 canonical data；
- API 缓存和状态处理；
- 前端展示；
- 页面交互。

前端原则上不直接连接多个外部金融数据源。

---

## 6. 数据源策略【冻结】

### 6.1 免费优先

当前 Hedge Board 数据工程只采用免费数据源 / 免费公开接口作为 V1 基础。

### 6.2 统一口径优先于统一 Provider

统一的是：

- canonical id；
- 字段；
- 单位；
- 时点；
- 计算方法；
- 状态语义；
- Primary / Fallback 规则。

不要求全部指标来自同一个 Provider。

### 6.3 AKShare 定位

AKShare 可作为重要统一接入层，尤其适合中国市场及已成熟封装的数据。

原则：

- AKShare 接口稳定、口径清晰时可优先复用；
- 官方免费 API 更稳定或 AKShare 上游陈旧时，直接使用官方源；
- 必须记录 AKShare 对应的 upstream source；
- AKShare 不是唯一 Source of Record。

### 6.4 Provider 优先级

```text
官方 Source of Record
    ↓
官方/权威分发层
    ↓
AKShare 等成熟统一接入层（适用时）
    ↓
稳定公开 Vendor / Community / Aggregator
    ↓
独立 Fallback
```

不得绕过 CAPTCHA、WAF、登录、权限或授权限制。

### 6.5 现成网站子模块复用【冻结】

网页上存在现成图表 / 子模块，不代表可直接搬入平台。

优先策略：

```text
官方 API
→ 自有 canonical data + 现有平台 UI 重画

官方 Embed / Widget
→ 仅作为展示层

公开但未文档化 endpoint
→ 只有稳定、合规且配 LKG 时作为 B-tier / fallback

只有网页 / JS 图表
→ 追溯 upstream source 后自行重画

CSP / X-Frame-Options / 登录 / WAF 限制
→ reference-only / not_configured
```

详细规则以 `HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md` 为准。

---

## 7. 通用数据合同【冻结】

所有金融序列和市场数据应尽可能包含：

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
- `rights_scope`（适用时）

统一状态：

- `ready`
- `partial`
- `degraded`
- `stale`
- `no_data`
- `not_configured`
- `error`

关键语义：

- `0` 不代表无数据；
- 空数组不代表抓取失败；
- Provider 失败不等于市场无数据；
- 旧数据不得静默伪装成最新；
- fallback 使用必须可见；
- 派生指标必须记录方法版本。

---

## 8. TradingView 角色【冻结】

TradingView 在本项目中主要负责：

- 图表展示；
- Widget；
- 用户查看大图和技术图表的交互入口。

TradingView 不作为通用市场数据抓取源。

项目自有数值、收益率、30 日曲线、历史序列等，由 `platform-data` 提供。

---

## 9. Market Detail 通用原则【冻结】

保留现有 Market Terminal 视觉和列结构，逐步把静态金融数据替换成真实数据。

适用模块进入实际开发后，优先真实化：

- latest / close；
- 1D；
- 1W；
- 1M；
- QTD；
- YTD；
- 1Y；
- 52W High；
- 30D Sparkline。

低频数据必须 frequency-aware；没有新 observation 时不得用 `0.00%` 冒充“没有变化”。

不同资产的交易日历、结算时点与报价时区必须保留，不允许为页面统一而静默混用。

技术状态列（1H、4H、日线、3日线、周线等）在统一算法未冻结前，不继续扩展假信号。

---

## 10. 30 日迷你曲线【冻结】

继续沿用现有 SVG Sparkline。

不在表格每行嵌入 TradingView Mini Chart。

```text
fake/static number[]
    ↓
canonical real history
    ↓
recent valid observations
    ↓
existing SVG sparkline
```

当前值、收益率和 Sparkline 应尽量来自同一 canonical series。

不要求所有行统一使用同一个 Provider。

---

## 11. 权威文档索引【冻结】

### 总体

- `docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`
- `docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`
- `docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`

### Macro

- `docs/hedge-board/specs/MACRO_V1_SPEC.md`
- `docs/hedge-board/specs/MACRO_DATA_SOURCE_MAP.md`

### Commodity

- `docs/hedge-board/specs/COMMODITY_V1_SPEC.md`
- `docs/hedge-board/specs/COMMODITY_DATA_SOURCE_MAP.md`

### Crypto

- `docs/hedge-board/specs/CRYPTO_V1_SPEC.md`
- `docs/hedge-board/specs/CRYPTO_DATA_SOURCE_MAP.md`

### US / A-Share / Global / Trading Tools

- 当前不创建新增 V1 Spec / Data Source Map；状态统一为 Deferred。

---

## 12. Data Feasibility & Implementation Plan【冻结为当前工程基线】

数据可行性与维护策略：

`docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`

统一实施计划：

`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`

实施前置顺序固定为：

```text
Phase F Data Feasibility & Website Module Audit
    ↓
Phase 0 Shared Data Foundation
    ↓
Phase 1 Shared Market Detail Data Layer
    ↓
Macro V1
    ↓
Commodity V1
    ↓
Crypto V1
    ↓
Hedge Board Phase 1 Offline Acceptance
```

Phase F 负责先证明：

- 数据真实可取；
- 免费条件可接受；
- 历史和更新频率满足产品需要；
- 网站子模块属于 API / Embed / Rebuild / Reference-only 哪一类；
- 数据适合什么存储格式；
- 长期维护风险可接受。

用户可以明确改变业务优先级；执行 Agent 不得自行重排。

当前状态：**Planning Ready / Engineering NOT STARTED**。

---

## 13. Change Control【冻结】

### GREEN：可直接执行

仅限当前明确开启的模块和已批准范围：

- 替换明确假数据；
- 已批准的数据源接入；
- API / Provider；
- 数据状态和质量；
- fallback；
- 测试；
- 已批准 Section 内的已批准指标；
- Bug 修复。

### YELLOW：必须先讨论

- 调整任何现有 Section 顺序；
- 更换主要图表形式；
- 修改指标定义或算法；
- 新增二级主题；
- 显著改变页面信息密度；
- 修改公共视觉组件；
- 重新开启 Deferred 模块；
- 改变已经冻结的总体 Phase 优先级；
- 在未通过 Phase F 的情况下强行使用高维护风险数据源。

### RED：无明确授权不得执行

- 删除、移动、替换现有设计；
- 重构 Hedge Board 整体 UI；
- 改变一级分类；
- 改导航；
- 修改 Deferred 模块；
- 将看板改造成 AI 投资决策系统；
- 修改 `main`；
- 未授权合并分支；
- 绕过 CAPTCHA / WAF / 登录 / CSP / 访问控制抓取第三方模块。

---

## 14. GitHub 执行原则【冻结】

后续执行 Agent 必须：

1. 先读取本 Master Plan；
2. 再读取 `HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`；
3. 再读取 `HEDGE_BOARD_IMPLEMENTATION_PLAN.md`；
4. 再读取当前模块 Spec / Data Source Map；
5. 只执行用户明确开启的 Phase；
6. 未完成 Phase F 前不得直接大规模实现业务页面；
7. 不自行重新设计产品；
8. 遵守 Additive Only；
9. 不得用 contract / schema / README 单独冒充业务 Phase 完成；
10. 端到端 Phase 以真实业务链路作为验收；
11. 无法验证时标记 `not_verified`，不得伪造；
12. 单一工具路径失败时先尝试合理替代路径；
13. Deferred 模块不得因顺手重构或公共组件修改而改变；
14. 当前仍属于规划 / 可行性审计阶段，未经用户明确“开始实施”不得自行进入大规模代码开发。

---

## 15. 线下验收原则【冻结】

所有实际开发先进入独立分支：

`feature/hedge-board-online-optimization`

不直接修改或合并 `main`。

最终由用户线下：

- pull 分支；
- 运行项目；
- 页面人工验收；
- 本地测试；
- 决定修复、继续或合并。

网页 Agent 自报“完成”不等于最终发布完成。

---

## 16. 当前计划状态【Current】

当前仍不进入工程实施。

第一阶段设计文档现为：

```text
Master Plan
    ↓
Module V1 Spec
    ↓
Data Source Map
    ↓
Data Feasibility & Maintenance
    ↓
Unified Implementation Plan
```

当前状态：

1. Macro V1：产品规格冻结 + Data Source Map baseline；
2. Commodity V1：产品规格冻结 + Data Source Map baseline；
3. Crypto V1：产品规格冻结 + Data Source Map baseline；
4. Data Feasibility & Maintenance：已建立；
5. Unified Implementation Plan：已更新为 Phase F 优先；
6. US / A-Share / Global / Trading Tools：Deferred。

当前下一步不是直接开发页面，而是：

> **Phase F — 对现有 Data Source Map 与用户已整理的网站 / 子模块做真实可行性审计。**

Phase F 完成并确认核心数据链可长期维护后，才进入 Phase 0。

---

## 17. 文档维护规则

本文件是当前分支上的 Hedge Board 最高权威计划文档。

- 用户明确确认的事项才可升级为冻结项；
- 子模块详细产品内容进入对应 `*_V1_SPEC.md`；
- 数据源细节进入对应 `*_DATA_SOURCE_MAP.md`；
- 跨模块数据可行性、网站子模块复用与存储维护进入 `HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`；
- 工程顺序与验收进入 `HEDGE_BOARD_IMPLEMENTATION_PLAN.md`；
- Deferred 状态只有用户明确提出时才能解除；
- 临时执行指令与本 Master Plan 冲突时，除非用户明确正在修改 Master Plan，否则以本文件为准。
