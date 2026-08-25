# 对冲基金看板｜宏观看板 V1 规格（Macro V1 Spec）

> 状态：Discussion Draft v0.1  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`  
> 作用：冻结“对冲基金看板 → 宏观看板”的产品内容、展示边界与验收口径。  
> 说明：本文件只描述宏观看板，不替代整个对冲基金看板 Master Plan。

---

## 1. 范围与开发原则【冻结】

当前只讨论并优化 `/hedge-board/macro`。

必须遵守上位 Master Plan 的 Additive Only 原则：

- 不删除现有内容；
- 不移动现有内容；
- 不改变现有顺序；
- 不重构现有整体 UI；
- 不改变现有视觉组件硬编码；
- 新内容以追加方式进入页面；
- 新增组件必须与现有平台视觉风格一致；
- 金融数据硬编码逐步真实化，但视觉组件硬编码不因“去硬编码”而改写。

开发期新增 Section 统一先追加在现有内容下方；真正的最终顺序、合并与删减，待 Macro V1 全部做完并线下验收后再决定。

---

## 2. Macro V1 新增内容总览【冻结】

开发期逻辑顺序：

1. Growth
2. Inflation
3. Rates
4. Global M2
5. Risk Appetite
6. Market Expectations / Event Probability

不新增独立 Macro Volatility Section。

现有美元净流动性、现有 Market Detail、现有其他宏观内容全部保留。

---

## 3. Growth【冻结】

目标是用少量高信号指标判断美国增长状态，不建设宏观数据库大全。

### 3.1 Growth / Production

同一张图：

- Real GDP YoY
- Industrial Production YoY

### 3.2 Labor

单独一张图：

- Initial Claims 4W MA

### 3.3 Broad Economic Activity

同一张图：

- CFNAI
- CFNAIMA3

CFNAI 保留较快响应，CFNAIMA3 作为趋势平滑辅助线。

不在 V1 继续加入 PMI、零售、地产、耐用品、非农等大量指标。

---

## 4. Inflation【冻结】

必须明确区分：

- Actual Inflation
- Upstream Inflation
- Market-Implied Inflation

### 4.1 Actual Inflation

同一张曲线图：

- CPI YoY
- Core CPI YoY
- PCE YoY
- Core PCE YoY

目的：同时观察 Headline vs Core、CPI 体系 vs PCE 体系。

### 4.2 Upstream Inflation

单独一张图：

- PPI YoY

页面命名采用“上游通胀 / Upstream Inflation”，不将 PPI 绝对定义为永远领先 CPI 的指标。

### 4.3 Actual vs Market-Implied Inflation

采用曲线图展示。

主序列：

- CPI YoY
- Core CPI YoY
- 5Y Breakeven
- 10Y Breakeven

辅助序列：

- 5Y5Y Forward Inflation

允许在图表状态区显示：

- 5Y BE - CPI YoY
- 10Y BE - CPI YoY

但必须命名为 `Inflation Pricing Gap` 或同等不误导的表述，并明确：该差值只用于比较当前实际通胀与市场中长期隐含定价，不代表预测误差。

---

## 5. Rates【冻结】

### 5.1 Short-End Rate Corridor

使用一张多序列图，不拆成多个 Section。

固定序列：

- Fed Target Lower
- Fed Target Upper
- IORB
- ON RRP Award Rate
- EFFR
- SOFR

目标：同时观察政策利率区间、准备金定价、隔夜工具以及实际货币市场成交利率。

### 5.2 Treasury Yields

严格只保留四个期限：

- 3M
- 2Y
- 10Y
- 30Y

Macro V1 不增加：

- 5Y
- 7Y
- 20Y
- 2s10s
- 3m10y

Treasury 官方数据优先，FRED 可作为权威分发或 fallback；具体 Source Map 另行冻结。

---

## 6. Liquidity / Global M2【冻结】

现有美元净流动性保留，不扩展成复杂流动性指标群。

只新增 Global M2 Proxy。

### 6.1 公式

固定公式：

```text
globalM2 =
  cnm2 * cnyusd
