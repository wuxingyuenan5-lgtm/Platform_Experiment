# 对冲基金看板优化总方案（Master Plan）

> 状态：Discussion Baseline / Draft v0.1  
> 适用分支：`feature/hedge-board-online-optimization`  
> 用途：作为后续对冲基金看板优化讨论、Phase 拆分、GitHub 执行任务与验收的统一约束来源。  
> 原则：已确认事项写入“冻结项”；未确认事项进入“待商讨”，不得由执行 Agent 自行补完或改变产品方向。

---

## 1. 产品定位【冻结】

对冲基金看板定位为：

**面向日常交易与研究的跨资产扫盘、数据集中展示和盘后复盘工具。**

主要解决：

- 将分散在多个网站、TradingView、数据工具中的核心市场数据集中展示；
- 快速查看当前值、历史走势、横截面对比和关键市场结构；
- 支持日常盘中扫盘和盘后复盘；
- 为后续信息整理与金融 AI 分析模块提供可靠、标准化的数据和图表基础。

当前阶段不承担：

- 自动生成投资观点；
- 市场状态自动判定；
- 宏观传导链自动分析；
- 组合暴露分析；
- 买卖建议、仓位建议或风险建议；
- 自动交易。

---

## 2. 一级分类【冻结】

保持现有一级结构，不进行重新设计：

1. 宏观
2. 商品
3. 加密
4. 美股
5. A股
6. 全球
7. 交易工具

后续优化重点是各子页内部的数据、图表、更新与交互，不重新讨论一级资产分类，除非用户明确提出变更。

---

## 3. UI 与页面边界【冻结】

### 3.1 总原则

**不重构现有 UI，只做增量优化。**

默认保持：

- 页面结构；
- 现有导航；
- 卡片结构；
- 表格结构；
- 字体；
- 颜色；
- 间距；
- 圆角；
- 阴影；
- 图表容器；
- Market Terminal 的整体视觉与交互方式。

### 3.2 默认冻结组件

除非为接口兼容进行最小改动，执行 Agent 不应主动重构：

- `HedgeResearchModule.vue`
- `MarketTerminalPage.vue`
- `TerminalDetailPanel.vue`
- `HedgeBoardSubnav.vue`
- `hedgeBoard.less`
- `strategy-theme.less`

### 3.3 允许的增量改动

允许：

- 新增 Section；
- 新增图表；
- 新增指标；
- 新增数据状态；
- 新增 API；
- 新增数据适配层；
- 替换假数据；
- 修复数据展示错误。

### 3.4 硬编码处理原则

需要区分：

- **视觉硬编码**：当前原则上保留；
- **页面配置硬编码**：可保留；
- **金融数据硬编码**：逐步清除，替换为真实数据链路。

---

## 4. 数据架构【冻结】

长期统一数据链路：

```text
External Source
    ↓
platform-data
    ↓
fetch / normalize / derive / validate
    ↓
versioned canonical JSON
    ↓
platform-api
    ↓
Research API
    ↓
Platform Web
    ↓
existing chart / table components
```

### 4.1 `platform-data` 职责

作为看板独立数据生产仓库，长期负责：

- Provider 接入；
- 数据抓取；
- 标准化；
- 派生指标；
- 历史数据保存；
- GitHub Actions / 定时更新；
- 数据质量检查；
- Last Known Good；
- 标准 JSON 输出。

### 4.2 `Platform_Experiment` 职责

负责：

- 读取标准化数据；
- API 缓存与状态处理；
- 前端展示；
- 页面交互。

前端不应直接连接多个外部数据源。

---

## 5. 通用数据合同【冻结】

所有金融序列和市场数据应尽可能统一包含以下元信息：

- `series_id`
- `label`
- `value`
- `observations`
- `unit`
- `currency`
- `source`
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

统一状态枚举：

- `ready`
- `partial`
- `degraded`
- `stale`
- `no_data`
- `not_configured`
- `error`

语义原则：

- `0` 不代表无数据；
- 空数组不代表抓取失败；
- Provider 失败不等于市场无数据；
- 旧数据不得静默伪装成最新数据；
- 派生指标必须保留方法版本与上游来源。

---

## 6. 数据源原则【冻结】

优先级原则：

