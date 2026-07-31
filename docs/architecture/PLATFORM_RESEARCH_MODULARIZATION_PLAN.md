# Platform Research低风险模块化计划

状态：**E3 Research Service宏观历史职责已完成，等待当前HEAD完整矩阵收口**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 1. 目标

在不改变Research API合同、权限、页面视觉、数据源语义、Completeness或Last Known Good行为的前提下，降低Research域高频修改所需上下文和单文件职责密度。

保留Platform Web / Platform API / Execution Runtime三大边界，不拆微服务，不引入新的框架、复杂依赖注入或跨域状态容器。

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

- Research页面路由、导航、信息层级和主要操作习惯不变；
- 四档视觉基线不变；
- 观察列表、CSV导出、个股快照和宏观预期交互不变。

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
```

`FreeResearchProvider`公开方法、三条Research API与Service调用面保持不变。

## 4. 实施门禁

### E0 — 依赖与规模审计：完成

- [x] 建立只读审计脚本；
- [x] 冻结Provider方法、API合同、状态词汇、LKG和页面视觉边界；
- [x] 确认原始`research_providers.py`为999行，`FreeResearchProvider`约881行、26个方法；
- [x] 确认Platform Web主热点仍为约3,772行的`hedgeBoard/index.vue`。

### E1 — Provider纯归一化层：完成

- [x] 抽离Decimal、整数、日期、DataFrame records、多字段择优；
- [x] 抽离收益率、趋势和最近历史值计算；
- [x] 增加边界测试并纳入Pyright；
- [x] 完整质量矩阵通过。

### E2 — Provider按数据域拆分：完成

保留`FreeResearchProvider`作为稳定Facade，全部使用显式组合和委托。

#### E2.1 宏观预期Adapter

- [x] Polymarket请求、分类、概率、排序、Limit和失败语义保持不变；
- [x] 真实Provider Smoke与完整矩阵通过。

#### E2.2 A股概览Adapter

- [x] 迁移现货、市场宽度、八指数快照、申万和短期情绪；
- [x] 保持AkShare延迟加载、指数异常隔离及涨跌停池HTTP合同；
- [x] 完整矩阵通过。

#### E2.3a Eastmoney DataCenter Client

- [x] 建立无状态`EastmoneyDataCenterClient`；
- [x] 保持URL、Report Name、Filter、分页、Sort、Header、超时、JSON提取和异常传播；
- [x] Facade保留`datacenter_rows()`兼容委托；
- [x] 完整矩阵通过。

#### E2.3b Stock DataCenter Adapter

- [x] 迁移融资融券、大宗交易、股东人数、分红、龙虎榜和限售解禁；
- [x] 保持Report、日期窗口、字段映射、Decimal溢价、席位Top 5和解禁并发；
- [x] 完整矩阵通过。

#### E2.3c Stock AkShare Adapter

- [x] 迁移`stock_financials`、`stock_forecast`、`stock_valuation_percentile`和`stock_news`；
- [x] 复用Facade现有AkShare延迟加载器；
- [x] 保持函数名、参数、字段择优、排序、Limit和空结果语义；
- [x] Facade四个方法仅改为显式委托；
- [x] 完整矩阵通过。

#### E2.3d Stock HTTP Adapter

- [x] 迁移`stock_quote`、`stock_reports`、`stock_announcements`、`stock_fund_flow`和`stock_investor_qa`；
- [x] 保持腾讯GBK行情、东方财富研报/公告/资金流、巨潮互动易的Endpoint、参数、Header和时间转换；
- [x] 保持行情金额缩放、Decimal和异常传播；
- [x] Facade五个方法仅改为显式委托；
- [x] 临时执行器已删除；
- [x] 完整质量矩阵通过：
  - Platform CI `30608770712`
  - Directory `30608770720`
  - User E2E `30608770763`
  - Hedge E2E `30608770689`
  - Visual `30608770701`
  - Provider Smoke `30608770724`
  - Secret `30608770741`
  - Version `30608770714`
  - Audit `30608770688`
- [x] 视觉Artifact ID `8784674299`，SHA-256 `fd0b00faea120390e7ea531cfddaab72e2e931805441f70487c9bb20d50959df`。

### E3 — Research Service状态职责：代码完成，最终矩阵待收口

- [x] 建立`research_macro_history.py`；
- [x] 将宏观概率JSON读取、原子写入、90日窗口、分钟去重和1日/7日变化计算移出Service；
- [x] 保持`RESEARCH_MACRO_HISTORY_PATH`和默认路径；
- [x] 保持异步锁与`asyncio.to_thread`文件I/O；
- [x] Service仅保留`_MACRO_HISTORY`组合调用；
- [x] `_MACRO_CACHE`、15分钟TTL、`_MACRO_LOCK`、LKG及`ready/stale/error`分支仍在Service；
- [x] 增加独立契约测试并纳入Pyright；
- [x] 目标Ruff、Pyright和Research测试通过；
- [x] 一次性写权限Workflow与脚本已删除；
- [ ] 以清理和文档同步后的最终HEAD完成全质量矩阵。

### E4 — 主看板渲染组件：下一门禁

仅提取无业务请求副作用的内联渲染组件和纯图表数学工具：

1. 先只读审计11个内联组件的Props、Emits、DOM、CSS选择器和状态依赖；
2. 优先选择纯展示、低耦合且已有视觉覆盖的单一组件；
3. 不移动请求、缓存、观察列表、CSV、个股快照或宏观状态；
4. 不改变页面路由、DOM语义、CSS类名或四档视觉；
5. 每个切口独立提交并跑完整矩阵；
6. 不为追求文件数量机械拆分。

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
- 不在Research重构中顺带修改Identity、Portfolio、Trading、Risk、Accounting或Reconciliation；
- 不因行数大而机械拆分显式数据映射。