+ usm2
+ eum2 * eurusd
+ jpm2 * jpyusd
+ gbm2 * gbpusd
```

覆盖：

- China M2
- US M2
- Euro Area M2
- Japan M2
- UK M2

### 6.2 统一口径

计算前必须统一：

- 货币单位；
- 数量级；
- 观察月份；
- FX 报价方向。

最终建议统一成 USD trillion 或 USD billion 后聚合。

### 6.3 时间对齐

使用五个地区均有有效观测值的最近共同月份。

不得把不同月份的数据直接拼成某一个“最新月份 Global M2”。

### 6.4 汇率

月度货币量转换使用对应月份的月平均 FX rate，避免单一月末汇率造成不必要的短期跳变。

### 6.5 展示

至少展示：

- Global M2 Level
- Global M2 YoY

其中 Global M2 必须标记为 `proxy / methodology-based derived series`，而不是官方统一全球 M2 统计。

---

## 7. Risk Appetite【冻结】

保持极简，只新增两项：

1. US High Yield OAS
2. HYG / LQD Ratio

建议使用两个独立图表，不强行共用一个纵轴。

不在 Macro V1 继续增加第三个或更多 risk-on / risk-off 指标。

---

## 8. Macro Volatility【冻结】

Macro V1 不新增独立 Volatility Section。

现有页面已有的 VIX、MOVE 等内容不删除，但本次不扩展宏观波动率体系。

未来波动率优先回归对应资产页。

---

## 9. Market Expectations / Event Probability【冻结】

### 9.1 产品形态

Macro V1 保留并完善原有“Polymarket 概率 + 历史概率曲线”的视觉形态。

不以 CME FedWatch 概率矩阵作为 Macro V1 的核心展示。

目标是让用户能快速看到：

- 当前事件概率；
- 概率随时间的变化；
- 1D / 7D 概率变化；
- 市场流动性与交易活跃度；
- 事件到期 / 结算时间；
- 数据来源与更新时间。

### 9.2 数据获取模型

Polymarket 数据链必须显式区分：

1. Event / Market metadata
2. 当前 outcome probability
3. CLOB token id
4. 历史 probability series

实现原则：

```text
explicit whitelist event / market id or slug
        ↓
Polymarket Gamma metadata
        ↓
outcomes / outcomePrices / clobTokenIds
        ↓
YES token or selected outcome token
        ↓
Polymarket CLOB price history
        ↓
probability history curve
```

不得继续采用“拉取大量市场 → 按标题关键词分类 → 自动塞入页面”的旧逻辑作为正式展示链路。

### 9.3 历史概率曲线

曲线必须来自真实 Polymarket historical price / probability series。

不得：

- 由当前概率随机生成历史曲线；
- 用占位 sparkline 冒充历史概率；
- 将无历史记录的市场展示为稳定概率曲线。

二元市场默认使用 YES token 概率。

多结果事件如存在多个互斥 outcome，应保留 outcome 与 token 的明确映射；若现有视觉组件不能在不重构 UI 的情况下显示多条 outcome 曲线，V1 可按独立 outcome 卡展示，而不是破坏现有组件。

### 9.4 白名单机制

正式展示必须由显式配置驱动，例如：

`platform-data/config/macro_events.yaml`

每个跟踪项至少应包含：

- id
- provider
- event_id / market_id / slug
- label
- category
- outcome / token selection
- enabled
- expiry
- minimum_liquidity（如适用）

可以建立“候选事件发现”任务辅助找新市场，但候选事件不得未经配置直接发布到宏观看板。

### 9.5 V1 事件类别

优先展示与主流金融市场最相关的事件，建议类别：

1. Monetary Policy
   - Fed rate decision / rate cut / rate hike / target range related markets

2. Macro Economy
   - recession / inflation / growth / major macro threshold related markets

3. Financial Markets
   - major equity index、Treasury yield、USD、gold、BTC 等具有明确金融市场意义的重大阈值或年度事件

4. Policy / Geopolitics
   - 仅保留对全球金融资产定价具有明显影响的关税、制裁、重大地缘冲突、重大财政或监管事件

Election 类事件不作为固定默认类别；只有在对金融市场具有明显影响并被显式加入白名单时才展示。

### 9.6 卡片信息

每张 Event Probability 卡原则上保留：

- 事件标题 / question
- 当前概率
- 历史概率曲线
- 1D probability change
- 7D probability change
- liquidity
- volume（数据可稳定获得时）
- expiry / resolution date
- source
- updated_at
- status

页面信息密度以现有 MacroExpectationPanel 的视觉结构为基准，不因补字段重构视觉组件。

### 9.7 数量控制

Macro V1 目标是“主流、高信号、可扫盘”，不是预测市场大全。

默认展示数量应保持克制，优先少量高流动性、高市场相关性的事件；最终数量在页面线下验收时再决定。

---

## 10. Macro Market Detail【冻结】

### 10.1 总原则

现有 Macro Market Detail 所有行先保留。

V1 不主动删除、重命名或重新排序现有行，也不因为新增研究 Section 就把所有新指标重复塞进 Market Detail。

优先任务是把现有静态金融数据、假收益率和假 30D sparkline 真实化。

### 10.2 A 类：日频市场数据，完整真实化

适用现有行：

- VIX
- DSPX（以能否取得稳定合法数据源为前提）
- DXY
- US 2Y
- US 10Y
- US 30Y
- China 2Y
- China 10Y
- China 30Y
- USDCNH
- TLT
- HYG
- MOVE
- 10Y TIPS Real Yield
- 10Y Breakeven Inflation

尽可能真实计算 / 展示：

- latest / close
- 1D
- 1W
- 1M
- QTD
- YTD
- 1Y
- 52W High distance
- 30D sparkline

### 10.3 B 类：政策 / 流动性日周频数据

适用现有行：

- DFF
- SOFR
- WALCL
- TGA
- RRP
- Net Dollar Liquidity

必须按指标本身的金融语义展示变化。

利率类变化优先以 bp 变化解释，而不是机械套股票收益率百分比。

### 10.4 C 类：低频宏观数据

适用现有行：

- CPI
- PCE
- UNRATE
- US M2

必须 frequency-aware。

月频数据在没有新 observation 时：

- 不把 1D / 1W 显示成 `0.00%` 冒充“没有变化”；
- 无有效比较 observation 的周期显示 `—` 或明确 no comparable observation；
- 30D 内不足以形成真实曲线时，不画假平线。

### 10.5 30D Sparkline

继续使用现有 SVG Sparkline 视觉组件。

数据来源必须是对应 canonical series 的最近约 30 个真实有效日度观测值。

不同 Market Detail 行允许使用不同 Primary Provider；不强制所有行从同一个网站获取。

当前值、收益率与 30D 曲线应尽量使用同一 canonical series 和同一价格 / 收益率口径。

### 10.6 技术状态列

当前 1H / 4H / 日线 / 3日线 / 周线技术箭头不作为 Macro V1 本轮优化目标。

不扩展假信号，不在本阶段重新设计算法。

最终是否保留、真实化或删减，待整体页面完成后线下验收决定。

---

## 11. 数据时效定位【冻结】

`platform-data` 当前定位是 Macro V1 的稳定数据生产与历史存储层，不承担实时 tick / 毫秒级行情数据库职责。

Macro V1 目标：

- 市场行情类：最新有效市场 / 官方日度值；
- 日频利率类：最新官方日值；
- 周频数据：最新发布 observation；
- 月频 / 季频：最新正式 observation；
- 所有序列明确 as_of、retrieved_at、frequency、stale 状态。

未来如需真正盘中实时行情，应使用独立实时市场数据服务，不依赖 GitHub Actions 冒充实时 feed。

---

## 12. 数据架构【继承 Master Plan】

统一链路：

```text
External Sources
    ↓
