# 创始人手工策略内核统一设计

> 2026-08-23 状态更新：Phase 0–1、跨所价差第三个“移动双边资金”模板和 Funding Phase 2 离线骨架已经提交。近期目标已收敛为：跨所价差实盘交互收尾、跨所与资费共用一个 Bybit UTA 的资源隔离、Funding 剩余数量有界 Chase 与增量配平修复，以及随后的小额受控真号验收。海内外价差暂停；Phase 3–5 不再作为上述真号测试的前置条件。

## 1. 设计结论

Variable-Global 第一阶段不建设通用量化策略平台。目标是稳定支撑少量、由创始人 CEO 手工触发、具有两腿或有限多腿的套利与对冲策略，并让新增第三个同类策略时不必修改共享执行主流程。

保留现有模块化单体 `platform-api` 和独立 `execution-runtime`。不引入微服务拆分、事件总线、动态插件系统、通用工作流引擎、策略常驻进程、自动调度或回测/实盘统一框架。

统一业务链路为：

```text
CEO 手工指令
    ↓
StrategyInstruction（唯一业务意图和审计入口）
    ↓
策略适配器生成不可变 ExecutionPlan
    ↓
ExecutionBatch 按计划执行、恢复和收敛
    ↓
TradeCommand → Execution Runtime → Venue
    ↓
Order / Fill / Position / Economic Event 权威事实
    ↓
Financial Facts + Reconciliation
    ↓
Strategy Read Model → 策略管理页面
```

核心原则是“一次人工指令、一个业务意图、一个受控执行闭环”。改单、撤单、追单和增量对冲都是原指令的子动作，不能生成第二个业务意图。

## 2. 当前问题与修复边界

当前系统已经具备有价值的安全基础：双 Live Write、Kill Switch、幂等键、Execution Batch、Trade Command、Runtime Journal、不可变金融事实、对账以及 `result_unknown` 失败关闭。这些能力继续保留。

需要收敛的问题包括：

1. `StrategyRun`、策略专属路由和通用 Execution Batch 形成多个业务入口，无法明确哪一个对象代表 CEO 的原始意图。
2. `execution_batches.py` 同时负责批次持久化、风险、调度、策略特例和状态收敛，策略差异正在进入共享引擎。
3. 资金费策略已经具备永续优先、Attempt 记录、取消终态确认和原子 Spot 增量 claim 的离线骨架；但跨 Attempt 重挂仍必须严格使用“计划上限减权威累计成交”的剩余数量，并补齐 TTL、mutation、同价重挂、重启和最终对账证据。完成这些聚焦修复前，Funding controlled-live 继续返回 423。
4. 黄金价差、资金费和只读策略账户使用不同的读取与展示拼装路径，前端仍依赖部分样例策略模型。
5. 旧 Catalog 中存在与正式 Trade Command 路径平行的历史实现，容易被新代码误用。
6. AI 测试治理把模拟测试、真实只读、真实交易混为一套审批仪式，导致完整端到端测试被拆成多个授权断点。

本设计只收敛策略业务入口、计划生成、执行编排、统一读模型和测试授权会话。Execution Runtime 的 Venue SDK 所有权、金融账本含义、现有外部合同以及默认关闭 Live Write 不在本次重写范围。

## 3. 产品范围

### 3.1 第一阶段支持

- 黄金跨场所价差：Bybit `XAUTUSDT` 与指定 MT5 黄金品种。
- Bybit 同账户资金费套利：CEO 指定永续空头与现货多头品种和两腿数量；与跨所价差共用同一个真实 Bybit UTA、Platform Account 和凭据引用。
- 跨所价差执行区提供“开仓价差、平仓价差、移动双边资金”三个并列模板；资金模板支持 Bybit 所内与 Bybit TradFi（MT5）之间的双向内部调拨、自动建议金额和结果核对。
- 抄底、短线交易员 A、短线交易员 B：策略管理页只读账户展示。
- CEO 在网页手工提交开仓、平仓和异常处置指令。
- 模拟环境完整自动化开平仓、故障恢复、账本和对账测试。
- 经一次会话授权后的真实只读验证或受控实盘闭环。
- 跨所与资费可以在同一 Bybit UTA 上同步运行，但初创阶段只允许不同 `category + symbol` 资源并发。

