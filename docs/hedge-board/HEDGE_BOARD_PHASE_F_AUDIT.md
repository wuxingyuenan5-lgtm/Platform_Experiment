# 对冲基金看板｜Phase F 数据与参考入口审计

> 状态：Initial Audit v0.6 / Engineering NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 可行性原则：`docs/hedge-board/HEDGE_BOARD_DATA_FEASIBILITY_AND_MAINTENANCE.md`  
> 实施计划：`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`  
> 适用分支：`feature/hedge-board-online-optimization`

---

## 1. Phase F 产品边界【冻结】

### 1.1 Trading Tools 只读

`/hedge-board/trading-tools/*` 继续保持 Deferred：

- 不开发；
- 不重构；
- 不改 UI；
- 不处理其元数据；
- Phase F 只读其中现有 `name / url / description / domain / tags`，把它作为现成参考网站库。

不建设第二套 Reference Links。

### 1.2 子页旧“交易工具”模块未来退出

Macro / Commodity / Crypto V1 完善后，子页不再重复展示整块 Trading Tools 目录。

最终目标：

```text
Native 数据 / 图表
+
少量精准 External Reference Button
```

当前不删除旧模块；实际删除/隐藏必须等对应 V1 完成并线下验收后处理。

### 1.3 最终判定状态

- `NATIVE_READY`：明确、低维护、可自动化；
- `NATIVE_CANDIDATE`：路线可行，仍需 live request / rights / schema 验证；
- `EXTERNAL_LINK`：不值得自建，跳转成熟原站；
- `OFFICIAL_EMBED`：官方 Widget 明显优于 Native / Link 时使用；
- `OPEN`：仍需研究；
- `NOT_CONFIGURED`：既无合理 Native 链路，也无合适参考入口。

核心原则：**好落地的自己落地；不好落地的直接给参考网站按钮。**

---

# 2. Macro 审计

| 数据/模块 | 状态 | Native 来源 | 维护判断 |
|---|---|---|---|
| GDP / CPI / Core CPI / PCE / Core PCE / PPI / UNRATE / M2 / Breakeven / HY OAS | `NATIVE_READY` | FRED / 官方上游 | 低 |
| UST 3M / 2Y / 10Y / 30Y | `NATIVE_READY` | U.S. Treasury | 低 |
| 10Y Real Yield | `NATIVE_READY` | Treasury / FRED fallback | 低 |
| SOFR / EFFR | `NATIVE_READY` | NY Fed / FRED fallback | 低 |
| Fed Target / IORB / ON RRP Award | `NATIVE_READY` | Fed / FRED | 低 |
| CFNAI / CFNAIMA3 | `NATIVE_READY` | FRED / Chicago Fed | 低 |
| Polymarket 概率 + 历史 | `NATIVE_READY` | Gamma + CLOB `prices-history` | 中，主要在 whitelist/token mapping |
| CME FedWatch | `EXTERNAL_LINK` | Trading Tools 精确页面 | 低 |
| MacroMicro复杂交叉图 | `EXTERNAL_LINK` | Trading Tools | 低 |
| TradingEconomics / 金十 / 奇货可查总览 | `EXTERNAL_LINK` | Trading Tools | 低 |

## 2.1 Global M2

| 组成 | 状态 | 来源 | 结论 |
|---|---|---|---|
| US M2 | `NATIVE_READY` | FRED / Fed | 成熟 |
| Euro Area M2 | `NATIVE_READY` | ECB SDMX API | JSON/CSV |
| Japan M2 | `NATIVE_READY` | BOJ Time-Series API | JSON/CSV |
| UK M2 | `NATIVE_READY` | BoE IADB CSV | 实施时最终复核 series 口径 |
| China M2 | `NATIVE_CANDIDATE → 高概率Native` | AKShare `macro_china_money_supply` + PBOC核验 | 重点防 stale / upstream停更 |
| FX | `NATIVE_READY` | ECB reference FX | 月均本地计算 |

### China M2 官方核验基准

2026 年 7 月金融统计数据报告的官方来源口径为：

- observation month：2026-07；
- M2 balance：355.51 万亿元；
- M2 YoY：7.7%；
- report date：2026-08-14。

实施时 AKShare 最新一行必须至少通过：

