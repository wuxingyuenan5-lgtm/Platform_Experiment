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

架构文档回答：

- 系统为什么这样设计；
- 模块如何协作；
- 哪些边界不能突破；
- 数据和契约由谁负责；
- 发生故障时应保持什么不变量。

具体实施记录进入对应 Issue、任务包、PR 或 Changelog。

## Composition Root 边界

- `platform-backend/app/main.py` 只装配 Router 与 Middleware，不承载业务规则。
- 风险敞口、EOD 策略和权限映射由各自模块显式导入，禁止运行时 monkey patch。
- 领域模块之间通过普通 import 建立可静态分析的依赖，不依赖启动顺序改变函数实现。
- 同一业务事实只能有一个权威实现；残余敞口计算统一由 `execution_exposure.py` 提供。
- `tests/test_architecture_boundaries.py` 对上述边界进行静态回归检查。

## 工程门禁边界

- Backend 与 Runtime 的 Ruff 检查覆盖完整 `app/` 与 `tests/`，新增文件不能绕过门禁。
- Python 安装完成后必须通过 `pip check`。
- Pyright 先覆盖执行 DTO、FinancialFact DTO/Normalization/Repository、Runtime 契约、迁移账本和权威下单边界；每次扩展必须保持所选模块清洁。
- Frontend 活跃交易界面持续执行完整零警告 ESLint、类型检查和生产构建。
- 活跃范围之外的新增或修改前端源文件通过 changed-file no-new-debt gate，禁止增加旧债。
- `scripts/check-repository-structure.py` 阻止 Backend 引入交易场所 SDK、Composition Root 混入业务逻辑、FinancialFact 服务层重新出现 SQL、平行上下文入口、临时测试命名和诊断工作流残留。
- `tests/test_architecture_financial_fact_normalization.py` 阻止标准化规则、错误契约或内容哈希重新回流到服务层，并阻止 Policy 依赖 Repository。

## 工作流与上下文边界

- 人工入口唯一为 `00-人工可读目录/README.md`。
- Agent 入口唯一为 `docs/codex/context-map.md`。
- 当前工程事实唯一由 `docs/codex/current-state.md` 维护。
- 每个非简单工作通过一个 Issue、一个任务包、一个 Issue 编号分支和一个开放 PR 推进。
- `scripts/check-workstream.py` 校验 Issue、分支、任务包和 PR 的一致性，并阻止同一 Issue 出现第二个开放 PR。
- Agent 默认只读取任务包、一个模块入口、3–8 个直接源文件和直接测试。

## Domain Schema 边界

- 执行、订单、批次、策略运行、持仓和运营 PnL API DTO 由 `platform-backend/app/execution_schemas.py` 统一维护。
- `platform-backend/app/schemas.py` 作为迁移期兼容入口，只允许显式公共别名重导出，不得重复定义执行域类型。
- FinancialFact、正式持仓、正式 PnL、NAV 和重建响应 DTO 由 `platform-backend/app/financial_fact_schemas.py` 统一维护。
- `platform-backend/app/financial_facts.py` 只保留兼容重导出与正式账务服务实现，不得重新定义这些公开 DTO。
- `tests/test_schema_boundaries.py` 与 `tests/test_architecture_financial_fact_schemas.py` 校验兼容导出的对象身份、字段快照和单一所有权。
- Schema 所有权迁移不得顺带改变 API 字段、SQL、哈希、FX、平均成本或 PnL 公式。

## Platform–Runtime 契约边界

- 当前执行 Command/Event 使用 `runtime-command` / `runtime-event` V1.0。
- 双端模型分别位于 Platform 和 Runtime 的 `app/runtime_contracts.py`。
- `docs/contracts/runtime-v1.json` 是字段顺序、名称和版本的可执行快照。
- Platform 发送显式 `contract_version` 和 `payload_version`；Runtime 对未知版本结构化拒绝。
- Platform 收到无法验证的 Event 时保留 `result_unknown`，不得解释为确定失败或自动重下。
- 契约不兼容变更必须提升版本并提供迁移/兼容测试，不能静默改变 V1。

