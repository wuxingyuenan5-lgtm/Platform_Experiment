# Cross-Spread Synthetic Execution Contract

状态：`active`  
当前工程批次：Issue #111 / PR #112  
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
- `LIMIT`：统一限价入口；当前已实现 Bybit FOK 主腿与 MT5 Market 对冲腿。

触发来源：

- `MANUAL`
- `STRATEGY`
- `TAKE_PROFIT`
- `STOP_LOSS`
- `KILL_SWITCH`
- `RISK_REDUCTION`

止盈和止损不是新的订单类型。它们触发普通 Close Action：

```text
TAKE_PROFIT + CLOSE_LONG_SPREAD + LIMIT
STOP_LOSS   + CLOSE_LONG_SPREAD + MARKET
```

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
- Bybit Market 或 FOK 必须确认真实成交后，才能提交 MT5。
- MT5 数量依据实际 Bybit Fill 与当前 Contract Size、Minimum、Step 计算。
- Bybit Close 使用 `reduceOnly=true` 和匹配的 `positionIdx`。
- MT5 Close 绑定目标 Position Ticket。
- 开仓后必须验证双边目标持仓；平仓后必须验证双边归零。
- 明确失败、已受理、处理中、结果未知和外部仓位不一致使用不同处置。
- `result_unknown` 不允许盲目重试、回滚或生成第二个业务意图。
- Platform 与 Runtime Live Write、退出监控、1 oz 和单生命周期限制保持独立且默认关闭／受限。

## 4. FOK Limit 合同

Limit 请求显式提供 `limitSpread`。Platform 在创建 ExecutionBatch 前：

1. 读取 Bybit 与 MT5 当前 Bid/Ask；
2. 计算当前可成交价差；
3. 验证当前价差满足限制；
4. 读取版本化 Bybit `priceTick`；
5. 应用非负 Hedge Reserve；
6. 按方向保守取 Tick；
7. 生成 Bybit `Limit + FOK` 价格。

当前价差不满足限制时返回 `409`，不创建 Batch，不提交任何 Venue 订单。

只有 Bybit 终态 `Filled`、累计成交量等于请求量且平均价格有效，才生成正常 Fill 并允许 MT5。

结果语义：

| Bybit FOK 结果 | MT5 | Exit Plan |
|---|---|---|
| 精确全部成交 | 按实际 Fill 对冲 | 正常继续 |
| 零成交取消 | 不提交 | Open 不建计划；Close 释放 Claim 回 `active` |
| 部分成交／数量不一致 | 不提交 | 对账／人工介入 |
| 超时／Query 或 Place 未知 | 不提交 | 对账／人工介入 |

Hedge Reserve 默认 `0`。真实 Tick 一致性和 Broker Reserve 必须由 Issue #39 的受控主机证据确认。

## 5. Exit Plan 执行方式持久化

每个 Exit Plan 持久化：

```text
takeProfitExecutionMode = market | limit
stopLossExecutionMode   = market | limit
```

迁移规则：

- 所有旧计划自动得到 `market / market`；
- 新 Open 请求未提供字段时仍默认 `market / market`；
- TP 与 SL 可独立选择；
- Stop Loss 默认 Market；选择 FOK 必须是显式操作。

FOK Stop Loss 可能零成交并使计划恢复 `active`。当风险降低优先于价格约束时应继续使用 Market。

## 6. 统一 Close Action

人工平仓、自动 TP 和自动 SL 都调用同一个 claimed-plan Close Action。

### 6.1 人工平仓

- 人工请求明确提供 `executionMode`；
- Limit 还必须提供 `limitSpread`；
- 原子 Claim 记录 `triggerReason=manual`。

### 6.2 自动 TP/SL

```text
读取活动计划
→ 使用可成交 Close Spread 判断阈值
→ 原子 Claim 并保存 triggerReason / triggerSpread / triggeredAt
→ 根据计划保存的 TP 或 SL execution mode 选择 Market/FOK
→ 调用统一 Close Action
```

自动 Limit 使用原子 Claim 保存的 `triggerSpread` 作为价差限制。它不会重新使用 TP/SL 阈值，也不会静默回退到 Market。

如果 Claim 后、下单前行情已经不满足该限制：

- 不创建 Batch；
- 不提交 Venue 订单；
- 释放 Claim，计划恢复 `active`；
- 下一轮重新观察最新报价。

### 6.3 FOK 重试幂等性

FOK Close 幂等键包含 `planId + triggeredAt`：

- 同一次 Claim 的重复提交映射到同一业务尝试；
- 干净零成交释放 Claim 后，下一次 Claim 使用新时间和新幂等键；
- 不会永久重放第一次零成交 Batch。

部分成交、数量不一致、提交后超时或结果未知不能释放 Claim，必须进入人工介入／对账。

## 7. API 与页面

Open 请求新增可选字段：

```json
{
  "takeProfitExecutionMode": "market",
  "stopLossExecutionMode": "market"
}
```

Exit Plan 响应返回相同字段。页面支持：

- Market/FOK 开仓；
- Market/FOK 人工平仓；
- 独立选择 TP 和 SL 的 Market/FOK；
- 查看计划保存的 TP/SL 执行方式；
- 查看 FOK 定价证据；
- 对 FOK Stop Loss 显示风险提示。

## 8. 分批状态

### Batch 1：统一合成指令模型——已完成

权威 `action / executionType / triggerReason`，Market 语义保持不变。

### Batch 2：FOK 价差限价——已完成

人工 Open/Close 支持 Market/FOK，精确全部成交后才允许 MT5。

### Batch 3：TP/SL 执行方式与统一 Close Action——Issue #111

- 迁移并持久化 TP/SL 执行方式；
- 旧数据默认 Market/Market；
- 人工、TP、SL 复用统一 Close Action；
- 自动 FOK 使用 claimed trigger spread；
- 干净未成交释放 Claim；异常结果不释放。

### Batch 4：PostOnly Chase——后续独立 Issue

- Bybit Private Order WebSocket；
- Bybit Private Execution WebSocket；
- PostOnly 创建、改单、撤单和成交竞态状态机；
- 自动／手动 Chase；
- TTL、改单阈值、最大次数、冷却和重挂；
- 部分成交的精确 MT5 映射或 Bybit 补偿。

### Batch 5：执行保护与复盘——暂缓讨论

用户已明确要求当前不执行。Quote Age、跨 Venue 时间差、Bid/Ask 宽度、MT5 Deviation、未对冲时长、真实价差偏差和费用拆分均不得混入 Batch 3 或 Batch 4。

## 9. 本地实盘边界

CI 只能证明类型、迁移、状态机、映射和安全分支，不能证明真实 Bybit／MT5 权限、Private WebSocket、Broker 字段、Terminal 稳定性、流动性、Tick 一致性或成交质量。

Issue #39 仍需依次验证：

1. Live Write 全关闭的只读核对；
2. 当前／历史 Order、Fill／Deal、Position 和 Account Risk；
3. 真实 Bybit Tick、数量 Step 与 Platform Contract Specification；
4. MT5 Hedge Reserve；
5. 受控 1 oz Market；
6. 受控 1 oz FOK，包括全成交、零成交和异常结果；
7. 自动 TP/SL 的 Market/FOK Claim 与 exactly-once 行为；
8. Batch 4 完成后再测试 PostOnly Chase；
9. 多轮干净 EOD 后才复审临时限制。
