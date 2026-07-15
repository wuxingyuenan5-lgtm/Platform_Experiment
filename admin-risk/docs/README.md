# Admin-Risk 文档入口

> 产品基线：Platform V5  
> 架构治理版本：Platform V6  
> 基线提交：`bd6a2046814e92a2688ec6c8a8de026f95f4fcc2`  
> 架构分支：`refactor/frontend-architecture-v6`

## 1. 文档定位

本目录是平台产品架构、模块需求、策略定义、UI 设计和技术架构的统一入口。

项目讨论、需求调整和开发任务应以本文件列出的 `active` 文档为准。历史交接、旧版需求、归档文件和未列入索引的 DRAFT 不作为当前实现依据。

## 2. 产品架构

Platform V5 的用户可见产品结构由六个一级模块构成：

1. 首页。
2. 对冲基金看板。
3. 新闻日历与理财。
4. 策略。
5. 风险管理。
6. 金融 AI。

数据、账户、财务、报表、监控、审计、用户、设置和通知等能力按照当前前端设计归入上述一级模块内部，作为二级或三级子板块。

产品层级与模块职责参见：

- `modules/一级模块定位总表.md`
- `architecture/module-ownership-matrix.md`

## 3. 技术架构

V6 技术架构分为四层：

1. 前端架构。
2. 后端架构。
3. 前后端协作架构。
4. 公共领域模型。

统一入口：

- `architecture/README.md`

必须区分：

- 产品模块决定用户从哪里进入。
- 前端架构决定路由、页面、组件和状态如何组织。
- 后端架构决定业务规则、服务、存储和数据权威。
- 协作架构决定 API、命令、事件和错误如何交换。
- 公共领域模型定义前后端共同业务语言。

## 4. 当前有效文档

### 4.1 产品模块

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

### 4.2 策略定义

- `strategies/资费套利.md`
- `strategies/跨所价差.md`
- `strategies/海内外价差.md`
- `strategies/抄底.md`
- `strategies/短线交易员L.md`
- `strategies/短线交易员W.md`

### 4.3 UI 设计

- `design/platform-ui-guidelines.md`：全平台视觉语言、页面结构、控件、图表、表格、状态和交互规范。

### 4.4 架构入口与跨层规范

- `architecture/README.md`
- `architecture/module-ownership-matrix.md`
- `architecture/strategy-capability-matrix.md`
- `architecture/domain-model-boundaries.md`

### 4.5 前端架构

- `architecture/frontend/frontend-overview.md`
- `architecture/frontend-state-ownership.md`
- `architecture/shared-ui-governance.md`
- `architecture/strategy-registry.md`

### 4.6 后端架构

- `architecture/backend/backend-overview.md`

当前只定义目标边界和建设原则，不代表后端、数据库和真实交易系统已经实现。

### 4.7 前后端协作架构

- `architecture/integration/frontend-backend-integration.md`

### 4.8 公共领域模型

- `architecture/domain/domain-overview.md`
- `architecture/domain-model-boundaries.md`

### 4.9 架构决策

- `architecture/decisions/ADR-001-一级架构保持不变.md`
- `architecture/decisions/ADR-002-交易平台与策略管理策略范围不同.md`
- `architecture/decisions/ADR-003-策略注册表作为唯一策略定义来源.md`
- `architecture/decisions/ADR-004-交易工具由Markdown生成.md`
- `architecture/decisions/ADR-005-技术架构分层.md`

架构决策发生变化时，应新增替代 ADR，并保留原决策记录。

### 4.10 文档治理与术语

- `governance/document-rules.md`
- `governance/glossary.md`

### 4.11 资产盘点与质量控制

- `audit/v5-asset-inventory.md`
- `audit/legacy-document-inventory.md`
- `audit/legacy-code-inventory.md`
- `quality/release-gate.md`
- `quality/smoke-checklist.md`

### 4.12 特殊数据源

- `trading-tools-bookmarks-review.md`：交易工具目录的人工维护源。

交易工具内容修改后执行 `pnpm sync:trading-tools`，生成后的 `marketTools.ts` 不作为人工维护入口。

## 5. 文档读取顺序

### 5.1 产品或模块任务

1. `docs/README.md`
2. `modules/一级模块定位总表.md`
3. 对应模块定位文档
4. 对应模块需求文档
5. `design/platform-ui-guidelines.md`
6. `architecture/module-ownership-matrix.md`
7. 相关代码

### 5.2 策略任务

1. `docs/README.md`
2. `modules/策略-模块定位.md`
3. `modules/交易平台-需求文档.md` 或 `modules/策略管理-需求文档.md`
4. 对应 `strategies/*.md`
5. `architecture/strategy-capability-matrix.md`
6. `architecture/strategy-registry.md`
7. `architecture/domain-model-boundaries.md`
8. 相关代码

### 5.3 前端页面和组件任务

1. `architecture/frontend/frontend-overview.md`
2. `design/platform-ui-guidelines.md`
3. `architecture/frontend-state-ownership.md`
4. `architecture/shared-ui-governance.md`
5. 对应模块和策略文档
6. 当前组件、主题变量和页面代码

### 5.4 后端设计任务

1. 对应模块和策略需求
2. `architecture/domain/domain-overview.md`
3. `architecture/domain-model-boundaries.md`
4. `architecture/backend/backend-overview.md`
5. `architecture/integration/frontend-backend-integration.md`
6. 专项技术方案和 ADR

### 5.5 前后端接口任务

1. 对应业务需求
2. `architecture/domain-model-boundaries.md`
3. `architecture/integration/frontend-backend-integration.md`
4. 前端 Repository／View Model
5. 后端 API DTO／Service
6. 具体接口契约

### 5.6 发布与清理任务

- 发布检查：`quality/release-gate.md`、`quality/smoke-checklist.md`
- 文档清理：`audit/legacy-document-inventory.md`
- 代码清理：`audit/legacy-code-inventory.md`

## 6. 文档状态

- `active`：当前有效，可作为产品或架构依据。
- `draft`：讨论稿，不替代 active 文档。
- `superseded`：已被新文档替代。
- `archived`：仅用于历史追溯。

归档文件统一位于 `docs/archive/`，归档清单见 `archive/MANIFEST.md`。

两份 `2026-07-16-*-DRAFT.md` 暂不纳入有效架构体系，只有完成评审并更新相应 active 文档或 ADR 后才可作为实施依据。

## 7. 维护原则

- 产品边界变化时，先更新模块或策略文档，再调整职责矩阵和代码。
- 前端架构变化时，更新前端总览、状态或组件规范。
- 后端边界或技术选型变化时，更新后端文档并形成 ADR。
- API、事件、错误和数据规范变化时，更新前后端协作文档。
- 公共业务对象变化时，先更新领域模型，再调整前端类型、后端模型和接口。
- UI 视觉和交互变化时，先更新全平台 UI 规范。
- 同一业务规则只在主责文档中完整定义，其他文档通过引用保持一致。
- 当前实现进度、临时任务和对话过程不写入正式产品文档。
