# Platform V6 最小发布门槛

状态：`active`  
适用基线：`main / Platform V6`  
总体计划：`../../../docs/planning/V6-交易安全加固实施计划.md`  
当前阶段：`../../../docs/planning/V6-Phase4D-实盘日终对账与运营门禁.md`

## 1. 目的

建立可重复、可审计的工程与运营门槛。涉及交易、账户、执行、风险、Live Adapter、FinancialFact、PnL、NAV、Venue Query、Reconciliation、EOD Report 或部署的变更，不能只凭页面效果或“接口能调用”判断完成。

必须区分：

- 工程验收：代码、离线 Provider Contract Tests、金样本、CI 和 Markdown。
- 运营验收：真实账户只读、影子核对、最小仓位写入、Kill Switch 演练和多个清洁日终周期。

工程验收通过不自动授予实盘写入权限，也不允许提高资金、仓位、品种或自动化频率。

## 2. 自动检查

### Frontend

```bash
cd admin-risk
pnpm sync:trading-tools
pnpm type:check
pnpm build
```

### Platform Backend

```bash
cd platform-backend
python -m ruff check app tests
python -m pytest
```

严格 Gate 至少覆盖：

- TradeCommand、ExecutionBatch、Execution Risk。
- FinancialFact 与 Formal Accounting。
- Venue Reconciliation 与 Live Economic Event Import。
- `app/eod_reconciliation.py`。
- `app/eod_policy.py`。
- `tests/test_eod_reconciliation.py`。
- `tests/test_eod_policy.py`。
- Phase 1–4C 全部安全、恢复、账务、实盘适配器和对账回归。

### Execution Runtime

```bash
cd execution-runtime
python -m ruff check app tests
python -m pytest
```

严格 Gate 至少覆盖 Journal、Gateway、Live Safety、Account Route、Bybit Live、MT5 Live、Secret Resolver 及全部 Runtime 回归。

### GitHub Actions

- `main`、`hardening/**` 和面向 `main` 的 PR 必须触发 Platform CI。
- Backend、Runtime、Frontend 全部通过后才允许合并。
- 失败日志保留短期 Artifact。
- README、START-HERE、Release Gate、Planning、Technical、Operations、API Spec 和 Changelog 变化必须触发 CI。
- 不允许强推 main 绕过检查。

## 3. TradeCommand 与 ExecutionBatch

- 正式写入口只有 TradeCommand 和 ExecutionBatch。
- 业务级幂等键必填。
- Strategy、active Binding、Account、Instrument、ContractSpecification 必须有效。
- 数量、价格和步长合法。
- Platform Live Gate 默认关闭。
- 每个 Batch Leg 生成独立 TradeCommand。
- StrategyInstance 身份必须传递到 Runtime。
- 相同幂等键不同载荷返回 409。
- Deprecated `/trading/orders` 不得作为 Live 写入口。

## 4. Runtime Command 幂等

- Runtime 在 Gateway 副作用前原子抢占 command_id。
- 重复 Command 返回持久化事件。
- 已认领但无事件时不重复调用 Gateway。
- Runtime 重启后 Journal 可恢复。
- LiveWriteClaim 在 SQLite 原子事务中认领。
- Command 载荷冲突拒绝。
- Query API 不得调用 submit_order。

## 5. Result Unknown

- 同步 ACK 不等于成交。
- Venue 明确拒绝与结果未知分开处理。
- 可能已到 Venue 但无法确认时返回 502，使 Platform 标记 `result_unknown`。
- `result_unknown` 不得直接重下。
- 第一层查 Runtime Journal，第二层查 Venue Order 与 Fill/Deal。
- 外部仍查不到时生成 Difference。
- External Fill/Deal ID 必须作为稳定事实身份。

## 6. Kill Switch 与 Execution Risk

- Global、Strategy、Account Kill Switch 在 Batch 认领前和每腿执行前检查。
- 命中后不能产生新增风险。
- Batch 固化腿间延迟、残留名义敞口和失败处置策略。
- `failed` 不等于风险解除。
- 自动平仓和替代对冲必须通过 TradeCommand。
- RiskAction 重放不得重复下单。
- 风险状态、动作、操作人和原因进入 AuditEvent。

## 7. Live Runtime 双重门禁

写入必须同时满足：

1. Runtime `environment=live`。
2. Runtime `liveWriteEnabled=true`；默认 false。
3. Account 位于 allowlist。
4. StrategyInstance 位于 allowlist。
5. Symbol 位于 allowlist。
6. 正数 Reference Price 可用。
7. 单笔 Notional 不超限。
8. 单日累计 Notional 不超限。
9. Platform Live Gate、Kill Switch 和 Execution Risk 已通过。
10. Credential Ref、Account Route 和 Instrument Map 完整。

任一条件无法确认时 fail-closed。不得自动回退 Fake Gateway。

## 8. Bybit 与 MT5 实盘适配器

### Bybit

- 使用 V5 Unified Trading API。
- `orderLinkId` 由 Platform Order ID 确定性派生。
- Place-order ACK 只生成 acknowledged，不生成虚假 Fill。
- Open Orders、History、Execution、Position、Wallet 和 Transaction Log 可查询。
- Execution ID、Funding ID 和 Fee ID 稳定且可幂等导入。
- API Key 和 Secret 不进入响应、日志和审计。

### MT5

