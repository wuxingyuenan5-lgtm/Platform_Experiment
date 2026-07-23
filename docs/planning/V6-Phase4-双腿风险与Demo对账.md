# V6 Phase 4：双腿风险处置、Demo 执行与日终对账

状态：`Phase 4A implemented / 4B-4D in progress`  
实施分支：`hardening/v6-phase4-demo-risk-reconciliation`  
跟踪 Issue：`#12`  
更新时间：`2026-07-23`

## Phase 4A 已实现

- ExecutionBatch 最大腿间延迟、最大残留名义敞口、禁止部分成交和自动修复参数。
- 第一腿成交、第二腿失败时，按实际 Fill 数量生成反向 `reduceOnly + FOK` 修复命令。
- 修复成功状态为 `compensated`；修复失败状态为 `risk_unresolved`，自动开启 Strategy Kill Switch。
- Global、Strategy、Account Kill Switch。
- 幂等人工处置：flatten、hold-and-escalate、mark-resolved。
- Demo 与 Live 独立门禁，默认均关闭；Phase 4 永不允许 Live。

## 后续同一 Phase 4 分支

- 4B：外部订单、成交、持仓和余额主动查询及 FinancialFact 导入。
- 4C：Bybit Demo 与 MT5 Demo 正式适配器。
- 4D：日终对账差异对象和演练。
