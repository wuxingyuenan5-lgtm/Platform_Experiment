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

## 已完成门禁

- [x] Phase A–D：基线、全仓审计、上下文治理、完整门禁、56页视觉基线和目录迁移；
- [x] Research E1–E5.1：Provider、状态、主看板低风险组件和A股本地观察列表；
- [x] Identity I1/I2.1：管理员与Session响应Presenter；
- [x] Portfolio P1–P3：纯估值、后端停止决策、共享Decimal与完整账户估值口径；
- [x] Frontend F1：TradingView外部Widget生命周期Owner；
- [x] Frontend F2：静态市场快照数据Owner与双Hash永久守卫；
- [x] 前端热点治理按停止条件正式收口；
- [x] 保持Platform Web / Platform API模块化单体 / Execution Runtime三边界；
- [x] Draft PR保持Open、Draft、Unmerged，`main`未修改。

## Portfolio P3证据

验证HEAD：`e41267cc70b5e852b3069d71a6a8d7b1092127ad`  
视觉Artifact：`8792572937`  
SHA-256：`5109b685a9b0e2b9926c364f6fbadf95aae5982a6a5d77b073e5c32a6f33a7de`

## Frontend F1 TradingViewWidget：完成

- [x] 新增`platform-web/src/views/hedgeBoard/components/TradingViewWidget.ts`；
- [x] 机械迁移外部脚本生命周期、观察器、布局修复、失败降级与清理；
- [x] 保留Widget配置、外部脚本、错误文案、DOM class、最小高度和时序；
- [x] 主页面继续通过原`HedgeResearchModule`合同传入同一组件；
- [x] 永久架构测试禁止新Owner依赖路由、API、权限、市场数据、持久化或网络请求；
- [x] 被触达的Vue事件规范化为`update:model-value`并通过no-new-debt；
- [x] 删除全部一次性写权限Workflow和迁移脚本。

### F1完整矩阵

验证HEAD：`96919d31fecbfb0e99cbbbac5fff735436ecab11`

- [x] Platform CI：`30631021600`；
- [x] Platform Directory Invariants：`30631021619`；
- [x] Version Consistency：`30631021640`；
- [x] Secret Scan：`30631021603`；
- [x] User System Browser E2E：`30631021630`；
- [x] Platform 0.9.2 Baseline Audit：`30631021938`；
- [x] Platform Visual Baseline：`30631021669`；
- [x] Hedge Board Browser E2E：`30631021604`；
- [x] Research Provider Smoke：`30631021624`。

视觉Artifact：`8793413949`  
SHA-256：`3fbc0b599690b97bdc59fcb9f318d74185fd5599823224cd7ffe8a24bae46da2`

## Frontend F2静态市场快照数据Owner：完成

### 已实施

- [x] 新增`platform-web/src/views/hedgeBoard/nativeData/marketSnapshotTables.ts`；
- [x] 机械迁移`SnapshotTableRow`、`SnapshotTableGroup`与`LOCAL_MARKET_DETAIL_TABLES`；
- [x] 主页面只保留实际使用的常量与类型import；
- [x] 保持字段、字符串、symbol、分组顺序与spark数组内容不变；
- [x] 保留既有静态资产合同，不修改LocalChartWidget、图表数学、CSS或UI；
- [x] 新模块不依赖API、Provider、Store、路由、权限、DOM或持久化；
- [x] 原始来源SHA-256：`20245f2606e15add5e97387c238532697c938677865c9d620178bbc9522b788a`；
- [x] 规范化语义SHA-256：`580983d83781cb7f0731dd39837d75b16eaf24be18751367432aa605fa0acc92`；
- [x] 永久架构测试同时冻结来源声明、语义内容、唯一Owner和禁止依赖；
- [x] 删除全部一次性写权限Workflow和迁移脚本。

### F2完整矩阵

验证HEAD：`56f53a67d8b85e2c6988da62044a2940b8eedc7e`

- [x] Platform CI：`30638593310`；
- [x] Platform Directory Invariants：`30638589820`；
- [x] Version Consistency：`30638591763`；
- [x] Secret Scan：`30638592137`；
- [x] User System Browser E2E：`30638591489`；
- [x] Platform 0.9.2 Baseline Audit：`30638591535`；
- [x] Platform Visual Baseline：`30638589936`；
- [x] Hedge Board Browser E2E：`30638591976`；
- [x] Research Provider Smoke：`30638589992`。

视觉Artifact：`8796528988`  
SHA-256：`5189b39b5778ce20ae425b0879006dc7c03694f48acce57a6aa5ba77efbdc2be`

## 前端热点停止决定

- [x] 共享范围选择器和SVG数学跨多类图表实现；
- [x] LocalChartWidget同时承担页面级组件分发与数据装配；
- [x] 相关DOM、测试和CSS无法形成单一低风险迁移边界；
- [x] 当前没有独立消费者、重复实现或可量化收益支撑新增抽象；
- [x] 决定停止继续拆分`hedgeBoard/index.vue`，不新增Composable、图表框架、微前端或第二套状态系统。

## 当前门禁：高风险业务域只读审计

本阶段只读取和建模，不修改代码。审计范围：

1. Trading订单意图、提交编排、生命周期、幂等性与Result Unknown；
2. Risk限额、Kill Switch、双人审批与Live Write门禁；
3. Financial Fact、正式投影与Accounting Owner；
4. Venue/EOD Reconciliation、Last Known Good与状态分类；
5. Platform API与Execution Runtime合同及Venue/Broker适配边界；
6. 现有Golden、失败关闭语义、重复实现和测试空白。

只有在找到一个具备明确Owner、可冻结合同、真实重复或维护收益、独立回滚点的切口后，才允许提出下一项代码变更。若审计结果显示现有边界已内聚，则记录停止决定并转入下一域。

## 后续顺序

高风险域只读审计 → Trading/Risk/Accounting/Reconciliation/Runtime逐门禁优化 → 旧Go/MySQL部署定性与仓库减负 → Windows/TLS/真实Venue与正式会计对账验收。

## Protected invariants

Browser Session/API-Key、CSRF/Origin、角色与会员隔离、Decimal、Financial Fact、PnL/NAV、正式会计、对账、不可变迁移、Kill Switch、双人审批、Live Write、幂等性、Market/FOK/PostOnly/TP-SL、Result Unknown、EOD/LKG、数据状态、TLS和Runtime边界均不得改变。

每一阶段必须具备明确文件范围、Golden、完整验收、回滚点和停止条件；不得在失败门禁上叠加改动。
