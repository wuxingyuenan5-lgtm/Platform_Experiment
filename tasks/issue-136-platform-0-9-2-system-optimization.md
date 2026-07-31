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
- [x] 保持Platform Web / Platform API模块化单体 / Execution Runtime三边界；
- [x] Draft PR保持Open、Draft、Unmerged，`main`未修改。

## Portfolio P3证据

验证HEAD：`e41267cc70b5e852b3069d71a6a8d7b1092127ad`  
视觉Artifact：`8792572937`  
SHA-256：`5109b685a9b0e2b9926c364f6fbadf95aae5982a6a5d77b073e5c32a6f33a7de`

## Frontend F1 TradingViewWidget：完成

### 已实施

- [x] 新增`platform-web/src/views/hedgeBoard/components/TradingViewWidget.ts`；
- [x] 从`hedgeBoard/index.vue`机械迁移原内联组件；
- [x] 保留Widget配置、外部脚本、错误文案、DOM class和最小高度；
- [x] 保留ResizeObserver、IntersectionObserver、双rAF、四组修复定时器、三次修复上限、0.2阈值和卸载清理；
- [x] 主页面继续通过原`HedgeResearchModule`合同传入同一组件；
- [x] 永久架构测试禁止新Owner依赖路由、API、权限、市场数据、持久化或网络请求；
- [x] 将被触达的Vue事件规范化为`update:model-value`以满足no-new-debt；
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

## 当前门禁：Frontend F2静态市场快照数据审计

当前主页面内的`LOCAL_MARKET_DETAIL_TABLES`及其两项类型是纯静态本地数据，体量大且与页面编排无关，符合`nativeData/`职责。实施前必须先建立精确内容Hash和Owner测试。

允许：

- 将类型和静态表迁入一个独立`nativeData`模块；
- 主页面保留显式import和原LocalChartWidget使用方式；
- 保持每个值、字符串、分组、顺序和spark数组等价。

禁止：

- 不修改快照内容或UI；
- 不合并现有`marketDetailCatalog.ts`；
- 不同时迁移LocalChartWidget、图表数学或CSS；
- 不接入API、Provider、Store或持久化。

若无法建立精确Hash与机械迁移边界，则停止F2，转入下一业务域只读审计。

## 后续顺序

前端热点治理 → 高风险域只读审计 → Trading/Risk/Accounting/Reconciliation/Runtime逐门禁优化 → 旧Go/MySQL部署定性与仓库减负 → 真实环境验收。

## Protected invariants

Browser Session/API-Key、CSRF/Origin、角色与会员隔离、Decimal、Financial Fact、PnL/NAV、正式会计、对账、不可变迁移、Kill Switch、双人审批、Live Write、幂等性、Market/FOK/PostOnly/TP-SL、Result Unknown、EOD/LKG、数据状态、TLS和Runtime边界均不得改变。

每一阶段必须具备明确文件范围、Golden、完整验收、回滚点和停止条件；不得在失败门禁上叠加改动。
