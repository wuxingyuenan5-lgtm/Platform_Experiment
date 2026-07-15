# 遗留文档盘点与归档清单

状态：`active`  
适用基线：Platform V5

## 1. 目的

识别当前仓库和本地项目中可能残留的旧需求、交接文档和 DOCX，明确哪些继续有效、哪些已被替代、哪些需要本地复核。

本清单只制定处理动作，本阶段不删除任何文件。

## 2. 当前有效文档

以下文件继续作为当前有效来源：

### 文档入口和治理

- `docs/README.md`
- `docs/governance/glossary.md`
- `docs/governance/document-rules.md`

### 架构

- `docs/architecture/module-ownership-matrix.md`
- `docs/architecture/strategy-capability-matrix.md`
- `docs/architecture/strategy-registry.md`

### 模块

- `docs/modules/一级模块定位总表.md`
- `docs/modules/首页-模块定位.md`
- `docs/modules/策略-模块定位.md`
- `docs/modules/交易平台-模块定位.md`
- `docs/modules/交易平台-需求文档.md`
- `docs/modules/策略管理-模块定位.md`
- `docs/modules/策略管理-需求文档.md`
- `docs/modules/对冲基金看板-模块定位.md`
- `docs/modules/新闻日历与理财-模块定位.md`
- `docs/modules/风控管理-模块定位.md`
- `docs/modules/金融AI分析-模块定位.md`
- `docs/modules/支撑模块-模块定位.md`

### 策略

- `docs/strategies/资费套利.md`
- `docs/strategies/跨所价差.md`
- `docs/strategies/海内外价差.md`
- `docs/strategies/抄底.md`
- `docs/strategies/短线交易员L.md`
- `docs/strategies/短线交易员W.md`

### 特殊单一数据源

- `docs/trading-tools-bookmarks-review.md`

该文件仍是交易工具目录的人工维护源，不能归档。

## 3. 明确归档候选

### 3.1 `docs/codex-session-handoff.md`

建议状态：`archived`

原因：

- 文档记录的是提交 V5 前的临时 Git 和本地工作区状态。
- 其中“远端正式基线仍为 V4”等信息已过期。
- 当前产品和架构口径已迁移到新的 active 文档。

处理建议：

1. 不再作为新对话默认读取文件。
2. 移入 `docs/archive/handoffs/`。
3. 保留原文用于历史追溯。

### 3.2 `docs/2026-07-15-项目上下文交接.md`

建议状态：`superseded`，随后 `archived`

原因：

- 原文对 V5 方向有帮助，但属于阶段性交接。
- 模块边界、策略能力和工程规则已经拆入正式文档。
- 交接文档不应继续承担产品定义。

替代来源：

- `docs/modules/`
- `docs/strategies/`
- `docs/architecture/`
- `docs/governance/`

### 3.3 `docs/strategy-module-current-requirements.md`

建议状态：`superseded`

原因：

- 属于策略模块旧的汇总需求口径。
- 当前需求已拆分为交易平台、策略管理和六类策略文档。

处理建议：

- 复核是否含有新文档尚未覆盖的唯一信息。
- 有效信息迁移后移入 `docs/archive/superseded/`。

### 3.4 `docs/strategy/2026-07-09-策略模块现状需求文档.md`

建议状态：`superseded`

原因：

- 原文是阶段性现状和修改记录。
- 当前模块需求已经形成稳定结构。
- 不应再与新的模块需求文档并列为 active。

### 3.5 `docs/strategy/2026-07-12-策略模块结构设计方案-A1.md`

建议状态：`superseded`

原因：

- 其核心原则已迁移到交易平台、策略管理、策略父模块及职责矩阵。
- 文件名中的 A1 表明其属于阶段性结构方案。
- 后续不应同时维护 A1 与正式模块文档。

处理建议：

- 保留历史版本。
- 在顶部标记被哪些新文档替代。
- 后续移入 `docs/archive/superseded/strategy/`。

### 3.6 `docs/strategy/2026-07-10-MT5黄金跨所价差建议看板需求文档.md`

建议状态：`review-required`

原因：

- 可能仍包含黄金跨所价差的具体页面字段和交易细节。
- 当前 `docs/strategies/跨所价差.md` 已建立正式策略边界，但未必覆盖原文全部细节。

处理建议：

1. 本地逐项对照当前跨所价差页面和正式策略文档。
2. 将仍有效的唯一信息迁移到 `docs/strategies/跨所价差.md` 或独立页面规格。
3. 完成后标记 `superseded` 并归档。

## 4. 用户确认存在的旧 DOCX

用户明确指出存在：

- `核心模块.docx`
- `需求文档.docx`

建议状态：`archived`

已知结论：

- 这些文件来自项目早期阶段。
- 当前模块定义和需求已经发生较大变化。
- 不应继续作为当前开发依据。

由于 GitHub 代码搜索不会可靠索引二进制 DOCX 文件名，当前无法仅通过代码搜索确认其仓库精确路径和内容。

本地处理步骤：

1. 在项目根目录和 `admin-risk/docs/` 下搜索两个文件。
2. 检查是否包含尚未迁移的唯一业务规则。
3. 将有效规则迁移到对应 active Markdown 文档。
4. 创建 `docs/archive/legacy-docx/`。
5. 移入归档目录并保留原文件。
6. 可按以下格式重命名：
   - `[已归档]核心模块.docx`
   - `[已归档]需求文档.docx`
7. 在 `docs/README.md` 中明确 archive 文件不作为开发依据。

本阶段不直接删除这些 DOCX。

## 5. 需要继续保留但改变用途的文档

### `docs/trading-tools-bookmarks-review.md`

状态：继续 `active`

用途：交易工具目录的唯一人工维护源。

规则：

- 修改交易工具链接时优先更新该文件。
- 通过 `pnpm sync:trading-tools` 生成前端 TypeScript 数据。
- 不将其归档为历史评审文件，即使文件名含 `review`。

### `docs/audit/*`

状态：`active`

用途：记录资产盘点和清理决策，不直接定义产品需求。

## 6. 建议归档目录

```text
docs/archive/
├─ legacy-docx/
├─ handoffs/
├─ superseded/
│  └─ strategy/
└─ historical-design/
```

## 7. 归档顺序

1. 先确认新 active 文档已经覆盖核心口径。
2. 对照旧文档，迁移唯一有效信息。
3. 在旧文档顶部标记状态和替代文档。
4. 再移动到 archive。
5. 更新 `docs/README.md`。
6. 不删除二进制或历史文件，除非用户另行明确要求。

## 8. 当前禁止动作

- 不直接删除 `核心模块.docx` 和 `需求文档.docx`。
- 不批量删除 `docs/strategy/`。
- 不将 `trading-tools-bookmarks-review.md` 归档。
- 不根据文件名直接判断内容全部无效。
- 不让临时交接文档继续覆盖 active 模块文档。

## 9. 完成标准

后续本地归档完成后应满足：

- `docs/README.md` 只索引当前有效文档。
- 旧 DOCX 位于 `docs/archive/legacy-docx/`。
- 交接文件位于 `docs/archive/handoffs/`。
- 被替代的策略文档位于 `docs/archive/superseded/strategy/`。
- 所有归档文件不再作为 Codex 默认上下文。
- 旧文档中的唯一有效信息已经迁移。
