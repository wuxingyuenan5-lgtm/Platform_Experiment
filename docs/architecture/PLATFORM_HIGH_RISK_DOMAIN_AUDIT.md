# Platform高风险业务域只读审计

状态：**H0责任盘点与H1 EOD路由Owner完成；H2 Venue路由仅只读复核**  
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

### Reconciliation：存在显式路由债务

Venue与EOD均已分离Schemas、Policy、Repository、Runtime Client与Service。Facade仍曾同时承担兼容导出、HTTP错误映射和FastAPI路由，Ownership目录明确标注待独立路由模块。

## H1 EOD路由Owner：完成

### 已实施

- [x] 新增`platform-api/app/eod_reconciliation_routes.py`；
- [x] 仅迁移`APIRouter`、`Query`、router定义和四个HTTP端点；
- [x] 路由模块运行时调用`app.eod_reconciliation` Facade；
- [x] `main.py`改为从专用路由模块导入router；
- [x] Facade继续拥有Repository/Service兼容别名、每次调用依赖装配和精确HTTP错误映射；
- [x] 保留现有Monkeypatch端口与函数名；
- [x] 更新Ownership和永久架构测试；
- [x] 删除全部一次性写权限Workflow和迁移脚本。

### 冻结HTTP合同

- `POST /ops/eod-reconciliation/reports`；
- `GET /ops/eod-reconciliation/reports/{report_id}`；
- `GET /ops/eod-reconciliation/reports`；
- `POST /ops/eod-reconciliation/reports/{report_id}/review`；
- 查询别名：`strategyInstanceId`、`accountId`、`businessDate`；
- response models、tags、409/404/422状态与文案不变。

Service、Policy、Repository、Schemas、Financial Fact、Venue Reconciliation、DDL、Decimal、自然键、幂等性、Review不可变性和Scale Gate均未修改。

### H1完整矩阵

验证HEAD：`5f992691c35921c0647cd8e7f800fca48a547359`

- Platform CI：`30640101027`
- Platform Directory Invariants：`30640101717`
- Version Consistency：`30640100742`
- Secret Scan：`30640100821`
- User System Browser E2E：`30640100255`
- Platform 0.9.2 Baseline Audit：`30640100980`
- Platform Visual Baseline：`30640101256`
- Hedge Board Browser E2E：`30640101724`
- Research Provider Smoke：`30640100623`

视觉Artifact：`8797146922`  
SHA-256：`f722456de6afce3068239a2de51ca58895133aa6cbd1eef6f0af9afc1ab00453`

## H2当前门禁：Venue路由只读复核

Venue Facade暴露订单、账户、Position、Balance、Difference、Runtime查询与跨域兼容端口，消费者面显著大于EOD。H2只能读取和建模，暂不批准代码迁移。

必须确认：

1. 五个Venue HTTP端点的精确路径、方法、response model、Query与错误映射；
2. 所有跨域兼容导出和直接调用方；
3. 路由是否能够仅通过Facade运行时调用而不改变Monkeypatch或依赖端口；
4. `venue_reconciliation.py`是否仍有非路由FastAPI职责必须保留；
5. 现有API、Service、Policy、Repository、Runtime Client和跨域Golden覆盖；
6. 拆分收益是否足以抵消更广的兼容消费者面。

若必须修改Service、Repository、Policy、Runtime Client、Financial Fact、错误映射或兼容函数，立即停止Venue路由抽取并记录保留决定。

Draft PR必须保持Open、Draft、Unmerged；不得修改或合并`main`。
