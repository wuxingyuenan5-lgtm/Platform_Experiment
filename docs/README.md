# 文档入口

这个目录只放“总入口”和“权威口径”。更细的历史文档暂时仍在 `admin-risk/docs`，后续按主题逐步收敛，不一次性大搬家。

## 当前最有用的文档位置

| 主题 | 位置 | 说明 |
|---|---|---|
| 产品模块需求 | `admin-risk/docs/modules` | 首页、策略、策略管理、风控、交易平台、新闻日历等 |
| 单策略文档 | `admin-risk/docs/strategies` | 资费套利、跨所价差、海内外价差、抄底、短线交易员 |
| 架构文档 | `admin-risk/docs/architecture` | 前后端边界、领域模型、Runtime、可靠执行 |
| 交易工具数据源 | `admin-risk/docs/trading-tools-bookmarks-review.md` | 仍被前端脚本读取，暂不移动 |
| 旧交接与归档 | `admin-risk/docs/archive` | 只查历史，不作为最新口径 |

## 根级权威文档

| 文件 | 用途 |
|---|---|
| `product/PRD.md` | 产品总口径，后续从模块文档抽取 |
| `product/ACCEPTANCE_CRITERIA.md` | 全局验收标准 |
| `technical/ARCHITECTURE.md` | 当前系统结构 |
| `technical/API_SPEC.md` | 后端 API 入口 |
| `technical/DATA_MODEL.md` | 数据库和领域模型入口 |
| `technical/DEPLOYMENT.md` | 本地启动、部署、回滚入口 |
| `technical/SECURITY.md` | 密钥、交易、权限、风控约束 |
| `operations/RUNBOOK.md` | 本地运行和排障 |
| `operations/WORKSPACE_HYGIENE.md` | Codex 降噪、忽略规则、清理边界 |

## 文档治理

- 根级文档负责“导航、最新口径、验收标准”。
- 详细长文档保留原路径，等内容稳定后再抽取。
- 不把同一业务规则复制到多个文件。
- 如果某个页面改动影响用户体验，更新验收标准。
- 如果某个改动影响 API、数据库、执行链路，更新技术文档。
- 如果新增大型依赖、构建产物、外部参考仓库或导出物，先判断是否应该进入 `.ignore`。
