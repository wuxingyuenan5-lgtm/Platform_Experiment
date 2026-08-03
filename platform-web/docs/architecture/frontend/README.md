# 前端架构文档入口

状态：`active`

## 阅读顺序

前端页面、组件或布局任务按以下顺序读取：

1. `frontend-overview.md`：前端总体分层和业务边界。
2. `responsive-layout-architecture.md`：页面壳层、视口、滚动、溢出、定位和组件重排的唯一架构主文档。
3. `routing-permission-and-environment.md`：路由、权限和运行环境。
4. `data-adapter-and-view-model.md`：数据适配与 View Model。
5. `../frontend-state-ownership.md`：状态归属。
6. `../shared-ui-governance.md`：共享组件与主题治理。
7. `../../design/platform-ui-guidelines.md`：视觉语言和 Design Token。
8. `../../quality/responsive-layout-acceptance.md`：跨视口测试矩阵、缺陷等级和发布门槛。

## 权威边界

| 内容 | 唯一主文档 |
|---|---|
| 前端总体分层 | `frontend-overview.md` |
| 响应式布局与页面壳层 | `responsive-layout-architecture.md` |
| 视口与缩放验收 | `../../quality/responsive-layout-acceptance.md` |
| 路由和权限 | `routing-permission-and-environment.md` |
| 数据适配与 View Model | `data-adapter-and-view-model.md` |
| 状态归属 | `../frontend-state-ownership.md` |
| 共享组件和主题边界 | `../shared-ui-governance.md` |
| 颜色、字体、间距和视觉组件 | `../../design/platform-ui-guidelines.md` |

## 响应式治理原则

- 不从随机业务页面开始打分辨率补丁。
- 先记录缺陷基线，再治理 Application Shell 和主要滚动所有权。
- Page Shell 负责页面标题、工具栏、摘要、主体和底部操作区。
- 业务组件声明自身最小宽高、重排和局部滚动规则。
- 后续实施按独立 Issue 分阶段推进，不一次性重写全平台。

历史决策参见：

- `../decisions/ADR-013-响应式布局体系与页面壳层治理.md`