### 3.2 明确不做

- 自动选币、自动计算仓位、自动调仓或自动再平衡。
- 根据价差、资金费率或行情条件自动触发交易。
- 无人值守交易、客户资金、多操作者资金管理或生产部署。
- 策略定时器、通用 DAG、动态代码加载、策略插件市场。
- 事件总线、消息队列、微服务化或新的依赖注入框架。
- 为回测与实盘强行建立同一策略接口。
- 海内外价差的交易执行、CTP 接入和真实账户配置；该策略当前保持暂停。
- 同一 Bybit `category + symbol` 被多个策略同时持有或操作；确有业务需求后再建设策略级仓位分配。

## 4. 模块职责

建议在 `platform-api/app/strategies/` 下逐步形成策略边界。目录是迁移目标，不要求第一批提交一次性搬完所有文件。

```text
strategies/
├── domain.py               # 指令、计划、头寸组和状态公共类型
├── instruction_service.py  # 创建、查询和人工处置用例
├── plan_service.py         # 选择策略适配器并冻结计划
├── orchestration.py        # 通用依赖与累计数量释放
├── capital_transfer.py     # 跨所价差内部资金调拨；不属于交易执行批次
├── read_model.py           # 策略页面统一读模型
└── adapters/
    ├── cross_spread.py     # 黄金业务校验和数量换算
    └── funding_carry.py    # 资金费业务校验和比例配平
```

各层职责如下：

| 组件 | 负责 | 不负责 |
| --- | --- | --- |
| 策略适配器 | 校验 CEO 业务参数；解析账户绑定和合约规格；生成不可变计划 | 下单、调用 Venue、保存成交、自动选标的或数量 |
| 通用编排器 | 按依赖提交腿；依据权威累计成交释放后续腿；恢复进度；失败收敛 | 理解黄金、资金费或策略名称；做收益判断 |
| Trade Command | 一次确定的下单意图及幂等身份 | 代表完整策略业务意图 |
| Execution Runtime | Venue SDK、外部副作用、ACK/Fill 区分、Runtime Journal | Platform 策略规则、正式会计和产品状态 |
| Financial Facts / Reconciliation | 不可变金融事实、正式持仓/PnL/NAV、平台与 Venue 差异 | 决定是否开仓或重试外部未知结果 |
| Capital Transfer | 查询两边真实可调拨余额；计算建议金额；执行和核对统一账户内调拨 | 下单、成为策略腿、外部地址提现、建设通用资金调度平台 |
| Strategy Read Model | 向前端提供一致的策略、账户、执行和数据质量视图 | 成为新的金融事实权威 |

共享编排代码不得出现 `if strategy_key == ...`。策略差异必须在冻结计划和数量释放表达式中完成。

## 5. 核心数据模型

### 5.1 StrategyInstance

表示一个可管理的策略实例，继续复用现有 Definition、Version、Instance 和 Account Binding 基础。

只保存稳定属性：

- 策略类型、版本和显示名称；
- `manual` 触发模式；
- `simulation/testnet/live` 交易模式；
- 生命周期状态；
- 账户绑定与 `read_only/trade_and_read` 能力；
- 基础币种、资金基数和数据质量。

本次方向、标的和数量属于 StrategyInstruction，不能写入长期实例配置。

### 5.2 StrategyInstruction

`StrategyInstruction` 是 CEO 一次业务意图的唯一权威对象。现有 `strategy_runs` 应迁移并重命名或语义升级为该对象，不建立长期并行的 Run 与 Instruction 两套模型。

最小字段：

