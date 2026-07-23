# V6 Phase 3：金融事实与正式账务

状态：`implementation complete / acceptance pending`  
实施分支：`hardening/v6-financial-facts-phase3`  
Pull Request：`#8 Build immutable financial facts and formal accounting`  
跟踪 Issue：`#7 V6 Phase 3：不可变金融事实、正式 PnL 与统一估值 NAV`  
总计划：`V6-交易安全加固实施计划.md`  
更新时间：`2026-07-23`

## 1. 本阶段目标

Phase 3 不继续扩张策略和页面，而是建立最小但可审计的正式账务链路：

```text
不可变 FinancialFact
→ ContractSpecification / Currency / Unit / FX 快照
→ 可重复重建的 Position 与 PnL
→ 同一 valuationTime 的多账户 NAV
```

当前仍只允许 Simulation / Fake Gateway，不开放 Paper、Demo 或 Live。

## 2. 不可变事实模型

统一事实表 `financial_facts` 支持：

- `external_order`
- `trade_fill`
- `deal`
- `funding`
- `swap`
- `fee`
- `balance`
- `position`
- `fx`

每条事实必须具有：

- 客户端 `idempotencyKey`
- `source + externalId + factType + strategyInstanceId` 外部身份
- StrategyInstance、Account、Instrument 归属
- 事件时间与入库时间
- 币种、数量、单位、合约乘数和汇率快照
- 内容哈希与数据质量状态

事实只允许新增，不提供更新和删除 API。同一身份只有在载荷完全一致时才返回原记录；载荷冲突返回 `409 Conflict`。

## 3. 正式投影

### 3.1 Position

`formal_positions` 由 Trade Fill / Deal 事实按事件时间重放生成。数量使用 Instrument 的 `quantityUnit`，平均价使用事实价格，重复导入不改变投影。

### 3.2 PnL

`formal_pnl_results` 分项保存：

- Trading PnL
- Funding PnL
- Swap PnL
- Fee PnL
- FX PnL
- Total PnL

Trade PnL 使用成交数量、成交价格和 ContractSpecification 的 `contractMultiplier`。跨币种事实必须携带 `fxRateToBase`；缺失汇率时保留事实，但投影标记 `incomplete`，不得把缺失值当作零或自动把 Stablecoin 当作 USD。

费用使用带符号经济贡献，通常以负数写入。

### 3.3 NAV

`formal_strategy_nav_snapshots` 在调用方指定的同一 `valuationTime` 下，为每个 active binding 账户选择不晚于该时点的最新 Balance Fact。

响应明确返回：

- `requiredAccountCount`
- `includedAccountCount`
- `missingAccountIds`
- `complete / partial / incomplete`

没有任何可用余额时，`equity` 和 `nav` 返回空值，不伪装为零。

## 4. API

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run
```

旧 `/pnl` 与 `/nav-snapshots` 端点暂时保留为工程兼容口径，但不得称为正式投资账务。新开发和内部核对必须使用 `formal-*` 端点。

## 5. 重建与审计

`financials/rebuild` 会清空指定 StrategyInstance 的正式 Position / PnL 投影，再从不可变事实完整重放。事实本身不会被修改。

以下操作写入 AuditEvent：

- FinancialFact 入库
- 正式投影重建
- 正式 NAV 快照创建

## 6. 金样本

资费套利金样本覆盖：

1. 买入 2 单位、卖出 1 单位。
2. Contract Multiplier 设置为 10。
3. 价格从 100 到 110，Trading PnL 应为 100。
4. Funding +5、Swap +2、Fee -1、FX +3。
5. Total PnL 应为 109。
6. 清空投影后重建，Position 与 PnL 必须保持一致。
7. 重复事实不得增加 factCount 或重复计入。

NAV 金样本覆盖两个 active binding 账户：一个账户缺失时状态为 partial；同一 valuationTime 下两个账户余额齐全时状态为 complete。

## 7. 验收清单

- [x] 事实重复导入不重复计入。
- [x] 相同身份不同载荷返回 409。
- [x] Position 和 PnL 可清空后重建。
- [x] Contract Multiplier 进入 Trading PnL。
- [x] Trading / Funding / Swap / Fee / FX 分项可查询。
- [x] NAV 按同一 valuationTime 汇总全部 active binding 账户。
- [x] 缺失账户和汇率显式标记，不自动当零。
- [x] 资费套利金样本覆盖事实、重放、PnL 和 NAV。
- [ ] 最终 Platform CI 通过并记录 Run ID。
- [ ] PR、Issue、Changelog 和总计划完成最终验收留痕。

## 8. 明确延期

Phase 3 不处理：

- Bybit / MT5 主动拉取和自动导入事实。
- 外部账单文件解析器。
- 双腿残留敞口自动平仓和 Kill Switch。
- 用户认证、RBAC、双人审批和生产密钥托管。
- Kafka、Kubernetes 或完整 Event Sourcing 框架。

这些内容进入 Phase 4 或后续运维阶段。