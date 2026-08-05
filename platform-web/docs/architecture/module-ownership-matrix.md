# Platform 0.10.x 模块职责、技术领域与数据权威矩阵

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：跨层架构

## 1. 文档定位

本文档定义六个一级产品模块及其子板块的产品归属，并映射对应技术领域、数据权威和允许操作。

必须区分：

- 产品归属：用户从哪里进入。
- 前端归属：路由、页面和组件如何组织。
- 技术领域：后端规则和对象属于哪个模块。
- 数据权威：哪个模块维护最终事实。
- Read Model：哪个查询层负责组合展示，但不拥有事实。

产品模块不等于后端服务边界。

## 2. 一级产品模块

1. 首页。
2. 对冲基金看板。
3. 新闻日历与理财。
4. 策略。
5. 风险管理。
6. 金融AI分析。

正式模块名称以 `docs/governance/glossary.md` 为准。

## 3. 产品职责原则

- 每项核心产品能力具有唯一主责模块和子板块。
- 其他模块可以读取、展示摘要或提供跳转，不建立冲突逻辑。
- 同一对象可以在多个页面展示，但使用目的和操作权限明确。
- 一级菜单位置不决定后端模块、数据库表和数据权威。
- 聚合 Read Model 不形成新的写入入口。

## 4. 模块与子板块

| 一级模块 | 主要子板块 |
|---|---|
| 首页 | 品牌主视觉、市场摘要、核心入口 |
| 对冲基金看板 | 宏观、商品、加密、美股、A 股、全球、交易工具 |
| 新闻日历与理财 | 宏观日历、新闻整理、理财信息 |
| 策略 | 交易平台、策略管理 |
| 风险管理 | 风控详情、账户与资产、财务与资金、数据与服务监控、报表、审计、用户与权限、个人账号、系统设置、消息通知 |
| 金融AI分析 | 研究问答、信息归纳、专题分析、情景推演、策略 Memo、分析任务与结果 |

## 5. 核心职责矩阵

| 业务对象或能力 | 主责产品模块／子板块 | 其他模块权限 | 主要技术领域 | 数据权威／写入入口 |
|---|---|---|---|---|
| 首页摘要与导航 | 首页 | 其他模块不维护副本 | Frontend Composition／Query Read Model | 首页配置与聚合查询 |
| 实时交易行情 | 策略／交易平台；看板只读 | 风险管理和金融AI分析按权限读取 | Market Data | Market Data 服务 |
| 宏观、资产和公司研究数据 | 对冲基金看板 | 交易平台有限引用；金融AI分析使用 | Research Data | Research Data 服务 |
| 新闻、宏观日历和理财内容 | 新闻日历与理财 | 首页、看板和金融AI分析引用 | Content and Calendar | 内容与日历数据源或维护入口 |
| 研究工具目录 | 对冲基金看板／交易工具 | 其他模块提供链接 | Content／Frontend Generated Data | Markdown 源和同步脚本 |
| 策略定义和前端能力 | 策略／共享策略定义 | 风险管理和报表引用 StrategyId | StrategyDefinition／Frontend Capability | 策略文档、前端注册表；未来 Strategy 服务 |
| 策略版本和实例 | 策略页面读取 | 风险管理读取状态 | Strategy | Strategy 服务 |
| 策略账户绑定 | 策略／管理或执行配置 | 账户与资产提供账户主档 | Strategy | StrategyAccountBinding；Account 只验证 accountId |
| 交易机会分析 | 策略／交易平台／行情分析 | 看板提供研究输入 | Market Data／Research Data／Strategy Analysis | 行情和分析数据服务 |
| TradeIntent 和执行参数 | 策略／交易平台／交易执行 | 风险管理提供规则和限制 | Trading／Execution | 前端表单发起，后端 TradeCommand 受理 |
| TradeCommand 和 ExecutionBatch | 策略／交易平台／交易执行 | 策略管理查询；风险管理读取异常 | Trading／Execution | 后端交易执行服务 |
| Order、Fill 和 Deal | 策略管理完整查询；交易平台展示当前批次 | 风险管理和报表只读 | Trading／Execution | 订单、成交和 MT5 Deal 服务／Gateway 同步 |
| 执行配平与暴露 | 策略／交易平台 | 策略管理复盘；风险管理监控 | Trading／Execution／Exposure | ExecutionBatch 和暴露计算 |
| Position | 策略管理完整查询；交易平台执行视图 | 风险管理和报表读取 | Account／Position | Position 服务或外部核对结果 |
| 策略损益和归因 | 策略／策略管理／策略损益 | 交易平台展示预计值；风险管理读取摘要 | PnL／Strategy Economic Ledger | PnL 和策略经济账本服务 |
| 固定时间策略净值 | 策略／策略管理 | 首页和风险管理读取摘要；客户侧展示后续再设计 | PnL／Strategy Economic Ledger | StrategyNavSnapshot，不等于正式 Fund NAV |
| 策略账户资金视图 | 策略／策略管理／账户资金 | 交易平台读取执行摘要 | Account／Capital／Backend Read Model | Account 事实与策略绑定组合查询 |
| 账户主档和资产结构 | 风险管理／账户与资产 | 策略页面按权限读取 | Account／Asset | Account 服务，不属于 Risk 内部模型 |
| 公司财务与经营资金 | 风险管理／财务与资金 | 报表汇总；策略管理仅展示策略经济结果 | Finance／Treasury | 后续财务服务，不与 Strategy Economic Ledger 混同 |
| 风险指标和状态 | 风险管理／风控详情 | 交易平台和策略管理只读使用 | Risk | Risk 服务 |
| 风险规则、额度和阻断 | 风险管理／风控详情、系统设置 | 交易平台执行限制 | Risk／Configuration | Risk 规则服务 |
| 风险事件和处置 | 风险管理／风控详情 | 策略、通知和报表引用 | Risk／Audit | Risk 事件和处置服务 |
| 高风险审批和双人复核 | 风险管理相关页面或目标业务页面 | 各模块发起并读取审批 | Approval and Control | Approval 服务；目标命令由原领域执行 |
| 对账和数据修正 | 策略管理、风险管理／数据监控 | 相关业务模块读取结果 | Reconciliation／Data Quality | 对账服务；修正通过授权命令写回主责领域 |
| 数据源和同步质量 | 风险管理／数据与服务监控 | 看板、策略和金融AI分析读取状态 | Data Quality／Integration | 数据质量和同步服务 |
| 系统和 Gateway 健康 | 风险管理／数据与服务监控 | 业务页面展示必要状态 | Observability／Gateway | 监控平台和 Gateway 健康接口 |
| Backend Read Model | 各页面按业务使用 | 不接受写入 | Query and Read Model | 可重建查询投影，不是权威事实 |
| 结构化报表 | 风险管理／报表 | 各领域提供数据 | Reporting | 报表服务和正式版本存储 |
| 操作、审批和配置审计 | 风险管理／审计 | 各领域提供事件 | Audit | Audit 服务 |
| 用户、角色和能力权限 | 风险管理／用户与权限 | 所有模块读取结果 | IAM／Permission | IAM 服务 |
| DeploymentEnvironment 配置 | 风险管理／系统设置或运维入口 | 所有模块读取 | Configuration／Operations | 受信任配置服务 |
| TradingMode 和交易能力 | 交易平台持续展示；风险管理监控 | 策略管理只读状态 | Trading／Risk／IAM／Configuration | 服务端综合 TradingPermissionState |
| 消息和阅读状态 | 风险管理／消息通知 | 各模块提供业务上下文 | Notification | Notification 服务 |
| AI 分析任务和结果 | 金融AI分析 | 看板、新闻和策略提供授权数据 | AI Orchestration／Research Data | 当前暂缓研发；未来由 AI 任务和结果服务维护 |