| 字段 | 含义 |
| --- | --- |
| `id` | 平台指令 ID |
| `idempotency_key` | 全局唯一；重复请求必须返回原指令 |
| `strategy_instance_id` | 策略实例 |
| `action` | `open`、`close` 或 `risk_disposition` |
| `position_group_id` | 平仓或处置时必填 |
| `requested_parameters_json` | CEO 原始输入，严格 Schema 校验 |
| `execution_plan_json` | 创建时冻结的计划快照 |
| `execution_batch_id` | 唯一业务批次 |
| `status` | 产品级状态 |
| `requested_by` | CEO 身份 |
| `reason/failure_reason` | 业务原因或失败原因 |
| `created_at/updated_at` | UTC 时间 |

产品级状态保持少而明确：

```text
accepted → executing → reconciling → completed
    │           │             │
    └───────────┴─────────────┴→ manual_intervention
    └→ rejected
executing → failed（仅限确认无外部成交或副作用）
```

`result_unknown` 不是成功或失败状态，而是进入 `manual_intervention` 的原因。任何已产生外部成交但未完成正常配平的指令也进入 `manual_intervention`。

### 5.3 ExecutionPlan

初创阶段不创建通用工作流表。ExecutionPlan 使用版本化 Pydantic Schema 校验后，以不可变 JSON 随 StrategyInstruction 持久化。计划至少包含：

- Schema 版本；
- 策略适配器版本；
- 每条腿的角色、账户、Instrument、外部 Symbol、方向和数量上限；
- 腿的执行顺序和前置依赖；
- `market`、`fok` 或 `post_only_chase` 执行政策；
- `terminal_full_fill` 或 `incremental_cumulative_fill` 后续腿释放条件；
- 后续腿累计释放公式和舍入规则；
- 合约乘数、最小数量和数量步长快照；
- TTL、检查间隔、最大改单/撤单重挂次数；
- 失败后停止、对账或人工处置规则；
- 计划生成时的账户绑定和权限快照。

计划一旦进入 `executing` 不可修改。配置或合约规格变化只影响下一条新指令。

### 5.4 StrategyPositionGroup

新增轻量经济头寸关联对象，用于解决“网页点击平仓时到底关闭哪一组腿”的问题。它不替代正式 Position 或账本。

最小字段包括：

- 策略实例和来源开仓指令；
- 各腿目标数量、已确认开仓数量和已确认平仓数量；
- 外部 Position Ticket 等必要关闭身份；
- `opening/open/partially_open/closing/closed/exception` 状态；
- 关联的开仓、平仓和风险处置指令。

数量必须从权威 Fill/Deal/Position 和对账结果更新，不能由前端或批次状态推断。平仓指令引用 Position Group，由后端计算每条腿最大可平数量，防止超平。

### 5.5 ExecutionBatch 与子对象

复用现有 Execution Batch、Batch Leg、Trade Command、Order、Fill 和运行时身份。Batch 新增或明确以下关联：

- `strategy_instruction_id` 唯一关联；
- 当前计划版本和恢复游标；
- 每条腿 `requested_quantity`、`proven_cumulative_fill`、`released_child_quantity`；
- 需要人工介入和对账的明确原因。

一个 StrategyInstruction 最多拥有一个业务 ExecutionBatch。PostOnly 的 amend 或 cancel-repost、资金费增量现货订单使用确定性子身份留在该 Batch 内。

### 5.6 InternalCapitalTransfer

“移动双边资金”是 Bybit 统一账户体系内的资金调拨，不是 StrategyInstruction、ExecutionPlan 的交易腿或 ExecutionBatch。初创阶段只建立一个轻量记录，用于防止重复划转、展示处理状态和解释余额变化：

- `id`、`idempotency_key`；
- `strategy_instance_id`；
- `direction`：`bybit_to_mt5` 或 `mt5_to_bybit`；
- `currency`、`amount`；
- `status`：`pending`、`completed`、`failed` 或 `result_unknown`；
- 外部 transfer ID、失败原因、`requested_by` 和 UTC 时间。

不引入审批流、任务队列、通用 Treasury 服务或资金工作流。客户端不得提交账户 UID、MT5 Login、API Key 或底层账户类型；后端从跨所价差实例的权威账户绑定解析。

## 6. 通用执行语义

