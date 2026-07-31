# 项目推进计划

## 权威入口

- 当前工程状态：`docs/codex/current-state.md`
- 系统性优化主线：GitHub Issue #136
- 总体方案：`docs/architecture/PLATFORM_0_9_2_SYSTEM_OPTIMIZATION_MASTER_PLAN.md`
- 当前任务包：`tasks/issue-136-platform-0-9-2-system-optimization.md`

## 已完成阶段

- Phase A–D：全仓审计、上下文治理、完整质量门禁、56页视觉基线和目录治理；
- Research E1–E5.1；
- Identity I1/I2.1；
- Portfolio P1–P3；
- Frontend F1/F2；
- High-risk H0–H2，并按停止条件保留Trading、Risk、Formal Accounting与Execution Runtime原Owner；
- Phase J / J0仓库证据、安全净化、Legacy冻结门禁和外部证据工具；
- Phase J / J2第一轮本地产物及上游托管脚手架清理。

## 当前阶段

继续Phase J / J2 GitHub仓库减负。只处理满足以下全部条件的候选：

1. 已完成当前分支引用核验；
2. 无需服务器、数据库、Windows、GitLab Runner或真实Venue权限；
3. 无需重算pnpm锁文件；
4. 不改变路由、API、权限、Financial Fact、Decimal、正式账务、对账或执行安全合同；
5. 能通过永久测试或静态门禁防止回归。

当前子目标是收口仓库身份、文档入口、无效生成物和明确失效的脚手架元数据。

## 延期验收

以下项目暂不阻塞GitHub内优化，但在0.10.1正式验收前仍必须完成：

- 旧服务器、Nginx、systemd与GitLab Runner证据；
- MySQL数据、备份、恢复和凭据轮换；
- Windows真实本地运行；
- HTTPS/TLS；
- 真实Venue/Broker；
- 正式会计、EOD、对账和最终回滚演练。

## 约束

- `execution-runtime`保持独立且不改名；
- `projects/risk-control`、`deploy/`、`platform-web/.gitlab-ci.yml`和生产API路由在外部证据完成前保持冻结；
- Draft PR保持Open、Draft、Unmerged；
- 未经所有者明确批准不得修改或合并`main`；
- `0.10.1`只在完整验收与所有者批准后进入。
