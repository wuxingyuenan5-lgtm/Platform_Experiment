# Variable-Global 本地工作台

这是当前正在开发的交易研究与策略平台工作区。核心目标不是“堆功能”，而是把策略研究、账户资金、执行链路、风控状态和投研看板组织成一个可以长期迭代的内部平台。

## 当前权威基线

- 正式分支：`main`
- Phase 3 代码发布提交：`77bf4223c2059d5a56fc08a2d49214351c396abc`
- Phase 4A 代码发布提交：`08096d7e72f4f365dc1c27d8e7f1c80ac648c1d2`
- Phase 4B 代码发布提交：`b86a2aa10ec1c39fe974cc6bf6d8dfbdd2475b19`
- 当前实施：Phase 4C Bybit 与 MT5 受控实盘适配器
- 总跟踪：GitHub Issue `#2`
- Phase 4 总计划：Issue `#12`
- Phase 4C：Issue `#18`，分支 `hardening/v6-phase4c-live-adapters`
- 总计划：`docs/planning/V6-交易安全加固实施计划.md`
- Phase 4C 计划：`docs/planning/V6-Phase4C-受控实盘适配器.md`
- 小资金实盘验收：`docs/operations/V6-小资金实盘验收手册.md`

`main` 的最新分支指针以 GitHub 为准。由于 Bybit 与 MT5 模拟环境不能充分复现实盘账户、成交、Funding 和 Swap，本阶段建设真实账户接入；最终运营验收以真实账户的小资金、最小允许仓位为主，但自动实盘写入仍默认关闭，必须先完成只读核对、影子对账、限额和 Kill Switch 验收。

## 先看这里

| 你要做什么 | 入口 |
|---|---|
| 看总体工程计划 | `docs/planning/V6-交易安全加固实施计划.md` |
| 看当前 Phase 4C | `docs/planning/V6-Phase4C-受控实盘适配器.md` |
| 看小资金实盘验收步骤 | `docs/operations/V6-小资金实盘验收手册.md` |
| 看 Live Adapter 技术设计 | `docs/technical/LIVE_VENUE_ADAPTERS.md` |
| 看 Phase 4B | `docs/planning/V6-Phase4B-外部查询与对账差异.md` |
| 看 Venue Query 与差异设计 | `docs/technical/VENUE_RECONCILIATION.md` |
| 看 Phase 4A | `docs/planning/V6-Phase4A-执行风险与Kill-Switch.md` |
| 看执行风险技术设计 | `docs/technical/EXECUTION_RISK_CONTROLS.md` |
| 看 FinancialFact 与正式账务设计 | `docs/technical/FINANCIAL_FACTS.md` |
| 看正式 API 口径 | `docs/technical/API_SPEC.md` |
| 改前端界面 | `admin-risk/src/views` |
| 看策略平台页面 | `http://127.0.0.1:5173/index.html#/strategy/platform` |
| 看策略管理页面 | `http://127.0.0.1:5173/index.html#/strategy/management` |
| 改平台后端 | `platform-backend/app` |
| 改执行网关 | `execution-runtime/app` |
| 查产品/架构文档 | `docs/README.md` 和 `admin-risk/docs` |
| 放临时输出 | `outputs/temp` |

## 当前运行口径

- 前端主入口：`5173`
- Platform Backend：`http://127.0.0.1:8000/api/v1`
- Execution Runtime：`http://127.0.0.1:8100`
- 默认 TradingMode：`simulation`
- 默认 Gateway：`fake`
- Live Runtime 必须使用独立 Environment、Journal、Account、Credential Ref 和 Platform Database。
- Live 配置模板：`execution-runtime/.env.live.example`。

## 正式交易写入口

```http
POST /api/v1/trading/commands
POST /api/v1/trading/execution-batches
POST /api/v1/trading/orders/{orderId}/reconcile
```

规则：

- TradeCommand 和 ExecutionBatch 必须提供 `idempotencyKey`。
- ExecutionBatch 必须提供 `strategyInstanceId`。
- 每条 Batch Leg 都必须生成 TradeCommand。
- `/api/v1/trading/orders` 仅作为 deprecated 兼容入口。
- `result_unknown` 只能查询恢复，不能直接重下。
- 正式 TradeCommand 必须把 StrategyInstance 身份传递到 Runtime。

## Phase 4A 执行风险入口

```http
GET /api/v1/risk/kill-switches/{scopeType}/{scopeId}
PUT /api/v1/risk/kill-switches/{scopeType}/{scopeId}
GET /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
PUT /api/v1/strategies/instances/{strategyInstanceId}/execution-risk-policy
GET  /api/v1/trading/execution-batches/{batchId}/risk
GET  /api/v1/trading/execution-batches/{batchId}/risk-actions
POST /api/v1/trading/execution-batches/{batchId}/risk-actions
```

- Batch 在认领前和每条腿执行前检查 global、strategy、account Kill Switch。
- 每个 Batch 固化腿间延迟、残留名义敞口和失败处置策略。
- 自动平仓和替代对冲必须通过 TradeCommand。
- 风险动作必须幂等并写入 AuditEvent。

## Phase 4B Venue Query 与对账入口

Runtime：

```http
GET  /venue/orders/by-platform/{platformOrderId}
GET  /venue/orders/{externalOrderId}
GET  /venue/fills
GET  /venue/positions
GET  /venue/balances
POST /venue/orders/{externalOrderId}/cancel
```

