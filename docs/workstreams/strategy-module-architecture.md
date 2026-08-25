# 策略模块架构工作流

状态：`in_progress`  
Owner：Founder CEO  
更新时间：2026-08-25  
当前基线：Platform `0.11.2` 候选；已包含 Funding 收口、CEO 会话候选和本工作流 MT5 协调修正

本文件是“策略模块架构”活跃阶段的唯一接续入口。它只维护当前范围、验收门、阻断和下一动作；稳定产品、合同和运维事实仍归属下方列出的长期权威文档。

## 阶段目标

在不引入新服务或通用组合引擎的前提下，把创始人本地策略平台收敛为一个可持续运行、可恢复、可审计的闭环：

- 策略管理统一展示六个策略及其真实账户状态；
- 跨所黄金价差和资金费率套利共用一个 Bybit UTA，并保持策略级订单、成交、费用和 PnL 归属；
- 两个交易策略从 CEO 业务指令进入 immutable Plan、单一 Batch、权威成交、对账和恢复；
- Funding 页面只使用真实账户、行情、指令和组合事实，不使用生产 mock；
- 本地 Web、Platform API、Runtime 能稳定常驻，执行任务结束不导致网站失联；
- 默认只读，任何真实写入仍受 Owner 场景授权、双 Live Write、Kill Switch、受控会话和强制复位约束。

## Owner 已确认范围

- 当前交易策略只有跨所黄金价差和资金费率套利；二者属于同一个实盘测试工作流，不拆成彼此等待的开发阶段。
- Funding `primary` 与 Cross `venue_a` 使用同一个逻辑账户 `bybit-live-main`；不得按 display name 或 API Key 名称推断同一账户。
- Cross 的 MT5 腿继续使用既有 `mt5-live-main`，其账户本质关系不要求 Owner 重新配置。
- Bottom 使用独立 Bybit 账户，只读展示账户、持仓、订单、风险和 PnL。
- Short-term A 使用一个 MT5 Terminal 经 Python API 串行切换，只读监控账户、持仓、订单、风险和 PnL；未知 Broker Symbol 不自动加入可交易目录。
- Short-term B 暂不绑定账户；A 的链路通过即可复用同类能力。
- 海内外价差保持暂停，不进入当前真实交易准备。
- 跨所执行区保留开仓、平仓、移动双边资金三个模板；真实 MT5 Transfer API 未验证时使用官方页面辅助模式。
- Funding 页面必须移除生产 mock，真实开平仓必须创建 StrategyInstruction，并能从刷新、超时和非终态恢复同一业务身份。
- 网站登录和三服务常驻属于本阶段完成条件，不作为独立运维项目延后。
- Cross 与 Funding 可以在同一受控测试工作流中准备和运行；共享 claim、资源互斥和余额预约防止互相干扰。

## 明确不在范围

- 海内外价差真实账户或交易执行。
- Bottom、Short A、Short B 的下单、改单、撤单或自动策略执行。
- 自动选币、自动定仓、自动再平衡、反向 Carry 或跨交易所 Funding。
- 同 Symbol 多策略仓位分配引擎、通用 Portfolio/Risk Engine、消息队列、事件总线或新增微服务。
- 多 MT5 Terminal 部署、自动导入 Broker 品种为可交易 Instrument。
- 未验证的 MT5 自动资金划转、链上提现或外部地址转账。
- 外部客户资金、多人基金运营、生产部署或无人值守 Live Write。
- 本阶段内执行真实订单；每个真实交易场景仍需 Owner 给出账户、策略、Symbol、数量、执行政策和绝对过期时间。

## 稳定架构边界

- `platform-web → platform-api → versioned Runtime contract → Venue SDK`；前端和 Platform 不直接调用 Venue SDK。
- `platform-api` 保持模块化单体；SQLite 继续作为当前本地数据库。
- `strategy_runs` 承担 StrategyInstruction 的持久业务身份；一个 Instruction 最多关联一个业务 ExecutionBatch。
- Immutable ExecutionPlan 冻结账户、Instrument、Symbol、腿顺序、数量、Step、Tick、Multiplier、执行政策和释放条件。
- ACK 不等于 Fill；Runtime Journal 与 Venue Order/Fill/Deal/Position 是外部执行证据。
- `result_unknown`、身份不一致、查询不可用和取消终态不明均停止新副作用并保留必要 claim/reservation。
- FinancialFact 是不可变金融事实；运营投影不能反向成为正式账务输入。
- 共享 UTA 的现金是账户事实，不复制为策略自有现金；归属通过 Strategy → Instruction → Batch → Command → External Identity 建立。

