# Platform Research与主看板低风险模块化计划

状态：**E4.2 MetricStrip代码与永久合同已完成，等待清理HEAD完整矩阵收口**  
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
- [x] 页面只改为显式导入；
- [x] 永久布局门禁冻结组件合同；
- [x] 修复任意`ai`子串误判；
- [x] `frontend-no-new-debt.py`改为真实基线比较：新文件零告警、遗留债务不得增加、触碰行零诊断、Fatal失败关闭；
- [x] 临时写权限工具已删除；
- [x] 完整矩阵通过：
  - Platform CI `30612132323`
  - Directory `30612132482`
  - User E2E `30612132418`
  - Hedge E2E `30612132455`
  - Visual `30612132339`
  - Provider Smoke `30612132362`
  - Secret `30612132500`
  - Version `30612132536`
  - Audit `30612132444`
- [x] 视觉Artifact `8785958564`，SHA-256 `01ad7db9a7495aedce8889fdd1f069c5ca07c854907863644a33cf0cc8f1a11f`。

### E4.2 MetricStrip：代码完成，最终矩阵待收口

- [x] 外置原Render Function至`components/MetricStrip.ts`；
- [x] 保持必填`metrics: Array<[string, string]>`；
- [x] 保持`metric-strip`根类；
- [x] 保持`article > span + strong`结构；
- [x] 保持`${label}-${value}` Key；
- [x] 页面只改为显式导入并删除内联定义；
- [x] 永久布局门禁冻结外部委托与DOM合同；
- [x] 新组件严格Lint、基线债务比较、策略Type Check和布局合同通过；
- [x] 临时写权限Workflow与脚本已删除；
- [ ] 以文档同步后的清理HEAD完成完整质量矩阵。

### E4.3 下一候选：后置

E4.2矩阵通过后，只读比较`ReserveRanking`、`GroupedBarChart`和`SnapshotDetailTable`。`LocalChartWidget`继续留在页面，因为其耦合市场数据、多个图表组件、Terminal配置、辅助函数和错误降级。

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