### 6.1 创建和领取

创建指令、冻结计划和声明唯一 Batch 必须在同一数据库事务或等价原子声明中完成。外部副作用只能发生在本地持久化成功之后。

同一幂等键重放时：

- 请求内容相同：返回原指令及当前状态；
- 请求内容不同：返回冲突；
- 不创建第二个 Batch、Trade Command 或 Order。

执行前继续检查 CEO 身份、策略状态、账户能力、LiveTradingSession、双 Live Write、Kill Switch、白名单和全局执行租约。浏览器身份不能绕过这些门。

### 6.2 腿依赖与累计释放

通用编排器只理解以下数据：

```text
dependency_leg
proven_cumulative_fill
release_condition
release_ratio
release_cap
quantity_step
already_released_quantity
```

允许释放的后续腿累计数量为：

```text
min(
  floor_to_step(proven_cumulative_fill × release_ratio),
  release_cap
) - already_released_quantity
```

小于或等于零时不创建子命令。重复 Fill/execId、重复 REST 查询或重启恢复不得再次释放相同数量。

只有计划中的释放条件满足后才计算可释放数量：`terminal_full_fill` 要求依赖腿的权威终态累计成交等于请求数量；`incremental_cumulative_fill` 允许每个去重后的权威累计成交增量继续释放。

黄金价差适配器把盎司与 MT5 合约乘数转换为计划中的 `release_ratio`，并使用 `terminal_full_fill`，继续保持当前跨场所 Market/FOK/PostOnly 的终态成交后对冲规则。资金费适配器根据 CEO 指定的两腿总数量形成比例，使用 `incremental_cumulative_fill`，允许每个新的永续累计成交增量释放对应的 Spot 数量步长。共享编排器只理解释放条件，不判断策略名称。

### 6.3 订单政策

- `market`：仅在该策略和当前受控测试会话明确允许时使用。
- `fok`：只有权威终态全量成交才正常释放下一腿；零成交安全结束；部分成交进入对账或人工介入。
- `post_only_chase`：总 TTL、检查间隔和最大变更次数来自冻结计划；取消终态未被权威证明前不得重挂。
- 不允许任何执行政策静默降级为 Market。

资金费开平仓按当前产品决定使用永续腿优先的有界 PostOnly Chase，然后按去重后的权威累计成交增量释放现货腿。当前两个市价腿的实现不能作为受控实盘完成证据。

### 6.4 共享账户、资源租约与资金预约

跨所价差和资费套利使用同一个真实 Bybit UTA、同一个 Platform `account_id` 和同一个凭据引用，不得用两个逻辑账户伪装同一个真实 UID。账户余额属于共享资金池；Order、Fill、Fee 和策略 PnL 通过 `strategy_instance_id → instruction_id → batch_id → trade_command_id → external identity` 归属。

交易租约从整个账户串行收敛为资源冲突串行，最小资源键是 `account_id + venue/category + symbol`：

- 不同 Symbol 可以并发；相同 `category + symbol` 的跨策略写入拒绝。
- 平仓、未确认外部订单和取消未终态继续占用对应资源。
- `result_unknown`、账户身份不明、余额或保证金不可用时至少保留相关资源；影响范围无法证明时升级为账户级冻结。
- “移动双边资金”取得账户级资金锁，期间不接受新的交易写入。

共享余额使用轻量资金预约而不是通用组合风控系统。每个活动 Instruction 原子记录账户、策略、币种和最大预计占用；新指令只能使用“权威可用余额减其他活动预约”。Batch 已终态、外部订单已证明终态并完成必要对账后才能释放；`result_unknown`、残余敞口和取消不确定不得释放。

只读账户同步按账户隔离，一个账户失败不能清空或阻塞其他策略的只读展示。

## 7. 开仓、平仓和人工处置

### 7.1 开仓

```text
CEO 提交业务参数
→ 后端校验身份与业务 Schema
→ 解析账户绑定和合约规格
→ 原子创建 Instruction + immutable Plan + Batch claim
→ 检查执行安全门
→ 首腿执行
→ 按权威累计成交释放后续腿
→ Venue/Platform 对账
→ 建立或更新 Position Group
→ completed 或 manual_intervention
```

