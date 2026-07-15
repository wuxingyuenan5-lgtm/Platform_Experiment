# 历史文档归档清单

状态：`active`

本文件记录已经实际移动到归档区的文件。归档内容仅供历史追溯，不作为当前产品和开发依据。

## 已完成归档

### 历史交接

- `handoff/codex-session-handoff.md`
  - 原路径：`docs/codex-session-handoff.md`
  - 原因：包含 V4、本地未提交状态等已经过期的信息。

- `handoff/2026-07-15-项目上下文交接.md`
  - 原路径：`docs/2026-07-15-项目上下文交接.md`
  - 原因：属于阶段性交接，相关规则已迁移到正式模块、策略和架构文档。

### 已被替代的策略文档

- `superseded/strategy-module-current-requirements.md`
  - 原路径：`docs/strategy-module-current-requirements.md`
  - 原因：旧的策略模块汇总需求，已被模块需求和六类策略文档替代。

- `superseded/strategy/2026-07-09-策略模块现状需求文档.md`
  - 原路径：`docs/strategy/2026-07-09-策略模块现状需求文档.md`
  - 原因：阶段性现状快照，且原文件存在编码显示异常风险，因此采用 Git Blob 原样移动。

- `superseded/strategy/2026-07-12-策略模块结构设计方案-A1.md`
  - 原路径：`docs/strategy/2026-07-12-策略模块结构设计方案-A1.md`
  - 原因：阶段性 A1 方案，核心规则已进入正式文档。

## 暂未归档

### 需要内容复核

- `docs/strategy/2026-07-10-MT5黄金跨所价差建议看板需求文档.md`
  - 状态：`review-required`
  - 原因：可能包含仍未迁移的具体交易字段和页面规格。

### 需要本地定位的 DOCX

- `核心模块.docx`
- `需求文档.docx`

GitHub 代码搜索无法可靠确认二进制 DOCX 的精确路径。应在本地找到文件、迁移仍有效信息后，再移入 `legacy-docx/`。

## 当前有效入口

所有当前需求和架构口径从 `../README.md` 开始读取。
