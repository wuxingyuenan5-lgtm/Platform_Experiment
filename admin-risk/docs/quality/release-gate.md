# Platform V6 最小发布门槛

状态：`active`  
适用基线：`main / Platform V6`  
总体计划：`../../../docs/planning/V6-交易安全加固实施计划.md`  
当前阶段：`../../../docs/planning/V6-Production-Gate-身份权限与实盘会话.md`

## 1. 目的

建立可重复、可审计的工程与运营门槛。涉及身份、权限、交易、账户、执行、风险、Live Adapter、FinancialFact、PnL、NAV、Venue Query、Reconciliation、EOD Report 或部署的变更，不能只凭页面效果或“接口能调用”判断完成。

必须区分：

- 工程验收：代码、离线 Provider Contract Tests、金样本、CI 和 Markdown。
- 运营验收：真实账户只读、双人批准、最小仓位写入、Kill Switch 演练和多个清洁日终周期。

工程验收通过不自动授予实盘写入权限，也不允许提高资金、仓位、品种或自动化频率。

## 2. 自动检查

### Frontend

```bash
cd admin-risk
pnpm sync:trading-tools
pnpm type:check
pnpm build
```

### Platform Backend

```bash
cd platform-backend
python -m ruff check app tests
python -m pytest
```

严格 Gate 至少覆盖：

- Authentication、Principal、RBAC 和安全审计上下文。
- LiveTradingSession 申请、批准、撤销、过期和原子额度认领。
- TradeCommand、ExecutionBatch、Execution Risk。
- FinancialFact 与 Formal Accounting。
- Venue Reconciliation、Live Economic Event Import 和 EOD。
- Phase 1–4D 全部安全、恢复、账务、实盘适配器和对账回归。

### Execution Runtime

```bash
cd execution-runtime
python -m ruff check app tests
python -m pytest
```

严格 Gate 至少覆盖 Journal、Gateway、Live Safety、Account Route、Bybit Live、MT5 Live、Secret Resolver 及全部 Runtime 回归。

### Repository Secret Scan

```bash
python scripts/scan-secrets.py
```

必须阻断：

- 私钥块。
- 常见 GitHub、AWS、OpenAI、Slack 等 Token 形式。
- 受控 Secret 字段中的高熵明文值。
- 未审核的 tracked `.env*` 文件。

审核过的 `admin-risk/.env*` 只允许公开 `VITE_*` 浏览器配置，仍接受 Token 和高熵内容扫描。扫描器自身 regex 源文件可以单独跳过，其他源码、测试、文档和配置不得整体排除。

### GitHub Actions

- `main`、`hardening/**` 和面向 `main` 的 PR 必须触发 Platform CI。
- Secret Scan 必须作为独立可诊断 Workflow 和 Platform CI 阻断 Job。
- Backend、Runtime、Frontend、Repository Safety 全部通过后才允许合并。
- 失败日志保留短期 Artifact。
- README、START-HERE、Release Gate、Planning、Technical、Operations、API Spec 和 Changelog 变化必须触发 CI。
- 不允许强推 main 绕过检查。

## 3. Authentication 与 Principal

Live 环境必须确认：

- 只允许 Production Authentication 模式；development identity 被拒绝。
- 除无业务数据 `/health` 外，匿名请求返回 401。
- Bearer Token 只以 SHA-256 哈希匹配，不在仓库、数据库、日志、响应或审计中保存原文。
- Credential 必须 active，User ID、Role 和 Credential ID 明确。
- Request ID 由可信 Header 或服务端生成并回传。
- Source IP 可用时进入安全上下文。
- 认证配置错误、未知 Credential 和停用 Credential 全部 fail-closed。

## 4. RBAC 与 Actor Binding

最小角色：viewer、researcher、trader、risk_officer、operations、admin。

必须确认：

- 未知 Permission 和未知 Role 默认拒绝。
- viewer 不能下单、读取审计、修改风险或批准实盘会话。
- trader 可以申请会话和提交交易，但不能批准自己的会话。
- risk_officer 可以操作 Kill Switch、风险处置、差异/EOD 复核和批准/撤销会话。
- operations 可以执行事实导入、对账和 EOD，但不能替代风险批准。
- admin 不能绕过 Applicant/Approver 分离。
- 请求体中的 actor、reviewer 等字段必须与认证 Principal 一致。
- 任何 Actor mismatch 返回 403，并有安全审计记录。

