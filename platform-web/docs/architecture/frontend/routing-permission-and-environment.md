# Platform V6 前端路由、权限与运行上下文规范

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：前端架构

## 1. 文档定位

本文档定义前端路由状态、页面访问权限、操作能力权限、部署环境、交易模式和交易能力展示规则。

必须区分：

- 路由：用户正在访问什么业务位置。
- 权限：用户是否可以查看或执行某项能力。
- DeploymentEnvironment：系统部署在哪里。
- TradingMode：当前是否产生模拟或真实交易结果。
- TradingPermissionState：当前上下文最终是否允许交易。

这些维度不得合并为单一 `environment`、角色或页面开关。

## 2. 路由设计原则

- 六个一级产品模块保持稳定。
- 路由表达用户可恢复、可分享的业务位置，不表达后端内部服务结构。
- 影响主视图的状态优先进入 path、route meta 或 query。
- 临时输入和局部交互不进入路由。
- 同一主状态只能有一个权威来源。
- 路由参数必须经过合法值校验和安全默认回退。
- 路由状态不包含敏感交易参数和权限结果。

## 3. 路由状态范围

### 应进入路由

- 当前一级或二级模块。
- 当前策略 ID。
- 当前主要视角，例如行情分析、交易执行、策略损益、账户资金和订单信息。
- 对冲基金看板资产分类。
- 新闻日历主要分类。
- 明确需要通过链接分享的日期区间或核心筛选。

### 不应进入路由

- 弹窗状态。
- 未提交的交易数量、价格和风险参数。
- 图表图例开关。
- 卡片展开状态。
- 临时分页，除非业务明确要求分享。
- 权限和风险判定结果。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 的客户端伪造值。

## 4. 策略模块路由

### 4.1 交易平台

建议：

```text
/strategy/platform?strategy=funding&view=analysis
/strategy/platform?strategy=crossSpread&view=execution
```

规则：

- `strategy` 来自统一 StrategyId。
- 只允许 `platform.enabled = true` 的策略。
- `view` 只允许 `analysis` 或 `execution`。
- 非法策略回退至首个有效平台策略。
- 非法视角回退至 `analysis`。
- 切换策略时默认进入目标策略的 `analysis`。
- 离开存在未提交参数的执行页前提示用户确认。

### 4.2 策略管理

建议：

```text
/strategy/management?strategy=funding&view=pnl
/strategy/management?strategy=dip&view=orders
```

规则：

- `strategy` 来自统一 StrategyId。
- 只允许 `management.enabled = true` 的策略。
- `view` 只允许 `pnl`、`capital` 或 `orders`。
- 切换策略时保留当前管理视角。
- 切换管理视角时保留当前策略。
- 兼容的日期区间和计价币种可以保留；策略特有筛选重新加载。

## 5. 页面访问权限

页面访问权限决定用户能否进入路由。

最低能力示例：

- `home.read`
- `hedgeBoard.read`
- `newsCalendar.read`
- `strategy.platform.read`
- `strategy.management.read`
- `risk.read`
- `financeAi.read`

路由守卫负责：

1. 检查登录状态。
2. 检查页面访问能力。
3. 检查数据范围是否允许访问目标策略、账户或对象。
4. 无权限时跳转统一无权限页或安全默认页。

路由守卫不能替代后端权限校验。

## 6. 操作能力权限

交易相关能力建议：

- `strategy.execution.prepare`
- `strategy.execution.submit`
- `strategy.execution.cancel`
- `strategy.execution.close`
- `strategy.execution.rebalance`
- `strategy.execution.override`
- `strategy.execution.manualResolve`

策略管理相关能力建议：

- `strategy.management.read`
- `strategy.reconciliation.read`
- `strategy.reconciliation.confirm`
- `strategy.data.import`
- `strategy.data.correct`

风险和管理能力建议：

- `risk.rule.read`
- `risk.rule.manage`
- `risk.event.resolve`
- `account.read`
- `account.manage`
- `audit.read`
- `report.generate`
- `user.manage`

角色只是能力集合。页面不得使用大量 `role === admin` 分支替代能力判断。

## 7. 前端权限表现

### 隐藏

适用于用户完全不应访问或知晓的管理能力。

### 禁用并说明原因

适用于用户可以理解业务上下文，但当前不能执行，例如：

