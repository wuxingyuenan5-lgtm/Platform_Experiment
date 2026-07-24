# Project Start Here

本文件是人和 Agent 进入项目时的唯一总入口。目标是在 5 分钟内确定：当前系统是什么、这次任务属于哪里、只需要读取哪些文件。

## 1. 默认读取顺序

1. 根目录 `AGENTS.md`：永久安全规则和协作规则。
2. `docs/context/CURRENT_STATE.md`：当前基线、进行中工作和已知限制。
3. `docs/context/MODULE_INDEX.md`：按任务选择模块上下文。
4. 当前任务文件：`tasks/<task-id>.md`。
5. 仅在涉及跨模块边界时阅读 `docs/architecture/SYSTEM_MAP.md`。

禁止把“阅读整个仓库”作为默认启动方式。

## 2. 按任务选择上下文

| 任务类型 | 必读目录 | 通常不需要读取 |
|---|---|---|
| 前端页面或接口调用 | `admin-risk/` 对应模块、`admin-risk/docs/START-HERE.md` | Backend/Runtime 全量代码 |
| Platform API、权限、账务 | `platform-backend/` 对应模块、Backend 测试说明 | Frontend 模板、Runtime 适配器实现 |
| 下单、Gateway、外部交易所 | `execution-runtime/` 对应模块、Runtime 测试说明 | Platform UI 与正式账务实现 |
| 跨模块契约 | `docs/contracts/`、双方 DTO/Schema | 其他不相关领域 |
| 数据库迁移 | `docs/database/`、Schema Owner 模块 | 页面和外部 Gateway |
| 生产运营 | `docs/operations/`、Live Safety 测试 | 研究性页面和临时输出 |

## 3. 每个任务必须先写清楚

任务文件必须包含：

- 目标与非目标；
- 允许修改的目录；
- 禁止改变的业务语义；
- 验收命令；
- 风险和回滚方式；
- 当前进度与下一步。

模板见 `tasks/TASK_TEMPLATE.md`。

## 4. 文档分工

- `AGENTS.md`：长期有效的硬规则，保持短小。
- `docs/context/`：当前状态和协作入口，可随项目演进更新。
- `docs/architecture/`：稳定边界与系统结构，不记录临时过程。
- `docs/decisions/`：关键决策及其原因。
- `docs/technical/`：协议、领域模型和实现约束。
- `docs/operations/`：部署、监控、故障与恢复。
- `tasks/`：单次工作上下文，是跨会话续接的主要载体。
- `outputs/`：临时分析结果，不作为事实来源。

## 5. 上下文预算

默认任务上下文应控制在：

- 1 个任务文件；
- 1 个模块入口文档；
- 3–8 个直接相关源文件；
- 相关测试；
- 必要时再加载 1–2 个架构或契约文件。

超过上述范围时，先解释为何属于跨模块任务，并在任务文件中记录新增上下文，而不是静默扩大扫描范围。
