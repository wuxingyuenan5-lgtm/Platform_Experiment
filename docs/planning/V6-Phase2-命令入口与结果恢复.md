# V6 Phase 2：命令入口与结果恢复

状态：`completed`  
代码基线：`main@27b9c19aa2a213ab00b53d736508670dd0d09db4`  
实施分支：`hardening/v6-command-recovery-phase2`  
Pull Request：`#5 Unify V6 trade commands and recover uncertain orders`  
跟踪 Issue：`#4 V6 Phase 2：统一 TradeCommand、恢复 result_unknown、前端动态 Catalog`  
总计划：`#2 V6 main：交易安全、可靠执行与账务正确性落地计划`  
验收 CI：`Platform CI #98 / run 29986397987`  
更新时间：`2026-07-23`

## 1. 目标

Phase 1 已解决交易输入 fail-closed 和 Runtime command 原子抢占。Phase 2 继续解决三个核心问题：

```text
业务写入口必须统一
+
结果未知必须恢复而不是重下
+
前端必须使用后端权威 Catalog
```

本阶段完成后仍只允许 Simulation / Fake Gateway，不开放 Paper 或 Live。

## 2. 权威交易链路

正式单腿链路：

```text
Frontend / Internal Caller
→ POST /api/v1/trading/commands
→ TradeCommand（强制 idempotencyKey）
→ Strategy / Account Binding / Instrument / Contract 校验
→ Order
→ Runtime Command
→ Runtime Journal
→ Gateway
→ Runtime Events
→ Order / Fill / Position / PnL Projection
```

正式双腿链路：

```text
Frontend
→ POST /api/v1/trading/execution-batches
→ ExecutionBatch（强制 batch idempotencyKey + strategyInstanceId）
→ 每条 Leg 生成独立 TradeCommand
→ leg idempotencyKey = batch idempotencyKey + role
→ Runtime / Gateway
→ 双腿 Order / Fill
→ Batch 状态
```

`POST /api/v1/trading/orders` 仅作为兼容入口保留，并已在 OpenAPI 中标记为 deprecated。新业务代码不得继续调用该入口。

## 3. TradeCommand 与 ExecutionBatch 规则

### 3.1 TradeCommand

创建前必须满足：

- StrategyInstance 存在且状态为 `active`。
- StrategyDefinition 的 V1 范围为 `closed_loop`。
- Account 与 StrategyInstance 存在 `active` 绑定。
- Account 状态为 `active`。
- Instrument 与 ContractSpecification 存在。
- 订单继续通过 Phase 1 的数量、价格、凭证与 Live 门禁校验。

TradeCommand 使用数据库唯一 `idempotency_key` 原子认领。重复请求仅在业务载荷完全一致时返回已存在命令；同一幂等键携带不同 Strategy、Account、Instrument、方向、订单类型、数量或价格时返回 409，不创建第二个 Order。

### 3.2 ExecutionBatch

- `idempotencyKey` 必填。
- `strategyInstanceId` 必填。
- `strategyKey` 必须与 StrategyInstance 一致。
- 两条腿在创建 Batch 前完成全部 Catalog 预校验，避免第一腿成交后才发现第二腿基础配置无效。
- Batch 通过数据库唯一键原子认领。
- 每条腿必须经过 TradeCommand，不允许直接生成随机 command 调用 Runtime。
- 重复 Batch 仅在 Batch 和所有 Leg 载荷完全一致时返回已有结果；同一幂等键对应不同方向、账户、标的、数量、价格或 Leg 配置时返回 409。

## 4. result_unknown 恢复

新增接口：

```http
POST /api/v1/trading/orders/{orderId}/reconcile
```

恢复流程：

```text
读取本地 Order
→ 仅处理 result_unknown
→ GET Runtime /commands/{commandId}/events
→ 校验 command_id 与 platform_order_id
→ 重放已持久化事件
→ 更新 Order / Fill / Position / PnL
→ 同步 TradeCommand 状态
```

安全规则：

- 恢复接口不会再次提交订单。
- Runtime 不可用或尚无事件时，Order 保持 `result_unknown`。
- Runtime event 身份与本地 Order 不匹配时返回上游错误，不写入投影。
- 相同 Fill event 重放时，`fills.id` 去重成功前不更新 Position、EconomicEvent 或 PnL。

当前恢复来源仅为 Runtime Journal。交易所／MT5 外部查单、查成交和查持仓属于后续阶段。

## 5. 前端动态 Catalog

资费套利执行面板已移除旧 Demo UUID 硬编码，启动时读取：

- StrategyInstance。
- StrategyAccountBinding。
- Account。
- Instrument。
- ContractSpecification。

仅在以下条件全部满足时开放提交按钮：

- 找到 `funding_arbitrage` 的 active Simulation 策略实例。
- 找到 active Simulation 绑定账户。
- 当前资产同时存在 `{SYMBOL}USDT` 与 `{SYMBOL}USDT-PERP`。
- 两个 Instrument 均存在 ContractSpecification。

Catalog 缺失时显示明确错误并禁止提交；缺失持仓和 PnL 显示 `—`，不再伪装为零。

## 6. 工程与测试

新增或强化：

- Runtime event identity 校验。
- Fill replay 幂等测试。
- `result_unknown` 恢复成功测试。
- Runtime 无事件时保持未知测试。
- ExecutionBatch 生成两条 TradeCommand 测试。
- Batch 重复请求不产生额外 Runtime 调用测试。
- TradeCommand 和 ExecutionBatch 幂等键载荷冲突测试。
- Smoke Script 改为使用权威 Strategy、Account、Instrument 与 TradeCommand。
- CI 严格覆盖 Phase 2 后端文件、全量 Pytest、前端 Type Check 和 Production Build。
- 权威 Markdown 变化纳入 CI 触发范围，确保代码和工程口径一起验收。

## 7. 明确延期

Phase 2 不处理：

- Bybit 或 MT5 真实／Demo 下单适配器。
- 外部 Venue 主动查单恢复。
- 正式 Funding、Swap、Fee、FX、Contract Multiplier PnL。
- 多账户同一估值时点 NAV。
- 双腿失败后的自动反向平仓、临时对冲和 Kill Switch。
- 用户认证、RBAC 和双人审批。

## 8. 验收记录

验收 CI：`Platform CI #98 / run 29986397987`

| 检查 | 结果 |
|---|---|
| Platform Backend Phase 2 strict Ruff Gate | 通过 |
| Platform Backend 全量 Ruff | 通过 |
| Platform Backend 全量 Pytest | 通过 |
| Execution Runtime strict Ruff Gate | 通过 |
| Execution Runtime 全量 Ruff 与 Pytest | 通过 |
| Frontend frozen-lockfile install | 通过 |
| Frontend strategy type-check | 通过 |
| Frontend production build | 通过 |
| TradeCommand / Batch 载荷一致性和冲突测试 | 通过 |
| Runtime Journal 恢复与 Fill 重放幂等测试 | 通过 |
| 代码、测试、API Spec、Release Gate、README、START-HERE、Changelog 一致性 | 通过 |

## 9. 下一阶段

Phase 3 聚焦金融事实与账务正确性：

1. 外部 Order／Fill／Deal／Funding／Swap／Fee／Balance／Position 不可变事实层。
2. ContractSpecification、Currency、Unit 和 FX 进入正式 PnL。
3. StrategyNavSnapshot 按同一估值时点汇总全部绑定账户。
4. 所有投影可由事实重新构建和核对。
