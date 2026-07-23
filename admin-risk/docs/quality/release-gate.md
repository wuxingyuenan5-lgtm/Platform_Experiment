# Platform V6 最小发布门槛

状态：`active`  
适用基线：`main / Platform V6`  
总体计划：`../../../docs/planning/V6-交易安全加固实施计划.md`  
当前阶段：`../../../docs/planning/V6-Phase3-金融事实与正式账务.md`

## 1. 目的

为以 Vibe Coding 为主的开发方式建立低成本、可重复、可审计的质量门槛。任何涉及交易、账户、持仓、PnL、Runtime、权限或部署的变更，不能只凭页面效果判断完成。

本规范是所有稳定提交和 Pull Request 的最低门槛，不等于完整生产测试体系。

## 2. 自动检查

### 2.1 前端

在 `admin-risk` 目录执行：

```bash
pnpm sync:trading-tools
pnpm type:check
pnpm build
```

要求：

- Markdown 交易工具源与生成数据一致。
- 本次范围无 TypeScript 类型错误。
- 模板、导入、路由、静态资源和正式打包无阻断错误。
- 交易页面不得依赖硬编码的正式账户、策略实例或 Instrument ID。
- 产品页面只展示用户完成业务任务所需的信息、操作和状态。
- 开发说明、实现解释、跳转机制、联调备注和大段辅助文案不得进入正式页面主要视觉层。
- 必要提示应短、准、就近呈现；完整解释进入对应 Markdown 文档。

### 2.2 Platform Backend

在 `platform-backend` 目录执行：

```bash
python -m ruff check app tests
python -m pytest
```

Phase 3 严格 Gate 至少覆盖：

- `app/main.py`
- `app/application.py`
- `app/financial_facts.py`
- `tests/test_financial_facts.py`
- Phase 1–2 交易安全与恢复测试

### 2.3 Execution Runtime

在 `execution-runtime` 目录执行：

```bash
python -m ruff check app tests
python -m pytest
```

### 2.4 GitHub Actions

- `main` push 必须触发 CI。
- `hardening/**` push 必须触发 CI。
- 面向 `main` 的 Pull Request 必须触发 CI。
- 后端、Runtime、前端检查全部通过后才允许合并。
- 不允许通过强制更新 `main` 绕过失败检查。
- 本批次修改文件必须通过严格 Ruff Gate；历史债务可以单独盘点，但不得隐藏。
- `docs/planning/**`、`docs/technical/**`、README、START-HERE、Release Gate 和 Changelog 变化必须触发 CI。

## 3. 交易安全检查

涉及交易写路径时，必须确认：

- 未知账户 fail-closed。
- 未知标的或缺失 ContractSpecification fail-closed。
- 非 `active` 账户禁止下单。
- Account 必须与 StrategyInstance 存在 active binding。
- StrategyInstance 必须 active，且当前策略在 V1 中允许闭环执行。
- 数量满足最小下单量和数量步长。
- 限价满足价格步长。
- Live 账户受全局开关保护，默认关闭。
- 凭证只保存引用，不进入数据库、响应、日志和代码。
- Runtime 在任何外部副作用前原子抢占 command。
- 重复 command 不会产生第二次 Gateway 调用。

任何一项无法确认，不能标记为可交易版本。

## 4. 命令入口与幂等检查

正式业务写入口只有：

```http
POST /api/v1/trading/commands
POST /api/v1/trading/execution-batches
```

必须确认：

- TradeCommand 强制提供 `idempotencyKey`。
- ExecutionBatch 强制提供 `idempotencyKey` 与 `strategyInstanceId`。
- 每条 ExecutionBatch Leg 都生成独立 TradeCommand。
- Leg 幂等键由 Batch 幂等键和 Leg Role 确定性派生。
- Batch 在执行第一条腿之前完成全部腿的 Catalog 预校验。
- 并发相同幂等键只允许一个调用者取得执行权。
- 重复 Batch 不会生成新的 TradeCommand、Order 或 Runtime 调用。
- 相同幂等键对应不同业务载荷时返回 409。
- `POST /api/v1/trading/orders` 仅为 deprecated 兼容入口，新业务不得依赖。

## 5. result_unknown 与事件重放检查

涉及未知结果和恢复时，必须确认：