Platform Backend：

```http
POST /api/v1/trading/orders/{orderId}/venue-reconcile
POST /api/v1/ops/venue-reconciliation/runs
GET  /api/v1/ops/venue-reconciliation/runs/{runId}
GET  /api/v1/ops/venue-reconciliation/runs/{runId}/differences
POST /api/v1/ops/venue-reconciliation/differences/{differenceId}/resolve
```

- Query 不能重发订单或改变外部仓位。
- `result_unknown` 先查询 Runtime Journal，再查询外部 Order 和 Fill。
- External Order、Fill、Position、Balance 导入不可变 FinancialFact。
- 外部与本地不一致时创建 Reconciliation Difference，不无痕覆盖。

## Phase 4C 受控实盘入口

Runtime 能力与经济事件：

```http
GET /gateway/capabilities
GET /venue/economic-events?accountId=...&instrumentId=...&eventType=...
```

Platform 导入：

```http
POST /api/v1/ops/live-economic-events/import
```

受控实盘顺序：

```text
只读实盘
→ 影子核对
→ 双重写开关与 allowlist
→ 单笔/单日限额
→ Kill Switch
→ 最小仓位运营验收
```

只读预检：

```powershell
.\scripts\live-readonly-preflight.ps1
```

该脚本只检查 Live Environment、Gateway、Credential Ref、Write Gate 和 Venue Readiness，不会下单、撤单或改变持仓。

Runtime Live Write 默认关闭，并独立检查：

- `environment=live`。
- `liveWriteEnabled=true`。
- Account、StrategyInstance、Symbol allowlist。
- 单笔最大名义金额。
- 单日最大累计名义金额。
- 确定性的 Bybit orderLinkId 或 MT5 Magic/Comment/Ticket。
- Credential Ref 完整且不进入日志和响应。

Bybit 下单 ACK 不等于成交；MT5 没有可确认 Deal 时也不能伪造 Fill。任何无法确认的写入结果进入 `result_unknown`，随后使用 Venue Reconcile。

## Phase 3 正式金融核对入口

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run
```

- FinancialFact 只新增。
- Quantity Unit、Settlement Currency 和 Contract Multiplier 来自 Backend Catalog。
- Formal PnL 分为 Trading、Funding、Swap、Fee、FX 和 Total。
- Formal NAV 对全部 active binding 使用同一 valuationTime。
- 缺失账户、Instrument 映射或 FX 显式标记 partial／incomplete，不补零。

## 根目录分工

| 目录 | 定位 | 当前策略 |
|---|---|---|
| `admin-risk/` | 正式前端工程 | Catalog 驱动，不硬编码账户和标的 ID |
| `platform-backend/` | 业务权威后端 | Strategy、Command、Order、Risk、FinancialFact、Reconciliation、Formal Accounting 权威 |
| `execution-runtime/` | 执行隔离网关 | Journal、Gateway、Live Safety、Venue Query、外部执行隔离 |
| `docs/` | 根级导航和执行计划 | 权威入口、计划和运行口径 |
| `admin-risk/docs/` | 详细产品和架构文档 | 与代码同步维护 |
| `tasks/` | 任务拆分与验收 | 每批改动独立留痕 |
| `outputs/` | 生成物和临时预览 | 不放源码 |
| `scripts/` | 启动、测试和运维脚本 | 跟随正式 API 更新 |

## 常用命令

```powershell
cd C:\Users\jiuxi\Desktop\codex\平台后端测试\admin-risk
$env:VITE_PLATFORM_API_BASE_URL="http://127.0.0.1:8000/api/v1"
pnpm vite --host 127.0.0.1 --port 5173

cd ..\platform-backend
python -m uvicorn app.main:app --reload --port 8000

cd ..\execution-runtime
python -m uvicorn app.main:app --reload --port 8100
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

1. 交易、权限、数据库、PnL、风险和部署变更必须独立审批并留痕。
2. 未知账户、标的、绑定、状态或执行结果必须 fail-closed。
3. 所有外部副作用必须在幂等认领之后发生。
4. Kill Switch 必须在新增风险前生效。
5. Runtime Live Gate 必须独立于 Platform Live Gate，默认关闭。
6. Query 与 Command 分离；同步 ACK 不等于成交。
7. 外部与本地差异不得无痕覆盖，必须形成 Difference。
8. 凭证只通过引用读取，不进入代码、数据库响应、日志和审计内容。
9. 产品页面只展示完成业务任务所需的信息、操作和状态；开发说明进入 Markdown。
10. 缺失持仓、PnL、行情、汇率和账户事实不得伪装为零。
11. `result_unknown` 必须先恢复和对账，不得重新提交。
12. 正式 Position、PnL 和 NAV 必须能追溯到不可变事实并支持重建。
13. 每批工程改动同步更新计划、测试、API Spec、Release Gate 和 Changelog。
14. 未通过 CI 的 PR 不得合入 main。

## 当前发布边界

Phase 4C 的工程实现可以通过离线 Provider Contract Tests 验收，但真实账户运营验收必须单独完成。后续测试优先采用真实账户的小资金和最小允许仓位；在真实只读核对、连续日终对账、最小仓位测试和 Kill Switch 演练完成前，`liveWriteEnabled` 必须保持 false。
