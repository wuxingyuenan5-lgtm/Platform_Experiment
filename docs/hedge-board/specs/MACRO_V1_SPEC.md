# 对冲基金看板｜宏观看板 V1 规格（Macro V1 Spec）

> 状态：Product Scope Frozen v1.0 / Engineering IN PROGRESS  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 数据源文档：`docs/hedge-board/specs/MACRO_DATA_SOURCE_MAP.md`  
> 适用分支：`feature/hedge-board-online-optimization`  
> 说明：本文件只描述宏观看板，不替代整个 Hedge Board Master Plan。

---

## 1. 全局原则【冻结】

宏观看板严格遵守 Hedge Board 全局 Additive Only：

- 不删除现有内容；
- 不移动现有内容；
- 不改变现有顺序；
- 不重构现有整体 UI；
- 不改变视觉组件硬编码；
- 新内容先追加在现有页面下方；
- 新增组件必须与现有平台视觉风格一致；
- 金融数据硬编码逐步真实化，但视觉组件不因“去硬编码”被重写。

最终页面顺序、合并与删减，等 V1 做完并线下验收后再决定。

当前阶段：**Owner 已于 2026-09-02 明确要求继续执行，Macro V1 工程进行中；冻结产品范围不变。**

---

## 2. Macro V1 新增结构【冻结】

开发期逻辑顺序：

1. Growth
2. Inflation
3. Rates
4. Global M2
5. Risk Appetite
6. Market Expectations / Event Probability

不新增独立 Macro Volatility Section。

现有美元净流动性、Macro Market Detail 和其他既有宏观内容全部保留。

---

## 3. Growth【冻结】

保持精简，不做宏观数据库大全。

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

CFNAI 保留较快响应，CFNAIMA3 作为趋势平滑辅助。

V1 不继续加入 PMI、零售、地产、耐用品、非农等大量指标。

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

### 4.2 Upstream Inflation

单独一张图：

- PPI YoY

页面命名采用“上游通胀 / Upstream Inflation”，不把 PPI 定义成永远领先 CPI 的指标。

### 4.3 Actual vs Market-Implied Inflation

使用曲线图展示。

主序列：

- CPI YoY
- Core CPI YoY
- 5Y Breakeven
- 10Y Breakeven

辅助序列：

- 5Y5Y Forward Inflation

允许在状态区显示：

- 5Y BE - CPI YoY
- 10Y BE - CPI YoY

命名为 `Inflation Pricing Gap` 或同等不误导表述，并明确：该差值只是当前实际通胀与中长期市场隐含定价的状态比较，不是预测误差。

---

## 5. Rates【冻结】

### 5.1 Short-End Rate Corridor

使用一张多序列图，不拆多个 Section。

固定：

- Fed Target Lower
- Fed Target Upper
- IORB
- ON RRP Award Rate
- EFFR
- SOFR

### 5.2 Treasury Yields

严格只保留：

- 3M
- 2Y
- 10Y
- 30Y

Macro V1 不增加 5Y、7Y、20Y、2s10s、3m10y。

---

## 6. Liquidity / Global M2【冻结】

现有美元净流动性保留，不扩展成复杂流动性指标群。

只新增 Global M2 Proxy。

### 6.1 公式

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

计算前统一：

- 货币单位；
- 数量级；
- 观察月份；
- FX 报价方向。

最终统一到 USD billion 或 USD trillion 后聚合。

### 6.3 时间对齐

使用五个地区均有有效观测值的最近共同月份。

### 6.4 汇率

月度货币量转换使用对应月份的月平均 FX rate。

### 6.5 展示

至少展示：

- Global M2 Level
- Global M2 YoY

Tooltip / 辅助信息应能够查看各地区成分规模或贡献。

Global M2 必须标记为 `proxy / methodology-based derived series`，不是官方统一全球 M2 指标。

---

## 7. Risk Appetite【冻结】

只新增：

1. US High Yield OAS
2. HYG / LQD Ratio

建议两个独立图表，不强行共用一个纵轴。

V1 不继续加入更多 risk-on / risk-off 指标。

---

## 8. Macro Volatility【冻结】

不新增独立 Volatility Section。

现有 VIX、MOVE 等不删除，但本次不扩展宏观波动率体系。

未来波动率优先回归对应资产页。

---

## 9. Market Expectations / Event Probability【冻结】

### 9.1 产品形态

Macro V1 保留并完善原有：

