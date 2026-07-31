# Platform Research低风险模块化计划

状态：**E2.3b Stock DataCenter Adapter完成，进入E2.3c AkShare个股Adapter**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 1. 目标

在不改变Research API合同、权限、页面视觉、数据源语义或Last Known Good行为的前提下，降低Research域高频修改所需上下文和单文件职责密度。

保留Platform Web / Platform API / Execution Runtime三大边界，不拆微服务，不引入新的框架或依赖注入容器。

## 2. 当前证据

使用以下只读命令生成可重复证据：

```bash
python scripts/audit-research-modularity.py \
  --format markdown \
  --output outputs/research-modularity-inventory.md
```

E0基线：`research_providers.py`共999行，`FreeResearchProvider`约881行、26个方法；`research_service.py`调用其中21个方法。当前已依次抽离：

```text
research_provider_normalization.py
research_provider_macro.py
research_provider_a_share.py
research_provider_datacenter.py
research_provider_stock_datacenter.py
research_provider_errors.py
```

当前依赖方向：

```text
research_routes
    -> research_service
        -> research_cache
        -> a_share_research_policy
        -> research_providers                  # stable facade
            -> research_provider_a_share
            -> research_provider_macro
            -> research_provider_datacenter
            -> research_provider_stock_datacenter
            -> research_provider_errors
            -> research_provider_normalization
            -> research_data_schemas
```

Facade公开方法、三条Research API与Service调用面保持不变。Adapter不持有缓存、LKG、Completeness或跨请求状态。

Platform Web当前主热点仍为`platform-web/src/views/hedgeBoard/index.vue`：约3,772行、11个内联渲染组件。A股页面本身已有六个可见组件和一个Composable，暂不机械拆分。

## 3. 不可改变合同

### API与权限

```text
GET /api/v1/research/a-share/dashboard
GET /api/v1/research/a-share/stocks/{code}/snapshot
GET /api/v1/research/macro/expectations
```

以上路由、HTTP语义和`platform:read`权限保持不变。

### 数据状态与容错

```text
loading / ready / partial / no_data / stale / error
```

必须保持：

- 单一Provider失败不得拖垮其他模块；
- 当前刷新失败时优先返回Last Known Good并标记`stale`；
- Fixture、Simulation和Fake Runtime不得冒充真实Provider或生产数据；
- Decimal、时间戳、source、error_code、message和Completeness语义不变；
- Adapter不得自行缓存或吞掉原先向Service传播的异常。

### 页面与操作

- 不改变Research页面路由、导航、信息层级和主要操作习惯；
- 不改变四档视觉基线；
- 不改变观察列表、CSV导出、个股快照和宏观预期交互。

## 4. 实施门禁

### E0 — 依赖与规模审计：完成

- [x] 建立只读审计脚本；
- [x] 量化前后端热点、Provider方法和API合同；
- [x] 冻结状态词汇、LKG和页面视觉边界。

### E1 — Provider纯归一化层：完成

- [x] 抽离Decimal、非负整数、日期、DataFrame records、多字段择优；
- [x] 抽离收益率、趋势和最近历史值计算；
- [x] 纳入Pyright并增加边界输入测试；
- [x] 完整质量矩阵通过。

### E2 — Provider按数据域拆分：进行中

保留`FreeResearchProvider`作为稳定Facade，使用显式组合和委托，不采用隐式多继承。

#### E2.1 宏观预期Adapter：完成

- [x] 建立`research_provider_macro.py`和共享错误模块；
- [x] 保持Polymarket请求、分类、概率、排序、Limit和失败语义；
- [x] 增加Adapter测试并纳入Pyright；
- [x] 真实Provider Smoke与完整矩阵通过。

#### E2.2 A股概览Adapter：完成

- [x] 建立`research_provider_a_share.py`；
- [x] 迁移现货、市场宽度、八指数快照、申万和短期情绪；
- [x] 保持AkShare延迟加载、指数异常隔离及涨跌停池完整HTTP合同；
- [x] 增加现货、指数、情绪和HTTP合同测试；
- [x] 完整质量矩阵通过。

#### E2.3a Eastmoney DataCenter Client：完成

