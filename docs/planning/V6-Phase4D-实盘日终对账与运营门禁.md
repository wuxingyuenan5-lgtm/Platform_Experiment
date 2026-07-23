# V6 Phase 4D：实盘日终对账、报告与运营门禁

状态：`engineering completed / merge pending / operational acceptance pending`  
实施分支：`hardening/v6-phase4d-eod-reconciliation`  
Pull Request：`#21 Build V6 Phase 4D live end-of-day reconciliation and scale gates`  
跟踪 Issue：`#20 V6 Phase 4D：实盘日终对账、报告与运营门禁`  
上级计划：Issue `#12`、`V6-交易安全加固实施计划.md`  
运营手册：`../operations/V6-小资金实盘验收手册.md`  
工程验收：`Platform CI #327 / run 30018515755`  
更新时间：`2026-07-23`

## 1. 目标

Phase 4D 将 Phase 3 的不可变金融事实、Phase 4A 的执行风险控制、Phase 4B 的外部查询与差异、Phase 4C 的受控实盘适配器，连接为每日可重复执行的运营闭环：

```text
Order / Fill / Deal
+ Position / Balance
+ Funding / Swap / Fee
→ FinancialFact
→ Formal Position / PnL / NAV
→ Reconciliation Difference
→ EOD Report
→ Human Review / Live Scale Gate
```

本阶段优先服务真实账户的小资金、最小仓位测试，不把模拟盘结果视为最终运营验收。

## 2. 日终身份与时间语义

每份报告由以下身份确定：

- `businessDate`
- `timezone`：IANA 时区，例如 `Asia/Shanghai`
- `valuationTime`：带 UTC Offset 的估值时点
- `strategyInstanceId`
- `accountId`
- `idempotencyKey`

约束：

- `businessDate` 必须与 `valuationTime` 在指定 IANA 时区下的日期一致。
- 同一身份、同一载荷重复提交返回原报告。
- 同一自然身份但载荷不同返回 `409 Conflict`。
- 外部失败不得生成虚假 `complete`。
- 报告保存 `owner`、`dueAt`、完成时间和 SLA 状态。

## 3. 日终编排

按固定顺序执行：

1. 对业务日期窗口内的 Platform Order，以及估值时点仍未终结的历史 Order 执行 Venue Reconcile。
2. 查询并导入外部 Position 与 Balance。
3. 查询并导入 Bybit Funding/Fee、MT5 Swap/Commission/Fee。
4. 从 FinancialFact 重建 Formal Position 与 Formal PnL。
5. 在统一 `valuationTime` 生成 Formal NAV。
6. 汇总当日及历史 Open/Accepted Reconciliation Difference、未映射事件、缺失账户和数据质量。
7. 生成 EOD Report，不自动解决或接受任何差异。

## 4. 报告状态

| status | 含义 |
|---|---|
| `complete` | 外部查询、事实导入、正式投影与 NAV 均成功，且没有未解释差异、未映射事件、缺失账户或不完整 PnL |
| `completed_with_differences` | 编排完成，但存在差异、跳过事件、缺失账户或不完整正式账务 |
| `partial` | 部分步骤成功、部分步骤失败 |
| `failed` | 无法形成有效日终链路，不能解释为零差异 |

SLA 状态独立计算：

- `pending`
- `met`
- `breached`
- `overdue`

## 5. 扩大实盘门禁

报告默认 `scaleGateStatus=blocked`。

只有 `status=complete` 时，才进入 `eligible_for_review`。人工复核只能做以下不可变决策：

- `approved_same_limits`：只批准继续使用当前小资金与当前限额，不自动提高限额。
- `needs_remediation`：需要修复差异、映射、数据质量或运行故障。
- `rejected`：当日结果不可接受。

Open Difference、Accepted Difference、未映射外部事件、缺失账户、不完整 PnL 或任一运行错误都阻断扩大资金、仓位、品种或自动化频率。

## 6. API

```http
POST /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports
GET  /api/v1/ops/eod-reconciliation/reports/{reportId}
POST /api/v1/ops/eod-reconciliation/reports/{reportId}/review
```

创建示例：