## Persistence 边界

- SQLite 仍是当前批准的数据库技术。
- 所有 DDL Owner、数据权威分类和迁移规则记录在 `docs/database/README.md`。
- `platform-backend/app/schema_migrations.py` 维护单调递增、带校验和的迁移账本。
- `platform-backend/app/financial_fact_repository.py` 是 FinancialFact 与正式 Position/PnL/NAV 的唯一 SQL、行映射和事务单元 Owner。
- `platform-backend/app/financial_facts.py` 不得直接导入数据库连接或包含 SQL。
- 事实写入与审计、Position 与 PnL 写入、重建清理、NAV 与审计必须分别保持单事务原子性。
- Version 1 只登记既有 Schema 基线，不移动或改写现有业务表。
- 已应用迁移不可修改；校验和漂移必须启动失败。
- 删除表/列、改变字段语义、转移账务权威或替换数据库属于专门高风险迁移。

## FinancialFact Normalization 边界

- `platform-backend/app/financial_fact_normalization.py` 是标准化结果结构、币种规范化、结算币种校验、目录派生数量单位/合约乘数、FX 转换、质量状态、Decimal/UTC/JSON 规范化和 SHA-256 内容哈希的唯一 Owner。
- Policy 只接收已解析的 `FinancialFactNormalizationContext`，不得访问 Repository、数据库或外部交易场所。
- `platform-backend/app/financial_facts.py` 负责解析策略、账户绑定和 Instrument 上下文，并保留 `normalize_fact(request)` 兼容包装器。
- 标准化键集合、文本值和内容哈希属于不可变事实身份；改变任一规则必须作为显式兼容性迁移，而不是普通重构。
- 纯 Policy Golden 固定完整标准化字典和精确 SHA-256；API 等价测试固定错误状态、持久化值和幂等冲突行为。

## Financial Projection 边界

- `platform-backend/app/trading.py` 负责成交后近实时运营投影，并且只写入 `positions` 与 `pnl_results`。
- `platform-backend/app/financial_fact_schemas.py` 负责正式账务公开 DTO。
- `platform-backend/app/financial_fact_normalization.py` 负责不可变事实标准化与内容哈希。
- `platform-backend/app/financial_fact_repository.py` 维护 `financial_facts`、`formal_positions`、`formal_pnl_results` 与正式 NAV 的持久化。
- `platform-backend/app/financial_facts.py` 负责目录上下文解析、平均成本、PnL 分项、重建编排和 API 路由。
- 运营投影服务于交易监控和即时展示，不构成正式会计权威；正式账务必须从不可变事实重建。
- 交易链路不得写入正式投影，正式账务链路不得读取运营投影作为计算输入。
- `tests/test_projection_boundaries.py`、FinancialFact Schema/Normalization/Repository 架构测试、Repository 事务测试与结构脚本共同执行回归检查。

## Test Taxonomy 边界

- Platform Backend 测试按 `architecture`、`unit`、`integration`、`live_safety` 四层执行。
- Execution Runtime 测试按 `unit`、`integration`、`live_safety` 三层执行。
- 每个测试在 collection 阶段必须获得且只能获得一个主标记；未知标记通过 `--strict-markers` 失败。
- CI 分层运行各套件，测试不得依赖其他层执行顺序或残留状态。
- 具体分类规则记录在各自 `tests/README.md`。

## Failure/Recovery 边界

- 网络超时、外部 ACK 丢失和 Gateway result unknown 都不能自动解释为外部失败。
- 已认领命令在结果未知后重复请求不得再次调用 Gateway。
- Fill 身份必须幂等；重复和乱序事件不能重复投影或把 `filled` 降级。
- 不可恢复事件、对账差异、EOD 不完整、备份/恢复失败必须 fail closed。
- 自动化故障矩阵和受控实盘验收顺序见 `docs/operations/FAILURE_INJECTION_ACCEPTANCE.md`。
