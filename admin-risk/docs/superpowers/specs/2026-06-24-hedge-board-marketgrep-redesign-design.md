# Hedge Board MarketGrep Redesign

## Goal

将 `对冲基金看板` 扩展为六个子项目：`宏观 / 加密 / 黄金 / 美股 / A股 / 全球`。其中 `美股 / 全球 / A股` 采用参考站 [MarketGrep 中文站](https://www.marketgrep.com/zh) 的信息架构、按钮体系、图表区块和详情阅读顺序；`宏观 / 加密 / 黄金` 保留现有研究型页面，但进入统一的主导航壳内。

## Confirmed Scope

- 仅处理前端布局、交互、文案层和图表占位设计，不接后端
- 美股页复刻 MarketGrep 主页面结构
- 全球页复刻 MarketGrep 全球页面结构
- A股页沿用同一壳体，但按 A 股语境改写模块
- 右上角页签式切换要覆盖 `美股 / 全球`，并在同一体系下加入 `A股`
- 顶层对冲基金看板子项目固定为：`宏观 / 加密 / 黄金 / 美股 / A股 / 全球`

## Visual Direction

- 不直接照搬 MarketGrep 的深色报刊皮肤
- 沿用当前平台浅底、金色边框、研究终端风格
- 保留 MarketGrep 的高密度指标卡、状态色、数字优先、几何卡片感
- 让新增三页在风格上属于同一平台，而不是外来落地页

## Information Architecture

### 1. Top-Level Navigation

`/hedge-board` 下新增并固定六个路由：

- `/hedge-board/macro`
- `/hedge-board/crypto`
- `/hedge-board/gold`
- `/hedge-board/us`
- `/hedge-board/a-share`
- `/hedge-board/global`

主页面顶部提供统一导航卡条，替代当前仅三项的内部认知。

### 2. Page Strategy

- `宏观 / 加密 / 黄金`：继续使用现有 `researchModules` 数据驱动页面
- `美股 / 全球 / A股`：切换到新的 `MarketTerminalPage` 组件

这意味着 `hedgeBoard/index.vue` 变成一个入口分发器，而不是单一内容页面。

### 3. Market Terminal Structure

`美股 / 全球 / A股` 三页共用如下骨架：

1. Hero 区
   - 市场名称
   - 更新时间
   - 市场状态 / regime
   - 一句结论 headline

2. Summary Cards
   - 温度分数
   - 风险状态
   - 广度 / 动量 / 波动摘要
   - 关键观察

3. Market Sections
   - 顶部页签切换器
   - 子模块按钮组
   - 卡片组 / 热力区 / 排名区 / 表格区

4. Detail Modal
   - 点击任一标的后展开
   - 展示阶段表现、属性、说明、占位 sparkline

### 4. A-Share Adaptation

A股页不生硬套用美股字段，改用本地化分组：

- 宽基：上证50、沪深300、中证500、中证1000、创业板、科创50
- 风格：大盘、小盘、成长、价值、红利
- 行业：AI硬件、消费电子、券商、银行、黄金、有色、新能源
- 资金与情绪：北向、融资余额、成交额、涨跌家数、风险偏好

## Component Boundaries

### Existing Entry

- `src/views/hedgeBoard/index.vue`
  - 管理当前 `hedgeCategory`
  - 渲染统一顶部导航
  - 对旧研究页和新终端页做条件分发

### New Files

- `src/views/hedgeBoard/components/MarketTerminalPage.vue`
  - 复刻型终端主组件
- `src/views/hedgeBoard/nativeData/marketTerminal.ts`
  - 美股 / 全球 / A股 的静态配置与 mock 数据

## Data Model

新终端页统一使用配置驱动：

- `MarketTerminalPageConfig`
  - `id`
  - `label`
  - `eyebrow`
  - `headline`
  - `summary`
  - `updatedAt`
  - `heroStats`
  - `switcherTabs`
  - `sections`
  - `detailMap`

每个 section 支持：

- 指标卡
- 排名卡
- 表格
- 快捷按钮

## Error Handling

- 未识别的 `hedgeCategory` 默认回到 `macro`
- 终端页缺失数据时显示占位文案，不抛模板错误
- 详情弹窗找不到标的时不打开

## Verification

- 六个子路由都能进入
- `美股 / 全球 / A股` 页面正常切换
- 顶部导航高亮正确
- 详情弹窗可打开关闭
- `macro / gold / crypto` 旧功能不回归
- `vue-tsc` 和 `vite build` 通过

## Out Of Scope

- 实时数据更新
- API 接入
- 权限逻辑变更
- 新增后端服务