**Polymarket 当前概率 + 历史概率曲线**

不以 CME FedWatch 矩阵作为 V1 核心展示。

目标快速展示：

- 当前概率；
- 历史概率曲线；
- 1D / 7D 概率变化；
- liquidity；
- volume（稳定可取时）；
- expiry / resolution date；
- source；
- updated_at；
- status。

### 9.2 数据模型

正式展示必须显式区分：

1. Event / Market metadata
2. outcome
3. current probability
4. token id
5. historical probability series

采用显式白名单，例如：

`platform-data/config/macro_events.yaml`

禁止继续使用“拉取大量市场 → 标题关键词分类 → 自动塞进页面”的旧逻辑作为正式发布链路。

### 9.3 事件类别

优先：

1. Monetary Policy
2. Macro Economy
3. Financial Markets
4. Policy / Geopolitics

Election 不作为固定默认类别；只有明确影响金融市场且被白名单选中时才展示。

### 9.4 数量控制

主页面只保留少量高相关、高流动性的主流金融事件。

建议同屏控制在约 6–8 个 active events，最终数量在线下页面验收时再定。

---

## 10. Macro Market Detail【冻结】

### 10.1 总原则

现有行全部先保留。

不删除、不重命名、不重新排序。

优先真实化现有静态金融数据、假收益率和假 30D Sparkline。

### 10.2 日频市场数据

适合完整真实化：

- VIX
- DSPX（前提是稳定合法免费源可用）
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

尽可能计算：

- latest / close
- 1D
- 1W
- 1M
- QTD
- YTD
- 1Y
- 52W High distance
- 30D Sparkline

### 10.3 政策 / 流动性数据

现有：

- DFF
- SOFR
- WALCL
- TGA
- RRP
- Net Dollar Liquidity

按指标本身语义展示变化；利率类优先使用 bp，而不是机械套股票收益率百分比。

### 10.4 低频宏观数据

现有：

- CPI
- PCE
- UNRATE
- US M2

必须 frequency-aware：

- 没有新 observation 时，1D / 1W 不显示 `0.00%` 冒充“没变”；
- 无可比较 observation 时显示 `—`；
- 30D 内不足以形成真实曲线时不画假平线。

### 10.5 30D Sparkline

继续使用现有 SVG Sparkline 视觉组件。

数据来自对应 canonical series 的真实历史观测。

不同 Market Detail 行允许使用不同 Primary Provider；不要求全部来自一个网站。

---

## 11. 图表通用展示能力【冻结】

### 11.1 Data Freshness

每个新增宏观图尽可能显示：

- Latest observation date
- Frequency
- Updated / retrieved time
- stale 状态

### 11.2 Latest vs Previous

低频宏观数据优先补充：

- latest
- previous
- delta / change

### 11.3 默认时间窗口

按数据频率设合理默认窗口，而不是所有图统一周期。

建议基线：

- Treasury / SOFR / Breakeven：1Y
- Claims：2Y
- CPI / PCE / PPI：5Y
- CFNAI：5Y
- GDP：10Y
- Global M2：10Y
- Polymarket：30D / All

### 11.4 不做 Event Marker

Macro V1 不增加 CPI / FOMC / NFP 等 Release / Event Marker。

原因：增加数据维护和图表复杂度，当前收益不足。

---

## 12. 数据源原则【冻结】

详细 Source Map 见：

`docs/hedge-board/specs/MACRO_DATA_SOURCE_MAP.md`

总体原则：

- 只用免费数据源作为 V1 基础；
- 统一 canonical contract，而不是强制统一 Provider；
- AKShare 能稳定、清晰获取的数据可优先复用；
- 官方 API 更稳定或 AKShare 上游陈旧时直接用官方免费源；
- 官方源可作为 Primary、Fallback 或 Cross-check，按数据集实际情况决定；
- 记录 upstream source；
- TradingView 只负责展示，不抓数据；
- 没有可靠免费链路时宁可 `not_configured`，不造数据。

---

## 13. 当前状态【冻结】

Macro V1 产品范围已经冻结。

当前已进入实施阶段；产品范围仍冻结，工程只按本规格和 Source Map 增量落地。

后续重新进入 Macro 工程开发时：

1. 先读取 Master Plan；
2. 再读取本 Spec；
3. 再读取 Macro Data Source Map；
4. 按独立 Phase 实施；
5. 不得影响 Deferred 的美股、A股、全球、交易工具页面；
6. 最终由用户线下验收。
