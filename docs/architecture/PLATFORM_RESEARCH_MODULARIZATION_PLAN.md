# Platform Research低风险模块化计划

状态：**E2.2 A股概览Provider完成，进入E2.3个股Provider依赖审计**  
关联Issue：#136  
关联Draft PR：#139  
审计分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 1. 目标

在不改变Research API合同、权限、页面视觉、数据源语义或Last Known Good行为的前提下，降低Research域高频修改所需上下文和单文件职责密度。

本阶段保留Platform Web / Platform API / Execution Runtime三大边界，不拆微服务，不引入新的框架或依赖注入容器。

## 2. 当前证据

使用以下只读命令生成可重复证据：

```bash
python scripts/audit-research-modularity.py \
  --format markdown \
  --output outputs/research-modularity-inventory.md
```

### 2.1 Platform API

E0审计基线：

| 文件 | 行数 | 当前职责 |
|---|---:|---|
| `platform-api/app/research_providers.py` | 999 | 第三方连接、字段归一化、A股概览、申万、情绪、个股、宏观预期 |
| `platform-api/app/research_service.py` | 475 | 并发编排、模块隔离、缓存、锁、LKG、宏观历史状态 |
| `platform-api/app/a_share_research_policy.py` | 232 | 无副作用的研究计算与申万聚合 |
| `platform-api/app/research_data_schemas.py` | 211 | 对外Pydantic合同 |
| `platform-api/app/research_cache.py` | 66 | 通用Last Known Good缓存 |
| `platform-api/app/research_routes.py` | 78 | FastAPI路由、权限和缓存头 |

`FreeResearchProvider`基线约881行、26个方法；`research_service.py`直接调用其中21个方法。当前已依次抽离纯归一化、宏观预期和A股概览职责，Facade公开方法与Service调用面保持不变。

当前依赖方向为：

```text
research_routes
    -> research_service
        -> research_cache
        -> a_share_research_policy
        -> research_providers                 # stable facade / stock methods remain
            -> research_provider_a_share
            -> research_provider_macro
            -> research_provider_errors
            -> research_provider_normalization
            -> research_data_schemas
```

`research_provider_a_share`通过构造参数接收Facade现有AkShare延迟加载器，不复制加载逻辑；该加载器仍供尚未拆分的个股方法使用。当前没有反向导入。

### 2.2 Platform Web

| 文件 | 行数 | 当前判断 |
|---|---:|---|
| `platform-web/src/views/hedgeBoard/index.vue` | 3,772 | 主热点；内联11个渲染组件，脚本约2,235行、样式约1,486行 |
| `platform-web/src/views/hedgeBoard/aShare/index.vue` | 389 | 页面Composition已相对清晰 |
| `platform-web/src/views/hedgeBoard/aShare/useAShareResearch.ts` | 429 | A股请求、缓存、观察列表和导出状态集中 |
| `platform-web/src/api/hedgeResearch.ts` | 227 | 三条Research API的类型与Client合同 |

A股页面已经拆为六个可见组件和一个Composable。当前前端最优先的结构性问题不是A股页面，而是`hedgeBoard/index.vue`中以下内联组件：

- `TradingViewWidget`
- `WidgetErrorBoundary`
- `MetricStrip`
- `DualAxisChart`
- `TreasuryFlowChart`
- `GroupedBarChart`
- `EtfWeeklyFlowsPanel`
- `YtdSummaryPanel`
- `ReserveRanking`
- `SnapshotDetailTable`
- `LocalChartWidget`

## 3. 不可改变合同

### 3.1 API与权限

以下路由、HTTP语义和`platform:read`权限保持不变：

```text
GET /api/v1/research/a-share/dashboard
GET /api/v1/research/a-share/stocks/{code}/snapshot
GET /api/v1/research/macro/expectations
```

### 3.2 数据状态

必须保持：

```text
loading / ready / partial / no_data / stale / error
```

以下语义不得弱化：

- 单一Provider失败不得拖垮其他模块；
- 当前刷新失败时优先返回Last Known Good并标记`stale`；
- Fixture、Simulation和Fake Runtime不得冒充真实Provider或生产数据；
- Decimal、时间戳、source、error_code和message字段语义保持不变。

### 3.3 页面与操作

