# 文档入口

本目录保存全平台权威工程文档。当前状态、模块Owner、合同、迁移纪律和运维规则必须优先从根级`docs/`读取；`platform-web/docs/`主要保留产品模块细节、前端设计历史和归档材料，不应覆盖根级最新口径。

## 首要入口

| 主题 | 权威位置 |
|---|---|
| 当前工程状态 | `codex/current-state.md` |
| 按任务选择上下文 | `codex/context-map.md` |
| 系统结构 | `architecture/SYSTEM_MAP.md` |
| 模块唯一Owner | `architecture/OWNERSHIP.md` |
| 0.9.2系统优化总方案 | `architecture/PLATFORM_0_9_2_SYSTEM_OPTIMIZATION_MASTER_PLAN.md` |
| 数据库、DDL Owner与迁移纪律 | `database/README.md` |
| Git工作流 | `engineering/GIT_WORKFLOW.md` |
| 运维和真实验收 | `operations/` |

`codex/CURRENT_CONTEXT.md`只保留旧链接兼容，不是当前工程事实来源。

## 产品与技术文档

| 主题 | 位置 | 说明 |
|---|---|---|
| 产品总口径 | `product/PRD.md` | 跨模块产品目标与范围 |
| 全局验收标准 | `product/ACCEPTANCE_CRITERIA.md` | 用户流程、视觉和基础运行要求 |
| 当前技术架构 | `technical/ARCHITECTURE.md` | 技术分层与服务边界 |
| API合同入口 | `technical/API_SPEC.md` | Platform API与Runtime接口语义 |
| 数据模型 | `technical/DATA_MODEL.md` | 数据库与领域模型入口 |
| 部署入口 | `technical/DEPLOYMENT.md` | 本地地址与部署引用 |
| 安全边界 | `technical/SECURITY.md` | 凭证、权限、交易与风控约束 |
| 运维手册 | `operations/RUNBOOK.md` | 本地运行和排障 |
| 仓库卫生 | `operations/WORKSPACE_HYGIENE.md` | 搜索降噪、生成物和清理边界 |

## 前端详细文档

| 主题 | 位置 | 说明 |
|---|---|---|
| 产品模块需求 | `../platform-web/docs/modules/` | 首页、策略、风控、交易、新闻日历等详细材料 |
| 单策略文档 | `../platform-web/docs/strategies/` | 资费套利、跨所价差、海内外价差等 |
| 前端架构与设计历史 | `../platform-web/docs/architecture/` | 只在根级架构文档未覆盖时作为补充 |
| 交易工具数据源 | `../platform-web/docs/trading-tools-bookmarks-review.md` | 仍由前端同步脚本读取，暂不移动 |
| 历史交接与归档 | `../platform-web/docs/archive/` | 只查历史，不作为最新口径 |

## 文档治理

- 同一工程事实只能有一个权威来源；
- 当前状态只更新`codex/current-state.md`和GitHub Issue #136；
- 模块Owner变化必须同步`architecture/OWNERSHIP.md`；
- API、数据库、Runtime合同或执行链路变化必须更新对应技术文档与可执行测试；
- 历史实施过程进入Issue、任务包、PR或归档，不复制到稳定架构说明；
- 新增大型依赖、构建产物、外部参考仓库或导出物前，先定义`.gitignore`、`.ignore`和清理边界。
