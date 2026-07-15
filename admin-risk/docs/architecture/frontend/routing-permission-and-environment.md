# Platform V6 前端路由、权限与环境规范

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`  
架构层级：前端架构

## 1. 文档定位

本文档定义前端路由状态、页面访问权限、操作能力权限以及运行环境展示规则。

路由负责表达可恢复、可分享的页面上下文；权限负责控制用户能否访问和操作；环境负责明确当前页面连接的是演示、模拟、测试还是实盘系统。三者不得混为一体。

## 2. 路由设计原则

- 六个一级产品模块保持稳定。
- 路由表达用户正在访问的业务位置，不表达后端内部服务结构。
- 影响主视图的状态优先进入 path、route meta 或 query。
- 临时输入和局部交互不进入路由。
- 同一主状态只能有一个权威来源。
- 所有路由参数必须有合法值校验和默认回退。

## 3. 路由状态范围

### 3.1 应进入路由的状态

- 当前一级或二级模块。
- 当前策略 ID。
- 当前主要工作视角，例如行情分析、交易执行、策略损益、账户资金、订单信息。
- 对冲基金看板资产分类。
- 新闻日历主要分类。
- 需要通过链接分享的日期区间或核心筛选条件。

### 3.2 不应进入路由的状态

- 弹窗是否打开。
- 表单正在输入的交易数量和价格。
- 图表图例开关。
- 卡片展开和折叠。
- 临时分页，除非明确需要分享。
- 未提交的敏感交易参数。
- 权限判断结果。

## 4. 策略模块路由语义

### 4.1 交易平台

建议稳定表达：

```text
/strategy/platform?strategy=funding&view=analysis
/strategy/platform?strategy=crossSpread&view=execution
```

规则：

- `strategy` 必须来自统一 `StrategyId`。
- 只允许 `platform.enabled = true` 的策略。
- `view` 只允许 `analysis` 或 `execution`。
- 非法策略回退到首个有效平台策略。
- 非法视角回退到 `analysis`。
- 切换策略时默认进入该策略的 `analysis`，除非未来需求明确允许保留执行视角。
- 离开存在未提交交易参数的执行页前，应提示用户确认。

### 4.2 策略管理

建议稳定表达：

```text
/strategy/management?strategy=funding&view=pnl
/strategy/management?strategy=dip&view=orders
```

规则：

- `strategy` 必须来自统一 `StrategyId`。
- 只允许 `management.enabled = true` 的策略。
- `view` 只允许 `pnl`、`capital` 或 `orders`。
- 切换策略时保留当前管理视角。
- 切换管理视角时保留当前策略。
- 兼容的日期区间和计价币种可以保留；策略特有筛选重新加载。

## 5. 页面访问权限

页面访问权限决定用户能否进入某个路由。

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
3. 检查数据范围是否允许访问目标账户或策略。
4. 无权限时跳转到统一无权限页面或安全默认页。

路由守卫不能代替后端权限校验。

## 6. 操作能力权限

操作权限必须比页面访问权限更细。

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

角色只作为能力集合，不在页面中用大量 `role === admin` 分支替代能力判断。

## 7. 前端权限表现

### 7.1 隐藏

适用于用户完全不应知道或使用的能力，例如无权进入某个管理模块。

### 7.2 禁用并说明原因

适用于用户可以看到业务上下文，但当前不能操作，例如：

- 无提交权限。
- 风险状态禁止执行。
- 数据已过期。
- 当前环境不允许真实交易。
- 账户不可用。

禁用状态必须提供明确原因，不只改变按钮颜色。

### 7.3 二次确认

高风险操作至少包括：

- 正式提交交易。
- 全部平仓。
- 撤销全部订单。
- 强制配平。
- 人工覆盖风险限制。
- 修改风险规则。
- 数据修正和对账确认。

确认内容应显示目标对象、数量、账户、环境和主要风险。

## 8. 运行环境

平台至少区分：

- `demo`：纯前端演示或 Mock 数据。
- `simulation`：后端模拟执行，不连接真实账户。
- `test`：测试环境，可能连接测试网或沙盒账户。
- `paper`：仿真实盘或模拟账户。
- `live`：真实资金和真实订单。

环境必须由受信任配置或后端会话返回，不由页面自行推断。

## 9. 环境展示规则

- 交易平台顶部持续显示当前环境。
- `demo`、`simulation`、`test` 和 `paper` 不得使用容易误认为实盘的文案。
- `live` 环境的正式交易动作必须具有明显但不过度干扰的实盘标识。
- 环境切换不得只依赖 URL query。
- 不同环境使用隔离的账户、凭证和后端配置。
- 页面不得在环境未知时开放正式交易按钮。

## 10. 权限和环境状态来源

前端可以缓存：

- 当前用户基本信息。
- 能力权限集合。
- 数据范围。
- 当前环境。
- 会话过期时间。

但最终权威来自 IAM、权限和环境配置服务。

前端不得将本地缓存的旧权限长期视为有效；高风险命令仍由后端重新校验。

## 11. 异常处理

- 登录过期：清理敏感状态并跳转登录。
- 权限变化：重新获取权限并刷新可用操作。
- 环境变化：清理未提交交易参数和实时订阅。
- 路由参数非法：回退安全默认值并替换 URL。
- 目标策略被停用：跳转到首个有效策略并提示原因。
- 目标账户无权限：不加载其数据，并显示权限错误。

## 12. 验收标准

- 主要页面上下文刷新后可以恢复。
- 非法路由参数不会导致白屏或越权。
- 策略 ID 只使用统一注册表定义。
- 页面访问权限和操作权限分开。
- 按钮禁用状态具有明确原因。
- 演示、模拟和实盘环境可被清晰识别。
- 前端权限控制不能替代后端最终校验。
