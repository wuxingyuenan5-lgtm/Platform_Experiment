# Platform Research与主看板低风险模块化计划

状态：**E5.1 A股观察列表本地持久化适配层已完成，等待清理HEAD完整矩阵收口**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 冻结合同

本计划只降低Research域与Hedge Board热点文件的职责密度，不改变Research API、权限、数据状态、缓存/LKG、页面视觉、用户操作或三大运行边界。

观察列表必须继续保持：空数组持久化、股票代码归一化、组内移动、账号API同步、CSRF、Dirty离线缓存、版本冲突重试、串行保存和`local/syncing/synced/offline`状态。

## 已完成

- E0–E3：Research审计、Provider领域Adapter、稳定Facade和宏观历史文件职责；
- E4.1：`WidgetErrorBoundary`；
- E4.2：`MetricStrip`；
- E4.3：`ReserveRanking`。

E4.3完整矩阵：

- Platform CI `30615078319`
- Directory `30615078247`
- User E2E `30615078255`
- Hedge E2E `30615078210`
- Visual `30615078193`
- Provider Smoke `30615078195`
- Secret `30615078238`
- Version `30615078222`
- Audit `30615078221`

视觉Artifact `8787106951`，SHA-256 `bdced6d20e0bbe1cd9a0f05e578de50edb3040770fb279b72af2944b6db82898`。

E4在此收口：其余内联组件依赖共享图表数学、页面级类型或市场数据，继续拆分不再属于单一低风险委托。

## E5.1 A股观察列表本地持久化

代码与永久合同已完成：

- 新增`aShareWatchlistLocalState.ts`；
- 迁移`WatchlistItem`、股票代码和条目归一化、去重、默认列表、本地缓存读写及Dirty标记；
- 保持原LocalStorage Key和空数组语义；
- Composable继续公开`normalizeStockCode`、`WatchlistItem`和`WatchlistSyncState`；
- 远端`rowVersion`、冲突Fetch-and-Retry、串行保存队列、Mutation Sequence及同步状态全部留在Composable；
- Dashboard、个股请求序列、上海日期、CSV、消息和复制逻辑保持原位；
- 永久布局门禁冻结本地适配层与远端同步边界；
- 人工复核发现并修复`WatchlistSyncState`公开类型遗漏，并新增永久断言；
- 一次性写权限Workflow与脚本已删除；
- 新模块严格Lint、基线债务比较、策略Type Check和布局合同通过。

待办：以本计划同步后的清理HEAD完成九项完整质量矩阵。

## E5后续

E5.1通过后只读评估Dashboard请求、个股快照请求和CSV/复制工具。远端观察列表一致性状态机不再拆分；没有明确上下文收益时停止E5代码修改。

每个切口必须通过Platform API、Research Provider、前端质量、两套浏览器、56张视觉基线及四项治理门禁。Draft PR始终保持Open、Draft、Unmerged；不得修改或合并`main`。
