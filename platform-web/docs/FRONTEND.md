# Frontend Architecture

Platform Web 是 Vue 模块化单体。它负责把产品能力组织为可理解、可恢复和可测试的工作台，不保存最终订单事实、不计算正式结算结果，也不独立决定风险或权限。

## 分层

```text
Router
  → Application / Module Shell
  → Page Shell and Orchestrator
  → Use Case / Composable
  → Domain Model / View Model
  → Repository / API Adapter
```

- Router 只管理导航、可恢复筛选和直接访问保护。
- Shell 统一页面高度、滚动、间距、标题、工具栏和错误边界。
- Page Orchestrator 组织用户任务，不承载跨页面全局规则。
- Composable 表达明确用例，不演变为无边界工具箱。
- API DTO 通过 Adapter 转换成稳定 View Model，不直接散入组件。
- Repository 连接 REST、WebSocket、Mock 或导入来源；切换来源不重写页面。

## 状态归属

| 状态                             | Owner                      |
| -------------------------------- | -------------------------- |
| 路由可恢复的主视角与筛选         | Router                     |
| 表单输入、展开和临时交互         | 页面本地状态               |
| 当前执行批次等模块协作状态       | 模块 Store                 |
| 用户、Capability、全局阻断和偏好 | 全局 Store                 |
| 订单、账户、持仓、PnL 等业务事实 | 服务端；前端只缓存查询结果 |

视口宽度不是业务状态。普通响应式布局使用 CSS 和统一壳层，不写入 Pinia 或业务 Store。

## 查询、命令与权限

- Query 可以缓存和重试，但必须保留时间、质量、加载、空数据与错误状态。
- Command 必须经过权限、参数、确认、幂等和提交状态，并返回可追踪业务 ID。
- `accepted`、`failed` 与 `result_unknown` 不得合并成一个“成功”外观。
- 菜单和按钮只改善体验；直接 URL 与后端 API 必须使用相同 Capability 语义。
- 前端不持有 Venue 凭据，不直接调用 Venue SDK，不用本地数组模拟真实命令完成。

## 模块边界

五个一级模块以 [产品总览](../../docs/product/PRD.md) 为准。宏观日历、新闻整理和理财信息分别归入对冲基金看板、金融 AI 分析及首页摘要入口，旧新闻日历路由只提供兼容跳转。策略内部包含交易平台与策略管理两个视角，共享稳定策略身份；页面路径不决定后端服务、数据库表或数据权威。

## 复杂度控制

- 优先复用现有组件、Composable 和 API Client。
- 没有跨多个页面的稳定需求，不新增全局 Store、框架或抽象层。
- 不做微前端，不按一级菜单复制一套基础设施。
- 大页面只在出现明确用户任务、测试边界或复用边界时拆分。
