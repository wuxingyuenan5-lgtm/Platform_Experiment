# Platform Research与主看板低风险模块化计划

状态：**E4.1 WidgetErrorBoundary已完成，等待最终清理HEAD完整矩阵收口**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 1. 目标

在不改变Research API合同、权限、页面视觉、数据源语义、Completeness或Last Known Good行为的前提下，降低Research域和主看板高频修改所需上下文与单文件职责密度。

保留Platform Web / Platform API / Execution Runtime三大边界，不拆微服务，不引入新框架、复杂依赖注入或跨域状态容器。

## 2. 冻结合同

### API与权限

```text
GET /api/v1/research/a-share/dashboard
GET /api/v1/research/a-share/stocks/{code}/snapshot
GET /api/v1/research/macro/expectations
```

以上路由、HTTP语义与`platform:read`权限保持不变。

### 数据状态与容错

```text
loading / ready / partial / no_data / stale / error
```

必须保持：

- 单一Provider失败不得拖垮其他模块；
- 当前刷新失败时优先返回Last Known Good并标记`stale`；
- Fixture、Simulation和Fake Runtime不得冒充真实Provider或生产数据；
- Decimal、时间戳、source、error_code、message和Completeness语义不变；
- Provider Adapter不得缓存、吞异常或持有跨请求状态。

### 页面与操作

- Research和Hedge Board页面路由、导航、信息层级与主要操作习惯不变；
- 四档视觉基线不变；
- 观察列表、CSV导出、个股快照和宏观预期交互不变；
- 组件抽离不得改变DOM语义、CSS类名、Props、默认插槽或错误隔离行为。

## 3. 当前依赖方向

```text
research_routes
    -> research_service                         # orchestration, cache, LKG, status
        -> research_cache
        -> research_macro_history               # file history only
        -> a_share_research_policy
        -> research_providers                    # stable facade
            -> research_provider_macro
            -> research_provider_a_share
            -> research_provider_datacenter
            -> research_provider_stock_datacenter
            -> research_provider_stock_akshare
            -> research_provider_stock_http
            -> research_provider_errors
            -> research_provider_normalization
            -> research_data_schemas

hedgeBoard/index.vue                             # page orchestration
    -> components/WidgetErrorBoundary.ts         # local render error isolation only
```

`FreeResearchProvider`公开方法、三条Research API与Service调用面保持不变。

## 4. 实施门禁

### E0 — 依赖与规模审计：完成

- [x] 建立只读审计脚本；
- [x] 冻结Provider方法、API合同、状态词汇、LKG和页面视觉边界；
- [x] 确认原始`research_providers.py`为999行，`FreeResearchProvider`约881行、26个方法；
- [x] 确认Platform Web主热点为约3,772行的`hedgeBoard/index.vue`。

### E1 — Provider纯归一化层：完成

- [x] 抽离Decimal、整数、日期、DataFrame records、多字段择优；
- [x] 抽离收益率、趋势和最近历史值计算；
- [x] 增加边界测试并纳入Pyright；
- [x] 完整质量矩阵通过。

### E2 — Provider按数据域拆分：完成

保留`FreeResearchProvider`作为稳定Facade，全部使用显式组合和委托。

- [x] E2.1宏观预期Adapter；
- [x] E2.2 A股概览Adapter；
- [x] E2.3a Eastmoney DataCenter Client；
- [x] E2.3b Stock DataCenter Adapter；
- [x] E2.3c Stock AkShare Adapter；
- [x] E2.3d Stock HTTP Adapter；
- [x] 数据源Endpoint、参数、Header、编码、日期窗口、Decimal、排序、Limit、异常传播和空结果语义保持不变；
- [x] Adapter不持有缓存、Completeness、LKG或跨请求状态；
- [x] E2.3d完整质量矩阵通过；
- [x] E2.3d视觉Artifact ID `8784674299`，SHA-256 `fd0b00faea120390e7ea531cfddaab72e2e931805441f70487c9bb20d50959df`。

### E3 — Research Service状态职责：完成

