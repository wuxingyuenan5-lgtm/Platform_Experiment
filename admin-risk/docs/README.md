# Admin-Risk 文档入口

> 当前产品基线：Platform V5  
> 基线提交：`bd6a2046814e92a2688ec6c8a8de026f95f4fcc2`  
> 文档重构分支：`refactor/frontend-architecture-v6`

## 1. 文档入口定位

本文件是项目产品需求、模块定位、策略定义和前端架构规范的唯一入口。

后续进行产品讨论、前端修改或 Codex 开发时，应优先读取本文件列出的 `active` 文档。未列入有效文档清单的旧 DOCX、阶段性交接、历史需求和临时设计稿，不得直接作为当前实现依据。

## 2. 文档状态

- `active`：当前有效，可以作为产品和开发依据。
- `draft`：正在讨论，不能替代 active 文档。
- `superseded`：已被新文档替代。
- `archived`：仅供历史追溯。

完整规则见 `governance/document-rules.md`。

## 3. 当前一级模块

Platform V5 当前一级模块只有：

1. 首页。
2. 对冲基金看板。
3. 新闻日历与理财。
4. 策略。
5. 风险管理。
6. 金融 AI。

数据、账户、财务、报表、监控、审计、用户、设置和通知等能力，按照当前前端设计归入上述一级模块内部，作为二级或三级子板块，不单独视为一级模块。

模块层级和主责见：

- `modules/一级模块定位总表.md`
- `architecture/module-ownership-matrix.md`

## 4. 当前有效文档

### 4.1 文档治理

- `governance/document-rules.md`：文档状态、命名、变更和归档规则。
- `governance/glossary.md`：平台、策略、交易、损益、账户和风险术语。

### 4.2 产品模块

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
- `modules/支撑模块-模块定位.md`：现有内嵌支撑子板块的过渡说明，后续按一级模块内部层级继续整理。

### 4.3 策略定义

- `strategies/资费套利.md`
- `strategies/跨所价差.md`
- `strategies/海内外价差.md`
- `strategies/抄底.md`
- `strategies/短线交易员L.md`
- `strategies/短线交易员W.md`

### 4.4 跨模块架构

- `architecture/module-ownership-matrix.md`
- `architecture/strategy-capability-matrix.md`
- `architecture/strategy-registry.md`
- `architecture/shared-ui-governance.md`
- `architecture/frontend-state-ownership.md`
- `architecture/domain-model-boundaries.md`

### 4.5 已接受的架构决策

- `architecture/decisions/ADR-001-一级架构保持不变.md`
- `architecture/decisions/ADR-002-交易平台与策略管理策略范围不同.md`
- `architecture/decisions/ADR-003-策略注册表作为唯一策略定义来源.md`
- `architecture/decisions/ADR-004-交易工具由Markdown生成.md`

决策变化时应新增替代 ADR，不直接删除历史记录。

### 4.6 资产盘点与质量

- `audit/v5-asset-inventory.md`
- `audit/legacy-document-inventory.md`
- `audit/legacy-code-inventory.md`
- `quality/release-gate.md`
- `quality/smoke-checklist.md`

### 4.7 特殊单一数据源

- `trading-tools-bookmarks-review.md`：交易工具目录的唯一人工维护来源。

修改后执行 `pnpm sync:trading-tools`，不要直接人工维护生成后的 `marketTools.ts` 内容。

## 5. AI / Codex 读取顺序

### 模块任务

1. `docs/README.md`
2. `modules/一级模块定位总表.md`
3. 对应一级模块或子板块定位文档
4. 对应需求文档
5. `architecture/module-ownership-matrix.md`
6. 相关源代码

### 策略任务

1. `docs/README.md`
2. `modules/策略-模块定位.md`
3. `modules/交易平台-需求文档.md` 或 `modules/策略管理-需求文档.md`
4. 对应 `strategies/*.md`
5. `architecture/strategy-capability-matrix.md`
6. `architecture/strategy-registry.md`
7. 相关源代码

### 清理和发布任务

- 清理前读取 `audit/legacy-document-inventory.md`、`audit/legacy-code-inventory.md`。
- 发布前读取 `quality/release-gate.md`、`quality/smoke-checklist.md`。

## 6. 归档

已经归档的 Markdown 位于：

- `archive/handoff/`
- `archive/superseded/`
- `archive/superseded/strategy/`

归档清单见 `archive/MANIFEST.md`。归档内容不作为默认开发依据。

仍待本地确认的旧文件：

- `核心模块.docx`
- `需求文档.docx`

确认其中唯一有效信息已迁移后，再移入 `docs/archive/legacy-docx/`，不直接删除。