## 验收门

| 门 | 完成定义 | 当前状态 |
|---|---|---|
| G1 阶段治理 | 唯一 workstream 存在；子任务以本文件接续 | `completed` |
| G2 本地服务 | 三服务健康、合同匹配、`expectedRuntime=true`；重复 start 不换 PID；登录烟测通过 | `verified` |
| G3 账户只读 | 共享 UTA、Bottom、Cross MT5、Short A 均可读；Short A 恢复主账号；Short B unbound | `verified` |
| G4 指令内核 | 幂等 Instruction、immutable Plan、单 Batch、共享 claim/reservation、unknown fail-closed | `verified_local` |
| G5 Cross 产品链路 | 开/单平/批平恢复稳定；三模板保留；真实账户与状态可见 | `candidate` |
| G6 Funding 市场与开仓 | spot/linear 显式合同、真实 context、后端 Decimal 数量、真实 open Instruction | `verified_local` |
| G7 Funding 平仓 | 引用真实 Open Group；已平量来自权威两腿 Fill；部分/未知/完成状态准确 | `verified_local` |
| G8 Funding 恢复 | non-terminal 自动轮询；刷新、超时、重新可见复用原身份；unknown 不自动重提 | `verified_local` |
| G9 受控会话 UX | CEO 可从页面建立合规测试窗口；默认未武装；过期/撤销/重启 fail-closed | `candidate_review` |
| G10 联合受控准备 | Cross/Funding 同一 UTA、资源冲突和余额预约通过；技术 readiness 可分别证明 | `candidate` |
| G11 真实场景证据 | Owner 授权的开仓、核实、对应平仓、对账、复位完成 | `not_authorized` |
| G12 最终质量 | 聚焦与相关回归、Ruff、Pyright、前端检查、文档归并全部通过 | `blocked_baseline` |

## 当前工作项

| 工作项 | 状态 | 已验证结果 | 当前阻断 | 下一动作 |
|---|---|---|---|---|
| 本地生命周期与登录 | `verified` | Web/API/Runtime 常驻；登录、`auth/me`、策略总览通过；重复 start 复用 PID | 无当前代码阻断 | 后续改动后执行烟测，保持服务运行 |
| 策略管理总览 | `candidate` | 六策略服务端驱动；Funding/Cross live binding、Bottom、Short A、Short B unbound 状态已接入 | 真实交易状态尚无受控场景证据 | 在后续指令/组合变化后复核页面事实 |
| Bybit 多账户与分类读取 | `verified` | logical account 显式传播；Funding context 区分 spot/linear；Spot 不再调用 position/list | 无当前只读阻断 | 保持多账户 client 隔离回归 |
| MT5 单 Terminal 只读/写互斥 | `verified_local` | Short A 读取切换后恢复主账号；Cross MT5 submit/cancel 与只读快照共用 coordinator lock，恢复失败阻断写 | 尚无真实账户并发证据 | 保持本地并发回归，真实场景只在授权窗口验证 |
| Funding 生产页面 | `verified_local` | sample import 已移除；真实 context；超时按 idempotency 找回；可见/联网恢复；non-terminal 自动轮询 | `result_unknown`/人工介入仍需人工查询，符合 fail-closed | 在真实只读账户页面复核状态和文案 |
| Funding 活动组合 | `verified_local` | 两腿累计 Fill 决定 authoritative closed；pending/unknown 分列预约；全平进入 history | 尚无真实 close Fill 与 EOD 证据 | 等待 Owner 授权的最小场景后对账 |
| Cross/Funding 共享 UTA | `candidate` | 同一 `account_id`、资源 claim、余额预约和 account-wide transfer claim 已实现并回归 | 尚无同一 Owner 场景下的真实写入和对账证据 | 本地联合回归后等待场景授权 |
| CEO 受控会话入口 | `candidate_review` | 管理页已复用 LiveTradingSession 创建、审批、撤销；默认不改变双 Live Write/Kill Switch | 当前 UI 对 Cross 只创建共享 Bybit account 会话，尚未证明覆盖 MT5 腿；API 总合同与现有 founder-demo 单人例外表述不一致 | 修正账户覆盖/校验并统一长期合同后再验收 |
| 质量基线 | `blocked_external` | 本轮 Funding 10 tests、前端恢复行为、MT5 协调 10 tests、Ruff/Runtime Pyright/前端 build 通过 | 全量前端 typecheck 被并发文件 `src/utils/http/axios/index.ts` 的未定义变量阻断；既有 instruction/batch 两测试当前失败 | 由对应并发工作流修复后串行复跑，不在本阶段越界覆盖 |
| Funding Settlement 与正式账务 | `pending_external` | Funding/fee/fill 事实和正式投影合同存在 | 尚无一笔 Owner 授权的真实 Funding Settlement 与关闭后 EOD 证据 | 真实场景获批后按 Runbook 留存证据 |

