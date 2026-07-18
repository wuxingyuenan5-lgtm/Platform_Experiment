# Account / Position 最小模型

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`

## 1. 目标

只保留账户同步、持仓展示、风险判断、交易校验和对账所需的最小对象。

第一阶段仅包含：

- Account。
- BalanceSnapshot。
- PositionSnapshot。

不建设复杂托管、现金子账、保证金引擎和多层账户树。

## 2. Account

Account 表示外部交易账户主档。

最小字段：

```text
accountId
venueId
externalAccountId
name
accountType
baseCurrency
tradingMode
enabled
```

规则：

- Account 不等于 Fund、Portfolio、Book 或 StrategyInstance。
- StrategyInstance 通过 StrategyAccountBinding 使用 Account。
- 密钥、密码和 Token 不存放在普通 Account 主档中。
- 同一个外部账户只建立一个平台 Account 主档。

## 3. BalanceSnapshot

BalanceSnapshot 表示某个时间点外部账户返回的余额事实。

最小字段：

```text
balanceSnapshotId
accountId
assetOrCurrency
balance
available
lockedOrUsed
occurredAt
receivedAt
source
qualityStatus
```

规则：

- balance、available 和 lockedOrUsed 使用 Decimal 字符串。
- 缺失字段保持缺失，不自动当作零。
- Snapshot 是时间点事实，不直接覆盖历史记录。
- 第一阶段允许不同 Venue 的余额字段不完全一致，由 Adapter 标准化到最小公共字段。

## 4. PositionSnapshot

PositionSnapshot 表示某个时间点的外部持仓事实。

最小字段：

```text
positionSnapshotId
accountId
instrumentId
side
quantity
quantityUnit
averagePrice
markPrice
unrealizedPnl
pnlCurrency
occurredAt
receivedAt
source
qualityStatus
```

规则：

- 对净持仓模式，side 可以为 long、short 或 flat。
- 对双向持仓模式，同一 instrumentId 可以同时存在 long 和 short 记录。
- quantity 必须结合 quantityUnit。
- averagePrice 和 markPrice 缺失时保持缺失。
- unrealizedPnl 是外部或平台当时计算结果，必须记录来源和时间。

## 5. 平台推导与外部事实

第一阶段允许同时存在：

- 由 Fill 推导的内部持仓。
- 外部系统返回的 PositionSnapshot。

两者不一致时：

```text
记录差异
→ 标记 difference_found
→ 进入对账或人工检查
```

不得直接以其中一方无痕覆盖另一方。

## 6. 第一阶段查询需求

必须支持：

- 按 accountId 查询最新余额。
- 按 accountId 查询最新持仓。
- 按 instrumentId 查询账户持仓。
- 显示 dataAsOf、source 和 qualityStatus。
- 标识持仓是否存在对账差异。

## 7. 暂不建设

第一阶段不建设：

- 多层现金子账。
- 复杂保证金模型。
- 跨账户净额结算。
- 证券借贷与抵押品管理。
- 完整托管账户体系。
- 日内逐笔余额账本。

需要时通过新需求和 ADR 增加。

## 8. 验收标准

- Account、Strategy 和 Fund 概念不混用。
- 余额和持仓能从 Crypto 与 MT5 Adapter 标准化进入平台。
- 金融值采用 Decimal 字符串。
- Snapshot 带明确时间、来源和质量状态。
- 外部持仓与内部推导持仓可以对账。
