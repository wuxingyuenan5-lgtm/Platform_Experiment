# 对冲基金看板｜商品看板 V1 规格（Commodity V1 Spec）

> 状态：Discussion Draft v0.1  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`  
> 作用：冻结“对冲基金看板 → 商品看板”的产品内容、展示边界与验收口径。  
> 说明：本文件只描述商品看板，不替代整个对冲基金看板 Master Plan。

---

## 1. 范围与全局原则【冻结】

商品看板遵守 Hedge Board 全局 Additive Only 原则：

- 不删除现有内容；
- 不移动现有内容；
- 不改变现有顺序；
- 不重构现有整体 UI；
- 不改变现有视觉组件硬编码；
- 新增内容先统一追加在现有商品页下方；
- 新增组件必须与现有平台视觉风格一致；
- 金融数据硬编码逐步真实化，但视觉组件硬编码不因“去硬编码”而改写。

最终页面顺序、合并与删减，待 Commodity V1 做完并线下验收后再决定。

---

## 2. 既有商品页内容【受保护】

当前商品页已有内容全部保留，包括但不限于：

### 2.1 黄金主图与波动率

- XAUUSD 主图；
- Gold IV / GVZ。

### 2.2 商品 Market Detail

现有覆盖：

- 现货黄金；
- 沪金主力；
- 现货白银；
- 沪银主力；
- 铜；
- 铂；
- 钯；
- 紫金矿业；
- 洛阳钼业；
- 铜陵有色；
- 金银比；
- 金铜比；
- 金油比；
- 金股比；
- BCOM；
- SPGSCI；
- WTI；
- Brent；
- 天然气。

### 2.3 黄金 ETF 与资金流【受保护核心模块】

现有：

- 全球各地区黄金 ETF 每周流入；
- 全球黄金 ETF 年内汇总；
- SPDR Gold Shares 每日流量；
- SPDR 持仓量 vs 黄金价格。

该模块不重做、不删除，只在未来需要时做数据真实化、稳定性与展示状态改进。

### 2.4 央行购金与官方储备【受保护核心模块】

现有：

- 官方黄金储备前十；
- 近一年持续增持的央行。

### 2.5 黄金宏观驱动【受保护】

现有：

- 金价 vs 10Y 名义利率；
- 金价 vs 10Y Breakeven；
- 金价 vs 10Y 实际利率；
- Gold vs DXY。

---

## 3. Commodity V1 新增内容总览【冻结】

在现有商品页内容下方新增：

1. Futures Curve / Term Structure
2. Inventory / Physical
3. Positioning / CFTC
4. Cross-Market Spreads
5. Commodity Volatility

V1 不新增农产品模块。

---

## 4. Futures Curve / Term Structure【冻结】

目标：展示商品特有的期限结构与近远月定价，而不是只看单一连续合约价格。

### 4.1 WTI

新增：

- 当前 WTI 期货曲线；
- M1-M2 spread；
- M1-M3 spread。

用于观察：

- Backwardation；
- Contango；
- 近端供需紧张程度。

### 4.2 Brent

新增：

- 当前 Brent 期货曲线；
- M1-M2 spread；
- M1-M3 spread。

### 4.3 Copper

新增：

- 当前铜期货期限结构；
- 近月/远月 spread。

### 4.4 Gold

黄金期限结构可保留为可选补充，但 V1 优先级低于原油和铜。

---

## 5. Inventory / Physical【冻结】

目标：补充商品供需与实物层信息，保持高信号、不过度扩展。

### 5.1 原油

优先：

- EIA U.S. Commercial Crude Oil Inventories；
- Cushing Crude Oil Inventories；
- Gasoline Inventories；
- Distillate Inventories。

### 5.2 铜

优先：

- LME Copper Stocks；
- COMEX Copper Stocks；
- SHFE Copper Inventory / Warehouse Receipts。

### 5.3 黄金

黄金已经有 ETF 持仓和央行储备两套强资金/持仓数据。

COMEX Gold Inventory 仅在能够获得稳定、免费、口径清晰的数据源时新增；否则不强制。

---

## 6. Positioning / CFTC【冻结】

V1 只覆盖核心商品：

- Gold；
- Silver；
- Copper；
- WTI；
- Natural Gas。

每个品种优先展示：

- Managed Money Net Position；
- Commercial Net Position；
- Net Position Historical Percentile。

目标：判断趋势资金拥挤度与持仓结构。

不在 V1 展示 CFTC 全量字段。

---

## 7. Cross-Market Spreads【冻结】

现有金银比、金铜比、金油比、金股比全部保留。

新增优先级：

### 7.1 Copper

- COMEX Copper vs LME Copper；
- SHFE Copper vs LME Copper。

未来如有明确需求，再考虑中国铜进口窗口等更复杂计算。

### 7.2 Crude Oil

- Brent - WTI spread。

### 7.3 Precious Metals

在免费稳定数据源可用时，考虑：

- 沪金 vs 国际黄金；
- 沪银 vs 国际白银。

V1 不强制为补齐而使用不稳定数据源。

---

## 8. Commodity Volatility【冻结为精简模块】

宏观看板不新增独立波动率模块；商品看板可以保留商品自身波动率。

V1 只优先：

- Gold：GVZ（现有，保留）；
- Oil：OVX。

Copper volatility 等若无稳定免费数据源，不在 V1 强制实现。

---

## 9. Gold Flow Stack【冻结】

黄金是商品页中数据结构最完整的子模块，V1 按以下逻辑保留并补强：

```text
Gold Price
   ↓
