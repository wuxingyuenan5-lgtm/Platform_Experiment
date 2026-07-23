# V6 Phase 4C：Bybit 与 MT5 受控实盘适配器

状态：`implementation complete / engineering acceptance pending / operational acceptance pending`  
实施分支：`hardening/v6-phase4c-live-adapters`  
跟踪 Issue：`#18 V6 Phase 4C：Bybit 与 MT5 受控实盘适配器`  
上级计划：Issue `#12`、`V6-交易安全加固实施计划.md`  
更新时间：`2026-07-23`

## 1. 变更背景

Bybit 与 MT5 模拟环境不能充分复现实盘账户、成交、Funding、Swap 和券商终端行为，因此本阶段不再建设“伪真的 Demo 壳”，而是建设真实账户的受控接入。

实施顺序固定为：

```text
只读实盘
→ 影子核对
→ 受控写入
→ 最小仓位运营验收
```

受控写入默认关闭。代码实现完成不代表真实资金写入已经获批。

## 2. 架构

```text
Platform TradeCommand / Venue Query
→ Platform Live Gate + Kill Switch
→ Runtime liveWriteEnabled + allowlist + notional limit
→ Account Router
→ Bybit Live Adapter / MT5 Live Adapter
→ Order / Fill / Deal / Position / Balance / Funding / Swap / Fee
→ FinancialFact / Formal Accounting / Reconciliation Difference
```

## 3. 只读实盘

### Bybit

- V5 Unified Trading API。
- 查询实时订单、历史订单、成交、持仓、钱包余额和 Transaction Log。
- Funding 与 Fee 映射为 VenueEconomicEventSnapshot。
- `orderLinkId` 使用 Platform Order ID 确定性派生，不暴露内部 UUID 原文。

### MT5

- Windows MT5 Terminal 与官方 Python Integration。
- 查询 Order、Deal、Position 和 AccountInfo。
- Swap、Commission、Fee 从 Deal 字段导入，不通过价格损益倒推。
- 使用 Magic Number、Comment、Order Ticket、Deal Ticket 和 Position Ticket 建立外部身份。

只读查询失败、凭证缺失、依赖缺失、Terminal 不可用或账户不匹配时必须 fail-closed，不能返回伪造空仓或零余额。

## 4. 受控写入门禁

Runtime 写入必须同时满足：

1. `environment=live`。
2. `liveWriteEnabled=true`；默认 false。
3. Account 位于 allowlist。
4. StrategyInstance 位于 allowlist。
5. Symbol 位于 allowlist。
6. 单笔名义金额不超过 `liveMaxOrderNotional`。
7. 当日累计名义金额不超过 `liveMaxDailyNotional`。
8. Platform Kill Switch 和 Execution Risk Gate 已通过。
9. Command、Platform Order 和外部 client identity 可追溯。
10. 凭证只通过 `secret://...` 解析。

任一条件无法确认，拒绝写入。

## 5. 结果语义

- Venue 明确拒绝或门禁拒绝：生成 `order_rejected`。
- 网络异常或提交后结果无法确认：Runtime 返回错误，Platform 将 Order 标记 `result_unknown`。
- Bybit place-order ACK 只表示请求被接受，不能直接视为成交。
- MT5 `order_send` 返回 Deal 时可以生成 Fill Event；否则仍需主动查询 Order/Deal。
- `result_unknown` 后续必须经过 Phase 4B Venue Reconcile，不得原样重下。

## 6. FinancialFact 导入

新增：

```http
GET  /venue/economic-events
POST /api/v1/ops/live-economic-events/import
```

导入范围：

- Bybit Funding、Fee。
- MT5 Swap、Commission、Fee。

导入使用 External Event ID 作为自然身份，并进入 Phase 3 不可变 FinancialFact。缺少 Instrument 映射的事件显式列入 skippedExternalIds，不伪装为完成。

## 7. 配置隔离

Simulation 与 Live 必须使用不同：

- Account ID。
- Runtime environment。
- Gateway name。
- Journal path。
- Platform database。
- Credential reference。

建议 Live Runtime 仅绑定本机或受控内网地址，不直接暴露公网。

## 8. 工程验收

- [x] Bybit 适配器具备 Order、Fill、Position、Balance、Funding、Fee 查询。
- [x] MT5 适配器具备 Order、Deal、Position、Balance、Swap、Fee 查询。
- [x] Account 确定性路由，不允许一个 Account 同时映射两个适配器。
- [x] 缺凭证、依赖、环境或映射时 fail-closed。
- [x] Runtime Live Write 默认关闭。
- [x] Account、Strategy、Symbol allowlist 生效。
- [x] 单笔和单日名义金额限制生效。
- [x] Bybit orderLinkId 与 MT5 Magic/Comment/Ticket 可追溯。
- [x] StrategyInstance 身份跨 Platform/Runtime 边界保留。
- [x] Funding、Swap 和 Fee 可幂等导入 FinancialFact。
- [x] 离线 Provider Contract Tests 已加入。
- [ ] Platform CI 全部通过并记录 Run ID。
- [ ] PR、Issue、README、API Spec、Release Gate、START-HERE 和 Changelog 完成最终留痕。

## 9. 运营验收

以下验收依赖真实账户、凭证、账户映射、Instrument 映射和人工确认，不能由 CI 替代：

- [ ] Bybit 真实账户完成只读订单、成交、持仓、余额和 Funding 核对。
- [ ] MT5 真实账户完成只读 Order、Deal、Position、Balance 和 Swap 核对。
- [ ] 连续多个日终周期不存在未解释差异。
- [ ] 使用最小允许仓位完成受控下单、撤单、查询和事实导入。
- [ ] Kill Switch 与人工接管演练通过。

运营验收未完成前，`liveWriteEnabled` 必须保持 false。

## 10. 明确延期

- 日终自动调度、SLA、责任人和报告属于 Phase 4D。
- WebSocket 持续状态流可在轮询查询稳定后补充。
- 认证、RBAC、双人审批和生产密钥托管仍未完成。
- 不扩大策略范围，不引入 Kafka、Kubernetes 或复杂微服务。