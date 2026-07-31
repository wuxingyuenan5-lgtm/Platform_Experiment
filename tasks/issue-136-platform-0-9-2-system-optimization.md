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

## 已完成主门禁

- [x] Phase A–D：基线、全仓审计、上下文治理、完整门禁、56页视觉基线和目录迁移；
- [x] Research E1–E5.1：Provider、状态、主看板低风险组件和A股本地观察列表；
- [x] Identity I1/I2.1：管理员与Session响应Presenter；
- [x] Portfolio P1–P3：纯估值、后端停止决策、共享Decimal与完整账户估值口径；
- [x] Frontend F1/F2：TradingView生命周期与静态市场快照数据Owner；
- [x] 前端热点治理按停止条件正式收口；
- [x] High-risk H0：Trading/Risk/Accounting/Reconciliation/Runtime责任盘点；
- [x] High-risk H1：EOD Reconciliation专用路由Owner；
- [x] 保持Platform Web / Platform API模块化单体 / Execution Runtime三边界；
- [x] Draft PR保持Open、Draft、Unmerged，`main`未修改。

## Portfolio P3证据

验证HEAD：`e41267cc70b5e852b3069d71a6a8d7b1092127ad`  
视觉Artifact：`8792572937`  
SHA-256：`5109b685a9b0e2b9926c364f6fbadf95aae5982a6a5d77b073e5c32a6f33a7de`

## Frontend F1证据

验证HEAD：`96919d31fecbfb0e99cbbbac5fff735436ecab11`  
视觉Artifact：`8793413949`  
SHA-256：`3fbc0b599690b97bdc59fcb9f318d74185fd5599823224cd7ffe8a24bae46da2`

## Frontend F2证据

- [x] `nativeData/marketSnapshotTables.ts`成为唯一静态快照Owner；
- [x] 来源SHA-256：`20245f2606e15add5e97387c238532697c938677865c9d620178bbc9522b788a`；
- [x] 规范化语义SHA-256：`580983d83781cb7f0731dd39837d75b16eaf24be18751367432aa605fa0acc92`；
- [x] LocalChartWidget、SVG数学、CSS、Provider、API、Store和持久化未修改。

验证HEAD：`56f53a67d8b85e2c6988da62044a2940b8eedc7e`  
视觉Artifact：`8796528988`  
SHA-256：`5189b39b5778ce20ae425b0879006dc7c03694f48acce57a6aa5ba77efbdc2be`

## High-risk H0责任盘点：完成

- [x] Trading订单意图、提交编排、Result Unknown和Cross-spread执行Owner已内聚，保留现状；
- [x] Risk限额、Kill Switch、双人审批和Live Write默认关闭边界已内聚，保留现状；
- [x] Financial Fact、Formal Projection、Position Math和正式会计Owner已内聚，保留现状；
- [x] Execution Runtime继续独占Venue SDK、外部副作用和Runtime Journal；
- [x] Reconciliation确认存在Facade与FastAPI路由混合的显式结构债务。

## High-risk H1 EOD路由Owner：完成

### 已实施

- [x] 新增`platform-api/app/eod_reconciliation_routes.py`；
- [x] 仅迁移四个端点、APIRouter、response models、tags和Query别名；
- [x] `main.py`从专用路由模块导入router；
- [x] Facade继续拥有兼容导出、每次调用依赖装配和409/404/422错误映射；
- [x] Service、Policy、Repository、Schemas、Financial Fact、Venue Reconciliation、DDL和Decimal未修改；
- [x] 保持现有Monkeypatch端口、幂等性、Review不可变性、`failed + blocked`和Scale Gate Fail Closed；
- [x] Ownership和永久架构测试已更新；
- [x] 全部一次性写权限Workflow和迁移脚本已删除。

### H1完整矩阵

验证HEAD：`5f992691c35921c0647cd8e7f800fca48a547359`

- [x] Platform CI：`30640101027`；
- [x] Platform Directory Invariants：`30640101717`；
- [x] Version Consistency：`30640100742`；
- [x] Secret Scan：`30640100821`；
- [x] User System Browser E2E：`30640100255`；
- [x] Platform 0.9.2 Baseline Audit：`30640100980`；
- [x] Platform Visual Baseline：`30640101256`；
- [x] Hedge Board Browser E2E：`30640101724`；
- [x] Research Provider Smoke：`30640100623`。

视觉Artifact：`8797146922`  
SHA-256：`f722456de6afce3068239a2de51ca58895133aa6cbd1eef6f0af9afc1ab00453`

## 当前门禁：H2 Venue路由只读复核

本阶段只读取和建模，不修改代码。必须完成：

1. 冻结五个Venue端点的路径、方法、response model、Query和错误状态；
2. 盘点Facade全部兼容导出和直接跨域消费者；
3. 核验现有Monkeypatch、API、Service、Policy、Repository和Runtime Client Golden；
4. 判断专用路由模块是否能只在运行时调用Facade而不改变兼容端口；
5. 判断拆分收益是否足以覆盖更广的消费者面。

若需要修改Service、Repository、Policy、Runtime Client、Financial Fact、HTTP错误映射或兼容Delegate，则停止Venue路由抽取并记录保留决定。

## 后续顺序

H2 Venue只读复核 → 其余高风险域按证据决定停止或单一切口 → 旧Go/MySQL部署定性与仓库减负 → Windows/TLS/真实Venue与正式会计对账验收。

## Protected invariants

Browser Session/API-Key、CSRF/Origin、角色与会员隔离、Decimal、Financial Fact、PnL/NAV、正式会计、对账、不可变迁移、Kill Switch、双人审批、Live Write、幂等性、Market/FOK/PostOnly/TP-SL、Result Unknown、EOD/LKG、数据状态、TLS和Runtime边界均不得改变。

每一阶段必须具备明确文件范围、Golden、完整验收、回滚点和停止条件；不得在失败门禁上叠加改动。