- `result_unknown` 不得被当作失败后直接重试。
- 恢复接口只能查询 Runtime／外部系统，不能重新提交原订单。
- Runtime 无事件或不可用时继续保持 `result_unknown`。
- Runtime event 的 `command_id` 与 `platform_order_id` 必须匹配本地记录。
- 事件缺失必要身份或时间字段时不得写入投影。
- Fill 只有在去重插入成功后才能更新 Phase 2 Position、EconomicEvent 和 PnL。
- 相同 Fill event 重放不得重复改变持仓和损益。
- 恢复后同步 TradeCommand 与 Order 状态。
- 人工处理和恢复动作必须有审计记录或明确后续任务。

当前仍只支持从 Runtime Journal 恢复；外部 Venue 查单恢复未完成前，不允许真实资金 Live。

## 6. 前端 Catalog 与产品界面检查

交易界面必须：

- 从 Backend 获取 StrategyInstance、StrategyAccountBinding、Account、Instrument 与 ContractSpecification。
- 只允许 active 且符合当前 TradingMode 的策略和账户。
- 不存在完整现货／永续或双腿 Catalog 时禁用提交。
- 明确显示当前 Strategy、Account 与 TradingMode。
- 缺失 Position、PnL、行情或费用显示 `—` 或未知，不自动显示零。
- 不允许通过环境变量或代码内 UUID 绕过后端 Catalog。
- 不展示开发说明、实现解释、跳转机制、联调备注或无业务必要的大段辅助文案。

## 7. Phase 3 FinancialFact 检查

事实入口：

```http
POST /api/v1/financial-facts
GET  /api/v1/financial-facts
```

必须确认：

- FinancialFact 只允许新增，不提供修改和删除业务 API。
- 客户端 `idempotencyKey` 唯一。
- 外部身份 `source + externalId + factType + strategyInstanceId` 唯一。
- 重复身份必须比较规范化载荷内容哈希。
- 身份相同且载荷一致时返回原事实。
- 身份相同但载荷不同必须返回 409。
- StrategyInstance 必须 active 且属于 closed-loop。
- Account 必须 active 且与 StrategyInstance 存在 active binding。
- Instrument 与 ContractSpecification 必须存在。
- Quantity Unit、Settlement Currency 和 Contract Multiplier 必须由后端 Catalog 快照确定。
- 事实必须保存 occurredAt、createdAt、source、externalId 和数据质量状态。
- 重复导入不得重复改变 Position、PnL 或 NAV。

## 8. Phase 3 Formal Position 与 PnL 检查

正式核对入口：

```http
POST /api/v1/strategies/instances/{strategyInstanceId}/financials/rebuild
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-positions
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-pnl
```

必须确认：

- Formal Position 与 PnL 只由 FinancialFact 生成。
- 投影清空后可以从事实完整重建。
- 重建不得修改或删除事实。
- Trade PnL 使用数量、价格、仓位方向和 Contract Multiplier。
- 非基础币种使用事实快照的 FX Rate。
- Stablecoin 不自动等同 USD。
- 缺失 FX 时保留事实但投影标记 `incomplete`。
- PnL 分项保存 Trading、Funding、Swap、Fee、FX 和 Total。
- Fee 使用带符号经济贡献，不与 Trading PnL 混写。
- 重建前后 Position、分项 PnL、Total PnL 和 factCount 一致。
- 旧 `/pnl` 接口不得被产品或文档标记为正式账务。

## 9. Phase 3 Formal NAV 检查

```http
GET  /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots
POST /api/v1/strategies/instances/{strategyInstanceId}/formal-nav-snapshots/run
```

必须确认：

- 调用方明确提供带时区 `valuationTime`，或服务端记录明确的当前 UTC 时间。
- 全部 active StrategyAccountBinding 使用同一 valuationTime。
- 每个账户只使用 `occurredAt <= valuationTime` 的最新 Balance Fact。
- 返回 `requiredAccountCount`、`includedAccountCount` 和 `missingAccountIds`。
- 全覆盖为 `complete`，部分覆盖为 `partial`，无有效覆盖为 `incomplete`。
- 无有效余额时 equity 和 nav 返回空值，不返回零。
- 跨币种余额缺失 FX 时该账户不能被视为有效覆盖。
- 旧 `/nav-snapshots` 接口不得被标记为正式账务。

## 10. 金样本检查

Phase 3 至少保留：

- 一套资费套利成交、Funding、Fee 和 PnL 重建样本。
- 一套包含 Contract Multiplier 的已实现损益样本。
- 一套非基础币种缺失 FX 的 incomplete 样本。
- 一套多账户同一 valuationTime 的 partial／complete NAV 样本。
- 重复事实和载荷冲突样本。

金样本预期值必须写在测试和实施文档中，不依赖人工口头解释。

