# Git Workflow and Version Governance

本项目采用两条工作通道：高风险或有行为变化的工作走完整工程流程；有限、非行为性的版本与 Markdown 维护走轻量维护流程。分类不确定时，默认使用完整工程流程。

## 1. 完整工程流程

以下变化必须使用完整工程流程：

- 产品、Backend、Runtime 或前端运行行为；
- 交易、执行、订单状态、风险、权限、凭证或资金安全；
- 数据库、迁移、Schema、Seed 或持久化语义；
- Platform–Runtime 合约、公开 API 或兼容性；
- 环境配置、部署行为、CI 工作流或安全默认值；
- 跨模块重构、生产故障修复或分类不明确的工作。

唯一关系：

```text
一个工程目标
  → 一个 GitHub Issue
  → 一个 tasks/issue-<number>-<slug>.md
  → 一个 <type>/issue-<number>-<slug> 分支
  → 一个引用该 Issue 的开放 PR
  → squash merge 到 main
```

同一 Issue 同时存在两个开放 PR，CI 失败。

### 开始工程任务前

1. 搜索开放 Issue、PR 和 `tasks/`，确认没有同一结果正在进行。
2. 已有 Issue 时复用，不再创建“类似但换名字”的任务。
3. 创建或更新任务包，先写目标、非目标、受保护语义和验收命令。
4. 从最新 `main` 创建分支。

工程分支格式：

```text
feature/issue-123-add-report
fix/issue-124-recover-order
refactor/issue-125-split-accounting-module
hardening/issue-126-runtime-safety
docs/issue-127-update-runbook
chore/issue-128-tooling
```

Slug 只能使用小写字母、数字和连字符；版本号写成 `0-8-1`，不能写成 `0.8.1`。

工程 PR 必须包含一个独立关联行：

```text
Issue: #123
```

也可以使用 `Closes #123`、`Fixes #123` 或 `Resolves #123`。

## 2. 轻量维护流程

轻量维护流程只用于**有限、可机器验证、没有产品行为或安全语义变化**的工作：

- 同步根 `VERSION`、Backend、Runtime 和前端展示版本；
- 新增或修正发布说明；
- README、Changelog 和 Markdown 的文字、链接、格式或当前状态修正；
- 不改变产品事实的发布元数据清理。

轻量维护流程使用：

```text
一个 docs/<slug> 或 chore/<slug> 分支
  → 一个 Maintenance PR
  → 正常 CI、Version Consistency（适用时）和 Secret Scan
  → squash merge 到 main
```

**不需要**单独创建 Issue、任务包或合并后的第二个元数据 PR。

维护分支示例：

```text
docs/release-0-8-1
chore/fix-release-links
```

维护 PR 必须包含以下三个独立声明：

```text
Maintenance: true
Behavior change: none
Safety change: none
```

维护 PR 不得再关联工程 Issue。只要需要关联 Issue，就应改用完整工程流程。

### 维护模式机器边界

`scripts/check-workstream.py` 只允许：

- Markdown 文件，但不包括 `AGENTS.md`、`.github/` 和 `tasks/`；
- 根 `VERSION`；
- `platform-backend/pyproject.toml` 的产品版本行；
- `execution-runtime/pyproject.toml` 的产品版本行；
- `admin-risk/.env` 的 `VITE_APP_VERSION` 行。

版本更新时，四个 maintained release 声明必须在同一 PR 中全部同步。机器检查会读取 patch，拒绝在版本文件中夹带其他配置变化。

以下任一情况会拒绝维护模式并要求完整工程流程：

- 修改应用源码、测试以外的可执行脚本、工作流或运行配置；
- 修改数据库、迁移、契约、权限、凭证或安全默认值；
- 文件重命名；
- 超过 20 个文件；
- PR 缺少明确的无行为变化、无安全变化声明；
- 分类存在争议。

## 3. PR 内容规则

所有 PR 都必须写明：

