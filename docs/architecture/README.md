# Architecture Documentation

本目录保存长期稳定的系统架构说明。

## 文档职责

- 架构说明：解释系统边界和模块关系。
- decisions：记录关键技术决策。
- operations：记录运行和生产流程。
- technical：记录接口和领域设计。

## 原则

不要把历史执行过程、PR记录和临时任务放入架构文档。

架构文档回答：

- 系统为什么这样设计。
- 模块如何协作。
- 哪些边界不能突破。

具体实施记录进入对应 Issue、PR 或 Changelog。

## Composition Root 边界

- `platform-backend/app/main.py` 只装配 Router 与 Middleware，不承载业务规则。
- 风险敞口、EOD 策略和权限映射由各自模块显式导入，禁止运行时 monkey patch。
- 领域模块之间通过普通 import 建立可静态分析的依赖，不依赖启动顺序改变函数实现。
- 同一业务事实只能有一个权威实现；残余敞口计算统一由 `execution_exposure.py` 提供。
- `tests/test_architecture_boundaries.py` 对上述边界进行静态回归检查。

## 工程门禁边界

- Backend 与 Runtime 的 Ruff 检查覆盖完整 `app/` 与 `tests/`，新增文件不能绕过门禁。
- Python 安装完成后必须通过 `pip check`，避免声明依赖与实际环境不一致。
- Frontend 活跃交易界面必须通过无修改、零警告 ESLint、类型检查和生产构建。
- `scripts/check-repository-structure.py` 阻止 Backend 引入交易场所 SDK、Composition Root 混入业务逻辑、临时测试命名和诊断工作流残留。

## Domain Schema 边界

- 执行、订单、批次、策略运行、持仓和 PnL API DTO 由 `platform-backend/app/execution_schemas.py` 统一维护。
- `platform-backend/app/schemas.py` 作为迁移期兼容入口，只允许使用显式公共别名重导出，不得重复定义执行域类型。
- `tests/test_schema_boundaries.py` 校验兼容导出的对象身份和单一所有权。
- `scripts/check-repository-structure.py` 在测试前阻止执行域 DTO 被重新复制回跨域 Schema 模块。

## Financial Projection 边界

- `platform-backend/app/trading.py` 负责成交后近实时运营投影，并且只写入 `positions` 与 `pnl_results`。
- `platform-backend/app/financial_facts.py` 负责不可变财务事实的摄取与正式投影重建，并维护 `financial_facts`、`formal_positions` 与 `formal_pnl_results`。
- 运营投影服务于交易监控和即时展示，不构成正式会计权威；正式账务必须从不可变事实重建。
- 交易链路不得写入正式投影，正式账务链路不得读取运营投影作为计算输入。
- `tests/test_projection_boundaries.py` 与 `scripts/check-repository-structure.py` 对命名、表读写方向和跨边界依赖执行静态回归检查。

## Test Taxonomy 边界

- Platform Backend 测试按 `architecture`、`unit`、`integration`、`live_safety` 四层执行。
- Execution Runtime 测试按 `unit`、`integration`、`live_safety` 三层执行。
- 每个测试在 collection 阶段必须获得且只能获得一个主标记；未知标记通过 `--strict-markers` 直接失败。
- CI 分层运行各套件，测试不得依赖其他层的执行顺序或残留状态。
- 具体分类规则分别记录在 `platform-backend/tests/README.md` 与 `execution-runtime/tests/README.md`。
