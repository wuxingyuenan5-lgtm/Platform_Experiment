# V6 PostOnly Chase 受控验收补充

状态：`active / operational acceptance required`  
对应工程：Issue #113 / PR #114  
基础手册：`V6-小资金实盘验收手册.md`  
合成执行合同：`../technical/CROSS_SPREAD_SYNTHETIC_EXECUTION.md`  
更新时间：`2026-07-26`

本文件只补充 PostOnly Chase 的真实主机验收。基础凭证、Market、FOK、Kill Switch、双腿失败处置和 EOD 要求仍以基础手册为准。

## 1. 准入顺序

PostOnly 不得作为第一种真实写入模式。顺序固定为：

```text
只读与历史证据
→ 影子核对
→ 1 oz Market 双向 Open/Close
→ 1 oz FOK 全成交与零成交
→ TP/SL Market/FOK
→ PostOnly Chase
```

任一前置阶段存在未解释 Difference、未知外部仓位或未关闭 Exit Plan，禁止进入 PostOnly。

## 2. 默认配置

开始前保持：

```text
Platform Live Write=false
Runtime Live Write=false
Cross-spread Exit Monitor=false
Bybit PostOnly Chase=false
Cross-spread acceptance max quantity=1 oz
Cross-spread non-closed lifecycle max=1
```

验收窗口中只能由负责人临时、显式开启 PostOnly。结束后必须恢复关闭。

需要记录：

- 负责人和时间窗口；
- Account、StrategyInstance、Symbol 和方向；
- 用户 `limitSpread`；
- 下单前 Bybit Bid/Ask 与 MT5 Bid/Ask；
- Platform 派生的 Bybit 硬价格边界；
- Bybit 真实 Tick Size；
- TTL、最小改单 Tick、最大 Mutation 和 Cooldown；
- Private Stream Credential Reference；
- Kill Switch 与人工撤单/平仓责任人。

不得记录凭证内容。

## 3. 私有流前置检查

保持 Live Write 关闭，验证：

- [ ] Private Order Stream 可订阅目标账户。
- [ ] Private Execution Stream 可订阅目标账户。
- [ ] 事件包含目标 Symbol、Order ID、Order Link ID 和 Execution ID。
- [ ] Chase 子订单共享同一确定性前缀，并有唯一子编号。
- [ ] 其他 Symbol、其他前缀和其他账户事件被忽略。
- [ ] 相同 Execution ID 重放不会重复累计成交量。
- [ ] Malformed Payload 产生明确断线/对账状态，不继续追单。
- [ ] WebSocket 明确失联后停止 Chase，不因 REST 行情仍可读取而继续改单。

CI Stub 不能代替这一步。

## 4. Maker 与硬价格边界

必须确认：

- [ ] Bybit 原生订单为 `Limit + PostOnly`。
- [ ] 买单不主动跨过当前 Ask；卖单不主动跨过当前 Bid。
- [ ] 买单价格不高于 Platform 派生的最大买入边界。
- [ ] 卖单价格不低于 Platform 派生的最低卖出边界。
- [ ] 每次 Amend/Repost 仍满足相同硬边界。
- [ ] Order Link ID 长度和唯一性符合 Venue 要求。

当前硬边界由提交前 MT5 参考价推导；Chase 期间不会动态重算 MT5 参考价。因此该测试只证明 Bybit 单腿 Maker/边界行为，不证明最终合成价差始终等于初始限制。

## 5. 正常全成交路径

每次只允许一个不超过 1 oz 的意图。

1. 选择流动性正常、盘口可观察的窗口。
2. 提交 PostOnly Open。
3. 核对首个子单 ACK，不把 ACK 当 Fill。
4. 观察 Private Order/Execution 事件。
5. 若价格移动达到阈值，核对 Amend；若 Amend 被拒绝，核对先 Cancel、终态确认后才 Repost。
6. 只有去重后的累计 Bybit 成交量精确等于请求量，才允许产生一个 Platform Fill。
7. 只有该 Fill 出现后，才允许提交 MT5。
8. 核对 MT5 数量按实际累计 Bybit Fill 和真实 Contract Size/Step 换算。
9. 核对双边真实 Position 后创建 Exit Plan。
10. 使用 PostOnly Close 重复验证 Reduce-only、Position Index 和 MT5 Position Ticket。
11. 双边真实仓位归零后才标记 `closed`。

