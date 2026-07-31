# 策略模块现状需求文档

## 文档定位

本文档用于记录当前平台中 `策略模块` 的真实现状，作为后续需求调整、重构讨论与功能落地的基线文档。

本文档遵循以下原则：

- 严格以当前代码和现有页面内容为准
- 不把“未来想做的能力”混入“当前已存在能力”
- 文末单独列出 `建议需求`，作为后续补强方向

## 模块总览

当前策略模块在路由层分为两大子模块：

1. `交易平台`
2. `策略管理`

对应路由文件：

- [strategy.ts](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/router/routes/modules/strategy.ts)

当前路由结构：

- `/strategy/platform`
  - 页面标题：`交易平台`
  - 实际入口文件：[platform/index.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/platform/index.vue)
- `/strategy/management`
  - 页面标题：`策略管理`
  - 实际入口文件：[strategy/index.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/index.vue)

角色权限现状：

- 仅 `admin`、`employee` 可访问

---

## 一、交易平台现状

### 1. 页面定位

`交易平台` 当前更像一个 `策略工作台容器`，负责在不同策略类型之间切换，并切换每种策略的 `分析视图` 与 `执行视图`。

当前入口文件：

- [platform/index.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/platform/index.vue)

### 2. 当前支持的策略工作台

当前仅支持两类 desk：

1. `资金`
   - 内部对应：`funding`
   - 实际工作台：[funding-carry/index.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/funding-carry/index.vue)
2. `价差`
   - 内部对应：`spread`
   - 实际工作台：[spread-carry/index.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/spread-carry/index.vue)

当前通过 URL query 控制 desk：

- `?desk=funding`
- `?desk=spread`

### 3. 顶部公共控制区现状

交易平台页面顶部存在一条统一控制 ribbon，包含：

- `desk 切换`
  - 资金
  - 价差
- `section 切换`
  - 行情分析
  - 交易执行

公共筛选项：

- `交易所`
  - Bybit
  - Binance
  - OKX
- `时间精度`
  - 30分钟
  - 1小时
  - 4小时

按 desk 区分的筛选项：

#### funding desk

- `币种`
  - BTC
  - ETH
  - SOL
  - DOGE
  - XRP
  - XAUT

#### spread desk

- `主腿标的`
  - 当前只有 `XAUTUSDT.P`
- `对冲腿标的`
  - 当前只有 `XAUUSD`

### 4. 资金工作台现状

#### 4.1 页面结构

资金工作台按 section 分为两种模式：

1. `analysis`
2. `execution`

#### 4.2 analysis 模式

当前由以下三块组成：

1. `FundingMarketBoard`
   - 文件：[FundingMarketBoard.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/funding-carry/components/FundingMarketBoard.vue)
   - 作用：
     - 显示摘要卡
     - 显示最高资金费率榜
     - 显示最低资金费率榜
     - 显示 USDT 永续 / 反向合约的费率热力表

2. `FundingChartPanel`
   - 文件：[FundingChartPanel.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/funding-carry/components/FundingChartPanel.vue)
   - 作用：
     - 展示选中币种的价格与资金费率趋势图

3. `FundingDetailPanel`
   - 文件：[FundingDetailPanel.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/funding-carry/components/FundingDetailPanel.vue)
   - 当前标题逻辑：`{{ viewLabel }}套利总览`
   - 内部当前包含：
     - 期现价差图
     - 借贷费率图
     - 期现价差表
     - 借贷费率表
   - 当前存在 3 个视图标签：
     - `期现价差`
     - `资金费率`
     - `借贷利率`

#### 4.3 execution 模式

当前由 `FundingOrderPanel` 组成：

- 文件：[FundingOrderPanel.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/funding-carry/components/FundingOrderPanel.vue)

当前页面内容包含：

- 策略标签
- 下一执行时间窗
- 账户信息
- 执行影响
- 执行反馈
- 左右腿信息卡
- 动作按钮

当前执行阶段标签：

- 待执行
- 开仓
- 移仓
- 保护

当前动作按钮现状：

- 开仓
- 移仓

### 5. 资金工作台数据现状

当前主要依赖 mock 数据文件：

- [funding-carry/mock/data.ts](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/funding-carry/mock/data.ts)

当前数据模块包括：

