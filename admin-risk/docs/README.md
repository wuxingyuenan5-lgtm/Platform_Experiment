# Admin-Risk 文档入口

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`

## 1. 文档定位

本目录是平台产品架构、模块需求、策略定义、UI 设计、技术架构和文档治理的统一入口。

项目讨论、需求调整和开发任务以本文件列出的 active 文档为准。Draft、历史交接和 archive 不作为默认实施依据。

## 2. 产品架构

Platform V5 的用户可见产品结构保持六个一级模块：

1. 首页。
2. 对冲基金看板。
3. 新闻日历与理财。
4. 策略。
5. 风险管理。
6. 金融 AI。

产品层级和职责：

- `modules/一级模块定位总表.md`
- `architecture/module-ownership-matrix.md`

产品菜单位置不等于后端服务、数据库表和数据权威归属。

## 3. 技术架构

Platform V6 技术架构分为：

1. 前端架构。
2. 后端架构。
3. 前后端协作架构。
4. 公共领域模型。
5. 跨层安全、可观测性和治理。

统一入口：

- `architecture/README.md`

必须区分：

- 产品模块决定用户从哪里进入。
- 前端架构决定路由、页面、组件和状态。
- 后端架构决定规则、模块、存储和数据权威。
- 协作架构决定 Query、Command、Event、错误和版本。
- 公共领域模型定义前后端共同业务语言。
- Backend Read Model 只负责查询，不形成新的业务事实。

## 4. Active 产品文档

### 4.1 模块定位与需求

- `modules/一级模块定位总表.md`
- `modules/首页-模块定位.md`
- `modules/对冲基金看板-模块定位.md`
- `modules/新闻日历与理财-模块定位.md`
- `modules/策略-模块定位.md`
- `modules/交易平台-模块定位.md`
- `modules/交易平台-需求文档.md`
- `modules/策略管理-模块定位.md`
- `modules/策略管理-需求文档.md`
- `modules/风控管理-模块定位.md`
- `modules/金融AI分析-模块定位.md`

现有文件名暂时保留兼容；正式一级模块名称以术语表中的“风险管理”和“金融 AI”为准。

### 4.2 策略定义

- `strategies/资费套利.md`
- `strategies/跨所价差.md`
- `strategies/海内外价差.md`
- `strategies/抄底.md`
- `strategies/短线交易员L.md`
- `strategies/短线交易员W.md`

### 4.3 UI 设计

- `design/platform-ui-guidelines.md`

## 5. Active 架构文档

### 5.1 架构入口和跨层规范

- `architecture/README.md`
- `architecture/module-ownership-matrix.md`
- `architecture/strategy-capability-matrix.md`
- `architecture/domain-model-boundaries.md`
- `architecture/security-observability-and-operations.md`

### 5.2 前端架构

- `architecture/frontend/frontend-overview.md`
- `architecture/frontend/routing-permission-and-environment.md`
- `architecture/frontend/data-adapter-and-view-model.md`
- `architecture/frontend-state-ownership.md`
- `architecture/shared-ui-governance.md`
- `architecture/strategy-registry.md`

### 5.3 后端架构

- `architecture/backend/backend-overview.md`
- `architecture/backend/service-boundaries.md`
- `architecture/backend/trading-execution-reliability.md`
- `architecture/backend/storage-ledger-and-audit.md`
- `architecture/backend/query-and-read-models.md`
- `architecture/backend/research-data-and-content-boundaries.md`

当前只定义目标边界和建设原则，不代表后端、数据库和真实交易系统已经实现。

### 5.4 前后端协作架构

- `architecture/integration/frontend-backend-integration.md`
- `architecture/integration/api-contract-and-versioning.md`
- `architecture/integration/realtime-events-and-recovery.md`

### 5.5 公共领域模型

- `architecture/domain/domain-overview.md`
- `architecture/domain-model-boundaries.md`
- `architecture/domain/status-enums-and-lifecycles.md`
- `architecture/domain/approval-and-dual-control.md`

### 5.6 架构决策

- `architecture/decisions/ADR-001-一级架构保持不变.md`
- `architecture/decisions/ADR-002-交易平台与策略管理策略范围不同.md`
- `architecture/decisions/ADR-003-策略注册表作为唯一策略定义来源.md`
- `architecture/decisions/ADR-004-交易工具由Markdown生成.md`
- `architecture/decisions/ADR-005-技术架构分层.md`
- `architecture/decisions/ADR-006-后端优先采用模块化单体.md`
- `architecture/decisions/ADR-007-部署环境与交易模式分离.md`

架构决策变化时新增替代 ADR，并保留历史决策。

## 6. 文档治理和术语

- `governance/document-rules.md`
- `governance/glossary.md`

重要唯一来源：

| 内容 | 主文档 |
|---|---|
| 中文术语 | `governance/glossary.md` |
| 公共对象 | `architecture/domain-model-boundaries.md` |
| 状态枚举 | `architecture/domain/status-enums-and-lifecycles.md` |
| 后端模块所有权 | `architecture/backend/service-boundaries.md` |
| 产品归属和数据权威 | `architecture/module-ownership-matrix.md` |
| 交易可靠性 | `architecture/backend/trading-execution-reliability.md` |
| API、错误、幂等和版本 | `architecture/integration/api-contract-and-versioning.md` |
| 实时事件和恢复 | `architecture/integration/realtime-events-and-recovery.md` |
| 审批和双人复核 | `architecture/domain/approval-and-dual-control.md` |
| 研究和交易数据边界 | `architecture/backend/research-data-and-content-boundaries.md` |
| Backend Read Model | `architecture/backend/query-and-read-models.md` |

## 7. 资产盘点和质量控制

- `audit/v5-asset-inventory.md`
- `audit/legacy-document-inventory.md`
- `audit/legacy-code-inventory.md`
- `quality/release-gate.md`
- `quality/smoke-checklist.md`

特殊人工维护源：

- `trading-tools-bookmarks-review.md`

修改交易工具后执行 `pnpm sync:trading-tools`；生成后的 `marketTools.ts` 不是人工维护入口。

## 8. Draft 文档

以下文件只用于后续讨论，不是当前开发和实施依据：

- `architecture/implementation-roadmap.md`
- `architecture/2026-07-16-vnpy平台架构初步方案-DRAFT.md`
- `architecture/2026-07-16-平台新增功能初步方案-DRAFT.md`

Draft 中的阶段、技术选型和新增功能，只有在用户确认并合并进 active 文档或 ADR 后才生效。

## 9. 文档读取顺序

### 9.1 产品或模块任务

1. `docs/README.md`
2. `modules/一级模块定位总表.md`
3. 对应模块定位和需求
4. `design/platform-ui-guidelines.md`
5. `architecture/module-ownership-matrix.md`
6. 相关代码

### 9.2 策略任务

1. `docs/README.md`
2. `modules/策略-模块定位.md`
3. 交易平台或策略管理需求
4. 对应 `strategies/*.md`
5. `architecture/strategy-capability-matrix.md`
6. `architecture/strategy-registry.md`
7. `architecture/domain-model-boundaries.md`
8. 相关代码

### 9.3 前端任务

1. 对应模块和策略文档
2. `architecture/frontend/frontend-overview.md`
3. `architecture/frontend/routing-permission-and-environment.md`
4. `architecture/frontend/data-adapter-and-view-model.md`
5. `architecture/frontend-state-ownership.md`
6. `architecture/shared-ui-governance.md`
7. 相关代码

### 9.4 后端领域任务

1. 对应模块和策略需求
2. `architecture/domain-model-boundaries.md`
3. `architecture/domain/status-enums-and-lifecycles.md`
4. `architecture/backend/service-boundaries.md`
5. 对应后端专题文档
6. `architecture/integration/frontend-backend-integration.md`
7. 专项技术方案和 ADR

### 9.5 API 和实时任务

1. 对应业务需求
2. `architecture/domain-model-boundaries.md`
3. `architecture/integration/frontend-backend-integration.md`
4. `architecture/integration/api-contract-and-versioning.md`
5. `architecture/integration/realtime-events-and-recovery.md`
6. 具体 OpenAPI 和事件契约

### 9.6 规划任务

1. 完成全部相关 active 架构审阅。
2. 阅读 `architecture/implementation-roadmap.md` 作为讨论输入。
3. 确认目标、优先级、人员、依赖和约束。
4. 另行形成正式 planning 文档、issue 或 milestone。

## 10. 文档状态

- `active`：当前有效。
- `draft`：讨论稿，不替代 active 文档。
- `superseded`：已被新文档替代。
- `archived`：仅供历史追溯。

详细规则见 `governance/document-rules.md`。

## 11. 维护原则

- 产品边界变化时先更新模块或策略文档。
- 公共对象变化时先更新领域模型和状态唯一来源。
- 前端变化更新前端规范。
- 后端所有权变化更新服务边界并形成 ADR，适用时。
- API 和事件变化更新协作主文档。
- 具体技术选型通过专项方案和 ADR 确认。
- 实施阶段和任务安排在正式规划中确认，不写入 active 架构。
- 当前对话过程不写入正式产品文档。