前端只提交业务参数，不提交账户 ID、腿顺序、Runtime 参数或风险绕过选项。

### 7.2 平仓

平仓必须引用 Position Group。后端从已核实的开仓数量、已平数量、当前外部持仓和必要 Position Ticket 生成平仓计划。前端不能重新猜测数量或自行交换方向。

平仓是一条新的 StrategyInstruction，但引用原经济头寸；它受新的幂等键和同样的双 Live Write、租约、数量上限和对账控制。

### 7.3 人工处置

不提供含糊的“重试”按钮。允许的处置动作保持有限：

- `reconcile`：重新查询 Runtime 和 Venue 权威事实，不产生外部写入；
- `acknowledge_external_state`：在证据完整时接受已核实的实际成交或持仓；
- `create_risk_reduction_instruction`：针对已证明的残余敞口创建新的、数量受限的风险处置指令；
- `close_exception`：仅在订单终态、持仓和账本已对账后关闭异常。

未知状态不能通过手工修改数据库直接变成成功、失败或零仓位。

### 7.4 移动双边资金

价差执行卡片使用三个并列模板：

```text
开仓价差 | 平仓价差 | 移动双边资金
```

资金模板展示 Bybit 所内可调拨余额、MT5 可转出余额、调拨方向和金额。默认方向从余额较多的一侧移向较少的一侧，默认金额为两边可调拨余额差额的一半，并受转出方真实 transferable/withdrawable amount 限制。CEO 可以换向或修改金额，确认前必须看到调拨前后预计余额。

Bybit 所内资金与 MT5 的调拨可能经过 Funding Account：

```text
Bybit UTA → Funding → MT5
MT5 → Funding → Bybit UTA
```

中间步骤成功、后续步骤失败时，资金保留在 Funding Account，记录为部分完成或失败并显示当前位置；不执行自动反向回滚。相同幂等键不得重复移动资金，`result_unknown` 不得盲目重试。

Bybit 官方资料确认 TradFi（MT5）通过 Funding Account 转入转出，并按 1:1 在 USDT 与内部余额单位 USDx 之间显示转换；但公开 V5 Internal Transfer API 当前没有列出 MT5/TradFi account type。真实自动划转实现必须使用已验证的 Bybit MT5 Transfer In/Out 接口。接口未确认时，产品降级为“自动计算并复制金额 → 打开 Bybit MT5 资金页 → 完成后刷新核对余额”，不得伪造自动划转成功。

## 8. API 设计

普通策略页面只依赖少量稳定接口：

```text
POST /api/v1/strategies/{instanceId}/instructions
GET  /api/v1/strategies/{instanceId}/instructions
GET  /api/v1/strategy-instructions/{instructionId}
POST /api/v1/strategy-instructions/{instructionId}/dispositions
GET  /api/v1/strategies/{instanceId}/dashboard
GET  /api/v1/trading/cross-spread/funding-transfer/quote
POST /api/v1/trading/cross-spread/funding-transfer
GET  /api/v1/trading/cross-spread/funding-transfers/{transferId}
```

建议的手工开仓请求：

```json
{
  "idempotencyKey": "browser-generated-uuid",
  "action": "open",
  "parameters": {
    "perpetualSymbol": "BTCUSDT",
    "perpetualQuantity": "1",
    "spotSymbol": "BTCUSDT",
    "spotQuantity": "0.02"
  },
  "reason": "CEO manual instruction"
}
```

平仓请求使用 `positionGroupId`，并可由 CEO 指定不超过已核实可平数量的目标。所有金融数值使用 Decimal 字符串，所有时间为带时区 UTC。

现有 Execution Batch、Order、Fill 和 Reconciliation 接口继续用于技术审计与兼容，但不再作为普通策略页面的主要聚合接口。旧策略专属端点先通过兼容层调用统一 Instruction Service，消费者迁移后再删除。

