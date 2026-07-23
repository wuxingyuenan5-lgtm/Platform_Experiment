# 人工阅读入口

状态：`active`  
产品基线：Platform V6  
架构版本：Platform V6 Simplified  
适用分支：`main`  
当前实施：Phase 2 命令入口与结果恢复  
文档层级：人工阅读入口

找文档先看项目根目录 `00-人工可读目录/README.md`。  
继续工程实施先看：

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Phase2-命令入口与结果恢复.md`
3. `quality/release-gate.md`

## 1. 当前一句话结论

```text
Phase 1：交易输入 fail-closed + Runtime command 原子抢占，已完成
+
Phase 2：TradeCommand 正式入口 + result_unknown 恢复 + 动态 Catalog，正在验收
+
Phase 3：金融事实、PnL 和 NAV 正确性，尚未开始
+
Phase 4：双腿风险处置、Bybit Demo、MT5 Demo 和日终对账，尚未开始
```

当前系统仍只允许 Simulation / Fake Gateway。Paper、Demo 和 Live 必须逐阶段验收，不能因页面存在执行按钮就解释为可实盘。

## 2. 先读这 10 篇

1. `../../docs/planning/V6-交易安全加固实施计划.md`
2. `../../docs/planning/V6-Phase2-命令入口与结果恢复.md`
3. `modules/一级模块定位总表.md`
4. `modules/策略-需求文档.md`
5. `modules/交易平台-需求文档.md`
6. `modules/策略管理-需求文档.md`
7. `architecture/platform-target-architecture.md`
8. `architecture/domain/domain-overview.md`
9. `architecture/reference-code-adoption-matrix.md`
10. `planning/V1-开发路线图.md`

## 3. 当前工程优先级

| 顺序 | 主题 | 状态 |
|---|---|---|
| 1 | Fail-closed、Runtime 幂等、CI、文档留痕 | 已完成 |
| 2 | TradeCommand、ExecutionBatch 幂等、`result_unknown` 恢复、动态 Catalog | 实现完成，验收中 |
| 3 | 外部事实层、ContractSpecification、PnL/NAV 重构 | 待实施 |
| 4 | 残腿处置、Bybit Demo、MT5 Demo、日终对账 | 待实施 |
| 5 | 新策略和新功能扩展 | 暂缓 |

## 4. 当前正式交易入口

单腿：

```http
POST /api/v1/trading/commands
```

双腿：

```http
POST /api/v1/trading/execution-batches
```

结果未知恢复：

```http
POST /api/v1/trading/orders/{orderId}/reconcile
```

`POST /api/v1/trading/orders` 仅为 deprecated 兼容入口，新代码不得继续使用。

## 5. 命令与恢复底线

- TradeCommand 必须有 `idempotencyKey`。
- ExecutionBatch 必须有 `idempotencyKey` 与 `strategyInstanceId`。
- 每条 Batch Leg 必须通过独立 TradeCommand。
- StrategyInstance 必须 active 且属于 V1 closed-loop。
- Account 必须 active 且与 StrategyInstance 存在 active binding。
- Instrument 和 ContractSpecification 必须存在。
- Runtime event 的 command_id 和 platform_order_id 必须与本地记录一致。
- 相同 Fill event 重放不得重复改变 Position 和 PnL。
- `result_unknown` 只能查询恢复，不得重新下单。
- Runtime 没有事件时必须继续保持未知。

## 6. 前端 Catalog 规则

交易页面不得硬编码正式账户、策略实例和 Instrument UUID。资费套利面板必须从 Backend 获取：

- StrategyInstance。
- StrategyAccountBinding。
- Account。
- Instrument。
- ContractSpecification。

如果当前资产没有同时配置现货和永续合约，按钮必须禁用并显示缺失原因。缺失持仓和 PnL 显示 `—`，不能显示伪造的零。

## 7. 策略模块 V1 口径

| 策略 | V1 定位 | 当前要求 |
|---|---|---|
| 资费套利 | 完整闭环 | 行情、命令、订单、成交、持仓、Funding／费用、PnL、固定时间净值 |
| 跨所价差 | 完整闭环 | Crypto 腿、MT5 腿、Order／Deal、持仓、Swap／费用、PnL、净值 |
| 海内外价差 | 分析／模拟／预留 | 不做正式汇率损益、CTP 和完整四层 PnL |
| 抄底 | 管理入口 + 占位 | 暂不做完整 Signal、TradeCycle 和订单自动归属 |
| 短线交易员 L/W | 管理入口 + 占位 | 暂不做完整违规记录、风险额度和正式归因 |

金融AI分析暂缓研发。

## 8. V1 最小对象

当前优先对象：

- StrategyDefinition / StrategyVersion / StrategyInstance。
- StrategyAccountBinding / Account。
- Instrument / ContractSpecification。
- TradeCommand / ExecutionBatch / Order / Fill / Deal。
- PositionSnapshot / BalanceSnapshot。
- EconomicEvent / PnLResult / PnLAttributionItem。
- StrategyNavSnapshot。

暂缓 Investor、ShareClass、申赎、正式 Fund NAV、完整 Finance Ledger、CTP 和金融AI后端。

## 9. 审视当前版本时必须问

- 所有业务下单是否经过 TradeCommand？
- 重复命令和重复事件是否真正幂等？
- `result_unknown` 是否只恢复而不重下？
- 账户和标的是否来自 Catalog？
- PnL 是否使用合约乘数、币种、单位、Funding、Swap、Fee 和 FX？
- NAV 是否按同一估值时点汇总全部账户？
- 单腿失败后是否有自动处置和 Kill Switch？
- Bybit/MT5 是否真正跑过 Demo，而非只存在接口壳？

当前只有前四项正在达到工程验收；后四项仍属于 Phase 3–4。

## 10. 文档与目录治理

- 当前不要大规模移动运行目录。
- 每个阶段必须有 Issue、分支、PR、实施计划、CI 记录和回滚说明。
- 代码变化同步更新 API Spec、Release Gate、README、START-HERE 和 Changelog。
- DRAFT 和历史文件最后再分批归档，不能在业务口径未稳定时大规模移动。
