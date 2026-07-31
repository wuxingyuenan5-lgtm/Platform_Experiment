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

V1 为资费套利和跨所价差至少需要支持 Crypto 与 MT5 账户。Account 应能表达账户来源和基础模式：

```text
sourceType        // crypto_exchange, mt5, fake_gateway, manual_source
accountMode       // spot, margin, perpetual, hedging, netting，按来源适用
tradingMode       // demo, simulation, paper, live
brokerOrVenueName
```

这些字段用于展示、权限和 Adapter 路由，不保存 API Key、密码、Token 或完整登录凭证。

规则：

- Account 不等于 Fund、Portfolio、Book 或 StrategyInstance。
- StrategyInstance 通过 StrategyAccountBinding 使用 Account。
- 密钥、密码和 Token 不存放在普通 Account 主档中。
- 真实 API Key、密码、Token 和 MT5 登录凭证必须进入独立 Secret／Credential 管理边界，Account 只保存非敏感标识和路由信息。
- 同一个外部账户只建立一个平台 Account 主档。
- V1 中一个自营账户在同一 tradingMode 下优先绑定一个主 StrategyInstance；多策略共享同一账户需要显式分摊和归属规则，默认暂缓。

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
externalSnapshotId
rawReference
```

V1 对 Crypto 与 MT5 的账户资金展示至少需要在 Adapter 可获得时补充：

```text
equity
marginUsed
freeMargin
marginLevel
unrealizedPnl
pnlCurrency
snapshotType      // balance, account_equity, margin
```

规则：

- Crypto 账户可能只有 balance、available、locked，也可能有 equity 和 margin 字段。
- MT5 账户至少应尽量映射 Balance、Equity、Margin、Free Margin 和 Margin Level。
- 不同来源缺失的字段保持缺失，不自动按零处理。
- 页面展示合并资金时必须显示 dataAsOf、source 和 qualityStatus。

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
externalSnapshotId
rawReference
```

V1 对跨所价差必须支持 MT5 Position 语义，Adapter 可获得时补充：

```text
externalPositionId
positionMode      // one_way, hedge, netting
externalSide
notionalValue
notionalCurrency
marginUsed
liquidationPrice
sourcePositionType // external_snapshot, platform_derived
```

MT5 场景必须明确：

- Order、Deal 和 Position 是不同对象。
- Hedging 账户可能同一 Instrument 多个方向或多张 Position。
- Netting 账户通常同一 Instrument 只有净持仓。
- PositionSnapshot 只是时间点事实，不替代 Fill、Deal 和平台推导持仓。

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
- 查询 StrategyInstance 绑定账户的最新资金和持仓摘要。
- 支持资费套利的现货腿／永续腿账户展示。
- 支持跨所价差的 Crypto 腿／MT5 腿账户展示。

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