Gold ETF Flow
   ├─ Global weekly net flow
   ├─ Regional flow
   ├─ YTD flow
   └─ SPDR daily flow / holdings
   ↓
Official Sector
   ├─ Central bank holdings
   └─ Central bank buying
   ↓
Macro Drivers
   ├─ Real yield
   ├─ Nominal yield
   ├─ Inflation expectations
   └─ DXY
   ↓
Positioning
   └─ CFTC Gold
```

V1 不继续增加大量黄金 ETF、矿企产量或新闻模块。

---

## 10. 商品覆盖与开发重点【冻结】

| 商品 | V1 重点 |
|---|---|
| 黄金 | ETF资金流、央行购金、实际/名义利率、DXY、CFTC |
| 白银 | 金银比、CFTC、国内外价格结构 |
| 铜 | 库存、期限结构、COMEX/LME/SHFE、CFTC |
| WTI/Brent | 库存、期限结构、Brent-WTI、CFTC、OVX |
| 天然气 | 库存、期限结构、CFTC |
| 铂/钯 | 先保留价格，不扩展复杂基本面 |
| 农产品 | V1 不纳入 |

---

## 11. Market Detail 真实化【方向冻结】

商品 Market Detail 继续沿用现有视觉与列结构。

后续逐步真实化：

- 最新/收盘值；
- 1D；
- 1W；
- 1M；
- QTD；
- YTD；
- 1Y；
- 52W High；
- 30D Sparkline。

每一行使用 canonical series，并尽量让当前值、收益率和 30D Sparkline 来自同一主数据源。

视觉组件不因数据真实化而重构。

---

## 12. 数据源原则【冻结】

商品看板继续遵循 Hedge Board 全局免费数据源优先原则：

- 免费；
- 稳定；
- 官方 Source of Record 优先；
- 可通过 AKShare 统一接入且口径稳定的数据可优先复用 AKShare；
- 官方 API 更稳定或 AKShare 上游不可靠时直接使用官方免费源；
- TradingView 仅作展示，不作为项目数据抓取源；
- Provider 失败不得用假数据替代；
- 无可靠免费源时返回 `not_configured`。

数据源细节后续单独进入 `COMMODITY_DATA_SOURCE_MAP.md` 讨论。

---

## 13. 当前不做【冻结】

Commodity V1 不新增：

- 农产品；
- 大量矿企基本面；
- 新闻流；
- 大规模商品宏观解释变量；
- 大量商品 IV 指标；
- 为补齐页面而使用不稳定或不明确授权的数据源。

---

## 14. 后续讨论项【OPEN】

1. WTI / Brent / Copper 期限结构具体展示形态；
2. EIA库存是否用绝对量 + WoW变化双展示；
3. LME / COMEX / SHFE 铜库存的最终统一单位；
4. CFTC Managed Money / Commercial 的具体 contract mapping；
5. COMEX-LME、SHFE-LME 铜价差的汇率、单位与合约期限对齐；
6. 沪金/国际金、沪银/国际银跨市场价差是否进入 V1；
7. OVX 的免费数据源；
8. 商品 Market Detail 各行 Primary/Fallback；
9. Commodity V1 最终页面顺序与线下验收后删减。
