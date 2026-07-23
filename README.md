# Variable-Global 本地工作台

这是当前正在开发的交易研究与策略平台工作区。核心目标不是“堆功能”，而是把策略研究、账户资金、执行链路、风控状态和投研看板组织成一个可以长期迭代的内部平台。

## 当前权威基线

- 正式分支：`main`
- Phase 3 代码发布提交：`77bf4223c2059d5a56fc08a2d49214351c396abc`
- 文档最终化：PR `#10`
- 当前状态：Phase 3 已完成，下一阶段为执行风险与 Demo 闭环
- 总跟踪：GitHub Issue `#2`
- Phase 1：PR `#3`，已完成
- Phase 2：Issue `#4`、PR `#5`，已完成
- Phase 3：Issue `#7`、PR `#9`，已完成
- 总计划：`docs/planning/V6-交易安全加固实施计划.md`
- Phase 3 记录：`docs/planning/V6-Phase3-金融事实与正式账务.md`

`main` 的最新分支指针以 GitHub 为准，不在文档中硬编码会随文档提交变化的 tip SHA。当前系统只允许 Simulation / Fake Gateway，不开放 Paper、Demo 或真实资金 Live。

## 先看这里

| 你要做什么 | 入口 |
|---|---|
| 看总体工程计划 | `docs/planning/V6-交易安全加固实施计划.md` |
| 看 Phase 3 验收记录 | `docs/planning/V6-Phase3-金融事实与正式账务.md` |
| 看 FinancialFact 与正式账务设计 | `docs/technical/FINANCIAL_FACTS.md` |
| 看正式 API 口径 | `docs/technical/API_SPEC.md` |
| 看已完成 Phase 2 | `docs/planning/V6-Phase2-命令入口与结果恢复.md` |
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

## Phase 3 正式金融核对入口

不可变事实：

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
```

可重建投影：

```http
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
```

统一估值时点 NAV：

```http
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run
```

口径：

- FinancialFact 只新增，不提供修改或删除业务 API。
- 重复事实只有在规范化载荷一致时才返回原记录；载荷冲突返回 409。
- Quantity Unit、Settlement Currency 和 Contract Multiplier 来自后端 Catalog。
- Formal PnL 分为 Trading、Funding、Swap、Fee、FX 和 Total。
- Formal NAV 对全部 active binding 账户使用同一 valuationTime。
- 缺失账户、汇率或事实时显式标记 partial／incomplete，不补零。
- 旧 `/pnl` 与 `/nav-snapshots` 仅为工程兼容口径。

## 根目录分工

| 目录 | 定位 | 当前策略 |
|---|---|---|
| `admin-risk/` | 正式前端工程 | Catalog 驱动，不硬编码账户和标的 ID |
| `platform-backend/` | 业务权威后端 | Strategy、Command、Order、FinancialFact、Formal Position/PnL/NAV 权威 |
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
5. 产品页面只展示用户完成业务任务所需的信息、操作和状态；开发说明、实现解释、跳转机制和联调备注不得进入正式界面。
6. 必要提示应短、准、就近呈现；完整解释进入 Markdown 文档，不在页面主要视觉层堆叠辅助文案。
7. 缺失持仓、PnL、行情、汇率和账户事实不得伪装为零。
8. `result_unknown` 必须先恢复和对账，不得重新提交。
9. 正式 Position、PnL 和 NAV 必须能追溯到不可变事实并支持重建。
10. 每批工程改动同步更新计划、测试、API Spec、Release Gate 和 Changelog。
11. 未通过 CI 的 PR 不得合入 main。

## Codex 降噪

根目录同时维护 `.gitignore` 和 `.ignore`：

- `.gitignore` 控制 Git 跟踪范围。
- `.ignore` 控制 `rg` / Codex 后续搜索范围。
- `node_modules/`、`.venv/`、`dist/`、`outputs/` 默认不进入扫描主路径。
- 大型外部参考代码已移出项目根目录，位置见上方入口表。