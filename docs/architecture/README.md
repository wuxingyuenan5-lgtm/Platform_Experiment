# Architecture Documentation

本目录保存长期稳定的系统架构说明。最简拓扑和依赖方向见 `SYSTEM_MAP.md`。

## 文档职责

- 架构说明：解释系统边界和模块关系。
- `docs/decisions/`：记录关键技术决策。
- `docs/operations/`：记录运行和生产流程。
- `docs/technical/`：记录接口和领域设计。
- `docs/contracts/`：保存可执行的跨服务版本快照。
- `docs/database/`：记录数据权威、DDL Owner 和迁移纪律。

## 原则

不要把历史执行过程、PR 记录和临时任务放入架构文档。

架构文档回答系统为何这样设计、模块如何协作、哪些边界不能突破、数据/契约由谁负责，以及故障时必须保持哪些不变量。具体实施记录进入对应 Issue、任务包、PR 或 Changelog。

## Composition Root 边界

- `platform-backend/app/main.py` 只装配 Router 与 Middleware，不承载业务规则。
- 风险敞口、EOD 策略和权限映射由各自模块显式导入，禁止运行时 monkey patch。
- 领域模块之间通过普通 import 建立可静态分析的依赖，不依赖启动顺序改变函数实现。
- 同一业务事实只能有一个权威实现；残余敞口计算统一由 `execution_exposure.py` 提供。

## 工程门禁边界

- Backend 与 Runtime 的 Ruff 检查覆盖完整 `app/` 与 `tests/`，新增文件不能绕过门禁。
- Python 安装完成后必须通过 `pip check`。
- Pyright 覆盖执行 DTO、FinancialFact DTO/Normalization/Repository/Projection Service、SQLite Connection/Bootstrap、Runtime 契约、迁移账本和权威下单边界。
- Frontend 活跃交易界面持续执行零警告 ESLint、类型检查和生产构建；其他新增/修改源文件执行 no-new-debt gate。
- `scripts/check-repository-structure.py` 阻止 Backend 引入交易场所 SDK、Composition Root 混入业务逻辑、正式账务边界漂移、平行上下文入口、临时测试命名和诊断工作流残留。
- FinancialFact Schema/Normalization/Repository/Projection Service 与 SQLite Connection/Bootstrap 各自有静态所有权测试。

## 工作流与上下文边界

- 人工入口唯一为 `00-人工可读目录/README.md`。
- Agent 入口唯一为 `docs/codex/context-map.md`。
- 当前工程事实唯一由 `docs/codex/current-state.md` 维护。
- 每个非简单工作通过一个 Issue、一个任务包、一个 Issue 编号分支和一个开放 PR 推进。
- `scripts/check-workstream.py` 校验 Issue、分支、任务包和 PR 一致性，并阻止同一 Issue 出现第二个开放 PR。

## Domain Schema 边界

- 执行域 API DTO 由 `platform-backend/app/execution_schemas.py` 统一维护。
- `platform-backend/app/schemas.py` 只允许显式兼容重导出，不得重复定义执行域类型。
- FinancialFact、正式持仓、正式 PnL、NAV 和重建响应 DTO 由 `platform-backend/app/financial_fact_schemas.py` 统一维护。
- `platform-backend/app/financial_facts.py` 只保留兼容重导出、目录解析、FinancialFact 写入编排和 API，不得重新定义公开 DTO。

## Platform–Runtime 契约边界

- 当前执行 Command/Event 使用 `runtime-command` / `runtime-event` V1.0。
- 双端模型分别位于 Platform 和 Runtime 的 `app/runtime_contracts.py`。
- `docs/contracts/runtime-v1.json` 是字段顺序、名称和版本的可执行快照。
- Platform 收到无法验证的 Event 时保留 `result_unknown`，不得解释为确定失败或自动重下。
- 不兼容变更必须提升版本并提供迁移/兼容测试。

## Persistence 边界

- SQLite 仍是当前批准的数据库技术。
- `platform-backend/app/database_connection.py` 是共享数据库路径、连接创建、 Row Factory、Foreign Key、Commit/Rollback/Close 的唯一 Owner。
- `platform-backend/app/database_bootstrap.py` 是完整核心 `SCHEMA_SQL`、新库 Schema 执行、兼容补列与部分唯一索引的唯一 Owner。
- `platform-backend/app/database.py` 显式重导出 Connection/Bootstrap 兼容接口，并只负责初始化顺序与暂存固定 Seed；它不得实现 `sqlite3.connect`、`CREATE/ALTER` 或 `executescript`。
- 初始化顺序固定为：Connection → Bootstrap（Schema + 兼容 DDL）→ Seed。
- Bootstrap Schema 文本由 SHA-256 `421f0625ffe3a8a26ca48bc827e64bd6aa6b2e49d95faef0b17313e808375801` 固定。
- 所有 DDL Owner、数据权威分类和迁移规则记录在 `docs/database/README.md`。
- `platform-backend/app/schema_migrations.py` 维护单调递增、带校验和的迁移账本。
- `platform-backend/app/financial_fact_repository.py` 是 FinancialFact 与正式 Position/PnL/NAV 的唯一 SQL、行映射和事务单元 Owner。
- 连接/Bootstrap 拆分由动态路径、事务行为、Schema Checksum、新库/旧库及重复启动快照共同证明等价。
- 已应用迁移不可修改；删除表/列、改变字段语义、转移账务权威或替换数据库属于专门高风险迁移。

## FinancialFact Normalization 边界

- `platform-backend/app/financial_fact_normalization.py` 是标准化结构、币种、结算校验、目录派生值、FX、质量状态、Decimal/UTC/JSON 和内容哈希的唯一 Owner。
- Policy 只接收已解析 Context，不得访问 Repository、数据库或外部交易场所。
- 标准化键集合、文本值和内容哈希属于不可变事实身份。

## Financial Projection 边界

- `platform-backend/app/trading.py` 负责成交后近实时运营投影，只写入 `positions` 与 `pnl_results`。
- `platform-backend/app/financial_fact_repository.py` 负责正式账务持久化和事务。
- `platform-backend/app/financial_projection_service.py` 负责平均成本、已实现与分项 PnL、正式重建和 NAV 计算。
- Projection Service 不依赖 FastAPI、配置模块或外部交易场所；数据库操作通过 Repository 完成。
- 运营投影不构成正式会计权威；正式账务必须从不可变事实重建。

## Test Taxonomy 边界

- Platform Backend 测试按 `architecture`、`unit`、`integration`、`live_safety` 四层执行。
- Execution Runtime 测试按 `unit`、`integration`、`live_safety` 三层执行。
- 每个测试在 collection 阶段必须且只能获得一个主标记；CI 分层运行且不得依赖其他层残留状态。

## Failure/Recovery 边界

- 网络超时、外部 ACK 丢失和 Gateway result unknown 不能解释为确定外部失败。
- 已认领命令在结果未知后重复请求不得再次调用 Gateway。
- Fill 身份必须幂等；重复和乱序事件不能重复投影或把 `filled` 降级。
- 不可恢复事件、对账差异、EOD 不完整、备份/恢复失败必须 fail closed。
- 自动化故障矩阵和受控实盘验收顺序见 `docs/operations/FAILURE_INJECTION_ACCEPTANCE.md`。
