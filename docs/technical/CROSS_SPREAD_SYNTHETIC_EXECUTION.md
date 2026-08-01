# Cross-Spread Synthetic Execution Contract

状态：`active`  
当前工程批次：Issue #113 / PR #114  
产品目标：完成跨所价差核心交易闭环，并在工程完成后进入 Issue #39 的 Windows 本地实盘验收。

## 1. 权威模型

跨所价差订单由三个正交维度组成：

```text
业务动作（做什么）
+ 执行方式（怎么成交）
+ 触发来源（为什么下达）
```

业务动作：

- `OPEN_LONG_SPREAD`：买 Bybit，卖 MT5。
- `CLOSE_LONG_SPREAD`：卖 Bybit，买 MT5。
- `OPEN_SHORT_SPREAD`：卖 Bybit，买 MT5。
- `CLOSE_SHORT_SPREAD`：买 Bybit，卖 MT5。

执行方式：

- `MARKET`：保护型市价生命周期。
- `LIMIT`：统一限价入口；内部策略包括 `fok` 和 `post_only_chase`。

触发来源：

- `MANUAL`
- `STRATEGY`
- `TAKE_PROFIT`
- `STOP_LOSS`
- `KILL_SWITCH`
- `RISK_REDUCTION`

止盈和止损不是新的订单类型。它们触发普通 Close Action。

## 2. 命令与结果恢复边界

- 新交易意图使用 `TradeCommand`；双腿意图使用 `ExecutionBatch`，每条 Leg 仍生成独立 `TradeCommand`。
- `idempotencyKey` 是原子业务身份；同一键载荷不同必须返回 409，不能生成第二个 Order、Batch 或 Runtime Command。
- 创建 Batch 前完成 Strategy、Account Binding、Instrument 与 ContractSpecification 的双腿预校验。
- 兼容订单入口不是新业务权威入口。
- `result_unknown` 只能通过 Runtime Journal 与后续 Venue 对账恢复；恢复流程重放已持久化事件，绝不重新提交订单。
- Runtime 事件身份不匹配、事件缺失或上游不可用时继续保持未知并阻止重复副作用。
- 当前自动化交易写入仍限于 Simulation / Fake Gateway；外部 Venue 主动恢复与真实资金启用受独立生产门禁约束。

## 2. 两类可成交方向

### 2.1 买 Bybit、卖 MT5

适用：`OPEN_LONG_SPREAD`、`CLOSE_SHORT_SPREAD`。

```text
Executable Spread = Bybit Ask - MT5 Bid
Raw Bybit Buy Limit = MT5 Bid + Limit Spread - Hedge Reserve
Submitted Buy Limit = floor(Raw Price / Tick Size) × Tick Size
```

用户限制是最大允许价差；Bybit 买价向下取 Tick，不能因舍入放宽限制。

### 2.2 卖 Bybit、买 MT5

适用：`OPEN_SHORT_SPREAD`、`CLOSE_LONG_SPREAD`。

```text
Executable Spread = Bybit Bid - MT5 Ask
Raw Bybit Sell Limit = MT5 Ask + Limit Spread + Hedge Reserve
Submitted Sell Limit = ceil(Raw Price / Tick Size) × Tick Size
```

用户限制是最小允许价差；Bybit 卖价向上取 Tick，不能因舍入放宽限制。

成交判断、TP/SL 触发和 Limit 换算必须使用可成交 Bid/Ask，不能用中间价替代。

## 3. 永久执行不变量

- Bybit 是第一腿／主腿。
- MT5 是跟随对冲腿。
- ACK 不等于 Fill。
- Bybit 主腿确认真实成交后，才能提交 MT5。
- MT5 数量依据实际 Bybit Fill 与当前 Contract Size、Minimum、Step 计算。
- Bybit Close 使用 `reduceOnly=true` 和匹配的 `positionIdx`。
- MT5 Close 绑定目标 Position Ticket。
- 开仓后必须验证双边目标持仓；平仓后必须验证双边归零。
- 明确失败、已受理、处理中、结果未知和外部仓位不一致使用不同处置。
- `result_unknown` 不允许盲目重试、回滚或生成第二个业务意图。
- Platform 与 Runtime Live Write、退出监控、1 oz 和单生命周期限制保持独立且默认关闭／受限。

## 4. FOK Limit 合同

Limit 请求显式提供 `limitSpread`，`limitStrategy` 缺省为 `fok`。

Platform 在创建 ExecutionBatch 前读取当前双边可成交报价、应用 Hedge Reserve、按 Tick 保守取整并生成 Bybit `Limit + FOK` 价格。当前价差不满足限制时返回 `409`，不创建 Batch，不提交任何 Venue 订单。

只有 Bybit 终态 `Filled`、累计成交量等于请求量且平均价格有效，才生成正常 Fill 并允许 MT5。

| Bybit FOK 结果 | MT5 | Exit Plan |
|---|---|---|
| 精确全部成交 | 按实际 Fill 对冲 | 正常继续 |
| 零成交取消 | 不提交 | Open 不建计划；Close 释放 Claim 回 `active` |
| 部分成交／数量不一致 | 不提交 | 对账／人工介入 |
| 超时／Query 或 Place 未知 | 不提交 | 对账／人工介入 |

## 5. Exit Plan 与统一 Close Action

每个 Exit Plan 持久化：

```text
takeProfitExecutionMode = market | limit
stopLossExecutionMode   = market | limit
takeProfitLimitStrategy = fok | post_only_chase
stopLossLimitStrategy   = fok | post_only_chase
```

迁移规则：

