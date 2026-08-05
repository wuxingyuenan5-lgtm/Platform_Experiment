# EOD Reconciliation and Live Scale Gate

状态：`active`
适用版本：`Platform 0.10.x`
合同状态：长期维护；历史实施材料保留在 Git 历史中。
## 1. 权威边界

EOD Report 是运营核对结果，不是新的金融事实来源：

```text
External Venue Facts
→ FinancialFact
→ Formal Position / PnL / NAV
→ Reconciliation Difference
→ EOD Report
```

- FinancialFact 仍是不可变外部事实入口。
- Formal Position/PnL/NAV 仍是可重建投影。
- Reconciliation Difference 保存外部与本地的不一致。
- EOD Report 只编排、引用、汇总和留痕，不反向修改外部事实或真实仓位。

## 2. 时间模型

报告同时保存：

- Business Date。
- IANA Timezone。
- Valuation Time。
- Created At。
- Completed At。
- Due At。

Business Date 不是简单的 UTC 日期。服务端使用 IANA Timezone 将 Valuation Time 转换为本地日期并验证一致性。

Formal NAV 使用相同 Valuation Time。订单、事实和余额不得跨不同估值时点拼接后伪装成同步结果。

## 3. 幂等模型

两层身份：

1. 客户端 `idempotencyKey`。
2. 自然身份：`businessDate + strategyInstanceId + accountId`。

服务端保存规范化请求的 SHA-256：

- 身份相同、载荷一致：返回原报告。
- 身份相同、载荷不同：返回 `409 Conflict`。

报告结果与人工复核均为不可变首写语义。需要在修复后重新运行同一业务日期时，应使用后续明确实现的报告修订/尝试号，不允许覆盖旧报告。

## 4. 编排步骤

### 4.1 Order

选择业务日期窗口内的订单，以及在估值时点仍未终结的历史订单。对每个订单执行 Phase 4B Venue Reconcile：

- Runtime Journal 优先。
- 外部 Order / Fill 后续查询。
- 不重新提交原订单。
- 外部事实幂等导入。
- 不一致生成 Difference。

### 4.2 Account Snapshot

运行账户级 Venue Reconciliation：

- Position。
- Balance / Equity / Available Balance。
- Formal Position 比较。
- Balance Snapshot 比较。

### 4.3 Economic Events

导入：

- Bybit Funding、Fee。
- MT5 Swap、Commission、Fee。

未映射 Instrument 的 External Event 保存于 `skippedExternalIds`，不能被解释为成功覆盖。

### 4.4 Formal Accounting

- 从 FinancialFact 重建 Formal Position/PnL。
- 统计 PnL `dataQualityState != complete`。
- 在统一估值时点运行 Formal NAV。
- 保存 Missing Account IDs。

## 5. 状态机

### Report Status

```text
complete
completed_with_differences
partial
failed
```

判断原则：

- 任何外部调用失败都必须进入 errors。
- 所有核心步骤均失败时为 failed。
- 部分成功、部分失败为 partial。
- 编排成功但存在 Difference、Skipped Event、Missing Account 或 Incomplete PnL 时为 completed_with_differences。
- 只有所有必要条件完整时为 complete。

### SLA Status

```text
pending → met
        ↘ breached
pending → overdue
```

SLA 不改变金融数据，只反映运营时效。

### Scale Gate

```text
blocked
→ eligible_for_review
→ approved_same_limits

blocked / eligible_for_review
→ needs_remediation | rejected
```

`approved_same_limits` 只允许保持当前测试规模，不表示允许提高资金、仓位或自动化频率。

## 6. 差异语义

至少支持：

- missing_local
- missing_external
- quantity_mismatch
- price_mismatch
- currency_mismatch
- status_mismatch

Open Difference 必须阻断扩大实盘。Accepted Difference 仍代表数据不一致，只是风险被人工接受，也必须阻断扩大范围，直到后续治理规则明确释放。

## 7. 失败策略

EOD 编排是 best-effort 聚合，但不能 fail-open：

- 每个阶段捕获故障并记录可审计错误。
- 已成功的外部事实和投影保留。
- 最终状态根据完整性判定。
- 不返回伪造空仓、零余额、零 PnL 或 complete。
- 不自动解决 Difference。
- 不自动改变 Kill Switch、Write Gate 或限额。

## 8. API

```http
POST /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports/{reportId}
POST /api/v1/ops/eod-reconciliation/reports/{reportId}/review
```

查询过滤：

- strategyInstanceId
- accountId
- businessDate

## 9. 审计

至少写入：

- `eod_reconciliation_completed`
- `eod_reconciliation_reviewed`

审计详情包含：

- Business Date / Timezone / Valuation Time。
- StrategyInstance / Account。
- Owner / Actor / Reviewer。
- Report / SLA / Scale Gate 状态。
- Difference、Skipped Event、Missing Account 和错误摘要。

## 10. 实盘运营原则

真实账户小资金测试必须：

1. 先通过 Read-only Preflight。
2. 先完成影子核对。
3. 只使用最小允许仓位。
4. 写开关、Allowlist、单笔和单日上限只在人工监督窗口开放。
5. 测试后强制复位。
6. 每个测试日生成 EOD Report。
7. 多个真实交易日无未解释差异后，才进入扩大规模评审。

## 11. 当前限制

- 自动调度尚未与 Windows Task Scheduler 或其他调度器正式绑定。
- 报告修订/尝试号仍待完成。
- 历史 Outstanding Difference 的全量阻断仍待完成。
- 订单筛选需完善为“当日窗口 + 未终结历史订单”。
- 认证、RBAC、双人审批、生产密钥托管和告警仍属于后续生产门禁。