- 一个可衡量结果；
- Included / Excluded；
- 哪些业务或安全语义不变；
- 实际执行的测试与 CI；
- 风险和回滚；
- 是否替代旧 PR。

不要在一个 PR 中顺手加入无关清理。

## 4. 需要换工程分支时

禁止先开第二条分支再决定用哪条。

正确顺序：

1. 在旧 PR 留下 `Superseded by #<new-pr>`；
2. 关闭旧 PR；
3. 更新任务包中的 Branch；
4. 从最新 `main` 创建新分支；
5. 新 PR 引用同一 Issue，并说明替代理由。

旧分支的提交仍保留在关闭 PR 中，不需要让旧分支长期停留在一个看似可发布的状态。

## 5. 合并方式

- 只通过 PR 进入 `main`。
- 默认 squash merge。
- 合并前必须基于当前 `main` 重新验证。
- CI、Secret Scan、架构检查和审查意见全部通过。
- 工程 PR 合并后关闭 Issue；维护 PR 没有 Issue 可关闭。

`main` 是唯一正式代码基线。功能版本、历史 PR 分支和任务分支都不能被描述为“另一套主版本”。

## 6. 版本治理

根目录 `VERSION` 是整个平台产品发布版本的唯一声明源。以下 maintained release 声明必须与其一致：

- `platform-backend/pyproject.toml` 的包版本；
- `execution-runtime/pyproject.toml` 的包版本；
- `admin-risk/.env` 的前端展示版本。

FastAPI 应用元数据和 Platform–Runtime 合约版本描述的是组件/API 兼容性，不随每个产品发布版本机械递增。`scripts/check-version-consistency.py` 与 CI 会阻止产品发布版本漂移。

常规版本发布可以直接使用轻量维护流程，但必须满足：

- 只修改四个版本声明和相关 Markdown；
- 不改变代码、配置语义、合约、迁移或安全默认值；
- Release Notes 明确区分工程完成与真实环境验收。

Release Notes 不要求记录 squash merge SHA。GitHub PR 和 `main` 历史是合并事实的权威来源；**不要为了回填 merge commit 再创建一个 Issue/PR**。

Tag 只用于经过验收、需要明确回滚或部署识别的稳定点，例如：

```text
engineering-baseline-2026-07
v0.8.0-rc1
v0.8.0
```

不要为每次提交打 Tag。

## 7. 跨对话续接

工程任务只需要提供：

```text
仓库：wuxingyuenan5-lgtm/Platform_Experiment
Issue：#123
任务包：tasks/issue-123-xxx.md
请先核验 main、Issue、分支和开放 PR，再继续。
```

轻量维护任务只需要提供目标和当前维护分支/PR；没有 Issue 或任务包。

Agent 默认读取：

1. `AGENTS.md`；
2. `docs/codex/current-state.md`；
3. 工程任务对应任务包（维护 PR 不适用）；
4. 目标模块或目标文档。

不要复制整段旧聊天，也不要要求重新扫描全仓。

## 8. 分支清理判断

满足以下全部条件可清理或归位：

- PR 已关闭；
- 工作已由另一个合并 PR 完整取代，或分支只有临时生成脚本/诊断工作流；
- 重要历史可由关闭 PR 和 commit SHA 找回；
- 与当前 `main` 比较后没有未迁移的独立业务成果。

不确定时不删除，先记录差异和归属。

## 9. 机器门禁

- `scripts/check-workstream.py`：完整工程流程唯一关系，以及轻量维护声明、分支和 changed-file 边界。
- `scripts/check-repository-structure.py`：架构、上下文、数据库和契约结构。
- `scripts/check-version-consistency.py`：产品发布版本一致性。
- Platform CI：Ruff、Pyright、Pytest、Frontend ESLint/type/build。
- Secret Scan：阻止凭证材料进入仓库。

规则被机器执行后，文档不再只是建议。