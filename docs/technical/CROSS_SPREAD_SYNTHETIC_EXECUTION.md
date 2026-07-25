# Cross-Spread Synthetic Execution Contract

状态：`active`  
当前实现批次：Issue #107 / PR #108  
产品目标：跑通“跨所价差 → 交易执行”页面的核心交易闭环，并在工程完成后进入 Issue #39 的 Windows 本地实盘验收。

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

- `MARKET`：使用已经完成的保护型市价生命周期。
- `LIMIT`：统一限价入口；当前仍 fail-closed，下一批首先实现 FOK 价差限价。

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

## 2. 两类可成交方向

四个业务动作在报价与定价层归并为两类：

### 2.1 买 Bybit、卖 MT5

适用动作：

- `OPEN_LONG_SPREAD`
- `CLOSE_SHORT_SPREAD`

可成交价差：

```text
Bybit Ask - MT5 Bid
```

该方向的价差限制是“不能高于最大允许值”。

### 2.2 卖 Bybit、买 MT5

适用动作：

- `OPEN_SHORT_SPREAD`
- `CLOSE_LONG_SPREAD`

可成交价差：

```text
Bybit Bid - MT5 Ask
```

该方向的价差限制是“不能低于最小允许值”。

信号可以额外观察中间价差，但成交判断、止盈止损触发和限价换算必须使用对应可成交 Bid/Ask。

## 3. 已完成的 Market 语义保持不变

Issue #107 只增加统一意图模型，不重新设计市价执行：

```text
生成 SyntheticOrderIntent
→ 映射到既有 OPEN_LONG / OPEN_SHORT / CLOSE_LONG / CLOSE_SHORT
→ Bybit 主腿提交并确认真实成交
→ MT5 按 Bybit 实际成交数量与当前合约规格对冲
→ 双边外部持仓核对
→ 明确失败时按既有规则补偿；未知结果不盲目重试
```

以下永久语义不因统一模型改变：

- Bybit 是第一腿／主腿。
- MT5 是跟随对冲腿。
- Bybit 平仓使用 `reduceOnly` 和匹配的 Position Index。
- MT5 平仓绑定目标 Position Ticket。
- 第二腿明确失败、未知、已受理和外部持仓不一致使用既有不同处置。
- 开仓后必须验证双边目标持仓；平仓后必须验证双边归零。
- Live Write、自动退出监控和临时 1 oz／单生命周期限制保持原状态。

## 4. Limit 分批计划

### Batch 1：统一合成指令模型

- 权威 `action / executionType / triggerReason`。
- 现有人工开仓、人工平仓、止盈和止损触发路径统一生成该模型。
- 公开 Market API 保持兼容，并附加标准化 `orderIntent`。
- `LIMIT` 在任何 Market 副作用前明确返回不可用。

### Batch 2：FOK 价差限价

- 用户输入价差限制，而不是固定 Bybit 单边价格。
- 根据 MT5 当前可成交报价、Bybit Tick Size 和滑点预留动态换算 Bybit FOK Limit。
- Bybit 全部成交后，MT5 按实际成交量市价对冲。
- 未全部成交则结束，不提交 MT5。
- 覆盖四个业务动作，但底层复用两类价格方向。

### Batch 3：止盈止损与人工平仓复用统一执行入口

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

## 5. 最终交易执行页面目标

页面核心输入：

```text
动作：开多 / 平多 / 开空 / 平空
执行：市价 / 限价
数量：oz
```

选择限价后展示：

- 限制价差。
- 当前可成交价差。
- 动态换算后的 Bybit 限价。
- 限价策略及有效期。
- 追单状态（后续批次）。

退出计划展示：

- 止盈价差与执行方式。
- 止损价差与执行方式。
- Trigger Reason。
- 真实 MT5 Position Ticket。

执行结果统一展示：

- Synthetic Action。
- Execution Type。
- Trigger Reason。
- Bybit 与 MT5 外部订单／成交身份。
- 预期价差与真实价差。
- 两腿延迟、未对冲时间、滑点、费用和最终核对状态。

## 6. 本地实盘边界

CI 只能证明类型、映射、状态和安全分支，不能证明真实 Bybit／MT5 权限、Broker 字段、Terminal 稳定性、流动性和成交质量。

所有批次工程完成后，Issue #39 仍按以下顺序执行：

1. Live Write 全部关闭的只读核对。
2. 当前订单、历史订单、Fill／Deal、Position 和 Account Risk 核对。
3. 受控 1 oz Market 测试。
4. 受控 1 oz FOK Limit 测试。
5. PostOnly／追单只在 WebSocket、部分成交和补偿证据成熟后测试。
6. 多轮干净 EOD 和无未解释 Difference 后，才复审临时限制。