```json
{
  "idempotencyKey": "eod-20260723-strategy-account",
  "businessDate": "2026-07-23",
  "timezone": "Asia/Shanghai",
  "valuationTime": "2026-07-23T23:59:00+08:00",
  "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
  "accountId": "account_live_bybit_primary",
  "actor": "eod-runner",
  "owner": "operations-owner",
  "dueAt": "2026-07-24T10:00:00+08:00"
}
```

## 7. PowerShell 运行入口

```powershell
.\scripts\run-live-eod-reconciliation.ps1 `
  -StrategyInstanceId "<strategy-instance-id>" `
  -AccountId "<account-id>" `
  -BusinessDate "2026-07-23" `
  -TimeZone "Asia/Shanghai" `
  -ValuationTime "2026-07-23T23:59:00+08:00" `
  -DueAt "2026-07-24T10:00:00+08:00" `
  -Actor "eod-runner" `
  -Owner "operations-owner"
```

默认先执行只读 Runtime Preflight。脚本不会提交订单、提高实盘限额或自动接受差异。非 clean 报告返回非零退出码并保留 JSON 输出。

## 8. 金样本

### 8.1 清洁日终

- Order Venue Reconcile 无差异。
- Position / Balance 对账无差异。
- Funding / Swap / Fee 无未映射事件。
- Formal PnL 全部 complete。
- Formal NAV 无缺失账户。
- 报告为 `complete + eligible_for_review`。
- 相同请求重复执行返回同一报告。
- 人工批准后仅为 `approved_same_limits`。

### 8.2 差异日终

- Position 数量不一致。
- 存在未映射 Swap 或 Funding。
- Formal NAV 缺少一个绑定账户。
- 报告为 `completed_with_differences + blocked`。
- 不允许 `approved_same_limits`。
- 可以不可变地标记 `needs_remediation`。

### 8.3 历史差异与订单窗口

- 历史 Accepted Difference 即使当日无新差异，也保持 `blocked`。
- 当日终结订单进入核对。
- 历史非终结订单继续进入核对。
- 历史已终结订单和估值时点之后订单不进入当日报告。

### 8.4 外部故障

- Venue Position、Balance、Economic Event 与 NAV 链路失败。
- 报告必须为 `failed` 或 `partial`。
- 不得返回 `complete`、零差异或可扩大限额状态。

## 9. 工程验收

最终工程验收：`Platform CI #327 / run 30018515755`

| 检查 | 结果 |
|---|---|
| Execution Runtime strict Ruff、full Ruff、Pytest | 通过 |
| Platform Backend strict Ruff、full Ruff、Pytest | 通过 |
| Frontend frozen install、type-check、production build | 通过 |
| EOD Report 表、API、幂等、SLA 和不可变复核 | 通过 |
| Order、Position、Balance、Economic Event、Formal PnL/NAV 编排 | 通过 |
| 历史 Open/Accepted Difference 扩大实盘阻断 | 通过 |
| 业务日期窗口与历史未终结订单 | 通过 |
| Clean、Difference、Historical Accepted、Order Window、External Failure 金样本 | 通过 |
| PowerShell 实盘日终入口 | 已加入 |
| README、START-HERE、API Spec、Release Gate、总计划和 Changelog | 已同步 |

## 10. 运营验收

以下内容需要真实账户、小资金和人工监督，不能由 CI 完成：

- [ ] Bybit 与 MT5 真实只读数据形成首份 EOD Report。
- [ ] 最小仓位成交日的 Order、Execution/Deal、Position、Balance、Funding/Swap/Fee 全链路一致。
- [ ] Kill Switch、断网、Runtime 重启、`result_unknown` 演练被报告记录。
- [ ] 连续多个真实交易日不存在未解释差异。
- [ ] 测试后 Write Gate、Notional Limit 和临时 allowlist 强制复位。

## 11. 明确边界

- CI 不接触真实凭证和真实账户。
- 日终编排不自动修改真实仓位来消除差异。
- Accepted Difference 只表示风险被人工接受，不表示数据一致。
- Phase 4D 工程完成不自动允许扩大实盘规模。
- 不引入 Kafka、Kubernetes 或复杂微服务。
