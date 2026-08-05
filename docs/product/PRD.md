# 产品总入口

Variable-Global 是围绕交易研究、策略管理、风险控制和个人账户构建的一组工作台。产品文档按模块管理，跨模块权限与数据状态由统一合同约束。

## 一级模块

| 模块 | 现有文档 | 当前产品判断 |
|---|---|---|
| 首页 | `platform-web/docs/modules/首页-需求文档.md` | 平台入口和跨资产观察面板；聚合 Owner 未配置时使用明确样例状态 |
| 对冲基金看板 | `platform-web/docs/modules/对冲基金看板-需求文档.md` | 市场扫描、工具入口和跨资产观察 |
| 策略 | `platform-web/docs/modules/策略-需求文档.md` | 资金费率、跨所价差和其他策略研究工作台 |
| 策略管理 | `platform-web/docs/modules/策略管理-需求文档.md` | 策略目录、账户资金、损益、订单和风险状态 |
| 交易平台 | `platform-web/docs/modules/交易平台-需求文档.md` | 研究与执行分层；`CrossVenueExecutionWorkspace` 是当前正式跨所执行工作区 |
| 风控管理 | `platform-web/docs/modules/风控管理-需求文档.md` | 内部高风险模块；员工只读，会员不可见且不可访问 |
| 新闻日历与理财 | `platform-web/docs/modules/新闻日历与理财-需求文档.md` | 宏观日历、新闻组织和活动信息，必须披露来源与数据状态 |
| 金融 AI 分析 | `platform-web/docs/modules/金融AI分析-需求文档.md` | 产品结构可见；真实 Provider 未配置时不得生成伪模型回答 |
| 设置与个人账号 | `docs/contracts/BROWSER_ACCESS_AND_PRODUCT_DATA.md` | 设置状态与本人账号分离；所有角色均拥有个人账号 |

## 产品口径

- 正式页面首先服务高频交易和投研工作流，不以整页“尚未配置”代替产品结构。
- 页面不得把实现细节当作产品文案；技术和 Runtime 术语只在执行、风控或运维语境出现。
- 策略管理展示策略、账户、损益、订单和风险，不展示调试面板。
- 研究、模拟和正式执行必须分层；样例内容始终 `actionable=false`。
- 写入能力同时受角色 Capability、数据状态、业务规则和 Live Write 门禁约束。

## 浏览器用户、权限和数据范围

浏览器用户系统采用四类固定业务角色。角色只是后端 Capability 集合的输入；菜单、直接 URL 和后端 API 必须消费同一权限语义。

| 角色 | 产品页面 | 风控与账号目录 | 写入能力 | 个人账号 |
|---|---|---|---|---|
| CEO | 全部正式页面 | 全部内部视图 | 广泛管理与产品能力，但安全门禁独立生效 | 本人资料、头像、密码、设备、会话和持仓 |
| 技术负责人 | 全部正式页面 | 内部视图与运行管理 | 接近完整的运行和产品能力，不含 CEO 身份治理 | 本人资料、头像、密码、设备、会话和持仓 |
| 员工 | 全部业务页面只读 | 风控管理和账号目录只读 | 拒绝业务写入 | 本人资料、头像、密码、设备、会话和持仓 |
| 会员 | 全部业务页面只读 | 不显示且后端拒绝 | 拒绝业务写入 | 本人资料、头像、密码、设备、会话和持仓 |

CEO 的后端通配 Capability 不绕过最后一个有效 CEO 保护、双人审批、Kill Switch、Allowlist、风险检查、查询确认、EOD 或 Platform/Runtime Live Write 双门禁。

前端隐藏按钮不是授权。后端必须从受信任 Principal 解析权限和资源范围；未知或无法判断的高风险请求默认拒绝。Browser Session 不能替代 API Key 或 LiveTradingSession，审批也不能替代执行权限、风险检查或数据范围。

## 产品数据状态

正式页面统一使用以下四种状态：

- `live`：有明确 Owner、来源和时间语义的真实 Provider 或 Platform 事实；
- `sample`：用于恢复产品结构的非实时样例，必须显著标识并设置 `actionable=false`；
- `unavailable`：所需 Provider 或 Application Owner 尚未配置；
- `error`：真实请求失败，不得静默替换为成功外观或零值。

Dashboard、策略管理、资金费率研究和价差研究当前含明确的样例状态；金融 AI Provider 不可用；宏观日历使用 TradingView 公开 Widget；设置页使用当前 Session 与 data-service health，并将设置写入 Owner 标为不可用。具体合同见 `docs/contracts/BROWSER_ACCESS_AND_PRODUCT_DATA.md`。

## 跨模块与安全边界

- 跨模块跳转只传递稳定业务 ID、时间范围和可恢复筛选；权限、凭证、敏感自由文本和未确认写入不得进入 URL。
- 跳转不转移数据权威；所有 Command 由目标领域重新鉴权和执行。
- 页面刷新后只恢复路由表达的主上下文；服务端业务状态必须重新查询。
- ACK 不等于 Fill；结果未知时不得由前端推断成功或无条件重试。
- 策略模块最低闭环覆盖 Strategy、Account、Order、Fill、Position、PnL、NAV、Risk 与 Reconciliation，并使用稳定策略身份。
- 金融 AI 接入真实 Provider 前，必须具备授权数据源、引用溯源、隔离执行、人工复核和明确的非交易权威边界。
