# Platform Research与主看板低风险模块化计划

状态：**E4.3 ReserveRanking代码与永久合同已完成，等待清理HEAD完整矩阵收口**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 1. 冻结目标与合同

本计划只降低Research域与Hedge Board热点文件的职责密度和任务上下文，不改变：

- 三条Research API、`platform:read`权限和HTTP语义；
- `loading / ready / partial / no_data / stale / error`状态；
- Completeness、Last Known Good、缓存、TTL与并发锁；
- 页面路由、导航、操作习惯、DOM语义、CSS类名和四档视觉；
- 观察列表、CSV导出、个股快照、宏观预期及真实Provider口径；
- Platform Web、Platform API与Execution Runtime边界。

禁止引入微服务、复杂依赖注入或跨域状态容器；禁止为通过门禁批量格式化整个历史热点文件。

## 2. 当前依赖方向

```text
research_routes
  -> research_service                 # orchestration, cache, LKG, status
      -> research_cache
      -> research_macro_history       # file history only
      -> a_share_research_policy
      -> research_providers           # stable facade
          -> domain adapters

hedgeBoard/index.vue                   # page orchestration
  -> components/WidgetErrorBoundary.ts
  -> components/MetricStrip.ts
  -> components/ReserveRanking.ts
```

## 3. E0–E3：完成

- [x] 依赖、规模、API、状态与视觉审计；
- [x] Provider纯归一化层；
- [x] 宏观预期、A股概览、Eastmoney DataCenter、Stock DataCenter、Stock AkShare和Stock HTTP Adapter；
- [x] `FreeResearchProvider`保持稳定Facade，三条API与Service调用面不变；
- [x] 宏观概率JSON读取、原子写入、90日窗口、分钟去重和1日/7日变化计算移出Service；
- [x] Service缓存、15分钟TTL、锁、LKG和状态分支保持原位；
- [x] E3完整矩阵通过；视觉Artifact `8785119449`，SHA-256 `67e925d8ef87f549863f211213619127ccbdaf26cb1369365304de7fc4eee8c4`。

## 4. E4 — 主看板渲染组件

原热点文件包含11个内联组件：

```text
TradingViewWidget
WidgetErrorBoundary
MetricStrip
DualAxisChart
TreasuryFlowChart
GroupedBarChart
EtfWeeklyFlowsPanel
YtdSummaryPanel
ReserveRanking
SnapshotDetailTable
LocalChartWidget
```

### E4.1 WidgetErrorBoundary：完成

- [x] 外置原Render Function；
- [x] 保持`widgetTitle` Prop、默认插槽、错误捕获、日志、`return false`、`local-empty`、360px高度和原降级文案；
- [x] 永久布局门禁冻结组件合同；
- [x] 前端无新增债务门禁校正为真实基线比较；
- [x] 临时写权限工具已删除；
- [x] 完整矩阵通过；视觉Artifact `8785958564`，SHA-256 `01ad7db9a7495aedce8889fdd1f069c5ca07c854907863644a33cf0cc8f1a11f`。

### E4.2 MetricStrip：完成

- [x] 外置原Render Function至`components/MetricStrip.ts`；
- [x] 保持必填`metrics: Array<[string, string]>`；
- [x] 保持`metric-strip > article > span + strong`结构；
- [x] 保持`${label}-${value}` Key；
- [x] 页面只改为显式导入并删除内联定义；
- [x] 永久布局门禁冻结外部委托与DOM合同；
- [x] 临时写权限工具已删除；
- [x] 完整矩阵通过：
  - Platform CI `30613049665`
  - Directory `30613049550`
  - User E2E `30613049677`
  - Hedge E2E `30613049611`
  - Visual `30613049532`
  - Provider Smoke `30613049535`
  - Secret `30613049606`
  - Version `30613049536`
  - Audit `30613049529`
- [x] 视觉Artifact `8786313538`，SHA-256 `14d2f2352fca0df6bf94f948d9d3e9da2cc6105abd0e1782dd006d48881dabbe`。

### E4.3 ReserveRanking：代码完成，最终矩阵待收口

- [x] 只读比较`ReserveRanking`、`GroupedBarChart`和`SnapshotDetailTable`后选择最低依赖候选；
- [x] 外置原Render Function至`components/ReserveRanking.ts`；
- [x] 保持必填`rows`和`color`、默认`diverging=false`；
- [x] 保持最大绝对值缩放、`${row.label}-${row.value}` Key、正负色和负值12px最小宽度；
- [x] 保持原数值格式化及“吨”显示；
- [x] 页面只改为显式导入并删除内联定义；
- [x] 永久布局门禁冻结外部委托、Prop、缩放、色调和显示合同；
- [x] 新组件严格Lint、基线债务比较、策略Type Check和布局合同通过；
- [x] 临时写权限Workflow与脚本已删除；
- [ ] 以本计划同步后的清理HEAD完成完整质量矩阵。

### E4.4 候选审计：后置

E4.3矩阵通过后再决定是否继续：

- `GroupedBarChart`依赖共享图表尺寸、坐标缩放、刻度、日期标签和轴格式化；
- `SnapshotDetailTable`依赖页面级类型、Sparkline、色调与箭头辅助函数；
- `LocalChartWidget`耦合市场数据、多个图表组件、Terminal配置、辅助函数和错误降级。

没有形成单一、纯展示、低依赖且可永久冻结的切口时，停止继续机械拆分。

## 5. 每步验收

每个结构切口均须通过：

- Platform API lint、type check和全测试；
- Research Provider Smoke；
- Platform Web lint、两套Type Check和生产Build；
- User System Browser E2E；
- Hedge Board Browser E2E；
- 56张四档视觉基线；
- Directory、Secret、Version和Baseline Audit。

Draft PR始终保持Open、Draft、Unmerged；不得修改或合并`main`。