```text
官方 Source of Record
    ↓
官方/权威分发层
    ↓
稳定公开 Vendor
    ↓
独立 Fallback
```

具体 Provider 可随可用性、授权、稳定性变化，不写死在前端。

重要数据应尽可能具备独立来源交叉检查或 fallback。

不得绕过：

- CAPTCHA；
- WAF；
- 登录限制；
- 访问控制；
- 授权限制。

---

## 7. TradingView 角色【冻结】

TradingView 在本项目中主要作为：

- 图表展示；
- Widget；
- 用户查看大图与技术图表的交互入口。

TradingView 不作为本项目的通用市场数据抓取源。

项目自有数值、收益率、30 日曲线、历史序列等，应由 `platform-data` 提供。

---

## 8. Market Detail / 市场明细【方向冻结】

保留现有 Market Terminal 视觉与列结构，逐步将静态值替换为真实数据。

当前优先真实化：

- 收盘/最新有效值；
- 1D；
- 1W；
- 1M；
- QTD；
- YTD；
- 1Y；
- 52 周高；
- 30 日迷你曲线。

当前技术状态列（如 1H、4H、日线、3日线、周线）在统一算法未冻结前，不继续扩展假信号。

---

## 9. 30 日迷你曲线【冻结】

继续沿用现有 SVG Sparkline 展示方式。

不在每行嵌入 TradingView Mini Chart。

数据改造目标：

```text
fake/static number[]
    ↓
real recent ~30 daily observations
    ↓
existing SVG sparkline
```

禁止使用随机数组或占位曲线冒充真实市场走势。

---

## 10. 当前开发范围：宏观看板【冻结】

当前优化只聚焦 `/hedge-board/macro`。

在 Macro V1 冻结前，不主动扩展：

- 商品；
- 加密；
- 美股；
- 全球；
- A股；
- 交易工具。

原有宏观看板内容原则上不删除、不移动、不重新排序，新增内容以增量方式进入。

---

## 11. 宏观看板 V1 目标内容【已确认方向】

### 11.1 现有美元流动性

保留当前净美元流动性展示，不扩大为复杂流动性体系。

### 11.2 全球 M2

新增全球 M2 代理指标。

初步覆盖：

- 美国；
- 欧元区；
- 中国；
- 日本。

要求：

- 保留各地区原始货币序列；
- 汇率转换逻辑透明；
- 统一到共同观察期；
- 对“全球 M2”明确标记为 proxy / methodology-based derived series；
- 保存方法版本。

具体口径、汇率来源、聚合方式：**待商讨并冻结**。

### 11.3 增长

当前方向：

- 美国实际 GDP 同比（基于 `GDPC1`）；
- Industrial Production 同比（`INDPRO`）；
- 4 周初请失业金（`IC4WSA`）；
- CFNAI；
- CFNAIMA3（是否同时展示待确认）。

原则：增长模块保持精简，不做宏观数据库大全。

### 11.4 通胀

拆分为三个概念层：

#### 实际通胀

- CPI；
- Core CPI；
- PCE；
- Core PCE。

#### 领先/上游通胀

- PPI。

#### 市场隐含通胀

- 5Y Breakeven；
- 10Y Breakeven；
- 5Y5Y Forward Inflation。

增加“实际通胀 vs 市场隐含通胀”的差异观察，但不得定义为简单预测误差。

具体对比口径、图表形式、期限匹配：**待商讨并冻结**。

### 11.5 利率

#### 短端政策/货币市场走廊

当前方向：

- Fed Target Lower；
- Fed Target Upper；
- IORB；
- ON RRP Award Rate；
- EFFR；
- SOFR。

#### 美国国债收益率

- 3M；
- 2Y；
- 10Y；
- 30Y。

原则：Treasury 官方优先，FRED 可作为便利分发或 fallback。

### 11.6 风险偏好

当前只保留少量高信号指标：

- US High Yield OAS；
- HYG / LQD ratio。

暂不扩展成独立“宏观波动率”板块。

### 11.7 市场预期

定义为**金融市场隐含的政策/宏观定价**。

第一目标：

- Fed 下一次会议概率；
- 未来会议利率路径；
- 年末目标利率分布。

