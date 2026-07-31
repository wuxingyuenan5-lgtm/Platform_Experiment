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
- [x] Phase J / J0仓库证据、凭据文档净化、Secret Scan增强、只读采集工具、MySQL聚合清单和人工交接；
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

## H1 EOD路由Owner：完成

- [x] `eod_reconciliation_routes.py`拥有四个端点、response models、tags和Query别名；
- [x] Facade保留兼容导出、每次调用依赖装配和409/404/422映射；
- [x] Service、Policy、Repository、Schemas、Financial Fact、Venue、DDL、Decimal、幂等性、不可变Review与失败关闭语义未修改。

验证HEAD：`5f992691c35921c0647cd8e7f800fca48a547359`

- Platform CI `30640101027`
- Directory `30640101717`
- Version `30640100742`
- Secret `30640100821`
- User E2E `30640100255`
- Audit `30640100980`
- Visual `30640101256`
- Hedge E2E `30640101724`
- Provider Smoke `30640100623`

视觉Artifact：`8797146922`  
SHA-256：`f722456de6afce3068239a2de51ca58895133aa6cbd1eef6f0af9afc1ab00453`

## H2 Venue路由Owner：完成

- [x] `venue_reconciliation_routes.py`拥有五个端点、response models和tags；
- [x] Facade保留Repository别名、兼容Delegate及503/422/409/403/404映射；
- [x] EOD、Live Accounting、Live Session和测试继续调用Facade兼容端口；
- [x] Service、Policy、Repository、Runtime Client、Schemas、Financial Fact、DDL与Decimal未修改；
- [x] 永久架构测试冻结Service、Facade、Routes与Main四边界。

验证HEAD：`7c60ac24d0b728a0c5383530310752a3070ed876`

- Platform CI `30641383890`
- Directory `30641383425`
- Version `30641384052`
- Secret `30641383524`
- User E2E `30641383467`
- Audit `30641383452`
- Visual `30641383554`
- Hedge E2E `30641383539`
- Provider Smoke `30641383446`

视觉Artifact：`8797697682`  
SHA-256：`3898d7b32d1413c8fddfe5c024c4c1eea31b67b05561ca66a5e48dd8355f6d93`

## 高风险结构治理停止决定

Trading、Risk、Formal Accounting与Execution Runtime已有明确且内聚的Owner；EOD与Venue的路由混合债务已清除。当前没有新的纯结构切口能够在不扩大策略、SQL、外部副作用或兼容面的前提下产生明确收益，因此停止继续拆分高风险域。

## Phase J / J0仓库工作：完成

权威审计：`docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md`。

### 已确认事实

- [x] `deploy/install-native.sh`定义另一套完整生产安装路径；
- [x] 旧路径构建Go Auth/Data服务并安装Nginx、systemd与MySQL依赖；
- [x] `platform-web/.env.production`仍请求`/api/auth`、`/api/data`和`/api/data/ws`；
- [x] Auth Service拥有独立MySQL用户Schema、JWT、Session和管理员初始化；
- [x] Data Service拥有MySQL数据、Bybit Client、账户加密和NAV Scheduler；
- [x] MySQL可能持有用户、Session、账户密钥、仓位和净值历史；
- [x] Legacy不能视为Demo、死代码或可直接归档目录。

### 安全与证据准备

- [x] 净化历史项目文档和旧启动入口中的可复用凭据与弱密码方案；
- [x] Secret Scan检测中文密码字段、SQL固定密码和MD5/SHA-1密码字面量；
- [x] 已泄露值按永久泄露处理，服务器侧仍须轮换；
- [x] `scripts/collect-legacy-production-evidence.sh`只采集最小服务器元数据；
- [x] `scripts/legacy-production-readonly-inventory.sql`只输出Schema与聚合统计；
- [x] 永久架构测试禁止读取Secret值、业务行、密码Hash和交易所密钥；
- [x] `docs/operations/LEGACY_PRODUCTION_EVIDENCE_HANDOFF.md`冻结授权执行、脱敏复核与回传规则；
- [x] 在外部证据完成前，禁止删除、重命名或自动切换旧生产体系。

### J0仓库完整矩阵

验证HEAD：`f6d981f8d344efe1d35c904a0681c4eebe4ced6a`

- Platform CI `30644276655`
- Directory `30644276369`
- Version `30644276072`
- Secret `30644276187`
- User E2E `30644279462`
- Audit `30644276220`
- Visual `30644276722`
- Hedge E2E `30644279273`
- Provider Smoke `30644276061`

视觉Artifact：`8798863140`  
SHA-256：`2e81205c692ad12f71b6d88b5db4329c50730b878fcb028e6b0d369306e86354`

该矩阵只证明仓库侧分类、安全守卫、采集工具和交接流程，不证明远程服务器、Nginx、systemd或MySQL当前状态。

## 当前门禁：J0外部只读证据

由拥有服务器和MySQL只读权限的人员执行，仍待完成：

- [ ] 服务器仓库目录、分支、HEAD与工作区状态；
- [ ] systemd启用/活动状态和监听端口；
- [ ] Nginx加载配置、域名、TLS和Legacy路由请求量；
- [ ] 环境文件存在性、权限、键名与Hash，不读取值；
- [ ] MySQL表、列、索引、约束、聚合行数和最近写入；
- [ ] 用户、Session、账户、敏感列占用与Bybit同步状态，不导出业务行；
- [ ] 备份、恢复演练和回滚路径；
- [ ] MySQL、JWT、账户加密、交易所与历史管理员凭据轮换；
- [ ] `/api/auth`、`/api/data`和WebSocket的真实消费者。

外部证据回传前：

- [ ] 不删除或重命名`projects/risk-control`；
- [ ] 不删除或改写`deploy/`；
- [ ] 不修改`.env.production`API路由；
- [ ] 不自动导入MySQL数据；
- [ ] 不关闭旧systemd服务；
- [ ] 不将旧JWT、密码Hash或Bybit任务直接迁入新体系；
- [ ] 不宣称旧体系为Demo或已废弃。

## 后续顺序

J0外部证据 → J1继续维护/受控迁移/确认无依赖三选一 → 仓库减负候选 → Windows/TLS/真实Venue与正式会计对账验收。

## Protected invariants

Browser Session/API-Key、CSRF/Origin、角色与会员隔离、Decimal、Financial Fact、PnL/NAV、正式会计、对账、不可变迁移、Kill Switch、双人审批、Live Write、幂等性、Market/FOK/PostOnly/TP-SL、Result Unknown、EOD/LKG、数据状态、TLS和Runtime边界均不得改变。