## 5. LiveTradingSession

正式 Live Command 必须依赖一个且仅一个有效会话。

会话必须固定：

- Session Type。
- StrategyInstance。
- Account。
- Symbol、Side、Order Type allowlist。
- Starts At 与 Ends At。
- Max Order Notional 与 Max Daily Notional。
- Read-only Verified At 与 Evidence Reference。
- Applicant、Approver、Reason 和 Payload Hash。

批准门禁：

- Applicant 与 Approver 必须不同。
- Platform 绝对单笔/单日限额必须显式且大于零。
- 申请限额不得超过平台绝对限额。
- Global、Strategy、Account Kill Switch 均关闭。
- 无 Open 或 Accepted Reconciliation Difference。
- 无时间重叠 Approved Session。
- existing_limits 必须有最新 clean EOD。
- scale_change 必须经过独立扩大规模评审；当前默认禁用。

认领门禁：

- 会话为 approved 且处于有效时间窗口。
- Strategy、Account、Symbol、Side、Order Type 完全匹配。
- Live Limit Order 使用明确正价格计算 Notional；无法确定价格时 fail-closed。
- 单笔限额通过。
- 单日累计限额使用 SQLite `BEGIN IMMEDIATE` 进行并发安全认领。
- Claim 以 Command ID 幂等；同 ID 不同载荷返回 409。
- Claim 成功后才允许写入 Order 并调用 Runtime。
- 会话撤销或过期后立即失效。

并发金样本必须证明：两个同时到达、单独合法但合计超限的 Command，只能有一个认领成功。

## 6. TradeCommand 与 ExecutionBatch

- 正式写入口只有 TradeCommand 和 ExecutionBatch。
- 业务级幂等键必填。
- Strategy、active Binding、Account、Instrument、ContractSpecification 必须有效。
- 数量、价格和步长合法。
- Platform Live Gate 默认关闭。
- 每个 Batch Leg 生成独立 TradeCommand。
- StrategyInstance 身份必须传递到 Runtime。
- 相同幂等键不同载荷返回 409。
- Deprecated `/trading/orders` 不得作为 Live 写入口。
- Live Command 必须额外通过 Production Authentication、RBAC 与 LiveTradingSession Claim。

## 7. Runtime Command 幂等与双重门禁

- Runtime 在 Gateway 副作用前原子抢占 command_id。
- 重复 Command 返回持久化事件。
- 已认领但无事件时不重复调用 Gateway。
- Runtime 重启后 Journal 可恢复。
- Runtime LiveWriteClaim 在 SQLite 原子事务中认领。
- Command 载荷冲突拒绝。
- Query API 不得调用 submit_order。
- Runtime `environment=live`、`liveWriteEnabled=true`、Account/Strategy/Symbol allowlist 和正数 Notional Limit 必须全部满足。
- 任一条件无法确认时 fail-closed，不得自动回退 Fake Gateway。

## 8. Result Unknown

- 同步 ACK 不等于成交。
- Venue 明确拒绝与结果未知分开处理。
- 可能已到 Venue 但无法确认时，Platform 标记 `result_unknown`。
- `result_unknown` 不得直接重下。
- 第一层查 Runtime Journal，第二层查 Venue Order 与 Fill/Deal。
- 外部仍查不到时生成 Difference。
- External Fill/Deal ID 必须作为稳定事实身份。

## 9. Kill Switch 与 Execution Risk

- Global、Strategy、Account Kill Switch 在会话批准、Command Claim、Batch 认领和每腿执行前检查。
- 命中后不能产生新增风险。
- Batch 固化腿间延迟、残留名义敞口和失败处置策略。
- `failed` 不等于风险解除。
- 自动平仓和替代对冲必须通过 TradeCommand。
- RiskAction 重放不得重复下单。
- 风险状态、动作、操作人和原因进入 AuditEvent。

## 10. Bybit、MT5 与 Venue Query

### Bybit

- 使用 V5 Unified Trading API。
- `orderLinkId` 由 Platform Order ID 确定性派生。
- Place-order ACK 只生成 acknowledged，不生成虚假 Fill。
- Open Orders、History、Execution、Position、Wallet 和 Transaction Log 可查询。
- Execution ID、Funding ID 和 Fee ID 稳定且可幂等导入。
- API Key 和 Secret 不进入响应、日志和审计。

