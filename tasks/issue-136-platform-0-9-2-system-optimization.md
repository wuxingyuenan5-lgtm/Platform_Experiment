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
- [x] High-risk H0–H2，并按停止条件保留Trading、Risk、Formal Accounting与Execution Runtime原Owner；
- [x] Phase J / J0仓库证据、凭据净化、Secret Scan增强、只读证据工具和Legacy冻结门禁；
- [x] Phase J / J2第一轮本地产物与上游托管脚手架清理；
- [x] Phase J / J2第二轮仓库身份、版本、文档可移植性和MT5桥接路径治理；
- [x] Phase J / J2第三轮共享VS Code配置和扩展推荐治理；
- [x] Platform Web / Platform API模块化单体 / Execution Runtime三边界保持不变。

## 高风险结构治理停止决定

Trading、Risk、Formal Accounting与Execution Runtime已有明确且内聚的Owner；EOD与Venue路由混合债务已清除。没有新的纯结构切口能够在不扩大策略、SQL、外部副作用或兼容面的前提下产生明确收益，因此停止继续拆分高风险域。

## Phase J / J0仓库工作：完成

权威审计：`docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md`。

已确认并冻结：

- `deploy/`定义Nginx、systemd、Go Auth/Data和MySQL旧生产路径；
- `platform-web/.env.production`仍请求`/api/auth`、`/api/data`和`/api/data/ws`；
- 旧Auth拥有独立MySQL、JWT、Session和管理员初始化；
- 旧Data拥有MySQL、Bybit Client、账户加密和NAV Scheduler；
- MySQL可能持有用户、Session、账户密钥、仓位和净值历史；
- Legacy不能视为Demo、死代码或可直接归档目录。

J0验证HEAD：`9981f7b5f7cdb60210efd3a6bba4f59477096df9`  
视觉Artifact：`8799314716`  
SHA-256：`e6916a36276e0d9877aa2c99b7ed7cbde31c03aeadc8ae9f0dce1bfb28965271`

## J1外部验收：延期，不阻塞GitHub优化

当前GitHub连接无法读取旧服务器、GitLab Runner或MySQL。按所有者指示，服务器、systemd、Nginx、TLS、MySQL、Legacy消费者、凭据轮换、回滚及GitLab Pipeline证据暂时跳过，但仍保留为最终发布条件。

外部证据返回前仍禁止：

- 删除或重命名`projects/risk-control`；
- 删除或改写`deploy/`；
- 删除或改写`platform-web/.gitlab-ci.yml`；
- 修改`.env.production`Legacy API路由；
- 自动导入MySQL、关闭旧服务或宣称Legacy已退役。

GitLab路径权威审计：`docs/architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md`。

## Phase J / J2 GitHub仓库减负：达到当前停止条件

权威规则：`docs/operations/WORKSPACE_HYGIENE.md`。

### 第一轮：已验收

- [x] 删除本地首页检查截图和过时目录快照；
- [x] 删除上游Vben `CNAME`、Gitpod配置和完整嵌套`.github`；
- [x] 新增永久前端仓库卫生门禁；
- [x] 将`.gitlab-ci.yml`识别为Legacy部署证据并永久冻结；
- [x] 去除Workspace Hygiene中的本机绝对路径和一次性容量数字。

验证HEAD：`3b251c795826ba583c5cefb11f160b315ee7a75e`  
视觉Artifact：`8800210265`  
SHA-256：`49ebc0157537caa130e3f8db379dd1c7ff8aa5192c01cc7aa25ec31e2bb13aa9`

### 第二轮：已验收

- [x] 前端包身份、版本、private状态和仓库链接归一；
- [x] 删除产品入口中的上游Vben身份、公开测试账号和错误链接，保留MIT归属；
- [x] VS Code启动入口归一为`127.0.0.1:4373/index.html`；
- [x] 版本检查与升版工具覆盖前端`package.json`；
- [x] 根README、PLAN、文档目录、部署入口、验收标准、Runbook和参考资料入口同步当前架构；
- [x] 新增仓库身份、前端版本、IDE端口、TSConfig覆盖和Markdown个人主目录永久门禁；
- [x] MT5桥接路径改为Windows `APPDATA`派生、非Windows相对路径回退和环境变量覆盖；
- [x] 新增三种MT5路径行为的Runtime单元测试。

验证HEAD：`4f945739afcff191f41bc4defc33c4661d88f327`

- Platform CI `30651097925`
- Directory `30651097916`
- Version `30651097942`
- Secret `30651098013`
- User E2E `30651098012`
- Audit `30651097911`
- Visual `30651098098`
- Hedge E2E `30651097960`
- Provider Smoke `30651098331`

视觉Artifact：`8801486707`  
SHA-256：`5a578af19799e27714ef0045544be14430b8a32c74d147e7a9af1438fa484d2d`

### 第三轮：已验收

- [x] 精简`platform-web/.vscode/settings.json`为当前Platform Web维护需求；
- [x] 保留pnpm、TypeScript SDK、Volar、ESLint、Stylelint、Prettier、Vue i18n和有效搜索排除；
- [x] 删除Vetur、旧Volar TS插件标志、MicroPython、Nuxt、Yarn/Bower及失效托管文件嵌套；
- [x] 删除旧`vue.vscode-typescript-vue-plugin`推荐，保留`vue.volar`；
- [x] 新增共享编辑器配置永久架构测试。

验证HEAD：`2afbecddfa819a0eba60ada4c5f944ae07ddd922`

- Platform CI `30651892610`
- Directory `30651893427`
- Version `30651893075`
- Secret `30651893154`
- User E2E `30651893615`
- Audit `30651893407`
- Visual `30651892973`
- Hedge E2E `30651893689`
- Provider Smoke `30651893126`

视觉Artifact：`8801803176`  
SHA-256：`126856ca9aa52fbdcc5f6a61a5fee6c930073866e385aa1df0b1b8a539ad3a96`

### 剩余GitHub候选：当前不可安全执行

- [ ] Platform API应用层仍显示历史版本`0.6.0`；
- [ ] Execution Runtime应用层仍显示历史版本`0.5.0`；
- [ ] 两个应用文件体积较大，当前只允许安全局部补丁，不做整文件人工重写；
- [ ] `platform-web/apps/test-server`仍进入pnpm workspace和锁文件，必须使用锁文件感知切口；
- [ ] 未完成静态引用、路由、构建和锁文件证据前，不批量删除疑似未使用源码。

当前GitHub连接下，没有其他同时满足“高置信度、无需锁文件、无需局部补丁、不触碰产品合同”的候选。J2按停止条件收口。

## 后续顺序

获得安全局部补丁或锁文件感知能力 → 处理剩余GitHub候选；否则转入延期的J1外部验收、Windows/TLS/真实Venue与正式会计对账验收 → 所有者批准。

## Protected invariants

Browser Session/API-Key、CSRF/Origin、角色与会员隔离、Decimal、Financial Fact、PnL/NAV、正式会计、对账、不可变迁移、Kill Switch、双人审批、Live Write、幂等性、Market/FOK/PostOnly/TP-SL、Result Unknown、EOD/LKG、数据状态、TLS和Runtime边界均不得改变。
