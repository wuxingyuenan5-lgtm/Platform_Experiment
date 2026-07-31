# Platform前端热点低风险治理计划

状态：**F1 TradingViewWidget独立职责准备实施**  
关联Issue：#136  
关联Draft PR：#139  
活动分支：`refactor/issue-136-platform-0-9-2-system-optimization`  
开发与验收版本：Platform `0.9.2`

## 目标

降低高频前端页面的上下文和职责密度，但不重写页面、不改变视觉、不建立微前端或第二套全局状态。

每个切口必须同时满足：

1. 独立且可命名的视觉职责；
2. 输入输出合同清晰；
3. 不依赖页面级路由、权限、请求或跨域状态；
4. 提取后能够减少目标页面认知范围，而不是仅增加文件数量；
5. 可由结构测试、Type Check、Build、Browser E2E和56页视觉基线证明等价。

## 冻结合同

- 页面路由、分类Tab、滚动恢复和工具目录加载逻辑不变；
- Research模块、Widget配置、数据来源和状态语义不变；
- Props、错误文案、DOM class、最小高度和外部脚本配置不变；
- ResizeObserver、IntersectionObserver、双requestAnimationFrame、布局修复定时器和卸载清理顺序不变；
- 外部图表失败不能影响其他模块；
- 不改变任何Platform API、权限、Provider或交易边界；
- 不迁移共享图表数学、静态市场数据或多个组件。

## F0 Research E4后剩余热点审计：完成

`platform-web/src/views/hedgeBoard/index.vue`仍同时包含：

- 页面路由与分类编排；
- TradingView外部脚本生命周期；
- 通用图表范围选择器与SVG数学；
- 多个本地图表组件；
- 大型静态市场详情表；
- LocalChartWidget分发；
- 页面样式。

审计结论：

- `DualAxisChart`、`TreasuryFlowChart`、`GroupedBarChart`及ETF图表共享范围选择器、SVG数学和页面级数据，暂不满足单一低风险提取；
- 静态市场详情表与LocalChartWidget仍与本地数据分发强耦合，暂不迁移；
- `TradingViewWidget`只接收一个`WidgetConfig`，独立拥有外部脚本加载、尺寸观察、可见性观察、布局修复、失败降级和清理，未读取路由、市场数据、API、权限或页面状态；
- 因此`TradingViewWidget`是当前唯一明确、低耦合且能实际减少主页面上下文的切口。

## F1 TradingViewWidget独立职责

### 允许改动

- 新增`platform-web/src/views/hedgeBoard/components/TradingViewWidget.ts`；
- 从`hedgeBoard/index.vue`机械迁移现有组件定义；
- 主页面改为显式import并继续把组件引用传给`HedgeResearchModule`；
- 移除仅由该内联组件使用的Vue生命周期import；
- 新增永久架构测试；
- 验证后删除一次性迁移工具。

### 禁止改动

- 不修改Widget配置、脚本地址、错误文案、class或高度；
- 不改变observer、timer、重试次数、阈值或渲染时序；
- 不修改HedgeResearchModule合同；
- 不同时拆分其他图表组件或共享数学；
- 不调整任何CSS或页面布局。

### Required verification

- 静态架构测试与提取前后合同断言；
- Platform Web Lint、no-new-debt、策略/用户Type Check和生产Build；
- Platform API与Execution Runtime完整检查；
- Research Provider Smoke；
- User System与Hedge Board Browser E2E；
- Secret、Version、Directory和Baseline Audit；
- 56页四档视觉基线。

### Stop conditions

出现以下任一情况立即回滚：

- 外部图表加载或失败降级语义改变；
- DOM class、最小高度、脚本配置或观察器时序改变；
- 主页面、Research模块或页面视觉发生回归；
- 新组件获得路由、API、权限、市场数据或持久化依赖；
- 任一完整门禁失败且不能证明为非本切口原因。

## F1之后

F1通过后重新测量`hedgeBoard/index.vue`，再只读判断共享图表范围选择器是否值得形成内部组件/Composable。若必须同时迁移多个图表或大范围CSS，则停止前端热点代码修改，进入下一业务域审计。

Draft PR必须保持Open、Draft、Unmerged；不得修改或合并`main`。
