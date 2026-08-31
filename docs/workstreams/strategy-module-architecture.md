# 策略模块架构工作流

状态：进行中

Owner：Founder CEO

更新日期：2026-08-30

本文件只保留跨任务接续所需的当前快照。产品、架构、合同和运维规则以文末的长期权威文档为准。

## 当前目标与已确认边界

本阶段把 Cross 与 Funding 收敛为可恢复、可对账的真实账户闭环。Funding 和 Cross 的 Bybit 腿共用逻辑账户 `bybit-live-main`，Cross 的 MT5 腿使用 `mt5-live-main`。策略管理继续统一展示六个策略；Bottom 和 Short A 只读，Short B 暂不绑定，海内外价差暂停。

Cross 保留开仓、平仓、移动双边资金三个模板。Funding 行情分析保留 Owner 原设计，交易执行使用真实 context、instruction identity、权威成交和对账链路，不使用生产 mock。两个 Alpha 策略共用 UTA 时，继续由 resource claim、余额预约和稳定业务身份防止相互干扰。

Owner 已确认 MT5 多账户不再采用单 Terminal 运行期切换：每个活跃 MT5 逻辑账户必须使用独立 Terminal 实例和独立 Worker，由 Runtime 后台自动启动、路由、重连和健康检查，不要求 Owner 人工维护多个窗口。一个 Worker 启动后只能服务一个 `account_id`，监控账户不得切换或改变 Cross 执行会话。

当前不建设通用组合引擎、消息队列或新的独立业务服务；不开放 Bottom/Short 交易，不做无人值守 Live Write、自动选币、自动定仓、未验证的资金划转或海内外价差实盘。交易安全边界不在本文重复，以 Runbook 和执行合同为准。

## 目前做到哪里

- 本地三服务受管启动和登录烟测链路已建立；策略管理使用服务端六策略概览和当前账户快照。
- Funding 已有真实 Spot/Perp 执行上下文、开平仓、非终态追踪、幂等恢复、权威已平数量和 active/history 语义。
- Cross 已有开仓、单平、批平、可恢复身份与双边账户资金展示。资金已就位，但平台内 MT5/TradFi 自动划转仍没有可部署的官方 API 授权，第三模板不能视为自动划转已验收。
- Runtime 已改为按显式 `account_id` 路由到独立 MT5 Worker/Terminal；Worker 只有在 Terminal 初始化且 Login/Server 身份核验后才 ready，RPC 面收窄到明确查询与写入方法。Runtime Journal 中同账户存在未解决命令时，新 MT5 写入在 Worker/Runtime 重启后仍会阻断。
- Short A 已有独立安装且账户登录成立，但新终端尚未完成外部 Python API 的一次性终端授权；它当前只影响 Short A 监控，不再改变 Cross 会话。
- Cross 两端已经真实读取并核对为空仓、空单，MT5 固定账户身份与 `XAUUSD.s` 规格可读。Cross Terminal 的 Algo Trading 仍关闭。Runtime Journal 另有 8 条历史 Bybit `XAUTUSDT` `result_unknown`；当前 Venue 恢复查询无法证明其终态，不得删库或强制标记完成。

## 尚未满足的验收

1. 完成两个真实终端的运行态验收：Cross Worker 可稳定读取和写前预检；Short A 完成外部 Python API 一次性授权后可独立只读，且失败隔离继续成立。
2. Owner 在页面手动完成 Cross 最小开仓、双腿核对、平仓和对账；随后使用共享 UTA 可用资金完成 Funding 最小仓位闭环。
3. 外部持仓、订单、成交、费用与 Platform/Runtime 事实一致，完成强制复位；任何 `result_unknown`、身份不一致或查询不可用均停止扩展。

## 阻断、决策与下一动作

Owner 决定在继续实盘前，由另一实施 AI 集中完成执行主链与 Connector 优化，然后由本阶段审核通过再恢复 Cross/Funding 测试。优化不得替换现有 Platform 业务内核，不得引入消息队列、微服务或通用组合引擎；重点是唯一业务入口、唯一恢复/查询语义、固定账户 Connector、历史 unknown 处置和可理解的执行证据。

实盘恢复前，必须先使 8 条历史 Bybit unknown 获得权威终态或明确的人工责任处置，再由 Owner 手动开启 Cross Terminal Algo Trading，重新核对双端身份、空仓空单和写前预检。

Short A 的新终端需要 Owner 在终端内完成一次外部 Python API 授权/登录保存；这不是 Cross 实盘前置条件，但仍是本阶段账户隔离验收的一部分。真实交易仍需页面中的当次金额确认；阶段记录本身不构成下单授权。

平台内 MT5/TradFi 自动划转的长期阻断是缺少可部署的官方 API/OAuth/Broker 授权；不使用网页 Cookie 作为长期服务器凭据。

## 长期权威

- 项目状态：`docs/PROJECT.md`
- 产品范围：`docs/product/modules/策略.md`
- 策略产品合同：`docs/product/strategies/资金费率套利.md`、`docs/product/strategies/跨所黄金价差.md`
- 系统与 Runtime 边界：`docs/architecture/SYSTEM_MAP.md`、`docs/contracts/VENUE_ADAPTERS.md`
- Cross 执行合同：`docs/contracts/CROSS_SPREAD_EXECUTION.md`
- 只读可观测与对账：`docs/contracts/LIVE_ACCOUNT_OBSERVABILITY.md`、`docs/contracts/EOD_RECONCILIATION.md`
- 实盘验收和强制复位：`docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md`
- 当前工程基线：`docs/BASELINE.md`

阶段验收完成后，只把稳定产品、执行、MT5 隔离和运维事实归并到上述权威文档，更新 `docs/PROJECT.md`，然后删除本阶段文件。不建立阶段归档。
