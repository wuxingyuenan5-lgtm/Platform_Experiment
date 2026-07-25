# Cross-Spread Synthetic Execution Contract

状态：`active`  
当前工程批次：Issue #109 / PR #110  
产品目标：跑通“跨所价差 → 交易执行”页面的核心交易闭环，并在核心工程完成后进入 Issue #39 的 Windows 本地实盘验收。

## 1. 核心分层

跨所价差交易不把开仓、平仓、止盈和止损视为与市价、限价并列的订单类型。

```text
业务动作（做什么）
  + 执行方式（怎么成交）
  + 触发来源（为什么下达）
```

### 1.1 业务动作

- `OPEN_LONG_SPREAD`：买 Bybit，卖 MT5。
- `CLOSE_LONG_SPREAD`：卖 Bybit，买 MT5。
- `OPEN_SHORT_SPREAD`：卖 Bybit，买 MT5。
- `CLOSE_SHORT_SPREAD`：买 Bybit，卖 MT5。

### 1.2 执行方式

- `MARKET`：保护型市价生命周期。
- `LIMIT`：统一限价入口；当前实现的第一种内部策略是 Bybit `FOK` 主腿加 MT5 市价对冲腿。

FOK、PostOnly Chase 和未来 IOC 是 `LIMIT` 的内部执行策略，不是与市价、限价并列的业务动作。

### 1.3 触发来源

- `MANUAL`
- `STRATEGY`
- `TAKE_PROFIT`
- `STOP_LOSS`
- `KILL_SWITCH`
- `RISK_REDUCTION`

止盈和止损只负责触发普通平仓动作。例如：

```text
TAKE_PROFIT + CLOSE_LONG_SPREAD + LIMIT
STOP_LOSS   + CLOSE_LONG_SPREAD + MARKET
```

Issue #109 只接入人工开仓和人工平仓的 FOK Limit。自动止盈止损仍固定使用 Market，直到后续批次为退出计划保存执行方式。

## 2. 两类可成交方向

四个业务动作在报价与定价层归并为两类。

### 2.1 买 Bybit、卖 MT5

适用动作：

- `OPEN_LONG_SPREAD`
- `CLOSE_SHORT_SPREAD`

可成交价差：

```text
Bybit Ask - MT5 Bid
```

该方向的用户限制是“价差不能高于最大允许值”。

FOK Bybit 最大买入价：

```text
Raw Bybit Buy Limit
= MT5 Bid + Limit Spread - Hedge Reserve

Submitted Bybit Buy Limit
= floor(Raw Price / Tick Size) × Tick Size
```

向下取 Tick，不能因价格舍入放宽用户的最大价差限制。

### 2.2 卖 Bybit、买 MT5

适用动作：

- `OPEN_SHORT_SPREAD`
- `CLOSE_LONG_SPREAD`

可成交价差：

```text
Bybit Bid - MT5 Ask
```

该方向的用户限制是“价差不能低于最小允许值”。

FOK Bybit 最低卖出价：

```text
Raw Bybit Sell Limit
= MT5 Ask + Limit Spread + Hedge Reserve

Submitted Bybit Sell Limit
= ceil(Raw Price / Tick Size) × Tick Size
```

向上取 Tick，不能因价格舍入放宽用户的最小价差限制。

信号可以额外观察中间价差，但成交判断、止盈止损触发和限价换算必须使用对应可成交 Bid/Ask。

## 3. Market 语义保持不变

```text
生成 SyntheticOrderIntent
→ 映射到既有 OPEN_LONG / OPEN_SHORT / CLOSE_LONG / CLOSE_SHORT
→ Bybit 主腿提交并确认真实成交
→ MT5 按 Bybit 实际成交数量与当前合约规格对冲
→ 双边外部持仓核对
→ 明确失败时按既有规则补偿；未知结果不盲目重试
```

以下永久语义不因 FOK 接入而改变：

- Bybit 是第一腿／主腿。
- MT5 是跟随对冲腿。
- Bybit 平仓使用 `reduceOnly` 和匹配的 Position Index。
- MT5 平仓绑定目标 Position Ticket。
- 第二腿明确失败、未知、已受理和外部持仓不一致使用既有不同处置。
- 开仓后必须验证双边目标持仓；平仓后必须验证双边归零。
- Live Write、自动退出监控和临时 1 oz／单生命周期限制保持原状态。
- Market 请求不携带 `limitSpread`，并继续走原 Market executor。

## 4. FOK Limit 执行合同

### 4.1 提交前定价

Limit 请求必须显式提供 `limitSpread`。Platform 在创建 ExecutionBatch 前：

1. 读取 Bybit 与 MT5 当前 Bid/Ask；
2. 计算对应方向的当前可成交价差；
3. 验证当前价差已经满足用户限制；
4. 读取 Platform 版本化 Contract Specification 的 Bybit `priceTick`；
5. 应用 `VG_CROSS_SPREAD_LIMIT_HEDGE_RESERVE_PRICE`；
6. 按方向进行保守 Tick 舍入；
7. 生成 Bybit FOK Limit 价格。

若当前可成交价差不满足限制，返回 `409`，不创建 Batch，不提交任何 Venue 订单。

Hedge Reserve 默认是 `0`。受控主机必须依据真实 MT5 Broker 的滑点证据配置非负值；工程代码不猜测经纪商滑点。

当前提交价格使用 Platform 版本化 `ContractSpecification.priceTick`。真实 Bybit Instrument Tick 与 Platform 合同一致性仍必须在 Issue #39 的只读验收中核对；CI 不证明真实交易所规格。

### 4.2 Bybit 终态

跨所价差 Limit 主腿提交：

```text
orderType=Limit
timeInForce=FOK
```