- 不改变Research页面路由、导航、信息层级和主要操作习惯；
- 不改变四档视觉基线；
- 不改变观察列表、CSV导出、个股快照和宏观预期交互。

## 4. 实施门禁

### E0 — 依赖与规模审计：完成

- [x] 建立只读审计脚本；
- [x] 量化前后端热点、Provider方法和API合同；
- [x] 确认A股页面已有组件边界；
- [x] 确认Provider与主看板内联组件为优先热点。

### E1 — Provider纯归一化层：完成

- [x] 抽离Decimal、非负整数、日期、DataFrame records、多字段择优；
- [x] 抽离收益率、趋势和最近历史值计算；
- [x] 新模块纳入Pyright并增加边界输入单元测试；
- [x] Provider公开方法、第三方请求、超时、并发和异常处理保持不变；
- [x] 一次性执行器与机械脚本已删除；
- [x] E1完整质量矩阵全部通过。

### E2 — Provider按数据域拆分：进行中

保留`FreeResearchProvider`作为稳定Facade，使用显式组合和委托，不采用隐式多继承。

#### E2.1 宏观预期Adapter：完成

- [x] 建立`research_provider_macro.py`和共享错误模块；
- [x] 保持Polymarket请求、分类、概率、排序、Limit和失败语义；
- [x] 增加Adapter单元测试并纳入Pyright；
- [x] Facade仅改为显式委托；
- [x] 一次性执行器与机械脚本已删除；
- [x] E2.1完整质量矩阵全部通过。

#### E2.2 A股概览Adapter：完成

- [x] 建立`research_provider_a_share.py`；
- [x] 迁移`a_share_spot`、`market_activity`、指数快照、申万和短期情绪；
- [x] 迁移`_index_snapshot`、`_intraday_signal`和`_limit_pool`私有实现；
- [x] 保持8个指数定义、`asyncio.gather(..., return_exceptions=True)`异常隔离和无有效指数时的错误语义；
- [x] 保持涨跌停池Endpoint、Token、分页、Sort、Referer、User-Agent、超时和失败返回空列表语义；
- [x] AkShare延迟加载器由Facade显式注入，不复制或提前导入AkShare；
- [x] 新Adapter纳入Pyright；
- [x] 增加现货归一化、指数部分成功、情绪池映射和HTTP合同测试；
- [x] Facade的5个公开方法仅改为显式委托，21个Service调用面不变；
- [x] 16个个股研究方法保持原地；
- [x] 一次性执行器与机械脚本已删除。

#### E2.3 个股研究Adapter：下一门禁

候选范围包括行情、财务、预告、估值、新闻、研报、公告、两融、大宗交易、持有人、分红、资金流、龙虎榜、解禁和互动问答。

实施前必须先完成：

1. 量化16个方法对AkShare、腾讯报价、东方财富HTTP和通用DataCenter查询的依赖；
2. 明确`datacenter_rows()`是否应先成为独立无状态Client；
3. 冻结所有Report Name、Filter、Sort、Referer、编码和错误语义；
4. 保持Facade和Service调用面；
5. 不与Service缓存、LKG、宏观历史或前端组件重构混合。

### E3 — Service状态职责

- 将宏观概率历史存储从Service编排中分离；
- 保留缓存Key、TTL、锁和LKG策略；
- 不把缓存或状态下沉到第三方Provider Adapter。

### E4 — 主看板渲染组件

优先提取无业务请求副作用的内联组件和图表数学工具：

1. Error Boundary与TradingView Widget；
2. 通用坐标轴、Range Selector和图表数学；
3. 本地Research图表组件；
4. 对应样式随组件迁移。

每次只移动一个可视职责，保持Props、渲染DOM和CSS选择器稳定。

### E5 — A股Composable复核

仅在E1–E4通过后评估Dashboard请求、个股快照、观察列表远端同步与CSV导出。除非证据显示变化频率或测试边界受益，否则不为追求文件数量机械拆分。

## 5. 每步验收

每个结构提交必须通过：

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
- 不替换AkShare、东方财富、腾讯或Polymarket数据源；
- 不改变真实Provider验收口径；
- 不改变Execution Runtime或Live Write边界；
- 不在Research重构中顺带处理Identity、Portfolio、Trading、Risk、Accounting或Reconciliation；
- 不因行数大而机械拆分显式数据映射。