资金调拨请求只允许 `idempotencyKey`、`direction` 和 Decimal 字符串 `amount`。报价接口返回两边真实可调拨余额、建议方向、建议金额、数据质量和读取时间；创建接口返回平台 transfer ID、外部 transfer ID（如有）及当前状态。

## 9. Strategy Read Model

`GET /strategies/{instanceId}/dashboard` 返回页面一次决策所需的统一投影：

- 策略实例、模式、账户能力和可操作状态；
- 数据质量、最新事实时间、延迟或不可用原因；
- 当前 Position Groups 和各腿权威数量；
- 活动/历史 Instructions、Batches、Orders 和 Fills 摘要；
- 账户余额、正式 Position、费用、资金费；
- 正式 PnL/NAV 和对账状态；
- Kill Switch、LiveTradingSession 和人工介入提示。

Read Model 只聚合现有权威事实，不成为新的账本。`unavailable`、`error`、`partial` 和 `stale` 不得渲染为零。页面保留现有布局与视觉层级，逐步删除生产路径上的样例策略数据依赖。

只读策略账户使用同一 Dashboard Schema，但 `allowedActions` 为空，任何写请求仍由 Platform API 和 Runtime 双重拒绝。

## 10. AI 测试会话与授权简化

### 10.1 目标

安全控制继续严格，但授权粒度改为“一次明确授权，一个完整测试闭环”。AI 必须能够在授权范围内连续启动服务、执行测试、核实结果、平仓、对账和复位，不再为每个技术动作重复询问。

不新增第二套会话平台。扩展现有 LiveTradingSession 的持久化和校验能力，增加明确的 `mode`、授权范围和复位证据；产品和文档统一称其为“受控会话”。Offline E2E 不创建 LiveTradingSession，只依赖隔离测试配置并证明没有真实账户或凭据。

最小字段：

| 字段 | 含义 |
| --- | --- |
| `mode` | `offline_e2e`、`live_read_only`、`controlled_live` |
| `operator` | 负责的 CEO |
| `allowed_accounts/strategies/symbols` | 明确范围 |
| `allowed_actions` | 查询、开仓、平仓、对账、复位等 |
| `quantity_ceilings` | 每条腿最大数量 |
| `execution_modes` | 本会话允许的 Market/FOK/PostOnly 等 |
| `expires_at` | 绝对过期时间 |
| `status/current_phase` | 当前步骤 |
| `reset_evidence` | 最终复位证据 |

### 10.2 Offline E2E

默认开发测试模式，使用 FakeGateway、测试 CEO、隔离数据库和 Runtime Journal。无需重复 Owner 授权，AI 可连续完成：

- 启动 Web、Platform API 和 Runtime；
- 登录测试 CEO；
- 两策略开仓、部分成交、增量配平和平仓；
- 重复点击、断线、重启和 `result_unknown` 故障注入；
- 账本、仓位、PnL 和对账验证；
- 停止测试服务并生成测试报告。

该模式必须通过配置和数据库身份证明没有真实账户或真实凭据。任何环境身份不明确时停止，而不是猜测。

### 10.3 Live Read-Only

每个会话授权一次账户、策略、Symbol、允许查询和有效期。会话内 AI 可以连续查询余额、持仓、合约规格、订单、成交、经济事件并进行影子对账，不再逐接口询问。所有写路由继续在 Platform 和 Runtime 层被拒绝。

### 10.4 Controlled Live

每个完整业务场景授权一次，授权范围包含：

- 指定测试账户、策略、Symbol 和两腿最大数量；
- 本场景允许的唯一执行政策；
- 开仓、权威核实、对应平仓、对账和强制复位；
- 单一负责 CEO、开始期限和绝对过期时间。

初次受控实盘验收仍按 Market、反向 Market、FOK、TP/SL、PostOnly Chase 的成熟度顺序推进，但每一个已授权场景天然包含完成该场景所需的开仓、对应平仓、对账和复位，不再把这些技术步骤拆成新的聊天授权。