## 11. 文档一致性

涉及以下变化时，必须同步更新 Markdown：

- 模块职责或架构边界。
- 策略能力和发布范围。
- 交易模式、Gateway 或账户安全规则。
- 状态机、幂等、恢复和对账语义。
- FinancialFact、损益、币种、单位、合约规格、FX 或风险口径。
- API、CI、部署和运行命令。

Phase 3 至少更新：

1. `docs/planning/V6-Phase3-金融事实与正式账务.md`。
2. `docs/technical/FINANCIAL_FACTS.md`。
3. `docs/technical/API_SPEC.md`。
4. `docs/planning/V6-交易安全加固实施计划.md`。
5. `CHANGELOG.md`。
6. 本 Release Gate。
7. README 和 START-HERE。
8. Pull Request、Issue 和验收记录。

普通样式微调可以不更新需求文档，但仍应有清晰提交记录。

## 12. 变更范围检查

提交前确认：

- 没有意外修改一级架构和路由。
- 没有误改归档文档。
- 没有直接修改生成文件作为唯一修改。
- 没有因局部问题重写公共主题。
- 没有顺手删除未确认引用的文件。
- 没有将页面本地状态无理由放入全局 Store。
- 没有将真实凭证、`.env`、数据库文件或运行日志提交到仓库。
- 大规模自动生成变更有来源和验收说明。
- 新增组合入口或文件拆分不改变既有 API 路由和应用生命周期。

## 13. 人工冒烟检查

执行 `smoke-checklist.md` 和根目录 `scripts/smoke-platform.ps1`，并额外检查：

- 后端和 Runtime 健康接口可用。
- Simulation/Fake Gateway 模式明确显示。
- 订单提交前能看到策略、账户、标的和交易模式。
- TradeCommand 与 ExecutionBatch 均返回可查询的幂等标识。
- 失败、处理中、结果未知和需要人工干预不会被展示为成功。
- Catalog 缺失时提交按钮不可用且原因清晰。
- FinancialFact、formal-positions、formal-pnl、formal-nav 路由可访问。
- 重复事实和重建结果符合金样本。
- 正式页面不存在无业务必要性的开发说明、实现解释或联调备注。
- 受影响页面无持续控制台错误。

本次未涉及的模块可以标记为“不适用”，但所有受影响路径必须检查。

## 14. 提交与 Pull Request 要求

一个稳定提交应当：

- 只表达一个清晰主题。
- 不混入无关重构。
- 提交信息说明改了什么。
- 代码、测试、文档在同一批次闭环。

Pull Request 必须写明：

- 基线 commit。
- 风险与影响范围。
- 自动检查结果和 CI Run ID。
- 人工验收结果。
- 回滚方式。
- 未完成和延期内容。

## 15. 阻断条件

存在以下任一情况时，不应合并或发布：

- 任一 CI Job 失败或未执行。
- 构建失败或本次范围类型检查失败。
- 未知账户、标的、绑定或状态可以继续下单或记账。
- 相同 command、batch 或 FinancialFact 可能重复产生外部副作用或重复记账。
- Batch Leg 绕过 TradeCommand。
- `result_unknown` 恢复会重新提交订单。
- 重放 Fill 或 FinancialFact 会重复更新 Position 或 PnL。
- FinancialFact 身份冲突没有返回 409。
- Trading PnL 未使用 Contract Multiplier。
- Stablecoin 被自动当成法币或缺失 FX 被默认按 1:1。
- Funding、Swap、Fee、FX 与 Trading PnL 混为一项。
- Formal Position/PnL 无法从事实重建。
- NAV 使用不同估值时点或缺失账户被静默补零。
- 交易页面继续使用硬编码账户或 Instrument ID。
- 正式产品页面存在无业务必要性的开发说明或大段辅助文案。
- 主要路由无法进入。
- 控制台出现持续性运行错误。
- active 文档与实现存在重大冲突。
- 旧 PnL/NAV 被误标为正式账务。
- Live 开关、凭证或回滚方案不清楚。

## 16. 后续升级

Phase 4 及以后逐步加入：

- 外部 Venue 主动查单、查成交、查持仓和事实自动导入。
- 外部账单解析与逐笔核对。
- Alembic 或等价数据库迁移体系。
- Vitest 纯函数和适配器测试。
- Playwright 核心交易路径自动化。
- Bybit Demo 与 MT5 Demo 端到端测试。
- 双腿残留敞口处置和 Kill Switch。
- 认证、RBAC、CODEOWNERS、分支保护和审批规则。