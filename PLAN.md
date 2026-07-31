# 项目推进计划

## 权威入口

- 当前工程状态：`docs/codex/current-state.md`
- 系统性优化主线：GitHub Issue #136
- 总体方案：`docs/architecture/PLATFORM_0_9_2_SYSTEM_OPTIMIZATION_MASTER_PLAN.md`
- 目录迁移方案：`docs/architecture/PLATFORM_DIRECTORY_MIGRATION_PLAN.md`

## 当前阶段

Phase A全仓审计、Phase B上下文减负和Phase C全平台视觉门禁均已完成。当前进入独立命名与目录治理阶段，先迁移Platform Web，再迁移Platform API；每个目录Gate均须通过完整CI、浏览器E2E和四档视觉基线。

## 约束

- 目录重命名不得与业务逻辑或模块重构混在同一提交；
- `execution-runtime`保持独立且不改名；
- `projects/risk-control`在真实服务器、MySQL和用户数据依赖确认前不得删除或机械迁移；
- Draft PR保持Open、Draft、Unmerged，未经所有者明确批准不得修改`main`。
