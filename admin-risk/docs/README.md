# Admin-Risk 文档入口

> 当前产品基线：Platform V5  
> 基线提交：`bd6a2046814e92a2688ec6c8a8de026f95f4fcc2`  
> 文档重构分支：`refactor/frontend-architecture-v6`

## 1. 文档入口定位

本文件是项目产品需求、模块定位、策略定义和前端架构规范的唯一有效入口。

后续进行产品讨论、前端修改或 Codex 开发时，应优先读取本文件列出的 `active` 文档。

未列入有效文档清单的旧 DOCX、阶段性交接、历史需求和临时设计稿，不得直接作为当前实现依据。

## 2. 文档状态

- `active`：当前有效，可以作为产品和开发依据。
- `draft`：正在讨论，不能直接替代 active 文档。
- `superseded`：已被新文档替代。
- `archived`：仅供历史追溯。

完整规则见：

- `governance/document-rules.md`

## 3. 当前有效文档

### 3.1 文档治理

- `governance/document-rules.md`：文档目录、状态、命名、变更、归档和 AI 读取规则。
- `governance/glossary.md`：平台、策略、交易、损益、账户、风控和工程术语的统一定义。

### 3.2 资产盘点与遗留清单

- `audit/v5-asset-inventory.md`：V5 页面、代码、文档和工程资产初步盘点。
- `audit/legacy-document-inventory.md`：旧 DOCX、交接文档和历史需求的归档计划。
- `audit/legacy-code-inventory.md`：遗留组件、大型页面、重复入口、生成文件和旧 API 占位清单。

### 3.3 跨模块架构

- `architecture/module-ownership-matrix.md`：模块主责和跨模块摘要展示边界。
- `architecture/strategy-capability-matrix.md`：六类策略在交易平台和策略管理中的能力范围。
- `architecture/strategy-registry.md`：统一策略注册表设计规范。
- `architecture/shared-ui-governance.md`：共享组件、主题变量、图表、表格和样式治理规范。

### 3.4 一级和支撑模块定位

- `modules/一级模块定位总表.md`
- `modules/首页-模块定位.md`
- `modules/策略-模块定位.md`
- `modules/对冲基金看板-模块定位.md`
- `modules/新闻日历与理财-模块定位.md`
- `modules/风控管理-模块定位.md`
- `modules/金融AI分析-模块定位.md`
- `modules/支撑模块-模块定位.md`

一级架构、一级导航、模块名称和现有路由均视为既定约束，本轮不做调整。

### 3.5 交易平台

- `modules/交易平台-模块定位.md`
- `modules/交易平台-需求文档.md`

当前策略范围：

- 资费套利。
- 跨所价差。
- 海内外价差。

固定页面：

- 行情分析。
- 交易执行。

### 3.6 策略管理

- `modules/策略管理-模块定位.md`
- `modules/策略管理-需求文档.md`

当前纳管策略：

- 资费套利。
- 跨所价差。
- 海内外价差。
- 抄底。
- 短线交易员 L。
- 短线交易员 W。

固定页面：

- 策略损益。
- 账户资金。
- 订单信息。

### 3.7 策略文档

- `strategies/资费套利.md`
- `strategies/跨所价差.md`
- `strategies/海内外价差.md`
- `strategies/抄底.md`
- `strategies/短线交易员L.md`
- `strategies/短线交易员W.md`

策略能力结论：

| 策略 | 交易平台 | 策略管理 |
|---|---:|---:|
| 资费套利 | 是 | 是 |
| 跨所价差 | 是 | 是 |
| 海内外价差 | 是 | 是 |
| 抄底 | 否 | 是 |
| 短线交易员 L | 否 | 是 |
| 短线交易员 W | 否 | 是 |

### 3.8 特殊单一数据源

- `trading-tools-bookmarks-review.md`：交易工具目录的唯一人工维护来源。

交易工具数据更新规则：

1. 修改该 Markdown 文件。
2. 执行 `pnpm sync:trading-tools`。
3. 生成 `src/views/hedgeBoard/tradingTools/data/marketTools.ts`。
4. 不直接人工修改生成文件中的工具内容。

## 4. 当前代码配置

统一策略注册表：

- `src/views/strategy/shared/strategyRegistry.ts`

当前状态：

- 已建立六类策略统一定义。
- 已明确平台和策略管理能力。
- 尚未接入现有页面。
- 暂不接入阶段 7－10 的策略页面，避免与用户本地修改冲突。

## 5. 本轮已完成范围

- 冻结 V5 基线并创建独立重构分支。
- 建立 V5 资产盘点。
- 建立全部现有一级模块和支撑模块定位。
- 建立交易平台和策略管理模块需求。
- 建立六类策略正式文档。
- 建立模块职责矩阵。
- 建立策略能力矩阵和策略注册表规范。
- 建立平台术语表。
- 建立文档治理规则。
- 建立遗留文档和遗留代码清单。
- 建立共享组件和主题治理规范。

## 6. 本轮明确不包含

- 资费套利具体代码迁移。
- 跨所价差具体代码迁移。
- 海内外价差具体代码迁移。
- 抄底具体代码迁移。
- 短线交易员 L/W 具体代码迁移。
- 后端、数据库和真实数据接入。
- 大规模目录搬迁。
- 旧文件和旧代码的实际删除。

上述策略页面修改由用户本地单独推进。

## 7. AI / Codex 开发读取顺序

### 模块任务

1. `docs/README.md`
2. 对应 `modules/*-模块定位.md`
3. 对应 `modules/*-需求文档.md`，如存在
4. `architecture/module-ownership-matrix.md`
5. `governance/glossary.md`
6. 相关源代码

### 策略任务

1. `docs/README.md`
2. `modules/策略-模块定位.md`
3. `modules/交易平台-需求文档.md` 或 `modules/策略管理-需求文档.md`
4. 对应 `strategies/*.md`
5. `architecture/strategy-capability-matrix.md`
6. `architecture/strategy-registry.md`
7. `architecture/shared-ui-governance.md`
8. 相关源代码

### 清理任务

1. `audit/legacy-document-inventory.md`
2. `audit/legacy-code-inventory.md`
3. `governance/document-rules.md`
4. 搜索实际引用
5. 完成替代后再删除

## 8. 历史文档处理

用户确认存在的旧文件：

- `核心模块.docx`
- `需求文档.docx`

处理原则：

1. 本地确认精确路径。
2. 提取仍有效且新文档未覆盖的信息。
3. 合并进入对应 active Markdown 文档。
4. 移入 `docs/archive/legacy-docx/`。
5. 不直接删除。

其他阶段性交接和历史策略文档的具体处理见：

- `audit/legacy-document-inventory.md`

## 9. 当前禁止事项

- 不改变一级架构。
- 不让旧 DOCX 覆盖当前 active 文档。
- 不直接删除 Legacy 组件。
- 不批量清理 API 占位文件。
- 不直接修改交易工具生成文件。
- 不因单页问题重写共享主题。
- 不在没有业务确认的情况下新增损益项、风险阈值或策略能力。

## 10. 维护规则

产品口径变化时：

1. 先更新对应 active 文档。
2. 再更新职责矩阵、能力矩阵或术语表。
3. 然后修改代码。
4. 最后检查文档和代码一致性。

当代码与 active 文档冲突时，应先指出冲突并由用户确认，不得自动以旧代码或旧文档为准。