- [x] 建立`research_macro_history.py`；
- [x] 将宏观概率JSON读取、原子写入、90日窗口、分钟去重和1日/7日变化计算移出Service；
- [x] 保持`RESEARCH_MACRO_HISTORY_PATH`和默认路径；
- [x] 保持异步锁与`asyncio.to_thread`文件I/O；
- [x] Service仅保留`_MACRO_HISTORY`组合调用；
- [x] `_MACRO_CACHE`、15分钟TTL、`_MACRO_LOCK`、LKG及`ready/stale/error`分支仍在Service；
- [x] 增加独立契约测试并纳入Pyright；
- [x] 一次性写权限Workflow与脚本已删除；
- [x] 完整质量矩阵通过：
  - Platform CI `30609898871`
  - Directory `30609898857`
  - User E2E `30609898866`
  - Hedge E2E `30609898855`
  - Visual `30609898845`
  - Provider Smoke `30609898846`
  - Secret `30609898863`
  - Version `30609898859`
  - Audit `30609898856`
- [x] 视觉Artifact ID `8785119449`，SHA-256 `67e925d8ef87f549863f211213619127ccbdaf26cb1369365304de7fc4eee8c4`。

### E4 — 主看板渲染组件：进行中

只读盘点确认`hedgeBoard/index.vue`包含11个内联组件：

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

#### E4.1 WidgetErrorBoundary：代码完成，最终矩阵待收口

- [x] 选择最低风险切口：单一字符串Prop、默认插槽、仅本地错误状态，无请求、缓存或路由依赖；
- [x] 建立`components/WidgetErrorBoundary.ts`并保留原Render Function；
- [x] 保留`onErrorCaptured`、`return false`、日志、`local-empty`根类、360px最小高度和原中文降级文案；
- [x] 页面改为显式导入，内联实现与无用Vue导入已删除；
- [x] `verify-hedge-board-layout.cjs`永久冻结外部委托和错误隔离合同；
- [x] 将错误的任意`ai`子串门禁收窄为真实AI功能标记，避免误伤`financials`、`mainNet20d`等客观字段；
- [x] 校正`frontend-no-new-debt.py`：
  - 新文件继续要求零错误、零警告；
  - 修改遗留文件按基线与当前逐规则、逐严重度比较，债务不得增加；
  - 所有实际触碰行必须零诊断；
  - 修改重命名保留原始基线路径，100%内容重命名继续由目录门禁负责；
  - Fatal诊断始终失败关闭；
- [x] 增加架构测试覆盖重命名、触碰行、规则计数、新文件和Fatal行为；
- [x] 目标组件Lint、真实基线债务比较、策略Type Check和布局合同通过；
- [x] 一次性写权限Workflow与脚本已删除；
- [ ] 以文档同步和临时工具清理后的最终HEAD完成全质量矩阵。

#### E4.2 下一候选：待E4.1矩阵通过后只读评估

只比较`MetricStrip`与`LocalChartWidget`的Props、DOM、样式和数据依赖；E4.1未完成前不提交下一组件代码。

### E5 — A股Composable复核：后置

仅在E4通过后评估Dashboard请求、个股快照、观察列表远端同步与CSV导出；无明确收益则保持现状。

## 5. 每步验收

每个结构切口必须通过：

- Platform API lint、type check和全测试；
- Research Provider Smoke；
- Platform Web lint、两套Type Check和生产Build；
- User System Browser E2E；
- Hedge Board Browser E2E；
- 56张四档视觉基线；
- Directory Invariants、Secret Scan、Version Consistency和Baseline Audit。

Draft PR始终保持Open、Draft、Unmerged；不得修改或合并`main`。

## 6. 非目标

- 不增加Research微服务；
- 不替换AkShare、东方财富、腾讯、巨潮或Polymarket数据源；
- 不改变真实Provider验收口径；
- 不改变Execution Runtime或Live Write边界；
- 不在Research或主看板重构中顺带修改Identity、Portfolio、Trading、Risk、Accounting或Reconciliation；
- 不因行数大而机械拆分显式数据映射；
- 不为通过格式门禁而批量格式化整个历史热点文件。
