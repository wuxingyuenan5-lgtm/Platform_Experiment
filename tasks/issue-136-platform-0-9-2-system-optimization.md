# Issue #136 — Platform 0.9.2 全平台系统性优化任务包

Workstream: critical  
Issue: #136  
Branch: `refactor/issue-136-platform-0-9-2-system-optimization`

## 交付边界

- Baseline：`feature/issue-134-platform-0-9-1-unified-delivery@8114fce45e46e7920f316f49d03db12dc424acf1`
- Development/acceptance：`0.9.2`
- Final accepted candidate：`0.10.1`
- Draft PR必须保持Open、Draft、Unmerged；`main`保持保护；最终进入需所有者明确批准。

## 已完成主门禁

- [x] Phase A–D：全仓审计、上下文治理、完整质量门禁、56页视觉基线和目录迁移；
- [x] Research E1–E5.1；
- [x] Identity I1/I2.1；
- [x] Portfolio P1–P3；
- [x] Frontend F1/F2；
- [x] High-risk H0责任盘点；
- [x] High-risk H1 EOD专用路由Owner；
- [x] High-risk H2 Venue专用路由Owner；
- [x] 前端热点与高风险结构治理按停止条件收口；
- [x] Phase J / J0仓库证据、凭据净化、Secret Scan增强、只读采集工具、MySQL聚合清单和人工交接；
- [x] Platform Web / Platform API模块化单体 / Execution Runtime三边界保持不变。

## 关键历史证据

### Portfolio P3

验证HEAD：`e41267cc70b5e852b3069d71a6a8d7b1092127ad`  
视觉Artifact：`8792572937`  
SHA-256：`5109b685a9b0e2b9926c364f6fbadf95aae5982a6a5d77b073e5c32a6f33a7de`

### Frontend F1

验证HEAD：`96919d31fecbfb0e99cbbbac5fff735436ecab11`  
视觉Artifact：`8793413949`  
SHA-256：`3fbc0b599690b97bdc59fcb9f318d74185fd5599823224cd7ffe8a24bae46da2`

### Frontend F2

验证HEAD：`56f53a67d8b85e2c6988da62044a2940b8eedc7e`  
视觉Artifact：`8796528988`  
SHA-256：`5189b39b5778ce20ae425b0879006dc7c03694f48acce57a6aa5ba77efbdc2be`

Snapshot来源SHA-256：`20245f2606e15add5e97387c238532697c938677865c9d620178bbc9522b788a`  
Snapshot规范化语义SHA-256：`580983d83781cb7f0731dd39837d75b16eaf24be18751367432aa605fa0acc92`

### H1 EOD路由Owner

验证HEAD：`5f992691c35921c0647cd8e7f800fca48a547359`  
视觉Artifact：`8797146922`  
SHA-256：`f722456de6afce3068239a2de51ca58895133aa6cbd1eef6f0af9afc1ab00453`

- `eod_reconciliation_routes.py`拥有四个端点；
- Facade保留兼容导出、每次调用依赖装配和409/404/422映射；
- Service、Policy、Repository、Schemas、Financial Fact、Venue、DDL、Decimal、幂等性和失败关闭语义未修改。

### H2 Venue路由Owner

验证HEAD：`7c60ac24d0b728a0c5383530310752a3070ed876`  
视觉Artifact：`8797697682`  
SHA-256：`3898d7b32d1413c8fddfe5c024c4c1eea31b67b05561ca66a5e48dd8355f6d93`

- `venue_reconciliation_routes.py`拥有五个端点；
- Facade保留Repository别名、兼容Delegate和完整错误映射；
- Service、Policy、Repository、Runtime Client、Schemas、Financial Fact、DDL与Decimal未修改；
- 永久架构测试冻结Service、Facade、Routes与Main四边界。

## 高风险结构治理停止决定

Trading、Risk、Formal Accounting与Execution Runtime已有明确且内聚的Owner；EOD与Venue的路由混合债务已清除。没有新的纯结构切口能够在不扩大策略、SQL、外部副作用或兼容面的前提下产生明确收益，因此停止继续拆分高风险域。

## Phase J / J0仓库工作：完成

权威审计：`docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md`。

已确认并冻结：