- 非 Windows 或无可用 Terminal 时 fail-closed。
- AccountInfo login 与配置账号一致。
- 下单前执行 `order_check`，写入使用 `order_send`。
- Order、Deal、Position、Balance、Equity、Margin 可查询。
- Magic、Comment、Order/Deal/Position Ticket 可追溯。
- Swap、Commission 和 Fee 从外部 Deal 字段导入。
- Password 和 Server 不进入响应、日志和审计。

## 9. Venue Query、FinancialFact 与 Difference

- Query 与 Command 分离。
- 404、空结果、网络错误、配置错误和结果未知含义不同。
- Query 失败不得返回伪造空仓或零余额。
- External Order、Fill/Deal、Position、Balance、Funding、Swap 和 Fee 使用稳定外部身份。
- 重复导入不得重复改变 Position、PnL 或 NAV。
- 外部与本地冲突形成 Reconciliation Difference，不无痕覆盖。
- Difference 首次处置记录不可被重复改写。
- `accepted` 不表示数据一致，只表示风险被人工接受。

## 10. Phase 4D EOD Report

```http
POST /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports/{reportId}
POST /api/v1/ops/eod-reconciliation/reports/{reportId}/review
```

必须确认：

- Business Date、IANA Timezone、Valuation Time 和 Due At 显式。
- Business Date 与 Valuation Time 在指定时区下的日期一致。
- 相同身份同载荷返回原报告；载荷冲突返回 409。
- 订单范围包括业务日期窗口和仍未终结的历史订单。
- Order、Execution/Deal、Position、Balance、Funding、Swap、Fee 全部进入编排。
- FinancialFact 导入后重建 Formal Position/PnL。
- Formal NAV 使用统一 Valuation Time。
- 外部调用失败进入 errors，不生成虚假 complete。
- Open 和 Accepted Difference 均阻断扩大实盘。
- Skipped External Event、Missing Account 和 Incomplete PnL 均阻断扩大实盘。
- 报告保存 Owner、Due At、Completed At 和 SLA 状态。
- 人工复核不可变。
- 只有 clean report 可以标记 `approved_same_limits`。
- `approved_same_limits` 不提高限额，不开启 Live Write。

## 11. EOD 金样本

至少保留：

1. Clean report：幂等、complete、eligible_for_review、不可变复核。
2. Difference report：open Difference、Skipped Event、Missing Account 导致 blocked。
3. Historical Accepted Difference：即使当日干净也阻断 Scale Gate。
4. Order Window：当日终结订单 + 历史非终结订单，排除历史已终结和估值后订单。
5. External Failure：所有外部步骤失败时为 failed，不是零差异 complete。
6. Natural identity payload conflict 返回 409。
7. 既有 Phase 1–4C 金样本全部通过。

## 12. 实盘 PowerShell 入口

```powershell
.\scripts\live-readonly-preflight.ps1
.\scripts\run-live-eod-reconciliation.ps1 ...
```

要求：

- EOD 脚本默认先运行只读 Preflight。
- 脚本不提交或撤销订单。
- 报告 JSON 保存在本地输出目录。
- 非 clean report 返回非零退出码。
- 脚本不得自动提高限额、清理 Difference 或开启 Live Write。

## 13. 前端与产品界面

- Simulation 与 Live 明确区分。
- Catalog 或 Gateway Capability 不完整时禁用提交。
- Live Write 关闭时不得显示为可执行。
- 缺失 Position、PnL、Risk、Venue、Difference 或 EOD 状态展示 `—` 或未知。
- 产品页面不展示开发说明、实现解释或联调备注。

## 14. 文档一致性

涉及交易、风险、Live Adapter、EOD、PnL、NAV、API、部署或运营门禁时，必须同步更新：

- 实施计划。
- 技术设计。
- API Spec。
- README。
- START-HERE。
- Release Gate。
- Changelog。
- Issue 与 Pull Request。

## 15. 阻断条件

任一情况存在，不得合并、开启 Live Write 或扩大实盘：

- 任一 CI Job 失败或未执行。
- Live Write 默认开启。
- Platform 或 Runtime 任一道门禁可被绕过。
- Account、Strategy、Symbol 或 Notional 未 fail-closed。
- 同步 ACK 被视为成交。
- `result_unknown` 会重下原订单。
- Query 失败被解释为空仓、零余额或 clean EOD。
- External Event 缺 Instrument Map 但未列入 skipped。
- 重复外部事实导致重复记账。
- Open 或 Accepted Difference 未阻断 Scale Gate。
- EOD 外部步骤失败但报告为 complete。
- 缺失 Account、FX、PnL 或 NAV 被补零。
- EOD 人工复核可被覆盖。
- EOD Review 自动提高限额或开启写入。
- Secret 出现在仓库、日志、截图、Markdown、审计或响应。
- active Markdown 与实现不一致。

## 16. 真实账户运营验收

必须人工留痕：

- Bybit 只读订单、成交、持仓、余额、Funding。
- MT5 只读 Order、Deal、Position、Balance、Swap。
- 最小允许仓位受控下单、撤单、查询和事实导入。
- Kill Switch、断网、Runtime 重启、`result_unknown` 演练。
- 每个真实测试日形成 EOD Report。
- 连续多个真实日终周期无未解释差异。
- 测试结束后 Write Gate、Notional Limit 和临时 allowlist 强制复位。

运营验收前 `liveWriteEnabled=false`。即使运营验收通过，也必须单独审批扩大资金和自动化。