### MT5

- 非 Windows 或无可用 Terminal 时 fail-closed。
- AccountInfo login 与配置账号一致。
- 下单前执行 `order_check`，写入使用 `order_send`。
- Order、Deal、Position、Balance、Equity、Margin 可查询。
- Magic、Comment、Order/Deal/Position Ticket 可追溯。
- Swap、Commission 和 Fee 从外部 Deal 字段导入。
- Password 和 Server 不进入响应、日志和审计。

### Query 与 Difference

- Query 与 Command 分离。
- Query 失败不得返回伪造空仓或零余额。
- External Order、Fill/Deal、Position、Balance、Funding、Swap 和 Fee 使用稳定外部身份。
- 重复导入不得重复改变 Position、PnL 或 NAV。
- 外部与本地冲突形成 Reconciliation Difference，不无痕覆盖。
- `accepted` 不表示数据一致；Open 与 Accepted Difference 均阻断会话批准和扩大实盘。

## 11. EOD Report

必须确认：

- Business Date、IANA Timezone、Valuation Time 和 Due At 显式。
- 订单范围包括业务日期窗口和仍未终结的历史订单。
- Order、Execution/Deal、Position、Balance、Funding、Swap、Fee 全部进入编排。
- FinancialFact 导入后重建 Formal Position/PnL。
- Formal NAV 使用统一 Valuation Time。
- 外部调用失败进入 errors，不生成虚假 complete。
- Open/Accepted Difference、Skipped Event、Missing Account 和 Incomplete PnL 均阻断扩大实盘。
- 人工复核不可变。
- 只有 clean report 可以标记 `approved_same_limits`。
- `approved_same_limits` 不提高限额，不开启 Live Write。

## 12. 前端与产品界面

- Simulation 与 Live 明确区分。
- Catalog、Auth、Session 或 Gateway Capability 不完整时禁用提交。
- Live Write 关闭、未认证或无 Approved Session 时不得显示为可执行。
- 缺失 Position、PnL、Risk、Venue、Difference、EOD 或 Session 状态展示 `—` 或未知。
- 产品页面不展示开发说明、实现解释或联调备注。

## 13. 文档一致性

涉及身份、权限、交易、风险、Live Adapter、EOD、PnL、NAV、API、部署或运营门禁时，必须同步更新：

- 实施计划。
- 技术设计。
- API Spec。
- README。
- START-HERE。
- Release Gate。
- Changelog。
- Issue 与 Pull Request。

## 14. 阻断条件

任一情况存在，不得合并、开启 Live Write 或扩大实盘：

- 任一 CI Job 或 Secret Scan 失败或未执行。
- Live 环境允许匿名或 development identity。
- Permission 未默认拒绝。
- Actor 可由请求体冒充。
- Applicant 可以批准自己的会话。
- 无 Approved Session 可以进入 Runtime。
- 会话范围、时间或限额可以被绕过。
- 并发 Command 可以共同穿透单日额度。
- Live Write 默认开启。
- Platform 或 Runtime 任一道门禁可被绕过。
- Kill Switch、Open/Accepted Difference 或 EOD Block 未阻断会话。
- 同步 ACK 被视为成交。
- `result_unknown` 会重下原订单。
- Query 失败被解释为空仓、零余额或 clean EOD。
- 重复外部事实导致重复记账。
- 缺失 Account、FX、PnL 或 NAV 被补零。
- Secret 出现在仓库、日志、截图、Markdown、审计或响应。
- active Markdown 与实现不一致。

## 15. 真实账户运营验收

必须人工留痕：

- Bybit 只读订单、成交、持仓、余额、Funding。
- MT5 只读 Order、Deal、Position、Balance、Swap。
- trader 申请、独立 risk_officer 批准最小仓位窗口。
- 最小允许仓位受控下单、撤单、查询和事实导入。
- Kill Switch、断网、Runtime 重启、`result_unknown` 演练。
- 每个真实测试日形成 EOD Report。
- 连续多个真实日终周期无未解释差异。
- 测试结束后 Session、Write Gate、Notional Limit 和临时 allowlist 强制复位。

运营验收前 `liveWriteEnabled=false`。即使运营验收通过，也必须进入独立扩大规模评审。