# Admin-Risk 文档入口

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：统一文档入口

## 1. 文档定位

本目录是平台产品架构、模块需求、策略定义、UI 设计、技术架构和文档治理的统一入口。

项目讨论、需求调整和开发任务以本文件列出的 active 文档为准。Draft、历史交接和 archive 不作为默认实施依据。

## 2. 一级产品架构

平台固定包含六个一级模块：

1. 首页。
2. 对冲基金看板。
3. 新闻日历与理财。
4. 策略。
5. 风险管理。
6. 金融AI分析。

产品层级和职责：

- `modules/一级模块定位总表.md`
- `architecture/module-ownership-matrix.md`

正式模块名称以 `governance/glossary.md` 为唯一来源。产品菜单位置不等于后端服务、数据库表和数据权威归属。

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

### 4.1 一级模块总表

- `modules/一级模块定位总表.md`

### 4.2 首页

- `modules/首页-模块定位.md`
- `modules/首页-需求文档.md`

### 4.3 对冲基金看板

- `modules/对冲基金看板-模块定位.md`
- `modules/对冲基金看板-需求文档.md`

### 4.4 新闻日历与理财

- `modules/新闻日历与理财-模块定位.md`
- `modules/新闻日历与理财-需求文档.md`

### 4.5 策略

- `modules/策略-模块定位.md`
- `modules/策略-需求文档.md`
- `modules/交易平台-模块定位.md`
- `modules/交易平台-需求文档.md`
- `modules/策略管理-模块定位.md`
- `modules/策略管理-需求文档.md`

### 4.6 风险管理

- `modules/风控管理-模块定位.md`
- `modules/风控管理-需求文档.md`

文件名中的“风控管理”暂时保留历史路径兼容，正文正式名称统一使用“风险管理”。

### 4.7 金融AI分析

- `modules/金融AI分析-模块定位.md`
- `modules/金融AI分析-需求文档.md`

六个一级模块均已具备“模块定位 + 需求文档”。

### 4.8 策略定义

- `strategies/资费套利.md`
- `strategies/跨所价差.md`
- `strategies/海内外价差.md`
- `strategies/抄底.md`
- `strategies/短线交易员L.md`
- `strategies/短线交易员W.md`

### 4.9 UI 设计

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

## 6. 文档治理和唯一来源

- `governance/document-rules.md`
- `governance/glossary.md`

| 内容 | 主文档 |
|---|---|
| 正式中文术语 | `governance/glossary.md` |
| 一级模块和完整性 | `modules/一级模块定位总表.md` |
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

当前实现、具体文件、Mock 位置和技术债务进入 audit 或实施盘点，不写入正式模块定位和需求。

特殊人工维护源：

- `trading-tools-bookmarks-review.md`

修改交易工具后执行 `pnpm sync:trading-tools`；生成后的 `marketTools.ts` 不是人工维护入口。

## 8. Draft 文档

以下文件只用于讨论，不是当前实施依据：

- `architecture/implementation-roadmap.md`
- `architecture/2026-07-16-vnpy平台架构初步方案-DRAFT.md`
- `architecture/2026-07-16-平台新增功能初步方案-DRAFT.md`

Draft 中的阶段、技术选型和新增功能，只有确认并合并进 active 文档或 ADR 后才生效。

## 9. 文档读取顺序

### 产品或模块任务

1. `docs/README.md`
2. `modules/一级模块定位总表.md`
3. 对应模块定位和需求
4. `design/platform-ui-guidelines.md`
5. `architecture/module-ownership-matrix.md`
6. 相关架构文档和代码

### 策略任务

1. `modules/策略-模块定位.md`
2. `modules/策略-需求文档.md`
3. 交易平台或策略管理需求
4. 对应 `strategies/*.md`
5. 策略能力和注册表规范
6. 公共领域模型
7. 相关代码

### 前端任务

1. 对应产品和策略文档
2. 前端总览
3. 路由、权限与运行上下文
4. 数据适配与 View Model
5. 状态归属
6. 共享 UI
7. 相关代码

### 后端领域任务

1. 对应产品和策略需求
2. 公共领域对象和状态
3. 服务边界
4. 对应后端专题
5. 协作契约
6. 专项方案和 ADR

### 规划任务

1. 完成相关 active 架构和产品文档审阅。
2. 阅读 `architecture/implementation-roadmap.md` 作为讨论输入。
3. 确认目标、优先级、人员、依赖和约束。
4. 另行形成正式 planning 文档、issue 或 milestone。

## 10. 文档状态和维护

- `active`：当前有效。
- `draft`：讨论稿，不替代 active 文档。
- `superseded`：已被新文档替代。
- `archived`：仅供历史追溯。

维护原则：

- 产品边界变化先更新模块或策略文档。
- 公共对象变化先更新领域模型和状态唯一来源。
- 前端、后端和协作变化更新对应架构文档。
- 技术选型通过专项方案和 ADR 确认。
- 实施阶段和任务安排在正式规划中确认。