- `fundingViewLabels`
- `fundingRangeLabels`
- `fundingCarryProfiles`
- `fundingMarketBoard`
- `fundingChartPanel`
- `fundingOrderPanel`

当前数据特点：

- 以静态 mock 为主
- 已经形成较清晰的数据结构分层
- 已具备“研究数据”与“执行面板数据”分离的雏形

### 6. 价差工作台现状

#### 6.1 页面结构

价差工作台同样分为：

1. `analysis`
2. `execution`

入口文件：

- [spread-carry/index.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/spread-carry/index.vue)

#### 6.2 analysis 模式

当前包括三大区块：

1. `Spread Overview`
   - 期限结构表
   - 机会分析表

2. `Spread Chart Card`
   - 主图标题：`主腿 - 对冲腿 价差联动`
   - 过滤项：
     - 粒度级别
     - 开始日期
     - 结束日期
   - 当前可切换展示：
     - 价差
     - 黄金价格

3. `Statistics Section`
   - 统计分析
   - 区间统计
   - 季节图表
   - 月度热力矩阵

#### 6.3 execution 模式

当前包括四大执行区块：

1. `策略指令`
2. `主腿 / 对冲腿执行卡`
3. `执行约束`
4. `执行反馈`

当前执行动作按钮：

- 策略开仓
- 策略平仓
- 止盈保护

#### 6.4 价差工作台数据现状

当前数据写在页面内部，未像 funding desk 一样完整拆到独立 mock 模块。

当前页面内直接维护的数据包括：

- 期限结构行数据
- 分位分析数据
- 统计卡数据
- 分布图数据
- 季节性数据
- 热力矩阵数据
- 执行摘要数据
- 执行反馈文本

当前特征：

- analysis 与 execution 共用同一页面内状态
- 数据结构尚未完全抽象成独立模块
- 可用性上足够演示，但工程层可维护性弱于 funding desk

---

## 二、策略管理现状

### 1. 页面定位

`策略管理` 当前更像一个 `策略运营与归因中台`，重点不在“实时交易操作”，而在：

- 看策略损益
- 看账户资金
- 看执行记录与订单信息
- 在不同策略 desk 间切换

入口文件：

- [strategy/index.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/index.vue)
- [management/index.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/index.vue)

### 2. 当前 desk 体系

当前 `策略管理` 有 3 个 desk：

1. `funding`
   - 标签：资金费率套利
2. `spread`
   - 标签：价差套利
3. `dip`
   - 标签：抄底策略

数据来源：

- [management/mock/data.ts](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/mock/data.ts)

### 3. 当前 section 体系

策略管理顶部 section tab 有 3 类：

1. `策略损益`
   - key: `pnl`
2. `账户资金`
   - key: `capital`
3. `订单信息`
   - key: `orders`

切换 desk 时，页面会自动：

- 重置记录 tab
- 重置周期到 `week`
- 重置 section 到 `pnl`

### 4. 策略损益 section 现状

当前由三块组成：

1. `StrategyOverviewBoard`
   - 文件：[StrategyOverviewBoard.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/components/StrategyOverviewBoard.vue)
   - 当前内容：
     - 策略损益总览
     - 周期切换
     - 统计卡
     - 盈利归因
     - 亏损归因
     - 运行同步状态

2. `StrategyDetailPanel`
   - 文件：[StrategyDetailPanel.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/components/StrategyDetailPanel.vue)
   - 当前内容：
     - detail.title
     - status
     - 动作按钮
     - 左右腿信息
     - 敞口分析
     - tabTables

3. `StrategyCurveGrid`
   - 文件：[StrategyCurveGrid.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/components/StrategyCurveGrid.vue)
   - 当前作用：
     - 以卡片图表形式展示多条策略曲线
   - 单卡组件：
     - [StrategyCurveCardChart.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/components/StrategyCurveCardChart.vue)

### 5. 账户资金 section 现状

当前由两块组成：

1. `StrategyKpiGrid`
   - 文件：[StrategyKpiGrid.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/components/StrategyKpiGrid.vue)
   - 当前作用：
     - 展示 KPI 卡片

2. `StrategyRuntimePanel`
   - 文件：[StrategyRuntimePanel.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/components/StrategyRuntimePanel.vue)
   - 当前标题：
     - `策略账户信息`
   - 当前内容：
     - strategyName
     - gauges
     - accountBreakdown

