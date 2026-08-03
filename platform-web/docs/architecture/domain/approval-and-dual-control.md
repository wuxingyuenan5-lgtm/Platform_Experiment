# Platform V6 审批与双人复核模型

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：公共领域模型

## 1. 文档定位

本文档定义高风险配置、数据修正、风险覆盖和实盘能力变更所使用的审批、Maker／Checker 和短期授权模型。

审批用于控制高风险操作，不替代：

- 用户能力权限。
- 后端业务校验。
- 风险判断。
- 目标对象自身状态。
- 审计记录。

## 2. 适用范围

以下操作原则上需要评估是否启用双人复核：

- 人工覆盖风险限制。
- 修改实盘风险规则和额度。
- 接受重大对账差异。
- 修正正式损益或账本数据。
- 修改实盘策略与账户绑定。
- 启用新的 Live Gateway 或实盘账户。
- 提高交易额度。
- 修改全局交易阻断规则。
- 执行影响多个账户或策略的批量操作。

普通只读查询和低风险日常操作不应无差别增加审批。

## 3. 核心对象

### 3.1 ApprovalPolicy

定义某类操作是否需要审批及其规则。

稳定字段：

- `approvalPolicyId`
- 操作类型
- 适用 DeploymentEnvironment
- 适用 TradingMode
- 适用账户、策略、额度或数据范围
- 所需审批人数
- 是否禁止发起人自批
- 授权有效期
- 状态和版本

### 3.2 ApprovalRequest

表示一次待审批的高风险操作请求。

稳定字段：

- `approvalRequestId`
- `approvalPolicyId`
- 发起人
- 目标对象类型和 ID
- 操作类型
- 请求参数摘要
- 风险和影响摘要
- 发起时间
- ApprovalStatus
- 过期时间
- 关联 requestId 和 traceId

### 3.3 ApprovalDecision

表示审批人的独立决定。

稳定字段：

- `approvalDecisionId`
- `approvalRequestId`
- 审批人
- 决定：approve／reject
- 理由
- 决定时间
- 审批时权限和数据范围快照

### 3.4 ApprovalGrant

表示审批通过后生成的短期操作授权。

稳定字段：

- `approvalGrantId`
- `approvalRequestId`
- 允许的操作类型
- 允许的目标对象
- 允许的参数范围或最大额度
- 生效和失效时间
- 是否已使用
- 使用后关联命令或变更 ID

ApprovalGrant 不能被用于不同对象、不同参数或不同环境。

## 4. Maker／Checker 原则

- Maker 是操作发起人。
- Checker 是独立复核和批准人员。
- 需要双人复核时，Maker 不得批准自己的请求。
- Checker 必须在审批时仍具备对应能力和数据范围。
- 审批不能仅依赖角色名称，应检查具体能力。
- 审批通过不等于目标操作已成功执行。
- 目标操作执行时仍需重新检查权限、环境、风险和对象版本。

## 5. 审批生命周期

状态以 `status-enums-and-lifecycles.md` 为唯一来源。

典型路径：

```text
draft → pending → approved → executed
pending → rejected
pending → cancelled
pending / approved → expired
```

规则：

- `approved` 表示满足审批条件，不表示已经执行。
- 授权过期后必须重新发起审批。
- 目标对象或关键参数变化后，原审批自动失效或重新评估。
- 同一审批请求不得被重复用于多个高风险操作。

## 6. 与交易命令的关系

需要审批的交易或风险覆盖流程：

```text
ApprovalRequest
   ↓ ApprovalDecision
ApprovalGrant
   ↓ command validation
TradeCommand / ConfigurationCommand
   ↓
Target Business Object
```

命令请求只提交 `approvalGrantId`，不相信前端提交的“已审批”布尔值。

后端验证：

- 授权存在且未过期。
- 操作人和授权使用人符合规则。
- 目标对象和参数范围一致。
- DeploymentEnvironment 和 TradingMode 一致。
- 授权尚未使用或允许规定次数。
- 目标对象版本没有发生导致审批失效的变化。

## 7. 与权限、风险和审计的关系

| 能力 | 作用 |
|---|---|
| Permission | 判断用户是否具备发起、审批或执行能力 |
| Approval | 对特定高风险操作进行独立复核 |
| RiskDecision | 判断业务风险是否允许、限制或阻断 |
| Audit | 记录发起、审批、执行和结果全过程 |

四者不能相互替代。

## 8. 前端要求

前端可以：

- 展示是否需要审批。
- 创建审批请求。
- 展示审批进度和过期时间。
- 允许授权人员批准或拒绝。
- 在目标操作确认页展示有效 ApprovalGrant。

前端不得：

- 自行判断审批已经生效。
- 通过隐藏字段绕过审批。
- 将旧审批复用于新的参数。
- 将“审批通过”展示为“操作成功”。

## 9. 数据与审计

审批记录至少长期保留：

- 原始请求参数摘要。
- 风险和影响摘要。
- 每位审批人的决定。
- 审批时权限上下文。
- 授权使用情况。
- 最终目标命令和执行结果。
- 取消、过期和失效原因。

审批记录不能被普通业务操作无痕删除或修改。

## 10. 初期实施原则

初期优先覆盖：

1. 风险规则和额度修改。
2. 人工风险覆盖。
3. 正式数据修正和重大对账差异。
4. Live Gateway、账户和策略绑定变更。

是否对单笔普通交易启用审批，应根据实际交易流程、人员规模和额度另行确认，不在当前架构中强制要求。

## 11. 验收标准

- 高风险操作可以配置是否需要双人复核。
- Maker 不能批准自己的请求，适用时。
- 审批通过与目标操作完成明确分开。
- ApprovalGrant 与对象、参数、环境和有效期绑定。
- 权限、审批、风险和审计职责分开。
- 审批和授权全过程可追溯。
