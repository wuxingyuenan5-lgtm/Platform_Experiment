# Admin-Risk 文档入口

> 产品基线：Platform V5  
> 基线提交：`bd6a2046814e92a2688ec6c8a8de026f95f4fcc2`  
> 架构分支：`refactor/frontend-architecture-v6`

## 1. 文档定位

本目录是 Platform V5 产品架构、模块需求、策略定义、UI 设计和前端规范的统一入口。

项目讨论、需求调整和开发任务应以本文件列出的 `active` 文档为准。历史交接、旧版需求、归档文件和未列入索引的临时文档不作为当前实现依据。

## 2. 产品架构

Platform V5 由六个一级模块构成：

1. 首页。
2. 对冲基金看板。
3. 新闻日历与理财。
4. 策略。
5. 风险管理。
6. 金融 AI。

数据、账户、财务、报表、监控、审计、用户、设置和通知等能力，按照当前前端设计归入上述一级模块内部，作为二级或三级子板块。

产品层级与模块职责参见：

- `modules/一级模块定位总表.md`
- `architecture/module-ownership-matrix.md`

## 3. 当前有效文档

### 3.1 产品模块

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

### 3.2 策略定义

- `strategies/资费套利.md`
- `strategies/跨所价差.md`
- `strategies/海内外价差.md`
- `strategies/抄底.md`
- `strategies/短线交易员L.md`
- `strategies/短线交易员W.md`

### 3.3 UI 设计

- `design/platform-ui-guidelines.md`：全平台视觉语言、页面结构、控件、图表、表格、状态和交互规范。

### 3.4 架构规范

- `architecture/module-ownership-matrix.md`
- `architecture/strategy-capability-matrix.md`
- `architecture/strategy-registry.md`
- `architecture/shared-ui-governance.md`：组件分层、共享范围、主题和代码组织治理。
- `architecture/frontend-state-ownership.md`
- `architecture/domain-model-boundaries.md`

### 3.5 架构决策

- `architecture/decisions/ADR-001-一级架构保持不变.md`
- `architecture/decisions/ADR-002-交易平台与策略管理策略范围不同.md`
- `architecture/decisions/ADR-003-策略注册表作为唯一策略定义来源.md`
- `architecture/decisions/ADR-004-交易工具由Markdown生成.md`

架构决策发生变化时，应新增替代 ADR，并保留原决策记录。

### 3.6 文档治理与术语

- `governance/document-rules.md`
- `governance/glossary.md`

### 3.7 资产盘点与质量控制

- `audit/v5-asset-inventory.md`
- `audit/legacy-document-inventory.md`
- `audit/legacy-code-inventory.md`
- `quality/release-gate.md`
- `quality/smoke-checklist.md`

### 3.8 特殊数据源

- `trading-tools-bookmarks-review.md`：交易工具目录的人工维护源。

交易工具内容修改后执行 `pnpm sync:trading-tools`，生成后的 `marketTools.ts` 不作为人工维护入口。

## 4. 文档读取顺序

### 4.1 模块任务

1. `docs/README.md`
2. `modules/一级模块定位总表.md`
3. 对应模块定位文档
4. 对应模块需求文档
5. `design/platform-ui-guidelines.md`
6. `architecture/module-ownership-matrix.md`
7. 相关源代码

### 4.2 策略任务

1. `docs/README.md`
2. `modules/策略-模块定位.md`
3. `modules/交易平台-需求文档.md` 或 `modules/策略管理-需求文档.md`
4. 对应 `strategies/*.md`
5. `design/platform-ui-guidelines.md`
6. `architecture/strategy-capability-matrix.md`
7. `architecture/strategy-registry.md`
8. 相关源代码

### 4.3 UI 与组件任务

1. `design/platform-ui-guidelines.md`
2. `architecture/shared-ui-governance.md`
3. 对应模块定位与需求文档
4. 当前共享组件、主题变量和页面样式

### 4.4 接口与业务对象任务

1. `architecture/domain-model-boundaries.md`
2. `governance/glossary.md`
3. 对应模块与策略文档
4. 当前 API、Mock 和页面类型

### 4.5 发布与清理任务

- 发布检查：`quality/release-gate.md`、`quality/smoke-checklist.md`
- 文档清理：`audit/legacy-document-inventory.md`
- 代码清理：`audit/legacy-code-inventory.md`

## 5. 文档状态

- `active`：当前有效，可作为产品和开发依据。
- `draft`：讨论稿，不替代 active 文档。
- `superseded`：已被新文档替代。
- `archived`：仅用于历史追溯。

归档文件统一位于 `docs/archive/`，归档清单见 `archive/MANIFEST.md`。

## 6. 维护原则

- 产品边界变化时，先更新模块或策略文档，再调整架构矩阵和代码。
- UI 视觉和交互变化时，先更新全平台 UI 规范，再调整组件与页面。
- 同一业务规则只在主责文档中完整定义，其他文档通过引用保持一致。
- 模块定位描述长期职责，需求文档描述功能要求，UI 文档描述视觉与交互标准，架构文档描述对象、状态和技术边界。
- 当前实现进度、临时任务和对话过程不写入正式产品文档。