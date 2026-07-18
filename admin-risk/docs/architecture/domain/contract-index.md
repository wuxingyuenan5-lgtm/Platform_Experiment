# Platform V6+ 公共领域契约入口

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：公共领域契约索引

## 1. 读取顺序

1. `unified-domain-model.md`：全平台对象关系和主责蓝图。
2. `domain-overview.md`：领域分组和核心不变量。
3. `value-currency-unit-and-time-contract.md`：金融数值、币种、单位、精度、舍入和时间唯一来源。
4. `status-enums-and-lifecycles.md`：状态枚举与生命周期唯一来源。
5. `approval-and-dual-control.md`：审批和 Maker／Checker。
6. `../domain-model-boundaries.md`：详细对象边界。
7. `../integration/runtime-command-event-contract.md`：Platform 与 Runtime 契约。

## 2. 唯一来源

| 主题 | 唯一来源 |
|---|---|
| 对象关系与主责 | `unified-domain-model.md` |
| 数值、币种、单位、精度和时间 | `value-currency-unit-and-time-contract.md` |
| 状态枚举和生命周期 | `status-enums-and-lifecycles.md` |
| 审批和双人复核 | `approval-and-dual-control.md` |
| Runtime Command／Event | `../integration/runtime-command-event-contract.md` |
| 后端模块所有权 | `../backend/service-boundaries.md` |

## 3. 关键规则

- Money 必须带 Currency。
- Quantity 必须带 Unit。
- Price 必须能结合 Instrument 和 ContractSpecification 解释。
- Rate 使用十进制倍率。
- Decimal 通过字符串跨系统传输。
- 缺失不等于零。
- occurredAt、receivedAt、businessDate、tradingDay、settlementDate 和 valuationDate 分开。
- TradeCommand、RuntimeCommand、ExecutionBatch、Order 和 Fill 状态分开。
- Gateway 连通、认证、同步、就绪和交易能力分开。
- 未知状态默认不得扩大交易风险。

## 4. 变更治理

修改本目录正式契约时必须检查：

- Platform API。
- Runtime Command／Event Schema。
- 数据库 Schema 和迁移。
- 前端 Adapter 和 View Model。
- 导入、报表和 Mock。
- 契约测试和兼容策略。

破坏性语义变化需要 ADR 和版本升级。