- 旧计划保留 `market / market`；
- 旧 Limit 策略默认 `fok`；
- TP 与 SL 可独立选择执行方式和 Limit 策略；
- Stop Loss 默认 Market；
- 人工平仓、自动 TP 和自动 SL 调用同一个 claimed-plan Close Action。

自动 Limit 使用原子 Claim 保存的 `triggerSpread` 作为价差限制，不静默回退到 Market。干净零成交或下单前行情失效可以释放 Claim；部分成交、数量不一致、提交后超时或结果未知不能释放 Claim。

## 6. PostOnly Chase 合同

PostOnly Chase 是 `LIMIT` 的内部策略：

```text
executionType = LIMIT
limitStrategy = post_only_chase
Runtime executionPolicy = post_only_chase
```

它不是新的业务动作，也不会改变四类合成指令。

### 6.1 默认状态

- Runtime Chase 开关默认关闭；
- Live Write 仍由 Platform 与 Runtime 双重控制；
- 1 oz 和单生命周期限制不变；
- 不自动启用退出监控；
- 不支持 IOC；
- 不静默改成 FOK 或 Market。

### 6.2 有界策略

- 明确 TTL；
- 最小改单距离以 Tick 计；
- 最大 Amend／Cancel-Repost 次数；
- 变更冷却；
- 每个子单使用同一 Chase 前缀和唯一子编号；
- 优先 Amend；Amend 被拒绝时才进入 Cancel/Repost；
- 只有终态 Cancel 私有事件确认后，才允许 Repost；
- 达到 TTL、最大次数或人工取消后停止继续追价；
- 不允许无限循环。

### 6.3 私有事件与竞态

Private Order 和 Private Execution 是主状态来源：

- Execution 使用稳定 `execId` 去重；
- 累计成交量单调递增且不能超过请求量；
- 重复事件不能重复增加 MT5 数量；
- 序列回退、序列缺口、Malformed Payload、私有流失联或 REST 不一致立即停止 Chase；
- 失联后只允许一次安全撤单尝试和有界 REST 终态对账；
- Cancel/Fill 与 Amend/Fill 竞态依据 Execution 累计量和最终 Venue 状态处理；
- 未确认终态时不重挂，不生成第二个业务意图。

### 6.4 Fill 与 MT5

当前安全口径为：

- 只有累计 Bybit 成交量精确等于请求量，才产生一个正常累计 Fill 并进入现有 MT5 路径；
- 重复 Execution 不会重复累计；
- 部分成交、无效数量 Step、断线或终态不一致不会提交 MT5；
- 残余 Bybit 敞口以明确人工介入／补偿证据保留，不能伪装成完整成交。

增量 MT5 对冲属于后续可单独讨论的策略扩展；当前实现优先保证不会重复对冲或错误放行第二腿。

### 6.5 当前限制

PostOnly 的 Bybit 硬价格边界由提交前的 MT5 可成交参考价和用户 `limitSpread` 推导。Chase 期间当前只追踪 Bybit Maker 盘口，不动态重估 MT5 参考价。

因此 PostOnly 继续默认关闭。真实启用必须通过 Issue #39 受控验收。跨 Venue 动态重估是否加入交易保护，留待后续单独讨论。

## 7. API 与页面

Open、人工 Close 与 TP/SL 计划支持：

```json
{
  "executionMode": "limit",
  "limitStrategy": "post_only_chase",
  "limitSpread": "-0.8"
}
```

页面继续沿用现有交易执行区结构，仅增加 Limit 策略选择和清晰风险提示：

- 市价；
- FOK 限价；
- PostOnly Chase；
- TP/SL 各自的执行方式和 Limit 策略；
- 当前限制价差和派生 Bybit 硬价格边界。

本批不加入事后订单分析面板，也不改变侧边栏、页面结构或视觉体系。

## 8. 分批状态

### Batch 1：统一合成指令模型——已完成

### Batch 2：FOK 价差限价——已完成

### Batch 3：TP/SL 执行方式与统一 Close Action——已完成

### Batch 4：PostOnly Chase——Issue #113 / PR #114

- 状态机、私有事件、Runtime 策略、Platform 合同、数据库迁移和页面选择已实现；
- 当前正在完成最终回归、文档与 CI；
- 未通过最终门禁前保持未合并状态。

### 原 Batch 5：事后订单分析／执行复盘——仅保留待讨论项

该范围当前不属于交易执行界面计划，也不预设最终产品位置。只在 Markdown 中记录候选内容：

- Quote Age 与跨 Venue 时间差；
- Bid/Ask 宽度；
- MT5 Deviation；
- 未对冲时长；
- 真实价差偏差；
- Maker/Taker、手续费、Commission、Swap、Funding 和执行成本拆分。

用户后续将单独决定：是否开发、哪些属于下单前保护、哪些属于事后分析，以及应放在订单详情、复盘页面、风险页面或其他位置。在明确决定前，不创建 Issue，不新增前端区域，不混入交易执行界面。

## 9. 本地实盘边界

CI 只能证明类型、迁移、状态机、映射和安全分支，不能证明真实 Bybit／MT5 权限、Private WebSocket、Broker 字段、Terminal 稳定性、流动性、Tick 一致性或成交质量。

Issue #39 仍需依次验证：

1. Live Write 全关闭的只读核对；
2. 当前／历史 Order、Fill／Deal、Position 和 Account Risk；
3. 真实 Bybit Tick、数量 Step 与 Platform Contract Specification；
4. MT5 Hedge Reserve；
5. 受控 1 oz Market；
6. 受控 1 oz FOK；
7. 自动 TP/SL 的 Market/FOK 行为；
8. PostOnly Private Stream、TTL、Amend、Cancel/Repost、断线和异常结果；
9. 多轮干净 EOD 后才复审临时限制。
