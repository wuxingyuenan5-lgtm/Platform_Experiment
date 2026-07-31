# Platform前端热点低风险治理计划

状态：**F1 TradingViewWidget已完成；F2静态市场快照数据边界审计中**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 目标

降低高频前端页面的上下文和职责密度，但不重写页面、不改变视觉、不建立微前端或第二套全局状态。

每个切口必须同时满足：

1. 独立且可命名的视觉或本地数据职责；
2. 输入输出合同清晰；
3. 不依赖页面级路由、权限、请求或跨域状态；
4. 提取后能够减少目标页面认知范围，而不是仅增加文件数量；
5. 可由结构测试、Type Check、Build、Browser E2E和56页视觉基线证明等价。

## 冻结合同

- 页面路由、分类Tab、滚动恢复和工具目录加载逻辑不变；
- Research模块、Widget配置、数据来源和状态语义不变；
- Props、错误文案、DOM class、最小高度和外部脚本配置不变；
- 外部图表失败不能影响其他模块；
- 不改变任何Platform API、权限、Provider或交易边界；
- 不同时迁移多个图表组件、共享数学和大范围CSS。

## F0 Research E4后剩余热点审计：完成

`platform-web/src/views/hedgeBoard/index.vue`仍同时包含：

- 页面路由与分类编排；
- TradingView外部脚本生命周期；
- 通用图表范围选择器与SVG数学；
- 多个本地图表组件；
- 大型静态市场详情表；
- LocalChartWidget分发；
- 页面样式。

首轮审计结论：

- `DualAxisChart`、`TreasuryFlowChart`、`GroupedBarChart`及ETF图表共享范围选择器、SVG数学和页面级数据，不适合作为首个切口；
- `TradingViewWidget`只接收一个`WidgetConfig`，独立拥有外部脚本加载、尺寸观察、可见性观察、布局修复、失败降级和清理，是首个明确低风险切口。

## F1 TradingViewWidget独立职责：完成

### 已完成实现

- [x] 新增`platform-web/src/views/hedgeBoard/components/TradingViewWidget.ts`；
- [x] 从`hedgeBoard/index.vue`机械迁移原组件定义；
- [x] 主页面显式import并继续把同一组件引用传给`HedgeResearchModule`；
- [x] 移除主页面不再使用的`onBeforeUnmount` import；
- [x] 保留`WidgetConfig`、脚本地址、错误文案、DOM class和最小高度；
- [x] 保留ResizeObserver、IntersectionObserver、双requestAnimationFrame、四组布局修复定时器、三次修复上限、0.2可见阈值和卸载清理；
- [x] 新增永久架构测试，禁止新组件依赖路由、API、权限、市场数据、持久化或网络请求；
- [x] 将被本切口触达的Vue事件名从等价的`update:modelValue`规范化为`update:model-value`，满足no-new-debt规则；
- [x] 删除全部一次性写权限Workflow和迁移脚本。

### F1完整矩阵证据

验证HEAD：`96919d31fecbfb0e99cbbbac5fff735436ecab11`

- Platform CI：`30631021600`
- Platform Directory Invariants：`30631021619`
- Version Consistency：`30631021640`
- Secret Scan：`30631021603`
- User System Browser E2E：`30631021630`
- Platform 0.9.2 Baseline Audit：`30631021938`
- Platform Visual Baseline：`30631021669`
- Hedge Board Browser E2E：`30631021604`
- Research Provider Smoke：`30631021624`

视觉Artifact：`8793413949`  
SHA-256：`3fbc0b599690b97bdc59fcb9f318d74185fd5599823224cd7ffe8a24bae46da2`

## F1后复核

F1后主页面仍保留共享图表范围选择器、SVG数学、LocalChartWidget分发和大型静态快照表。

当前判断：

- 共享图表数学仍被多种不同图表组件共同调用，提取需要同步迁移多个组件和较大测试面，暂不进入；
- `LOCAL_MARKET_DETAIL_TABLES`及其`SnapshotTableRow`/`SnapshotTableGroup`类型是纯静态本地目录，不读取页面状态、路由、API、权限或DOM；
- 该静态块体量大，显著增加主页面阅读成本，并与现有`nativeData/`目录职责一致；
- 因此F2优先审计将静态市场快照表迁入独立`nativeData`模块，而不是继续拆图表组件。

## F2候选：静态市场快照数据Owner

### 允许范围

- 迁移`SnapshotTableRow`、`SnapshotTableGroup`和`LOCAL_MARKET_DETAIL_TABLES`到独立本地数据模块；
- 主页面只保留类型/常量import与既有LocalChartWidget使用方式；
- 保持每个字段、字符串、数组顺序、分组、symbol和spark数据逐字节等价；
- 新增静态数据Hash与Owner架构测试。

### 禁止范围

- 不合并或改写`marketDetailCatalog.ts`，两者分别承担可选市场目录与本地快照展示数据；
- 不修改任何快照值、标签、颜色、图表逻辑或UI；
- 不同时迁移LocalChartWidget、SVG数学或CSS；
- 不把静态数据接入API、Provider、全局Store或持久化。

F2只有在数据块边界和Hash可被精确冻结后才实施；否则停止该切口。

Draft PR必须保持Open、Draft、Unmerged；不得修改或合并`main`。