- `deploy/`定义Nginx、systemd、Go Auth/Data和MySQL旧生产路径；
- `platform-web/.env.production`仍请求`/api/auth`、`/api/data`和`/api/data/ws`；
- 旧Auth拥有独立MySQL、JWT、Session和管理员初始化；
- 旧Data拥有MySQL、Bybit Client、账户加密和NAV Scheduler；
- MySQL可能持有用户、Session、账户密钥、仓位和净值历史；
- Legacy不能视为Demo、死代码或可直接归档目录。

仓库侧安全准备：

- 净化历史凭据和弱密码方案；
- Secret Scan覆盖中文密码字段、SQL固定密码和MD5/SHA-1字面量；
- `scripts/collect-legacy-production-evidence.sh`只采集最小服务器元数据；
- `scripts/legacy-production-readonly-inventory.sql`只输出Schema与聚合统计；
- `docs/operations/LEGACY_PRODUCTION_EVIDENCE_HANDOFF.md`冻结授权、脱敏和回传规则；
- 永久架构测试禁止读取Secret值、业务行、密码Hash和交易所密钥。

J0验证HEAD：`9981f7b5f7cdb60210efd3a6bba4f59477096df9`

- Platform CI `30645414569`
- Directory `30645414648`
- Version `30645414566`
- Secret `30645414560`
- User E2E `30645414615`
- Audit `30645414517`
- Visual `30645414551`
- Hedge E2E `30645414775`
- Provider Smoke `30645414626`

视觉Artifact：`8799314716`  
SHA-256：`e6916a36276e0d9877aa2c99b7ed7cbde31c03aeadc8ae9f0dce1bfb28965271`

## J1外部验收：延期，不阻塞GitHub优化

当前GitHub连接无法读取旧服务器、GitLab Runner或MySQL。按所有者指示，以下验收暂时跳过，但仍保留为最终发布条件：

- 服务器、systemd、Nginx、TLS与访问日志；
- MySQL Schema、聚合数据、备份与恢复；
- Legacy消费者、凭据轮换和回滚；
- GitLab项目、`runner20`、`risk-web.rta-office.com`和历史Pipeline。

外部证据返回前仍禁止：

- 删除或重命名`projects/risk-control`；
- 删除或改写`deploy/`；
- 删除或改写`platform-web/.gitlab-ci.yml`；
- 修改`.env.production`Legacy API路由；
- 自动导入MySQL、关闭旧服务或宣称Legacy已退役。

GitLab路径权威审计：`docs/architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md`。

## 当前门禁：Phase J / J2 GitHub仓库减负

权威规则：`docs/operations/WORKSPACE_HYGIENE.md`。

### 已实施切口

- [x] 删除`platform-web/home-2560-check.png`本地截图；
- [x] 删除`platform-web/src/file_structure.txt`过时目录快照；
- [x] 在`platform-web/.gitignore`中防止同类产物回归；
- [x] 删除上游Vben `CNAME`和未使用的Gitpod配置；
- [x] 删除完整的`platform-web/.github`上游元数据子树；
- [x] 新增`test_architecture_frontend_repository_hygiene.py`永久门禁；
- [x] 将`.gitlab-ci.yml`识别为Legacy部署证据并加入永久冻结；
- [x] 去除Workspace Hygiene中的本机绝对路径、过时文件名和一次性容量数字。

### J2继续规则

只允许高置信度、已完成引用核验的删除或归档。遇到以下情况立即停止并单独规划：

- 需要重算pnpm锁文件；
- 影响路由、API、权限、Financial Fact、Decimal、账务或对账；
- 影响生产配置、Legacy资产或运行时数据；
- 依赖Windows、服务器、数据库或真实Venue证据；
- 无法通过完整质量矩阵和56页视觉基线证明无回归。

## 后续顺序

J2 GitHub仓库减负 → 其他GitHub内高置信度优化 → 延期的J1外部验收 → Windows/TLS/真实Venue与正式会计对账验收 → 所有者批准。

## Protected invariants

Browser Session/API-Key、CSRF/Origin、角色与会员隔离、Decimal、Financial Fact、PnL/NAV、正式会计、对账、不可变迁移、Kill Switch、双人审批、Live Write、幂等性、Market/FOK/PostOnly/TP-SL、Result Unknown、EOD/LKG、数据状态、TLS和Runtime边界均不得改变。