```text
observation_month == latest PBOC month
value ≈ official PBOC value
upstream provenance recorded
stale gate passed
```

AKShare 函数成功返回不等于数据最新。

### Macro 结论

Macro 核心数据基本不存在结构性获取障碍，是三个 V1 中最适合优先 Native 的模块。

---

# 3. Commodity 审计

| 数据/模块 | 状态 | Native 来源 | 维护判断 |
|---|---|---|---|
| EIA crude / Cushing / gasoline / distillate | `NATIVE_READY` | EIA API v2 | 低 |
| CFTC Gold / Silver / Copper / WTI / NatGas | `NATIVE_READY` | CFTC PRE API | 低 |
| Gold ETF monthly regional/fund flow | `NATIVE_CANDIDATE + EXTERNAL_LINK fallback` | WGC monthly XLSX / page | 中 |
| Gold ETF weekly flow | `NATIVE_CANDIDATE + EXTERNAL_LINK fallback` | WGC weekly page/data chain | 中 |
| SPDR holdings / daily flow | `NATIVE_READY` | SPDR Historical Archive XLSX/API | 中低 |
| CME Gold stocks | `NATIVE_READY` | `delivery_reports/Gold_Stocks.xls` | 低中 |
| CME Silver stocks | `NATIVE_READY` | `delivery_reports/Silver_stocks.xls` | 低中 |
| CME Copper stocks | `NATIVE_READY` | `delivery_reports/Copper_Stocks.xls` | 低中 |
| LME monthly warehouse stocks / queue | `NATIVE_READY` | LME公开月度XLSX | 中 |
| LME daily 2-day delayed breakdown | `EXTERNAL_LINK` | LME页面涉及登录/注册 | 高 |
| LME historical price / full prompt curve | `EXTERNAL_LINK` | LME / SMM / 奇货可查 | 高 |
| WTI current futures curve | `NATIVE_CANDIDATE / EXTERNAL_LINK fallback` | CME公开settlement网页/未文档化JSON链候选 | 中高 |
| Brent current futures curve | `NATIVE_CANDIDATE / EXTERNAL_LINK fallback` | ICE公开多到期月 delayed quotes | 中高 |
| COMEX-LME / SHFE-LME | `EXTERNAL_LINK优先` | SMM / 奇货可查 | 高 |
| 国内跨期 / 库存 / 仓单 | `NATIVE_CANDIDATE` | AKShare + SHFE/INE | 中 |
| GVZ | `NATIVE_READY` | Cboe | 低 |
| OVX | `NATIVE_READY` | Cboe | 低 |
| CVOL / 高级金属期权 | `EXTERNAL_LINK` | CME CVOL / option pages | 低 |

## 3.1 WGC

WGC 当前公开信息确认：

- ETF holdings / flows 网页更新；
- 月度提供 XLSX；
- 数据覆盖 100+ physically-backed products；
- 但部分图表存在登录提示；
- 本轮直接月度 XLSX 下载测试出现 403。

因此 WGC 暂不升级 `READY`。

策略：

```text
稳定公开数据链验证成功 → NATIVE
否则 → WGC External Link
```

不为 WGC 使用登录自动化或脆弱网页逆向。

## 3.2 SPDR

SPDR GLD Historical Archive 的官方下载目标实际返回 XLSX，说明链路明显优于网页解析。

结论：`NATIVE_READY`。

## 3.3 CME 金属库存

Registrar Reports 页面公开 Gold / Silver / Copper Stocks 链接；本轮逐项点击均返回 Excel：

```text
https://www.cmegroup.com/delivery_reports/Gold_Stocks.xls
https://www.cmegroup.com/delivery_reports/Silver_stocks.xls
https://www.cmegroup.com/delivery_reports/Copper_Stocks.xls
```

因此当前值及今后每日归档可以 Native。

历史回补能力单独评估，不影响“从现在开始自动存储”。

## 3.4 LME

月度 Warehouse Company Stocks and Queue Data 的 XLSX 可以无登录直接下载，因此月度库存 `NATIVE_READY`。

日度两日延迟 stock breakdown 仍涉及登录/注册，不建立登录抓取链，直接外链。

## 3.5 WTI Curve

需要特别区分：