只有同时满足以下条件才产生 Platform Fill 并允许 MT5：

- Bybit Order 达到终态 `Filled`；
- 累计成交量等于请求量；
- 平均成交价格有效。

### 4.3 零成交

Bybit FOK 被取消且累计成交量为零：

- 生成明确拒单事件；
- ExecutionBatch 结束为失败；
- 不提交 MT5；
- FOK 开仓不创建退出计划；
- FOK 人工平仓释放原子 Claim，退出计划恢复 `active`，允许用户重新报价。

### 4.4 部分成交、数量不一致或未知结果

以下结果不能按正常 FOK 处理：

- 取消时累计成交量大于零；
- Bybit 报告 `Filled`，但累计成交量与请求量不一致；
- 终态确认超时；
- Query 或 Place 结果未知。

处理原则：

- 不生成可驱动 MT5 的正常 Fill 事件；
- 不自动提交 MT5；
- ExecutionBatch／退出计划进入对账或人工介入；
- 不把未知结果解释为零成交；
- 不自动重试原业务意图。

### 4.5 全部成交

Bybit FOK 全部成交后：

- ExecutionBatch 读取实际 Bybit Fill 数量；
- 按当前 MT5 Contract Size、最小量和 Step 重新计算 MT5 lot；
- 提交一笔 MT5 Market 对冲；
- 开仓完成后验证双边目标持仓；
- 平仓完成后验证双边目标持仓归零；
- 第二腿明确失败时继续使用既有补偿／人工接管规则。

## 5. API 定价证据

Limit Open/Close 响应附加 `limitExecution`：

```json
{
  "direction": "BUY_BYBIT_SELL_MT5",
  "limitSpread": "-0.8",
  "executableSpread": "-0.9",
  "mt5ReferencePrice": "2501.0",
  "hedgeReserve": "0",
  "bybitTickSize": "0.1",
  "rawBybitLimitPrice": "2500.2",
  "bybitLimitPrice": "2500.2",
  "currentlyExecutable": true,
  "timeInForce": "FOK"
}
```

该证据说明 Platform 如何得到提交价，不代表真实 Venue 已成交。真实 Order、Execution、Deal 和 Position 仍以 Runtime/Venue 证据为准。

## 6. 分批状态

### Batch 1：统一合成指令模型——已完成

- 权威 `action / executionType / triggerReason`。
- 人工开仓、人工平仓、止盈和止损触发路径统一生成该模型。
- Market API 附加标准化 `orderIntent`。

### Batch 2：FOK 价差限价——Issue #109

- 用户输入价差限制，而不是固定 Bybit 单边价格。
- 两类可成交方向与保守 Tick 换算。
- Bybit FOK 终态全成交确认。
- 全成交后按实际数量执行 MT5 Market。
- 零成交、部分成交和未知结果使用不同状态语义。
- 人工开仓和平仓支持 Market / FOK Limit。
- 自动 TP/SL 仍使用 Market。

### Batch 3：止盈止损复用执行选择

- 退出计划保存止盈执行方式和止损执行方式。
- 人工平仓、止盈、止损调用同一个 Close Action。
- 第一阶段默认：止盈可选择 Limit，止损默认 Market。
- 不新增“止盈订单类型”或“止损订单类型”。

### Batch 4：PostOnly Chase

- Bybit Private Order WebSocket。
- Bybit Private Execution WebSocket。
- PostOnly 创建、改单、撤单与成交竞态状态机。
- 自动追单和手动追单。
- TTL、改单阈值、最大追单次数、冷却与重挂条件。
- 部分成交后的精确 MT5 映射或 Bybit 补偿。

IOC 只保留为后续接口，不在当前 1 oz 阶段默认开放。

### Batch 5：执行保护与复盘

- Bybit／MT5 Quote Age。
- 跨 Venue 时间差。
- 双边 Bid/Ask 宽度。
- MT5 Deviation 与真实成交滑点。
- 最大未对冲时长及分级告警。
- 目标价差、下单时可成交价差、真实成交价差和偏差。
- Bybit Maker/Taker、真实手续费、MT5 Commission、Swap、Funding 和执行成本拆分。
- 开仓 Fail Closed；平仓按风险降低原则使用独立、更宽但有限的保护阈值。

## 7. 交易执行页面

当前页面支持：

```text
开仓动作：开多 / 开空
人工平仓：平多 / 平空
执行方式：市价 / FOK 限价
数量：oz
限制价差：Limit 时必填
```

FOK 返回后展示：

- 两类执行方向；
- 限制价差与下单时可成交价差；
- Bybit FOK 提交价；
- MT5 参考价；
- Bybit Tick Size；
- MT5 Hedge Reserve。

PostOnly 追单、改单状态、真实成交价差、两腿延迟和费用复盘属于后续批次。

## 8. 本地实盘边界

CI 只能证明类型、映射、状态和安全分支，不能证明真实 Bybit／MT5 权限、Broker 字段、Terminal 稳定性、流动性、Tick 一致性和成交质量。

所有核心批次工程完成后，Issue #39 仍按以下顺序执行：

1. Live Write 全部关闭的只读核对。
2. 当前订单、历史订单、Fill／Deal、Position 和 Account Risk 核对。
3. 核对真实 Bybit Tick、数量 Step 与 Platform Contract Specification。
4. 配置并记录 MT5 Hedge Reserve 证据。
5. 受控 1 oz Market 测试。
6. 受控 1 oz FOK Limit 测试，包括全成交、零成交和异常结果演练。
7. PostOnly／追单只在 WebSocket、部分成交和补偿证据成熟后测试。
8. 多轮干净 EOD 和无未解释 Difference 后，才复审临时限制。
