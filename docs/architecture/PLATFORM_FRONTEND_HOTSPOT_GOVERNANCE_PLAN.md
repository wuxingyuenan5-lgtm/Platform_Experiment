# Platform前端热点低风险治理计划

状态：**F1与F2均已完成；前端热点代码治理正式收口**  
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

`platform-web/src/views/hedgeBoard/index.vue`曾同时包含页面编排、TradingView生命周期、共享图表数学、本地图表组件、大型静态快照表、LocalChartWidget分发与页面样式。

审计后仅批准两个有独立职责、可机械验证且能显著降低上下文成本的切口：

- F1：TradingView外部Widget生命周期；
- F2：纯静态市场快照数据Owner。

共享图表数学、LocalChartWidget和CSS从未被批准为同一批次迁移对象。

## F1 TradingViewWidget独立职责：完成

### 已完成实现

- [x] 新增`platform-web/src/views/hedgeBoard/components/TradingViewWidget.ts`；
- [x] 从`hedgeBoard/index.vue`机械迁移原组件定义；
- [x] 主页面继续通过原`HedgeResearchModule`合同传入同一组件；
- [x] 保留Widget配置、脚本地址、错误文案、DOM class和最小高度；
- [x] 保留ResizeObserver、IntersectionObserver、双requestAnimationFrame、四组布局修复定时器、三次修复上限、0.2可见阈值和卸载清理；
- [x] 永久架构测试禁止新Owner依赖路由、API、权限、市场数据、持久化或网络请求；
- [x] 被触达的Vue事件规范化为`update:model-value`并通过no-new-debt；
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

## F2静态市场快照数据Owner：完成

### 已完成实现

- [x] 新增`platform-web/src/views/hedgeBoard/nativeData/marketSnapshotTables.ts`；
- [x] 机械迁移`SnapshotTableRow`、`SnapshotTableGroup`和`LOCAL_MARKET_DETAIL_TABLES`；
- [x] 主页面只保留`LOCAL_MARKET_DETAIL_TABLES`与`SnapshotTableGroup`显式import；
- [x] 保持全部字段、字符串、symbol、分组顺序和spark数组内容不变；
- [x] 保留既有`void [LOCAL_MARKET_DETAIL_TABLES, GroupedBarChart, SnapshotDetailTable]`静态资产合同；
- [x] 未修改LocalChartWidget、SVG数学、CSS、Provider、API、Store或持久化；
- [x] 永久架构测试确认新模块无依赖、主页面不再拥有内联静态表；
- [x] 原始提取来源SHA-256固定为`20245f2606e15add5e97387c238532697c938677865c9d620178bbc9522b788a`；
- [x] 忽略字符串外排版空白后的规范化语义SHA-256固定为`580983d83781cb7f0731dd39837d75b16eaf24be18751367432aa605fa0acc92`；
- [x] 删除全部一次性写权限Workflow和迁移脚本。

双Hash分别承担来源证据和长期语义守卫，避免Prettier换行或引号格式造成伪失败，同时继续冻结字段、值、顺序和数组内容。

### F2完整矩阵证据

验证HEAD：`56f53a67d8b85e2c6988da62044a2940b8eedc7e`

- Platform CI：`30638593310`
- Platform Directory Invariants：`30638589820`
- Version Consistency：`30638591763`
- Secret Scan：`30638592137`
- User System Browser E2E：`30638591489`
- Platform 0.9.2 Baseline Audit：`30638591535`
- Platform Visual Baseline：`30638589936`
- Hedge Board Browser E2E：`30638591976`
- Research Provider Smoke：`30638589992`

视觉Artifact：`8796528988`  
SHA-256：`5189b39b5778ce20ae425b0879006dc7c03694f48acce57a6aa5ba77efbdc2be`

## F2后停止结论

F2后主页面剩余职责已形成相对内聚的页面级图表与编排边界：

- 共享范围选择器和SVG数学被多种不同图表共同调用；
- LocalChartWidget同时承担组件分发与页面级数据装配；
- 相关样式与DOM结构跨多个本地图表组件；
- 继续提取必须同步迁移多个组件、数据集、测试与CSS，无法保持“一次一个低风险职责”的原则；
- 当前没有重复实现、独立消费者或可量化维护收益足以抵消新增跳转和抽象成本。

因此停止继续拆分`hedgeBoard/index.vue`，不新增Composable、图表框架、微前端或第二套状态系统。后续只允许基于明确产品需求或真实重复证据重新开启专项审计。

## 下一门禁

进入高风险业务域只读审计。先梳理Trading、Risk、Accounting、Reconciliation与Execution Runtime的现有Owner、合同、重复实现和真实测试覆盖；在形成Golden、失败关闭语义和明确收益前，不进行代码迁移。

Draft PR必须保持Open、Draft、Unmerged；不得修改或合并`main`。