- CME 产品结算网页：午夜 CT 后可免费查看；
- CME DataMine flat-file：不能假设免费，当前存在数据/许可费用；
- CME网页底层历史上存在 `CmeWS/mvc/Settlements/...` JSON 请求模式，但该接口不是正式稳定 API，不可直接视为生产级 Source of Record。

因此 WTI curve 仍为 `NATIVE_CANDIDATE`。

只有当实施环境验证公开结算表/JSON链在 GitHub Actions 稳定、允许使用且无高维护风险时才 Native；否则 External Link。

## 3.6 Brent Curve

ICE Brent 数据页公开多个合约到期月，但网页抓取层未直接暴露稳定结构化表。

暂保留 `NATIVE_CANDIDATE / EXTERNAL_LINK fallback`，不做脆弱逆向承诺。

---

# 4. Crypto 审计

| 数据/模块 | 状态 | Native 来源 | 维护判断 |
|---|---|---|---|
| BTC / ETH spot | `NATIVE_READY` | Binance / Coinbase | 低 |
| Binance Funding / OI | `NATIVE_READY` | Binance Futures API | 低 |
| Bybit Funding / OI | `NATIVE_READY` | Bybit V5 | 低 |
| OKX Funding / OI | `NATIVE_READY` | OKX API v5 | 低 |
| Deribit Funding / OI | `NATIVE_READY` | Deribit | 低 |
| BTC DVOL | `NATIVE_READY` | Deribit | 低 |
| BTC/ETH option snapshot / mark IV | `NATIVE_READY` | Deribit | 中 |
| IV Term Structure / 25D Skew | `NATIVE_CANDIDATE` | Deribit chain + 本地计算 | 中高 |
| Stablecoin total / USDT / USDC | `NATIVE_READY` | DefiLlama | 低 |
| BTC ETF Daily Flow | `NATIVE_CANDIDATE → 高概率Native` | Farside公开daily table | 中低 |
| ETH ETF Daily Flow | `NATIVE_CANDIDATE → 高概率Native` | Farside公开daily table | 中低 |
| Bitcoin Treasuries | `EXTERNAL_LINK` | BitcoinTreasuries | 高 |
| MVRV / Realized Cap | `NATIVE_CANDIDATE` | Coin Metrics Community候选 | 中 |
| NUPL / SOPR | `NATIVE_CANDIDATE` | Coin Metrics Community候选 | 中 |
| Exchange Balance / Netflow | `EXTERNAL_LINK` | CryptoQuant / Glassnode / Arkham | 高 |
| LTH / STH Supply / Cost Basis | `EXTERNAL_LINK优先` | Checkonchain / Glassnode | 高 |
| Liquidation Heatmap | `EXTERNAL_LINK` | Coinglass | 很高 |
| Aggregate Funding / OI | `NATIVE_READY（首批3 Venue）` | Binance + Bybit + OKX | 中 |
| BTC专业期限结构 | `NATIVE_CANDIDATE / EXTERNAL_LINK` | 简版自建 / Checkonchain | 中高 |
| Whale / Wallet Intelligence | `EXTERNAL_LINK` | Arkham / CryptoQuant / BGeometrics | 高 |

## 4.1 Multi-Venue 第一版

```text
Aggregate = Binance + Bybit + OKX
Venue = Binance / Bybit / OKX
Deribit = Options/DVOL核心 + 可选derivatives补充
```

### Funding

不同 venue / symbol 的 funding interval 不应写死为统一 8 小时。

Canonical至少记录：

- raw funding rate；
- funding interval hours；
- funding timestamp；
- venue；
- contract type；
- methodology version。

先统一 interval，再做 OI-weighted aggregate。

### OI

不同 venue / contract type 的 OI 单位不同。

Bybit官方明确：BTCUSD inverse OI 与 BTCUSDT linear OI 单位不同。因此：

```text
raw OI
→ contract type
→ price / multiplier conversion
→ USD notional
→ aggregate
```

不得直接对原始数值求和。

OKX funding API 的公式与周期存在历史变更，provider必须保留 methodology version / quality flag。

## 4.2 Coin Metrics

已确认：

- Community API 无需 key；
- Community free tier 为 non-commercial use / Creative Commons；
- metric IDs：`CapMVRVCur`、`CapRealUSD`、`NUPL`、`SOPR`；
- Community API 当前状态页显示 operational；
- Coin Metrics 的公开状态记录也出现过 BTC 的 `CapMVRVCur / CapRealUSD / NUPL` 等网络指标维护记录。

