# Platform高风险业务域审计与边界治理

状态：**H0–H2完成；高风险结构治理正式收口**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 审计原则

高风险域禁止以“文件过大”或“模块化”为迁移理由。代码切口必须同时满足：

1. 现有Owner、Golden与失败关闭合同明确；
2. 迁移对象不包含业务计算、状态机、SQL、外部副作用或安全决策；
3. HTTP、DTO、Decimal、幂等性、错误映射与兼容端口可逐项冻结；
4. 具备独立回滚点和完整质量矩阵；
5. 新边界减少职责混合，而不是增加抽象层。

## H0责任盘点结论

### Trading：保留现状

- `trade_command_execution.py`拥有Order创建、安全校验、Runtime分发、Result Unknown与Event移交；
- `order_execution_intents.py`拥有reduce-only、Venue目标与执行策略意图；
- Cross-spread Market、Limit、FOK、PostOnly、TP/SL与Exit Plan已有专用Owner；
- 未发现第二套订单提交Owner或可安全迁移的纯职责。

### Risk：保留现状

Execution Risk、Kill Switch、双人审批、Live Write与账户/策略约束已有独立Owner和默认关闭语义。Browser Session不能替代API-Key或Live授权。

### Formal Accounting：保留现状

- `financial_fact_normalization.py`拥有不可变事实规范化与内容Hash；
- `financial_fact_repository.py`拥有事实与正式投影持久化；
- `financial_projection_service.py`拥有Financial Fact重放、Multiplier/FX、组件PnL、正式重建与NAV；
- `position_math.py`是Operational与Formal共享的唯一纯仓位计算Owner；
- Operational projection不得作为Formal calculation输入。

### Execution Runtime：保留边界

`execution-runtime/`继续独占Venue SDK、外部副作用与Runtime Journal。Platform API只能通过版本化Runtime合同发送命令和读取结果。

### Reconciliation：仅存在路由混合债务

Venue与EOD已拥有独立Schemas、Policy、Repository、Runtime Client与Service。H0确认剩余结构债务仅为Facade同时承担兼容端口、HTTP错误映射和FastAPI路由。

## H1 EOD路由Owner：完成

- [x] 新增`platform-api/app/eod_reconciliation_routes.py`；
- [x] 仅迁移四个HTTP端点、response models、tags和Query别名；
- [x] 路由模块运行时调用`app.eod_reconciliation` Facade；
- [x] Facade保留兼容别名、每次调用依赖装配和精确409/404/422映射；
- [x] Service、Policy、Repository、Schemas、Financial Fact、Venue Reconciliation、DDL、Decimal与失败关闭语义未修改；
- [x] 更新Ownership和永久架构测试；
- [x] 删除全部一次性写权限工具。

验证HEAD：`5f992691c35921c0647cd8e7f800fca48a547359`

- Platform CI：`30640101027`
- Directory：`30640101717`
- Version：`30640100742`
- Secret：`30640100821`
- User E2E：`30640100255`
- Audit：`30640100980`
- Visual：`30640101256`
- Hedge E2E：`30640101724`
- Provider Smoke：`30640100623`

视觉Artifact：`8797146922`  
SHA-256：`f722456de6afce3068239a2de51ca58895133aa6cbd1eef6f0af9afc1ab00453`

## H2 Venue路由Owner：完成

### 只读复核结论

Venue Facade拥有更广的兼容面，但直接消费者均依赖Facade函数或兼容别名，而非router对象：

- EOD使用`audit`、`reconcile_order_with_venue`、`run_account_reconciliation`和`validate_strategy_account`；
- Live Accounting使用`audit`、`canonical_hash`、`runtime_get`和`validate_strategy_account`；
- Live Trading Session使用`ensure_schema`；
- API、Service与Runtime Client测试直接Monkeypatch Facade或Service端口。

因此只迁移router与五个端点不会改变跨域消费者。Facade必须继续作为稳定兼容边界。

### 已实施

- [x] 新增`platform-api/app/venue_reconciliation_routes.py`；
- [x] 仅迁移五个HTTP端点、response models和tags；
- [x] `main.py`改为从专用路由模块导入router；
- [x] 路由模块运行时调用`app.venue_reconciliation` Facade；
- [x] Facade保留全部Repository别名、Service Delegate、Runtime 503和域错误422/409/403/404映射；
- [x] 保留现有Monkeypatch端口及所有直接跨域消费者；
- [x] Service、Policy、Repository、Runtime Client、Schemas、Financial Fact、Operational projection、DDL与Decimal未修改；
- [x] 永久架构测试冻结Service、Facade、Routes与Main四边界；
- [x] 更新Ownership目录；
- [x] 删除全部一次性写权限Workflow和迁移脚本。

### 冻结HTTP合同

- `POST /trading/orders/{order_id}/venue-reconcile`；
- `POST /ops/venue-reconciliation/runs`；
- `GET /ops/venue-reconciliation/runs/{run_id}`；
- `GET /ops/venue-reconciliation/runs/{run_id}/differences`；
- `POST /ops/venue-reconciliation/differences/{difference_id}/resolve`；
- response models、tags与503/422/409/403/404错误合同不变。

### H2完整矩阵

验证HEAD：`7c60ac24d0b728a0c5383530310752a3070ed876`

- Platform CI：`30641383890`
- Platform Directory Invariants：`30641383425`
- Version Consistency：`30641384052`
- Secret Scan：`30641383524`
- User System Browser E2E：`30641383467`
- Platform 0.9.2 Baseline Audit：`30641383452`
- Platform Visual Baseline：`30641383554`
- Hedge Board Browser E2E：`30641383539`
- Research Provider Smoke：`30641383446`

视觉Artifact：`8797697682`  
SHA-256：`3898d7b32d1413c8fddfe5c024c4c1eea31b67b05561ca66a5e48dd8355f6d93`

## 高风险结构治理停止结论

H0保留了已经内聚的Trading、Risk、Formal Accounting与Execution Runtime边界；H1/H2清除了Reconciliation Facade中唯一明确的FastAPI路由混合债务。

剩余高风险模块没有第二套业务Owner、明确重复实现或可在不迁移策略/SQL/副作用的前提下形成的新切口。继续拆分将增加兼容层与测试面，而不会降低业务风险。

因此停止高风险域代码迁移。后续只有在出现真实重复、产品变更或验收缺口时才重新开启专项审计。

## 下一门禁：Legacy L0部署与数据依赖定性

只读审计`projects/risk-control`及旧Go/MySQL资产，确认：

1. 是否仍被服务器、定时任务、用户数据或生产流程使用；
2. Go/MySQL依赖、环境变量、部署入口、数据库Schema与迁移责任；
3. 与当前Platform API / Execution Runtime是否存在功能重叠或真实外部依赖；
4. 哪些内容属于历史证据、可归档资产、仍在用系统或不可删除数据；
5. 在完成服务器与数据证据前，不删除、不重命名、不迁移该目录。

Draft PR必须保持Open、Draft、Unmerged；不得修改或合并`main`。