只有超出账户、策略、Symbol、数量、执行模式、时间或动作范围，或者发生 `result_unknown`、身份不一致、持仓不一致、取消不确定、外部查询不可用时，AI 才必须停止并重新请求 Owner 决策。

## 11. 安全边界

以下控制不因授权简化而降低：

- Platform Live Write 与 Runtime Live Write 独立且默认关闭；
- CEO 身份必要但不足以授权下单；
- Kill Switch、全局执行串行、幂等、指令数量上限和累计成交上限；
- ACK 不等于 Fill，Venue 终态和 Fill/Deal 是权威；
- `result_unknown` 禁止盲目重试、盲目回滚和重复业务意图；
- 取消确认不等于取消终态，未证明终态前不得重挂；
- 外部查询失败是 unavailable，不是空订单、零余额或零仓位；
- 每个受控会话结束必须证明双 Live Write 关闭、临时能力关闭、外部订单终态和持仓/账本完成对账；
- 凭据、原始密钥和敏感证据不写入仓库、普通日志或页面响应。
- 内部资金调拨不使用外部地址或链上提现能力，但仍须使用真实可调拨余额、CEO 身份、幂等和结果核对；未知结果不得自动重试。

## 12. 迁移方案

迁移必须小步、可回滚，并保持现有本地闭环可运行。

### 阶段 0：冻结与契约对齐

- 暂停新增策略执行特例。
- 为当前资金费实现与已批准语义的差异增加失败测试。
- 明确现有端点、表、前端消费者和兼容期限。
- 更新受控实盘 Runbook：授权粒度改为完整场景，但不降低交易安全门。

### 阶段 1：统一 Instruction 与不可变 Plan

- 将 `strategy_runs` 语义升级为 StrategyInstruction，必要时追加字段和新版本 Schema。
- 创建 Instruction Service 和两个策略适配器。
- 旧黄金与资金费路由通过兼容层创建统一 Instruction。
- 底层暂时继续调用现有 Execution Batch，业务行为不扩大。
- 在跨所价差执行卡片增加第三个“移动双边资金”模板，先完成报价、自动金额、幂等记录、FakeGateway 闭环和官方页面辅助模式；只有确认可用的 Bybit MT5 Transfer 接口后才启用真实自动划转。

### 阶段 2A：跨所价差实盘交互收尾

- 保留现有交易底座，只修复重复点击、超时恢复、页面刷新恢复、状态准确性和批量平仓逐项结果。
- UI 必须区分提交、受理、单腿成交、双腿完成、对账、人工干预和 `result_unknown`；不得把“已提交”显示为“已成交”。
- 完成聚焦浏览器测试后直接继续现有跨所实盘验收，不等待 Phase 3–5。

### 阶段 2B：共享 Bybit 账户并发隔离

- 资费真实绑定复用跨所价差相同的 Bybit `account_id` 与凭据引用。
- 用 `account + category + symbol` 资源租约代替整个账户互斥；不同 Symbol 可并发，相同资源拒绝。
- 增加轻量资金预约，证明两个策略不会重复使用同一份可用资金。
- 资金调拨、账户级未知状态和账户 Kill Switch 继续阻止账户写入。

### 阶段 2C：资金费策略安全闭环

- Attempt 重挂数量必须是计划最大数量减所有历史 Attempt 的权威累计成交，提交前再次验证不超过上限。
- 实现并证明有界 PostOnly Chase、取消终态、至少一 Tick 价格变化、TTL、maxMutations、重启恢复和未知结果。
- 按去重后的权威永续累计成交增量原子释放 Spot，证明数量步长、余数和并发恢复。
- 两腿完成后保持 `reconciling`，只有真实订单、成交、仓位和余额证据一致才进入 `completed`。
- 全部离线测试通过后，用共享账户选择不与跨所冲突的 BTC/ETH 等 Symbol 进入极小额受控真号验收。

### 后续维护：Phase 3–5

- 黄金通用编排迁移、Position Group、统一 Read Model、一键 Offline E2E 和旧路径清理继续保留为维护计划。
- 这些工作不得阻塞跨所价差收尾或资费首次小额真号测试。
- 海内外价差保持暂停，Owner 重新启用前不配置真实交易账户。