## 6. TTL 与最大次数

分别验证：

- [ ] TTL 到期后停止继续追价并请求撤单。
- [ ] 达到最大 Mutation 后停止继续追价并请求撤单。
- [ ] 未达到最小 Tick 距离时不改单。
- [ ] Cooldown 未结束时不改单。
- [ ] 终态 Cancel 未确认前不 Repost。
- [ ] 撤单结果未知时不 Repost。
- [ ] 停止后不会产生第二个业务意图。

## 7. 断线与竞态

真实资金不需要主动制造危险部分成交；可结合最小仓位、受控网络演练和注入 Stub 验证。

必须覆盖：

- Private Stream 在 Working 状态断线；
- Amend ACK 与 Fill 同时到达；
- Cancel ACK 与 Fill 同时到达；
- Cancel 终态之前收到迟到 Execution；
- 重复 Execution；
- 事件序列回退或缺口；
- Private Event 与 REST 终态不一致；
- Runtime 重启、Route Store 丢失或 Terminal 不可用。

验收结果：

- [ ] 断线、序列异常或身份异常后不继续自动 Chase。
- [ ] 只允许一次安全撤单尝试和有界 REST 终态对账。
- [ ] 未确认全成时不提交 MT5。
- [ ] 重复 Execution 不重复增加累计量或 MT5 数量。
- [ ] Cancel/Repost 不产生两个同时活动的 Bybit 子单。
- [ ] 未知状态保留为未知/人工介入，不伪装为零成交。

## 8. 部分成交

当前工程安全口径不是增量 MT5 对冲：

- 部分成交不得生成正常完整 Fill；
- 不得自动提交 MT5；
- 不得继续 Cancel/Repost；
- 必须停止 Chase，并通过 Venue Query 确认累计成交量；
- 残余 Bybit 敞口进入明确人工补偿或风险接管。

必须记录外部 Order、Execution ID、累计数量、成交均价、责任人、补偿动作和最终归零证据。

## 9. TP/SL PostOnly

只有人工 PostOnly Open/Close 验收通过后才测试自动触发。

- [ ] Exit Plan 保存的 TP/SL Execution Mode 与 Limit Strategy 正确。
- [ ] 自动 Trigger 使用原子 Claim 的 `triggerSpread`。
- [ ] 自动 PostOnly 不读取人工 Close 输入。
- [ ] 下单前失败或干净零成交按合同释放 Claim。
- [ ] 部分成交、未知结果或提交后异常不释放 Claim。
- [ ] 自动路径不静默改为 FOK 或 Market。
- [ ] Exit Monitor 测试结束后恢复关闭。

止损优先降低风险时，仍建议使用 Market；PostOnly 止损必须单独评估未成交风险。

## 10. EOD 与复位

PostOnly 测试日必须核对：

- 所有 Chase 子订单及 Order Link 前缀；
- Private Execution ID 去重结果；
- Requested、Cumulative Filled、Remaining Quantity；
- Amend、Cancel、Repost 次数与时间；
- Platform Fill 与 MT5 Deal 是否只在精确全成后出现；
- 外部 Position、FinancialFact、Formal PnL/NAV 和 Reconciliation Difference。

强制复位：

- [ ] Platform Live Write=false。
- [ ] Runtime Live Write=false。
- [ ] Bybit PostOnly Chase=false。
- [ ] Runtime 单笔和单日 Notional=0。
- [ ] Cross-spread Exit Monitor=false。
- [ ] 所有子订单已确认终态。
- [ ] 双边外部仓位已归零或有明确责任人的人工接管。
- [ ] 当日 EOD 完成。

## 11. 不属于本补充的范围

Quote Age、跨 Venue 时间差、Bid/Ask 宽度、MT5 Deviation、未对冲时长、真实价差偏差和费用拆分目前只作为 Markdown 中的待讨论事后订单分析／执行复盘候选。

它们没有被加入交易执行界面，也没有预设最终产品位置。是否开发、哪些属于交易前保护、哪些属于事后分析以及放在哪个页面，由后续产品讨论决定。
