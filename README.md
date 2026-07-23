# Variable-Global 本地工作台

这是当前正在开发的交易研究与策略平台工作区。核心目标不是“堆功能”，而是把策略研究、账户资金、执行链路、风控状态和投研看板组织成一个可以长期迭代的内部平台。

## 当前权威基线

- 正式分支：`main`
- 当前 main：`27b9c19aa2a213ab00b53d736508670dd0d09db4`
- 当前实施：Phase 2 命令入口与结果恢复
- 总跟踪：GitHub Issue `#2`
- Phase 2：Issue `#4`、PR `#5`
- 总计划：`docs/planning/V6-交易安全加固实施计划.md`
- Phase 2 记录：`docs/planning/V6-Phase2-命令入口与结果恢复.md`

当前系统只允许 Simulation / Fake Gateway，不开放 Paper 或真实资金 Live。

## 先看这里

| 你要做什么 | 入口 |
|---|---|
| 看总体工程计划 | `docs/planning/V6-交易安全加固实施计划.md` |
| 看当前 Phase 2 | `docs/planning/V6-Phase2-命令入口与结果恢复.md` |
| 改前端界面 | `admin-risk/src/views` |
| 看策略平台页面 | `http://127.0.0.1:5173/index.html#/strategy/platform` |
| 看策略管理页面 | `http://127.0.0.1:5173/index.html#/strategy/management` |
| 改平台后端 | `platform-backend/app` |
| 改执行网关 | `execution-runtime/app` |
| 查产品/架构文档 | `docs/README.md` 和 `admin-risk/docs` |
| 查外部参考代码 | `C:\Users\jiuxi\Desktop\codex\平台设计其他辅助内容\平台移动文件夹，例如参考代码等\参考代码` |
| 放临时输出 | `outputs/temp` |
| 查工作区降噪规则 | `docs/operations/WORKSPACE_HYGIENE.md` |

## 当前运行口径

- 前端主入口：`5173`
- 前端标准地址：`http://127.0.0.1:5173/index.html#/strategy/platform`
- 后端主入口：`http://127.0.0.1:8000/api/v1`
- 后端健康检查：`http://127.0.0.1:8000/health`
- Runtime Gateway：`http://127.0.0.1:8100`
- 默认 TradingMode：`simulation`
- 默认 Gateway：`fake`

`4373` 只是 Vite 默认配置启动出来的另一个前端实例，不作为主工作入口。

## 正式交易写入口

单腿订单：

```http
POST /api/v1/trading/commands
```

双腿策略：

```http
POST /api/v1/trading/execution-batches
```

结果未知恢复：

```http
POST /api/v1/trading/orders/{orderId}/reconcile
```

规则：

- TradeCommand 和 ExecutionBatch 必须提供 `idempotencyKey`。
- ExecutionBatch 必须提供 `strategyInstanceId`。
- 每条 Batch Leg 都必须生成 TradeCommand。
- `/api/v1/trading/orders` 仅作为 deprecated 兼容入口，禁止新业务继续依赖。
- `result_unknown` 只能查询恢复，不能直接重下。

## 根目录分工

| 目录 | 定位 | 当前策略 |
|---|---|---|
| `admin-risk/` | 正式前端工程 | Catalog 驱动，不硬编码账户和标的 ID |
| `platform-backend/` | 业务权威后端 | Strategy、Command、Order、Fill、Position、PnL 权威 |
| `execution-runtime/` | 执行隔离网关 | 独立进程、Journal、命令原子抢占 |
| `docs/` | 根级导航和执行计划 | 只放权威入口、计划和运行口径 |
| `admin-risk/docs/` | 详细产品和架构文档 | 与代码变更同步维护 |
| `references/` | SQL 和小型参考材料 | 不放大型外部仓库 |
| `tasks/` | 任务拆分与验收 | 每批改动独立留痕 |
| `outputs/` | 生成物和临时预览 | 不放源码 |
| `deploy/` | 部署材料 | 暂不移动 |
| `projects/` | 历史/并行服务实验 | 暂不移动 |
| `scripts/` | 启动、测试和运维脚本 | 必须跟随正式 API 口径更新 |

## 常用命令

前端：

```powershell
cd C:\Users\jiuxi\Desktop\codex\平台后端测试\admin-risk
$env:VITE_PLATFORM_API_BASE_URL="http://127.0.0.1:8000/api/v1"
pnpm vite --host 127.0.0.1 --port 5173
```

平台后端：

```powershell
cd C:\Users\jiuxi\Desktop\codex\平台后端测试\platform-backend
python -m uvicorn app.main:app --reload --port 8000
```

执行网关：

```powershell
cd C:\Users\jiuxi\Desktop\codex\平台后端测试\execution-runtime
python -m uvicorn app.main:app --reload --port 8100
```

完整冒烟：

```powershell
.\scripts\smoke-platform.ps1
```

## 稳定提交门槛

```powershell
cd admin-risk
pnpm type:check
pnpm build

cd ..\platform-backend
python -m ruff check app tests
python -m pytest

cd ..\execution-runtime
python -m ruff check app tests
python -m pytest
```

详细要求见 `admin-risk/docs/quality/release-gate.md`。

## 工程原则

1. 交易、权限、数据库、PnL 和部署变更必须单独审批和留痕。
2. 未知账户、标的、绑定、状态或执行结果必须 fail-closed。
3. 所有外部副作用必须在幂等认领之后发生。
4. 前端不得硬编码正式账户、策略实例和 Instrument ID。
5. 缺失持仓、PnL 和行情不得伪装为零。
6. `result_unknown` 必须先恢复和对账，不得重新提交。
7. 每批工程改动同步更新计划、测试、API Spec、Release Gate 和 Changelog。
8. 未通过 CI 的 PR 不得合入 main。

## Codex 降噪

根目录同时维护 `.gitignore` 和 `.ignore`：

- `.gitignore` 控制 Git 跟踪范围。
- `.ignore` 控制 `rg` / Codex 后续搜索范围。
- `node_modules/`、`.venv/`、`dist/`、`outputs/` 默认不进入扫描主路径。
- 大型外部参考代码已移出项目根目录，位置见上方入口表。