### 6. 订单信息 section 现状

当前由左右两块组成：

1. `StrategyExecutionPanel`
   - 文件：[StrategyExecutionPanel.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/components/StrategyExecutionPanel.vue)
   - 当前内容：
     - 执行状态切换
     - 策略指令
     - 执行反馈
     - 当前状态执行视图
     - 执行动作
   - 当前执行状态标签：
     - 执行预案
     - 降风险
     - 保护单

2. `StrategyRecordsPanel`
   - 文件：[StrategyRecordsPanel.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/components/StrategyRecordsPanel.vue)
   - 当前标题：
     - `损益明细与订单信息`
   - 当前内容：
     - tabs
     - tables
     - activeRecordTab 切换

### 7. desk 细分能力现状

#### 7.1 funding desk

除通用 `overview/detail/kpi/runtime/execution/records` 外，还引入了专用组件：

- [FundingTerminalPanel.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/components/FundingTerminalPanel.vue)

当前可见能力包括：

- 费率监控
- 当前持仓
- 执行队列
- 当前持仓与费率执行
- 持仓加权费率 / 净 carry / 价格 图层切换

#### 7.2 spread desk

除通用区块外，还引入了专用组件：

- [SpreadResearchPanel.vue](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/components/SpreadResearchPanel.vue)

当前可见能力包括：

- `日内结构`
- `季节图表`
- `价差矩阵`
- `XAUTUSDT.P - XAUUSD 价差联动`
- `日内统计`
- `季节图表`
- `振幅统计`
- `月度热力分布`
- `价差矩阵`
- `选中配对线性关系`

#### 7.3 dip desk

当前 `dip` desk 已在 mock 数据层存在，且接入策略管理主切换，但页面表现仍主要复用通用策略管理组件体系。

现状判断：

- 它已经是一个独立策略类别
- 但专用研究面板和专用执行面板的独立感弱于 funding / spread

---

## 三、数据结构现状

### 1. 策略管理核心类型

文件：

- [management/types.ts](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/types.ts)

当前已经定义的核心数据结构包括：

- `StrategyDeskKey`
- `StrategyPeriodKey`
- `StrategyKpiCard`
- `StrategyAccountBreakdown`
- `StrategyGaugeMetric`
- `StrategyExecutionMetric`
- `StrategyLogItem`
- `StrategyCurveCard`
- `StrategyTableSection`
- `StrategyOverviewConfig`
- `StrategyDetailSnapshot`
- `StrategyDeskProfile`

说明：

- 当前策略管理的数据结构已经具备较强的“页面驱动配置化”特征
- mock 数据和组件 props 的对应关系较清晰
- 后续如果要接接口，具备比较好的替换基础

### 2. 策略管理 mock 数据现状

文件：

- [management/mock/data.ts](C:/Users/jiuxi/Desktop/codex/平台最终版/Variable-Global-main/admin-risk/src/views/strategy/management/mock/data.ts)

当前已维护：

- `strategyDeskOrder`
- `strategyDeskProfiles`
- `funding / spread / dip` 三个策略档案
- 每个档案均包含：
  - `title`
  - `subtitle`
  - `strategyName`
  - `overview`
  - `detail`
  - `kpis`
  - `gauges`
  - `accountBreakdown`
  - `execution`
  - `curves`
  - `tabs / tables`

### 3. 交易平台数据现状

#### funding desk

当前数据已经分为：

- 研究概览数据
- 热力表数据
- 图表数据
- 订单执行面板数据
- 每个交易所 profile 数据

#### spread desk

当前数据仍以内嵌页面状态与常量数组为主，未完全抽象成统一类型系统。

---

## 四、当前交互现状

### 1. 已有切换交互

当前策略模块已有的核心切换包括：

- 路由级切换
  - 交易平台 / 策略管理
- desk 级切换
  - funding / spread / dip
- section 级切换
  - 分析 / 执行
  - 损益 / 资金 / 订单
- 周期切换
  - day / week / month / custom
- 明细 tab 切换
  - record tabs
  - 研究 panel tabs
  - 执行状态 tabs

### 2. 已有筛选交互

交易平台当前已有：

- 交易所切换
- 币种切换
- 主腿 / 对冲腿切换
- 时间精度切换
- 日期范围切换

### 3. 已有动作交互

