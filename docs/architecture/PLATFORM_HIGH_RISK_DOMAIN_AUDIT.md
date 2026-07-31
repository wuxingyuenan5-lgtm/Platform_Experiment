# Platform高风险业务域只读审计

状态：**H0责任盘点完成；H1仅批准EOD路由模块边界验证**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 审计目标

在不改变交易、风险、会计、对账或Runtime语义的前提下，确认高风险域的现有Owner、失败关闭合同、Golden与真实结构债务。

本阶段禁止以“文件过大”或“模块化”作为代码迁移理由。只有同时满足以下条件的切口才可进入实现：

1. 现有职责边界已由Owner目录和测试明确描述；
2. 迁移对象不包含业务计算、状态机、SQL、外部副作用或安全决策；
3. HTTP、DTO、Decimal、幂等性、错误映射和失败关闭语义可逐项冻结；
4. 现有消费者和兼容端口能够保持不变；
5. 具备单独回滚点和完整质量矩阵。

## H0现有Owner盘点

### Trading

- `trade_command_execution.py`拥有单一Order创建、安全校验、Runtime分发、Result Unknown与Event移交；
- `order_execution_intents.py`拥有reduce-only、Venue目标与执行策略意图；
- Cross-spread Market、Limit、FOK、PostOnly、TP/SL与Exit Plan已由多个专用Owner分离；
- 当前未发现第二套订单提交Owner或可安全迁移的纯展示职责。

结论：保留现状，不进行Trading代码迁移。

### Risk

- Execution Risk、Kill Switch、双人审批、Live Write与账户/策略约束已有独立Owner和默认关闭语义；
- Browser Session不能替代API-Key或Live授权；
- 风险门禁与订单提交相邻但并非重复实现。

结论：保留现状，不进行Risk代码迁移。

### Formal Accounting

- `financial_fact_normalization.py`拥有不可变事实规范化与内容Hash；
- `financial_fact_repository.py`拥有事实与正式投影持久化；
- `financial_projection_service.py`拥有Financial Fact重放、Multiplier/FX、组件PnL、正式重建与NAV；
- `position_math.py`是Operational与Formal共享的唯一纯仓位计算Owner；
- Operational projection不得作为Formal calculation输入。

结论：会计边界已内聚，不进行Accounting代码迁移。

### Execution Runtime

- `execution-runtime/`拥有Venue SDK、外部副作用与Runtime Journal；
- Platform API通过版本化Runtime合同发送命令和读取结果；
- Platform不得获得Venue SDK或绕过Runtime Journal。

结论：保留Platform API / Execution Runtime边界，不迁移外部副作用。

### Reconciliation

Venue与EOD均已分离Schemas、Policy、Repository、Runtime Client与Service。剩余Facade仍同时承担兼容导出、HTTP错误映射和FastAPI路由。

- `venue_reconciliation.py`暴露大量跨域兼容端口，供EOD和其他调用方复用；
- `eod_reconciliation.py`只有四个公开用例Delegate、每次调用依赖装配、四类稳定HTTP错误映射和四个路由；
- Ownership目录已将两者标记为“routes pending dedicated route-module extraction”。

## 候选比较

### Venue路由：暂缓

Venue Facade同时暴露订单、账户、Position、Balance、Difference与Runtime查询兼容端口。直接拆分虽然可以机械完成，但消费者面更广，容易把路由治理与跨域兼容治理混为一体。

停止原因：当前不是最小独立切口。

### EOD路由：批准进入H1验证

EOD具备清晰的路由边界：

- `POST /ops/eod-reconciliation/reports`；
- `GET /ops/eod-reconciliation/reports/{report_id}`；
- `GET /ops/eod-reconciliation/reports`；
- `POST /ops/eod-reconciliation/reports/{report_id}/review`。

列表查询别名固定为：

- `strategyInstanceId`；
- `accountId`；
- `businessDate`。

现有Browser/API Golden已覆盖：

- 创建与幂等回放；
- Payload冲突409；
- Clean report审批；
- Review不可变冲突409；
- 非Clean审批422；
- 列表过滤与查询别名；
- 外部失败必须形成`failed + blocked`报告，不能伪装为Complete。

## H1允许范围：EOD路由Owner

仅允许：

1. 新增`platform-api/app/eod_reconciliation_routes.py`；
2. 将`APIRouter`、`Query`、router定义和四个端点函数机械迁移至新模块；
3. 路由模块通过`from app import eod_reconciliation as facade`在调用时访问Facade；
4. `main.py`改为从新路由模块导入router；
5. 更新架构测试与Ownership目录；
6. 删除一次性迁移工具。

Facade必须继续拥有并保持：

- Repository/Service稳定兼容别名；
- `_service_dependencies()`每次调用装配；
- `_call_service()`精确HTTP状态与文案映射；
- `create_eod_report`、`get_eod_report`、`list_eod_reports`、`review_eod_report`函数名；
- 可被现有测试Monkeypatch的依赖端口。

## H1禁止范围

- 不修改Service、Policy、Repository、Schemas、Financial Fact或Venue Reconciliation；
- 不改变四个路径、HTTP方法、response model、tags或查询别名；
- 不改变409、404、422错误状态与文案；
- 不改变报告状态、Scale Gate、Review不可变性、幂等性或失败报告语义；
- 不修改数据库DDL、Migration、Decimal、时区或自然键；
- 不抽取Venue路由；
- 不引入DI容器、框架、微服务或新全局状态。

## Required verification

- 永久架构测试冻结Facade、Routes与Main三边界；
- EOD完整API Golden与Policy/Service/Repository测试；
- Platform API Ruff、Pyright和完整Pytest；
- Platform Web Lint、no-new-debt、两套Type Check和Build；
- Execution Runtime完整检查；
- User System与Hedge Board Browser E2E；
- Provider Smoke、Secret、Version、Directory、Baseline Audit；
- 56页四档视觉基线。

## Stop conditions

出现以下任一情况立即停止并回滚：

- 现有Monkeypatch端口或兼容导出失效；
- 路径、查询别名、response model、错误状态或文案变化；
- EOD失败被误报为Complete或Scale Gate不再Fail Closed；
- 需要修改Service、Policy、Repository、Schema或Venue逻辑；
- 新路由模块获得SQL、Runtime、Financial Fact或业务策略依赖；
- 任一完整门禁失败且不能证明为非本切口原因。

Draft PR必须保持Open、Draft、Unmerged；不得修改或合并`main`。
