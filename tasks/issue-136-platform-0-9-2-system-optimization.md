# Issue #136 — Platform 0.9.2 全平台系统性优化任务包

Workstream: critical  
Issue: #136  
Branch: `refactor/issue-136-platform-0-9-2-system-optimization`

## 交付边界

- Baseline：`feature/issue-134-platform-0-9-1-unified-delivery@8114fce45e46e7920f316f49d03db12dc424acf1`
- Development/acceptance：`0.9.2`
- Final accepted candidate：`0.10.1`
- Draft PR保持Open、Draft、Unmerged；`main`保持保护；最终进入需所有者明确批准。

## 已完成主门禁

- [x] Phase A–D：全仓审计、上下文治理、质量门禁、56页视觉基线和目录迁移；
- [x] Research E1–E5.1；
- [x] Identity I1/I2.1；
- [x] Portfolio P1–P3；
- [x] Frontend F1/F2；
- [x] High-risk H0责任盘点；
- [x] High-risk H1 EOD专用路由Owner；
- [x] High-risk H2 Venue专用路由Owner；
- [x] 前端热点与高风险结构治理按停止条件收口；
- [x] Platform Web / Platform API模块化单体 / Execution Runtime三边界保持不变。

## 关键历史证据

- Portfolio P3：`e41267cc70b5e852b3069d71a6a8d7b1092127ad`；视觉`8792572937`；SHA-256 `5109b685a9b0e2b9926c364f6fbadf95aae5982a6a5d77b073e5c32a6f33a7de`。
- Frontend F1：`96919d31fecbfb0e99cbbbac5fff735436ecab11`；视觉`8793413949`；SHA-256 `3fbc0b599690b97bdc59fcb9f318d74185fd5599823224cd7ffe8a24bae46da2`。
- Frontend F2：`56f53a67d8b85e2c6988da62044a2940b8eedc7e`；视觉`8796528988`；SHA-256 `5189b39b5778ce20ae425b0879006dc7c03694f48acce57a6aa5ba77efbdc2be`。
- Snapshot来源SHA-256：`20245f2606e15add5e97387c238532697c938677865c9d620178bbc9522b788a`。
- Snapshot规范化语义SHA-256：`580983d83781cb7f0731dd39837d75b16eaf24be18751367432aa605fa0acc92`。

## H1 EOD路由Owner：完成

- [x] `eod_reconciliation_routes.py`拥有四个端点、response models、tags和Query别名；
- [x] Facade保留兼容导出、依赖装配和409/404/422映射；
- [x] Service、Policy、Repository、Schemas、Financial Fact、Venue、DDL、Decimal与失败关闭语义未修改。

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

### 已实施

- [x] 新增`platform-api/app/venue_reconciliation_routes.py`；
- [x] 仅迁移五个端点、APIRouter、response models和tags；
- [x] `main.py`从专用路由模块导入router；
- [x] Facade继续拥有Repository别名、兼容Delegate及503/422/409/403/404错误映射；
- [x] EOD、Live Accounting、Live Session和测试继续调用Facade兼容端口；
- [x] Service、Policy、Repository、Runtime Client、Schemas、Financial Fact、DDL与Decimal未修改；
- [x] 永久架构测试冻结Service、Facade、Routes与Main四边界；
- [x] Ownership目录已更新；
- [x] 一次性写权限Workflow与脚本已清除。

### H2完整矩阵

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

Trading、Risk、Formal Accounting与Execution Runtime已有明确且内聚的Owner；EOD与Venue的显式路由混合债务已清除。当前没有新的纯结构切口能够在不扩大策略、SQL、外部副作用或兼容面的前提下产生明确收益，因此停止继续拆分高风险域。

## 当前门禁：Phase J / J0旧生产部署定性

权威计划：`docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md`。

### 已确认仓库事实

- [x] `scripts/dev-platform.ps1`定义当前目标三进程：Platform Web、Platform API和Execution Runtime；
- [x] `deploy/install-native.sh`定义另一套完整生产安装路径；
- [x] 旧路径构建两个Go服务并安装Nginx、systemd和MySQL依赖；
- [x] `deploy/README.md`包含固定服务器、MySQL、备份、升级和回滚步骤；
- [x] `platform-web/.env.production`仍默认请求`/api/auth`、`/api/data`和`/api/data/ws`；
- [x] 旧Auth Service拥有独立MySQL用户Schema、JWT和管理员初始化；
- [x] 旧Data Service拥有独立MySQL数据、Bybit Client和NAV Scheduler；
- [x] 旧服务CORS、安全模型、角色和数据合同不能自动等价为Platform API。

### J0停止条件

在服务器、Nginx、MySQL、用户、凭据、API消费者和数据证据齐备前：

- [ ] 不删除或重命名`projects/risk-control`；
- [ ] 不删除或改写`deploy/`；
- [ ] 不修改`.env.production`API路由；
- [ ] 不自动导入MySQL数据；
- [ ] 不关闭旧systemd服务；
- [ ] 不将旧JWT、密码Hash或Bybit任务直接迁入新体系；
- [ ] 不宣称旧体系为Demo或已废弃。

### J0待取得真实证据

- [ ] 服务器当前仓库目录、分支、HEAD和工作区状态；
- [ ] systemd、监听端口和实际进程；
- [ ] Nginx加载配置、域名和TLS状态；
- [ ] 环境文件存在性和权限，不读取或记录Secret值；
- [ ] MySQL数据库、表、约束、数据量和最后更新时间；
- [ ] 用户、角色、审批、密码Hash格式与新身份模型映射；
- [ ] 账户、净值、Bybit同步和外部写入依赖；
- [ ] `/api/auth`、`/api/data`及WebSocket的全部真实消费者；
- [ ] 备份恢复、切换和回滚方案。

## 后续顺序

J0真实依赖定性 → J1继续维护/受控迁移/确认无依赖三选一 → 仓库减负候选 → Windows/TLS/真实Venue与正式会计对账验收。

## Protected invariants

Browser Session/API-Key、CSRF/Origin、角色与会员隔离、Decimal、Financial Fact、PnL/NAV、正式会计、对账、不可变迁移、Kill Switch、双人审批、Live Write、幂等性、Market/FOK/PostOnly/TP-SL、Result Unknown、EOD/LKG、数据状态、TLS和Runtime边界均不得改变。