- [x] 建立无状态`EastmoneyDataCenterClient`；
- [x] 保持URL、Report Name、Filter、分页、Sort、Source、Client、User-Agent、超时和JSON提取语义；
- [x] 保持HTTP错误与畸形Payload向上抛出；
- [x] Facade保留`datacenter_rows()`兼容委托；
- [x] 六个派生方法暂不移动；
- [x] 新增精确HTTP合同及异常测试并纳入Pyright；
- [x] 完整矩阵全部通过：
  - Platform CI `30602550119`
  - Directory `30602550137`
  - User E2E `30602550112`
  - Hedge E2E `30602550136`
  - Visual `30602550151`
  - Provider Smoke `30602550113`
  - Secret `30602550114`
  - Version `30602550129`
  - Audit `30602550118`
- [x] 视觉Artifact ID `8782483998`，SHA-256 `d6e186466fe782dfe5b1e16b5750d808a95f929ab73b97ee2c8b5fdf7e78c890`。

#### E2.3b Stock DataCenter Adapter：完成

- [x] 建立`research_provider_stock_datacenter.py`；
- [x] 迁移融资融券、大宗交易、股东人数、分红、龙虎榜和限售解禁；
- [x] 保持六个Report Name、Filter、分页、排序、日期窗口与字段映射；
- [x] 保持大宗交易Decimal溢价计算；
- [x] 保持龙虎榜买卖席位二次查询及Top 5限制；
- [x] 保持解禁历史/未来90日双查询并发；
- [x] Facade六个公开方法仅改为显式委托；
- [x] `datacenter_rows()`兼容入口仍保留；
- [x] 其余9个公开个股方法保持原地；
- [x] 增加Report合同、字段映射、溢价、席位和解禁测试并纳入Pyright；
- [x] 完整矩阵全部通过：
  - Platform CI `30602935788`
  - Directory `30602935739`
  - User E2E `30602935780`
  - Hedge E2E `30602935795`
  - Visual `30602935741`
  - Provider Smoke `30602935786`
  - Secret `30602935746`
  - Version `30602935770`
  - Audit `30602935752`
- [x] 视觉Artifact ID `8782620603`，SHA-256 `64c63a77550f6547eacf800bf82dc16c481a80069c2a1cd547a4216e00799894`。

#### E2.3c AkShare个股Adapter：下一门禁

候选范围仅包括：

```text
stock_financials
stock_forecast
stock_valuation_percentile
stock_news
```

实施要求：

1. 继续注入Facade现有AkShare延迟加载器，不复制或提前导入AkShare；
2. 冻结全部AkShare函数名、参数、DataFrame字段择优、排序、Limit和空结果语义；
3. Facade四个公开方法只改为委托；
4. 不移动腾讯行情、东方财富研报/公告/资金流和巨潮互动易五个独立HTTP方法；
5. 不改变Stock Snapshot模块隔离、Completeness、缓存、LKG或状态词汇；
6. 增加Adapter契约测试并纳入Pyright；
7. 完成后重跑完整质量矩阵。

#### E2.3d 独立HTTP个股Adapter：后置

候选范围：

```text
stock_quote
stock_reports
stock_announcements
stock_fund_flow
stock_investor_qa
```

该阶段必须按数据源冻结腾讯、东方财富和巨潮的编码、Endpoint、参数、Header、时间转换与异常语义，不与E2.3c混合。

### E3 — Service状态职责

- 将宏观概率历史存储从Service编排中分离；
- 保留缓存Key、TTL、锁和LKG策略；
- 不把缓存或状态下沉到第三方Provider Adapter。

### E4 — 主看板渲染组件

优先提取无业务请求副作用的内联组件和图表数学工具，保持Props、DOM和CSS选择器稳定。

### E5 — A股Composable复核

仅在E1–E4通过后评估Dashboard请求、个股快照、观察列表远端同步与CSV导出；不为追求文件数量机械拆分。

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
- 不替换AkShare、东方财富、腾讯、巨潮或Polymarket数据源；
- 不改变真实Provider验收口径；
- 不改变Execution Runtime或Live Write边界；
- 不在Research重构中顺带处理Identity、Portfolio、Trading、Risk、Accounting或Reconciliation；
- 不因行数大而机械拆分显式数据映射。