## 当前下一动作

1. 聚焦审核 CEO 受控会话面板：Cross 必须覆盖实际 Bybit 与 MT5 账户范围，输入必须遵循 Catalog/Decimal/时间合同，且不得由 UI 暗示已经武装。
2. 将 founder-demo 单人例外与通用双人审批合同的差异提交 Owner 确认；确认前不扩大为生产审批规则。
3. 等并发 HTTP 客户端修复落地后，串行复跑前端 typecheck 和两条既有失败回归，区分真实缺陷与基线变化。
4. 在不触发外部写入的前提下执行三服务、登录、策略管理、Funding/Cross 只读烟测。
5. 保持 Runtime 与 Platform Live Write 关闭，不创建真实会话，不执行真实交易。

## 需要 Owner 决策

| 决策 | 当前可选边界 | 默认处理 |
|---|---|---|
| 创始人本地受控会话审批 | 仓库已有 disabled-by-default 的 `founder_demo_live_acceptance_enabled` 最小测试例外；需确认其是否保留为正式本地运营规则 | 不启用该设置，不把例外扩展到生产 |
| 首个 Cross/Funding 真实场景 | 明确账户、两个策略的 Symbol、每腿最大数量、执行政策、开始期限和绝对过期 | 不创建会话、不武装、不下单 |
| 首次是否允许同一窗口实际并行 | 同一工作流内顺序发起以便归因；或在资源不冲突时并发发起 | 只证明并发安全，不执行外部写入 |
| Funding 真实 Pair | Owner 指定永续/现货组合；系统不自动选币 | 不推断 Symbol |

## 关联长期权威文档

- 产品总边界：`docs/product/modules/策略.md`
- Funding 产品合同：`docs/product/strategies/资金费率套利.md`
- Cross 产品合同：`docs/product/strategies/跨所黄金价差.md`
- 系统边界：`docs/architecture/SYSTEM_MAP.md`
- Platform/Runtime API：`docs/contracts/API.md`
- Cross 执行合同：`docs/contracts/CROSS_SPREAD_EXECUTION.md`
- Venue 与只读查询：`docs/contracts/VENUE_ADAPTERS.md`、`docs/contracts/LIVE_ACCOUNT_OBSERVABILITY.md`
- 金融事实与对账：`docs/contracts/FINANCIAL_FACTS.md`、`docs/contracts/EOD_RECONCILIATION.md`
- 受控实盘操作：`docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md`
- 稳定工程基线：`docs/BASELINE.md`

## 阶段结束时的归并清单

全部验收门满足后才执行：

- 将稳定的 Funding 开平仓、组合、恢复和 shared-account 语义归并到对应产品与合同文档。
- 将最终 Runtime spot/perp、MT5 session/write lock 和 capability 语义归并到 Venue/API 合同。
- 将受控会话审批、页面操作、强制复位和联合测试顺序归并到 Live Acceptance Runbook。
- 将真实 Funding Settlement、关闭、EOD 与差异处置保留到批准的 operator evidence 位置，不写入项目驾驶舱过程记录。
- 根据最终证据只更新 `docs/PROJECT.md` 的结果、阻断和下一动作，不改变其结构。
- 删除本文件；不建立阶段 archive，历史由 Git 保留。