## 6. 信息镜像规则

| 信息 | 交易平台 | 策略管理 | 风险管理 | 权威领域 |
|---|---|---|---|---|
| 可用资金 | 判断执行条件 | 观察策略资金占用 | 展示账户和风险视图 | Account |
| 当前持仓 | 支持调整和平仓 | 完整查询、统计和复盘 | 展示风险摘要 | Position |
| 收益 | 预计收益和当次影响 | 实际损益和归因 | 读取风险相关摘要 | PnL／Strategy Economic Ledger |
| 风险 | 展示限制和许可 | 展示策略风险状态 | 维护规则、事件和处置 | Risk |
| 订单与成交 | 当前 ExecutionBatch | 完整历史查询 | 读取异常和关联风险 | Trading／Execution |
| 审批 | 发起或使用交易相关授权 | 发起数据修正或对账授权 | 管理风险和配置审批 | Approval and Control |
| 运行上下文 | 展示 DeploymentEnvironment、TradingMode 和交易能力 | 展示数据来源和模式 | 监控和配置 | Configuration／IAM／Risk／Trading |

信息镜像不得形成独立口径或重复写入入口。

## 7. 新增功能归属检查

新增页面、接口、服务或业务能力前，确认：

1. 所属一级产品模块和子板块。
2. 处理的公共领域对象。
3. 前端权限是写入、操作、只读摘要还是跳转。
4. 后端技术领域和数据权威。
5. 是否属于权威对象或 Backend Read Model。
6. 是否已存在主责入口、模型、接口或组件。
7. 是否会形成重复管理或冲突口径。
8. 是否需要审批、审计或新的 ADR。

## 8. 验收标准

- 所有用户功能归入六个一级产品模块之一。
- 正式模块名称使用“金融AI分析”。
- 每个核心对象具有明确技术领域和数据权威。
- 产品菜单位置不会导致技术领域被错误合并。
- Research Data、Execution Market Data 和内容数据分开。
- StrategyAccountBinding 和 Account 主档所有权明确。
- Backend Read Model 不形成写入入口。
- 权限、审批、风险、审计和命令执行职责分开。