当前已有前端演示型动作按钮，但本质仍偏展示和 mock 反馈：

- 策略开仓
- 策略平仓
- 止盈保护
- 移仓
- 保护单

现状判断：

- 当前交互适合演示
- 尚未形成真实交易流程、审批流、风控流、回写流

---

## 五、当前工程结构现状

### 1. 目录分层

当前策略模块目录主要分为：

- `views/platform`
  - 交易平台入口
- `views/strategy/funding-carry`
  - 资金费率策略工作台
- `views/strategy/spread-carry`
  - 价差策略工作台
- `views/strategy/management`
  - 策略管理工作台
- `views/strategy/shared`
  - 共享组件

### 2. 当前优点

- 页面分层已经比较清楚
- 策略管理具备较好的 mock 数据配置化结构
- funding desk 的数据拆分优于 spread desk
- 交易平台与策略管理在概念上已分离

### 3. 当前不足

- `交易平台` 路由实际挂在 `views/platform`，命名上与策略目录不统一
- `spread-carry` 数据与页面耦合偏重
- `策略管理` 中 `dip` 专属能力不够清晰
- 交易平台与策略管理之间尚无清晰的状态联通模型
- 当前大量动作按钮仍是“演示级反馈”，不是“真实可落地动作”

---

## 六、现状需求基线总结

如果严格基于当前平台现状，可以把策略模块定义为：

### 交易平台

当前是一个面向交易员或研究执行者的 `策略分析 / 执行工作台`，支持：

- funding 与 spread 两种策略场景切换
- 分析视图与执行视图切换
- 多种基础筛选器
- 图表、热力表、统计表和执行面板展示

### 策略管理

当前是一个面向策略运营与复盘的 `策略管理看板`，支持：

- funding / spread / dip 三类策略 desk 切换
- 按损益、资金、订单三个维度查看策略
- 查看策略归因、敞口、曲线、账户信息、执行记录和订单记录

---

## 七、建议需求

以下内容不属于“当前已实现能力”，而是基于现状明显应补齐的方向。

### 1. 交易平台建议需求

- 建立真实的 `策略状态机`
  - 观察中
  - 待开仓
  - 开仓中
  - 持仓中
  - 移仓中
  - 平仓中
  - 风控冻结
- 把当前演示按钮改为 `可接后端动作`
  - 开仓
  - 平仓
  - 移仓
  - 止盈
  - 风险保护
- 增加 `策略信号面板`
  - 信号来源
  - 信号强度
  - 触发条件
  - 当前执行建议
- 增加 `执行前检查`
  - 滑点
  - 流动性
  - 杠杆占用
  - 账户可用资金
  - 风控阈值
- spread desk 建议拆出独立 mock / type / service 层

### 2. 策略管理建议需求

- 建立 `策略生命周期视图`
  - 草稿
  - 运行中
  - 观察中
  - 暂停
  - 终止
- 增加 `策略列表总表`
  - 当前策略管理偏 desk 视角，缺少横向总览
- 增加 `策略版本管理`
  - 参数变更记录
  - 调仓规则变更记录
  - 风控参数变更记录
- 增加 `策略归因穿透`
  - 从总收益下钻到单策略、单交易所、单标的、单订单
- 增加 `策略与交易平台联通`
  - 交易平台里的执行结果自动回写策略管理

### 3. 数据与工程建议需求

- 统一 trading platform 与 strategy management 的字段体系
- 给 spread desk 建立与 funding desk 对齐的数据模型
- 增加接口层占位
  - account
  - strategy signal
  - execution action
  - order records
  - pnl attribution
- 把 mock 数据逐步替换为：
  - `service + adapter + view-model` 三层

### 4. 产品层建议需求

- 明确 `交易平台` 与 `策略管理` 的职责边界
  - 交易平台偏实时决策与执行
  - 策略管理偏复盘、归因、监控、运营
- 明确 `funding / spread / dip` 三类策略的统一框架
  - 信号
  - 仓位
  - 收益
  - 风险
  - 执行
  - 复盘

---

## 八、建议你下一步如何修改这份文档

你后面改这份文档时，建议按以下顺序修改：

1. 先删掉你不想保留的现状模块
2. 再补“你真正想要的策略框架”
3. 再决定交易平台和策略管理之间哪些数据要打通
4. 最后再让我按你改过的文档去落代码