- 缺少操作权限。
- TradingPermissionState 为 `read_only` 或 `blocked`。
- 风险状态禁止操作。
- 报价或关键数据已过期。
- 账户、Gateway 或执行服务不可用。
- 当前 TradingMode 不支持该操作。

禁用状态必须提供明确原因，不只改变颜色。

### 二次确认

高风险操作至少包括：

- 正式提交交易。
- 全部平仓。
- 撤销全部订单。
- 强制配平。
- 人工覆盖风险限制。
- 修改风险规则。
- 数据修正和对账确认。

确认内容显示目标对象、账户、数量、TradingMode、主要风险和审批要求。

## 8. DeploymentEnvironment

DeploymentEnvironment 表示系统部署位置：

- `development`
- `testing`
- `staging`
- `production`

规则：

- 由受信任配置或后端会话返回。
- 不通过域名、URL query 或页面颜色推断。
- 不同部署环境使用隔离的配置、凭证和数据源。
- `production` 不代表已经启用实盘。

## 9. TradingMode

TradingMode 表示交易执行模式：

- `demo`：纯前端演示或 Mock。
- `simulation`：后端模拟执行。
- `paper`：模拟账户、测试网、沙盒或仿真实盘。
- `live`：真实资金和真实订单。

V1 中，交易所真实 API 模拟盘、测试网、受控非 Live 账户和 MT5 Demo 均按 `paper` 或受限测试配置展示；不能因为使用真实 SDK 就展示为 `live`。

规则：

- 由服务端受信任上下文返回。
- 交易平台顶部持续展示 TradingMode。
- 交易执行页必须同时展示 source／Gateway、TradingMode 和 TradingPermissionState，避免用户把 Fake、Simulation、Paper 和 Live 混淆。
- 非 `live` 模式不得使用容易误认为实盘成交的文案。
- `live` 模式需要明显但不过度干扰的实盘标识。
- TradingMode 变化时清理未提交交易参数和不兼容订阅。

## 10. TradingPermissionState

TradingPermissionState 表示当前上下文最终可用的交易能力：

- `disabled`
- `read_only`
- `enabled`
- `blocked`

它不是简单权限字段，而是服务端综合结果。至少考虑：

- DeploymentEnvironment。
- TradingMode。
- 用户能力和数据范围。
- 账户和策略实例状态。
- 风险状态与全局阻断。
- Gateway、执行服务和关键依赖健康。
- 报价和必要数据质量。

前端依据该结果隐藏或禁用操作，但正式命令仍由后端再次校验。

## 11. 页面运行上下文

前端可以缓存：

- 当前用户基本信息。
- 能力权限集合。
- 数据范围。
- DeploymentEnvironment。
- TradingMode。
- TradingPermissionState 及原因。
- 会话过期时间。

最终权威来自 IAM、配置、风险、账户和交易服务。

页面不得在以下情况开放正式交易：

- 上下文尚未加载。
- DeploymentEnvironment、TradingMode 或交易权限未知。
- 实时连接中断且权威状态尚未恢复。
- 关键数据质量不满足交易要求。

## 12. 异常处理

- 登录过期：清理敏感状态并跳转登录。
- 权限变化：重新获取权限和交易能力结果。
- DeploymentEnvironment 变化：重新初始化应用上下文。
- TradingMode 变化：清理未提交交易参数和实时订阅。
- 路由参数非法：回退安全默认值并替换 URL。
- 策略被停用：跳转至首个有效策略并提示原因。
- 账户无权限：不加载相关数据，显示权限错误。
- 交易能力变为 blocked：立即禁用新增命令，但不在前端擅自处理已有订单。

## 13. 唯一来源

- 状态码和含义：`../domain/status-enums-and-lifecycles.md`。
- 权限服务端协作：`../integration/frontend-backend-integration.md`。
- 部署环境与交易模式分离决策：`../decisions/ADR-007-部署环境与交易模式分离.md`。

本文只定义前端如何使用这些结果，不重新定义后端风险和执行规则。

## 14. 验收标准

- 主要页面上下文刷新后可以恢复。
- 非法路由参数不会导致白屏或越权。
- 策略 ID 只使用统一注册表定义。
- 页面访问权限和操作权限分开。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 分开。
- 按钮禁用状态具有明确原因。
- 演示、模拟、Paper 和实盘可被清晰识别。
- 前端权限和状态展示不能替代后端最终校验。