任何阶段都不能同时重做 Runtime、账本、前端视觉和策略编排。一个迁移切片只改变一个主要责任边界。

## 13. 验收标准

### 13.1 指令与幂等

1. 同一幂等键和相同请求只返回原 Instruction；不同请求返回冲突。
2. 一个 Instruction 最多产生一个业务 Batch。
3. 浏览器重复点击、API 超时和服务重启不产生第二个业务意图。
4. 计划在执行开始后不可修改，恢复使用原计划快照。

### 13.2 执行与数量

1. 下一腿只有在计划声明的释放条件满足后才执行，累计释放不超过依赖腿权威累计成交映射出的数量。
2. 累计外部成交不超过 CEO 输入的每腿上限。
3. 重复 Fill/execId 不重复释放 Spot 或 MT5 对冲。
4. PostOnly 取消终态未证明前不重挂，不静默降级为 Market。
5. `result_unknown`、身份异常或查询不可用阻止新副作用并保留租约。

### 13.3 开平仓和对账

1. 平仓引用 Position Group，最大数量来自已核实事实，不能超平。
2. 指令、Batch、Trade Command、Order、Fill/Deal、Position 和金融事实可以双向追溯。
3. 完成状态必须有 Venue 终态和对账证据，不能只依赖 API 200 或 Batch 状态。
4. 未知、过期或不完整金融数据不显示为零。

### 13.4 权限与测试会话

1. Offline E2E 无真实凭据、无真实账户副作用，能够无重复授权完成完整闭环。
2. Live Read-Only 在一个授权会话内完成全部查询和影子对账，任何写请求均失败。
3. Controlled Live 在一个场景授权内完成规定的开仓、对应平仓、对账和强制复位。
4. 超范围或异常状态立即停止；会话过期不会自动恢复 Live Write。
5. 只读策略账户在 Platform 与 Runtime 两层都不能提交、改单或撤单。

### 13.5 工程质量

1. 现有黄金与资金费本地闭环回归测试继续通过，并新增部分成交和重启属性测试。
2. 共享编排器不存在策略名称分支。
3. Strategy Dashboard 的每个金融字段都有明确事实来源和数据质量状态。
4. 不新增服务、队列、事件总线或长期后台策略进程。
5. Context Pack、版本、仓库结构、文档一致性和 `git diff --check` 通过，已知基线失败必须独立说明。

### 13.6 双边资金调拨

1. 页面以第三个独立模板展示资金调拨，不与开仓或平仓字段混用。
2. 建议金额来自两边真实可调拨余额，允许 CEO 换向和修改，所有金额保持 Decimal 精度。
3. 相同幂等键不重复划转；`pending` 可查询，`result_unknown` 不自动重试。
4. UTA、Funding、MT5 任一步失败都显示资金当前所在账户，不伪造回滚或成功。
5. FakeGateway 可以完成双向闭环；真实自动划转必须有已验证的 Bybit MT5 接口，否则使用官方页面辅助模式。

## 14. 后续执行 AI 的工作边界

后续执行 AI 应先把本设计拆成上述阶段的独立实施计划，而不是一次性重构整个策略模块。

执行要求：

- 首个实现切片只能做阶段 0 和阶段 1，不得同时迁移两个策略执行语义。
- 资金费 P0 安全差异必须通过失败测试先被固定，再实现修复。
- 每个数据库变更保持追加式迁移，不重写已有金融事实。
- 每个旧入口在删除前必须列出真实消费者和兼容替代。
- 不修改未授权的外部凭据、真实账户、Live Write 或生产状态。
- 不以“架构优化”为理由引入本设计明确排除的基础设施。
- 工作区存在未提交改动时，先记录精确写集，保护并适配现有修改，不覆盖用户工作。

本设计完成的是目标边界和迁移合同，不代表任何外部连接、真实账户、Live Write、实盘开平仓或生产能力已经得到证明。