platform-data
    ↓
normalize / derive / validate / store / LKG
    ↓
versioned canonical output
    ↓
platform-api
    ↓
Platform Web
    ↓
existing UI components
```

前端不直接抓取 FRED、Treasury、Polymarket、Yahoo、TradingView 或其他外部数据源。

---

## 13. 开发阶段建议【当前基线】

1. Phase 1A — Market Expectations / Event Probability 真实数据链
2. Phase 1B — Macro Market Detail 真实化 + 30D Sparkline
3. Phase 1C — Growth
4. Phase 1D — Inflation
5. Phase 1E — Rates
6. Phase 1F — Global M2
7. Phase 1G — Risk Appetite
8. Phase 1H — Macro 整体数据质量、状态、UI一致性与回归验收
9. Offline Acceptance
10. Macro V1 Freeze

开发期 Section 顺序只是临时逻辑顺序；最终页面顺序、删减和合并在完整页面线下验收后决定。

---

## 14. 当前仍需后续数据工程冻结的事项【OPEN】

产品规格层已基本确定，以下转入 Data Source Map / 工程规格讨论：

1. 每个 Growth / Inflation / Rates 序列的 Primary / Fallback Provider；
2. Global M2 各地区 M2 与 FX 的精确 series id；
3. Global M2 历史修订与共同月份对齐实现；
4. HYG / LQD 的 adjusted price 数据源；
5. HY OAS 的 Primary / Fallback；
6. Macro Market Detail 每行完整 Source Map；
7. DSPX / MOVE / DXY / 中国国债等公开数据源稳定性；
8. Polymarket whitelist 的首批具体 event / market id；
9. Polymarket 卡片默认 history window 与更新频率；
10. 每个序列 stale threshold；
11. GitHub Actions 更新频率和失败 / LKG 策略的具体参数。

这些 OPEN 项不得由执行 Agent 随意改变上述已冻结产品定义。