CME FedWatch 为优先研究方向，但正式实现前必须确认当前合法、稳定、可自动化的数据访问方式。

若真实数据链未配置，不得伪造，返回 `not_configured`。

### 11.8 事件概率

与“市场预期”分开。

仅用于用户主动关注的离散事件。

Polymarket 等预测市场若使用，必须采用显式白名单配置：

- 不自动扫描全部市场；
- 不通过标题关键词自动分类并展示；
- 白名单为空时属于“暂无配置事件”，不是 Provider 错误。

---

## 12. 宏观看板暂不新增内容【冻结】

当前暂不新增独立宏观波动率 Section。

原因：波动率未来更多在对应资产页内呈现。

除非用户后续明确变更，不主动扩展该板块。

---

## 13. Phase 路线【当前建议基线，待最终确认】

建议按垂直切片推进：

1. Phase 1A — 市场预期真实数据链路
2. Phase 1B — 宏观 Market Detail 真实化 + 30 日曲线
3. Phase 1C — 增长
4. Phase 1D — 通胀
5. Phase 1E — 利率
6. Phase 1F — 全球 M2
7. Phase 1G — 风险偏好
8. Phase 1H — 宏观看板整体数据质量、视觉与回归验收
9. Macro V1 Freeze

Phase 顺序本身尚未最终冻结，可在完整商讨后调整。

---

## 14. Change Control【冻结】

### GREEN：可直接执行

- 替换假数据；
- 数据源接入；
- API；
- Provider；
- 数据质量；
- fallback；
- 测试；
- 已批准 Section 内新增已批准指标；
- Bug 修复。

### YELLOW：先讨论再执行

- 调整 Section 顺序；
- 更换主要图表类型；
- 修改指标定义或计算口径；
- 增加新的二级主题；
- 明显改变页面信息密度；
- 影响多个页面的公共组件改造。

### RED：无明确授权不得执行

- 重构整体 Hedge Board UI；
- 删除现有模块；
- 改变一级分类；
- 改导航；
- 将看板改造成 AI 投资决策系统；
- 修改非当前 Phase 的业务模块；
- 修改 `main`；
- 未授权合并分支。

---

## 15. GitHub 执行 Agent 规则【冻结】

后续每个执行任务必须：

1. 先读取本 Master Plan；
2. 只执行指定 Phase；
3. 不得自行重新设计产品；
4. 不得用 contract / schema / README 单独冒充业务 Phase 完成；
5. 端到端 Phase 必须以真实业务链路作为验收标准；
6. 若某一步无法验证，可标记 `not_verified`，但不得伪造；
7. 单一工具路径失败时，应优先寻找等价 GitHub/API 实现路径，而不是立即停止；
8. 只有真实权限、工具、关键输入或破坏性操作阻塞时才允许停止。

---

## 16. 待完整商讨事项【OPEN】

以下事项尚未最终冻结：

1. 宏观看板最终 Section 顺序与页面信息层级；
2. 每个 Section 的具体图表形态；
3. Growth 中 CFNAI / CFNAIMA3 的保留方式；
4. 实际通胀与隐含通胀差异的精确口径；
5. 全球 M2 的严格定义、地区权重、汇率与共同观察期；
6. 利率走廊采用一张图还是拆成政策利率/货币市场两层；
7. Fed 市场预期的数据源与自动化方案；
8. Polymarket 白名单事件的配置和展示规则；
9. Macro Market Detail 应保留哪些现有行、增加哪些行；
10. 中国宏观变量在当前“宏观”页中的深度与边界；
11. 是否增加经济意外指数、金融条件指数、收益率曲线斜率等高阶指标；
12. 图表默认时间窗口和各频率数据的对齐规则；
13. 数据更新时间、stale threshold 与日常刷新 SLA；
14. 数据仓库的长期存储格式与历史版本策略；
15. Macro V1 的最终验收清单。

---

## 17. 文档维护规则

本文件是当前分支上的对冲基金看板优化权威底稿。

后续商讨中：

- 用户明确确认的事项，从 `OPEN` 移入冻结项；
- 有争议或未确认的内容保留 `OPEN`；
- 执行 Agent 不得自行将建议状态升级为冻结状态；
- 每次重大方案冻结应更新文档版本和 commit。
