# Issue #136 — Platform 0.9.2 全平台系统性优化任务包

Workstream: critical  
Issue: #136  
Branch: `refactor/issue-136-platform-0-9-2-system-optimization`

## 交付边界

- Baseline branch: `feature/issue-134-platform-0-9-1-unified-delivery`
- Frozen baseline SHA: `8114fce45e46e7920f316f49d03db12dc424acf1`
- Development/acceptance version: `0.9.2`
- Final accepted candidate: `0.10.1`
- Merge policy: Draft only; never auto-merge; never modify `main`; owner approval required.
- Live Draft PR, HEAD, CI and review status: GitHub Issue #136.
- Superseded PRs #137 and #138 remain closed and unmerged as branch-governance history.

## Core objective

对整个基金投研交易资管平台进行证据化审计、减负、架构与代码优化、命名治理、AI上下文和Token优化，并在保持平台可运行、前端视觉和业务/安全语义稳定的前提下完成0.9.2开发验收，最终形成0.10.1正式候选。

对冲基金看板只是Research业务域中的一个模块，不是本任务中心。

## 已完成门禁

- [x] 冻结真实0.9.1统一交付基线并建立Issue #136、独立0.9.2分支和Draft PR；
- [x] 完成全仓代码、目录、依赖、CI、测试、文档、Token、部署和数据库证据化审计；
- [x] 建立单一当前状态、Context Map、模块AGENTS和按任务读取工具；
- [x] 建立Platform API、Runtime、前端Build、Provider Smoke、两套Browser E2E、Secret、Version、Directory、Audit和56页视觉门禁；
- [x] 完成`admin-risk → platform-web`与`platform-backend → platform-api`原子目录迁移；
- [x] 完成Research E1–E5.1的Provider、状态、主看板低风险组件和A股观察列表职责拆分；
- [x] 完成Identity I1管理员响应Presenter和I2.1 Session Presenter；
- [x] 完成Portfolio P1会员持仓纯估值Owner并通过完整质量矩阵；
- [x] 完成Portfolio P2 Fund catalog/NAV mutation响应只读复核并收口后端模块化；
- [x] 保持Platform Web / Platform API模块化单体 / Execution Runtime三边界，无微服务化或重型基础设施扩张。

## Portfolio P1纯估值层：完成

### 已实施

- [x] 新增`platform-api/app/member_holding_valuation.py`作为无数据库、无HTTP、无权限和无审计副作用的纯估值Owner；
- [x] 使用只读Protocol解除估值Owner对Repository记录类型的依赖；
- [x] Service继续拥有Fund/NAV加载、会员范围、近期再认证、事务、审计和错误映射；
- [x] 保持Decimal字符串、NAV三态、币种一致性、UTC归一化、36小时陈旧阈值和未来5分钟边界；
- [x] 新增完整响应Golden、Decimal/时间边界测试、纯度架构测试和Pyright覆盖；
- [x] 更新`docs/architecture/OWNERSHIP.md`、Portfolio专项计划和文档一致性守卫；
- [x] 删除一次性写权限Workflow和迁移脚本。

### 验收证据

验证HEAD：`1697345b59517d603a30377934271ba5946d4856`

- [x] Platform API Ruff、Pyright和全测试：Platform CI `30626771566`；
- [x] Execution Runtime Ruff、Pyright和全测试：Platform CI `30626771566`；
- [x] Platform Web Lint、Type Check和生产Build：Platform CI `30626771566`；
- [x] Research Provider Smoke：`30626771610`；
- [x] User System Browser E2E：`30626771578`；
- [x] Hedge Board Browser E2E：`30626771582`；
- [x] Secret Scan：`30626771577`；
- [x] Version Consistency：`30626771572`；
- [x] Platform Directory Invariants：`30626771569`；
- [x] Platform 0.9.2 Baseline Audit：`30626771579`；
- [x] 56页四档视觉基线：`30626771581`。

视觉Artifact：`8791768494`  
SHA-256：`74df3b5503ed41204719acd1d06203fcc3fa3c9479a18972a544acc2a81a7a32`

## Portfolio P2只读复核：完成

- [x] `_fund_response`已被基金目录和NAV mutation两处局部复用，无跨模块重复；
- [x] Fund catalog只包含Repository读取与四字段列表映射；
- [x] NAV mutation响应依赖事务内更新后的Fund、持久化NAV和规范化估值时间；
- [x] 两处均无独立政策、计算、错误合同或跨域复用；
- [x] 决定不新增Fund catalog或NAV mutation Presenter；
- [x] Portfolio后端模块化正式收口，不触碰Financial Fact、Position Math或Formal Projection。

## 当前门禁：Portfolio前端与公共展示

复核会员自助与管理员视角的持仓展示，重点统一Decimal、币种、NAV三态、空收益率和零收益率表达。只有存在真实重复、错误或可维护性收益时才修改组件；每一改动必须保持权限范围、API合同、DOM/样式和视觉基线。

后续顺序仍为：Portfolio前端与公共展示 → 前端热点治理 → 高风险域只读审计 → Trading/Risk/Accounting/Reconciliation/Runtime逐门禁优化 → 旧Go/MySQL部署定性与仓库减负 → 真实环境验收。

## Protected invariants

- Browser Session和API-Key权限隔离；
- CSRF、Origin、角色、最后CEO和会员数据隔离；
- Decimal、Financial Fact、PnL、NAV、正式会计和对账语义；
- 不可变数据库迁移、备份和恢复；
- Kill Switch、两人审批和Live Write默认关闭；
- 幂等性、Market、FOK、PostOnly、TP/SL和Result Unknown；
- EOD、Reconciliation、Last Known Good与`partial`/`stale`/`no_data`/`error`；
- TLS验证与Platform API / Execution Runtime边界；
- 现有用户可见布局、信息层级、主要流程和响应式行为。

## Stage gate and rollback

每一主阶段必须具备：明确文件范围、基线与Golden、单独提交组、完整验收、可回滚点和停止条件。不得在失败门禁上继续叠加改动。

出现业务、交易、会计、权限、数据库或错误合同漂移，无法保持视觉等价，暴露秘密，关闭TLS/类型/安全检查，需要修改`main`，或基线不稳定时，立即停止并报告。