但仍未在当前工具环境完成“用 Community endpoint 对 BTC 四指标逐项返回 200”的直接请求，因此不把四项升级为 `READY`。

`rights_scope` 必须记录；未来用途超出 Community 条款时直接换源或外链。

## 4.3 Farside ETF Flow

BTC / ETH daily flow tables：

- 无需登录即可查看；
- HTML 表结构清晰；
- 页面说明自动更新；
- 有完整历史页面；
- 页面底部标明 `All rights reserved`，未找到明确授权我们再分发其表格数据的条款。

因此技术上高概率 Native，但权利状态标记：

```text
rights_scope = review_required
```

若最终仅限内部看板且符合使用边界，可实施；若对外发布权利不清晰，则改用其他来源或 External Link。

## 4.4 Bitcoin Treasuries

未发现值得依赖的正式稳定公共 API，且名单本身需要专业维护。

固定为 `EXTERNAL_LINK`，不继续投入网页抓取工程。

---

# 5. External Link 可达性审计

以下只审“将来实际可能放按钮的高价值入口”，不遍历整个 Trading Tools。

| 入口 | 状态 | 审计判断 |
|---|---|---|
| CME FedWatch | `LINK_READY` | 公共页面直接可达，无需登录即可看到工具说明/iframe |
| Coinglass Funding Rate | `LINK_READY` | 公共页面可达，包含 BTC/ETH OI-weighted funding 等视图 |
| Coinglass Open Interest | `LINK_READY` | 公共页面可达，可作为多交易所 OI 专业参考 |
| Coinglass Liquidation HeatMap | `LINK_READY_WITH_GATING` | 页面可达，但出现 Prime 标识，部分功能可能会员限制 |
| Checkonchain BTC Term Structure | `LINK_READY_BROWSER_QA` | URL可达但属于JS/静态图应用，爬虫无正文；浏览器验收即可 |
| Deribit Options Metrics | `LINK_READY_BROWSER_QA` | 页面明确要求 JavaScript，无需把它当数据API |
| Greeks.live Data Lab | `LINK_READY_BROWSER_QA` | JS应用，适合作为外链 |
| CryptoQuant BTC Summary | `LINK_READY_POSSIBLE_GATING` | 页面可达但JS驱动，部分指标可能账号限制 |
| Arkham | `LINK_READY` | 旧 `intel.arkm.com` 应迁移为当前 `https://arkm.com/`；公开首页已有 exchange flows / wallet tracking |
| SMM Import Arbitrage | `LINK_READY_POSSIBLE_GATING` | 页面公开但有登录/注册入口，爬虫视角显示暂无数据 |
| 1qh 跨期价差 | `LINK_READY` | 公开页面可达，覆盖 SC/CU/AU/AG 等并有期限结构工具 |

外链按钮上线前仍需用户线下浏览器最终点击验收，但这些候选不需要继续做程序化逆向。

---

# 6. 当前剩余真正高价值 Live Validation

Phase F 已不需要继续扩需求，剩余问题收敛为：

1. **China M2**：在真实可联网 Python/Actions 环境调用 AKShare，确认最新一行已经同步到 2026-07 且数值与 PBOC 355.51 万亿元一致；
2. **WGC ETF Flow**：寻找稳定无需会话的数据链；否则直接 External Link；
3. **WTI Curve**：验证 CME 公开 settlement table/未文档化 JSON 链在 GitHub Actions 的稳定性与使用边界；不通过则外链；
4. **Brent Curve**：验证 ICE 是否有低维护结构化入口；否则外链；
5. **Farside**：最终确认内部使用/再分发 rights_scope；
6. **Coin Metrics**：真实请求 Community endpoint 验证 BTC `CapMVRVCur,NUPL,SOPR,CapRealUSD` entitlement；
7. **Multi-Venue**：在真实运行环境固定 Binance/Bybit/OKX 的 funding interval、contract multiplier、OI USD-notional 公式，并写测试样例。

其它核心数据源已经有明确 `NATIVE_READY` 或 `EXTERNAL_LINK` 路径。

本文件仍属于 Phase F 审计，不代表任何业务 Phase 已开始实施。
