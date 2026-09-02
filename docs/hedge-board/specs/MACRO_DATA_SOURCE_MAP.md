# 对冲基金看板｜宏观看板数据源映射（Macro Data Source Map）

> 状态：Discussion Draft v0.1  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 产品规格：`docs/hedge-board/specs/MACRO_V1_SPEC.md`  
> 适用分支：`feature/hedge-board-online-optimization`  
> 目标：为 Macro V1 冻结免费数据源、Primary/Fallback、Canonical ID、频率、单位、时效与授权边界。  
> 原则：统一的是项目内部 Canonical Data Contract 与 Provider 接口，不强求单一外部数据源。

---

## 1. 总体数据源原则【冻结】

### 1.1 免费优先

Macro V1 仅使用免费可访问数据源。若某指标没有可信、稳定、合法的免费链路：

- 保留现有展示位置；
- 数据状态设为 `not_configured` / `no_data`；
- 不伪造；
- 不从 TradingView 反向抓取；
- 不使用未经确认的野生爬虫补齐。

### 1.2 AKShare 的角色【冻结】

AKShare 作为优先复用的数据接入层之一，用于降低中国市场及部分公共数据源的接入和维护成本。

但：

- AKShare 是 Provider Adapter，不是最终 Canonical Source；
- 必须记录 `upstream_source`；
- 若 AKShare 上游陈旧、接口失效、语义不匹配或官方 API 更稳定，则直接使用官方免费源；
- 关键指标必须进行 freshness validation；
- 不因 AKShare 返回成功就自动判定为 `ready`。

### 1.3 Provider 优先级

```text
免费官方 Source of Record
    ↓
免费官方/权威分发层
    ↓
AKShare 成熟稳定接口
    ↓
可靠免费 Public Web Provider
    ↓
not_configured
```

实际优先级可按数据集调整；总体目标是：准确、稳定、免费、易维护。

### 1.4 数据权利字段

每个 Series / Instrument 记录：

- `access_cost`
- `usage_scope`
- `redistribution`
- `rights_note`

推荐枚举：

- `public_domain`
- `free_with_attribution`
- `internal_research`
- `review_required`
- `restricted`

“免费访问”不等于“可自由对外再分发”。

---

## 2. Canonical 数据合同【冻结】

所有来源统一映射到项目内部结构，至少包含：

- `series_id`
- `label`
- `observation_date`
- `value`
- `unit`
- `currency`
- `frequency`
- `timezone`
- `source`
- `upstream_source`
- `source_id`
- `source_url`
- `retrieved_at`
- `as_of`
- `status`
- `is_stale`
- `fallbacks_used`
- `quality_flags`
- `methodology_version`

Derived series 额外记录：

- `components`
- `transform`
- `transform_parameters`

---

## 3. Growth Source Map【冻结】

| Canonical ID | 指标 | Primary | Source ID / Function | Fallback | Frequency | Unit / Transform | Rights |
|---|---|---|---|---|---|---|---|
| `us_real_gdp_yoy` | Real GDP YoY | FRED | `GDPC1` | BEA | Quarterly | 本地计算 YoY | public / attribution |
| `us_indpro_yoy` | Industrial Production YoY | FRED | `INDPRO` | Federal Reserve | Monthly | 本地计算 YoY | public / attribution |
| `us_initial_claims_4w` | Initial Claims 4W MA | FRED | `IC4WSA` | U.S. DOL | Weekly | persons / thousands as published | public / attribution |
| `us_cfnai` | CFNAI | FRED | `CFNAI` | Chicago Fed | Monthly | index | public / attribution |
| `us_cfnai_ma3` | CFNAI 3M MA | FRED | `CFNAIMA3` | Chicago Fed | Monthly | index | public / attribution |

说明：Growth 不采用 AKShare-first。美国官方宏观通过 FRED 的统一接口更稳定、字段语义更清楚。

---

## 4. Inflation Source Map【冻结】

### 4.1 Actual Inflation

| Canonical ID | 指标 | Primary | Source ID | Fallback | Frequency | Transform |
|---|---|---|---|---|---|---|
| `us_cpi_yoy` | CPI YoY | FRED | `CPIAUCSL` | BLS | Monthly | YoY |
| `us_core_cpi_yoy` | Core CPI YoY | FRED | `CPILFESL` | BLS | Monthly | YoY |
| `us_pce_yoy` | PCE Price Index YoY | FRED | `PCEPI` | BEA | Monthly | YoY |
| `us_core_pce_yoy` | Core PCE YoY | FRED | `PCEPILFE` | BEA | Monthly | YoY |

### 4.2 Upstream Inflation

| Canonical ID | 指标 | Primary | Source ID | Fallback | Frequency | Transform |
|---|---|---|---|---|---|---|
| `us_ppi_yoy` | PPI YoY | FRED | `PPIFIS` | BLS | Monthly | YoY |

### 4.3 Market-Implied Inflation

| Canonical ID | 指标 | Primary | Source ID | Fallback | Frequency | Unit |
|---|---|---|---|---|---|---|
| `us_5y_breakeven` | 5Y Breakeven | FRED | `T5YIE` | OPEN | Daily | percent |
| `us_10y_breakeven` | 10Y Breakeven | FRED | `T10YIE` | OPEN | Daily | percent |
| `us_5y5y_forward` | 5Y5Y Forward Inflation | FRED | `T5YIFR` | OPEN | Daily | percent |

### 4.4 Inflation Pricing Gap

Derived，不设独立外部 Provider：

- `5Y BE - CPI YoY`
- `10Y BE - CPI YoY`

仅作当前实际通胀与市场中长期隐含定价的状态比较，不定义为预测误差。

---

## 5. Rates Source Map【冻结】

### 5.1 Treasury Yields

| Canonical ID | Tenor | Primary | Fallback | Frequency | Unit |
|---|---:|---|---|---|---|
| `us_tsy_3m` | 3M | U.S. Treasury | FRED | Daily | percent |
| `us_tsy_2y` | 2Y | U.S. Treasury | FRED | Daily | percent |
| `us_tsy_10y` | 10Y | U.S. Treasury | FRED | Daily | percent |
| `us_tsy_30y` | 30Y | U.S. Treasury | FRED | Daily | percent |

Treasury 官方 XML/CSV feed 为主；不对缺失 tenor 自行插值后伪装真实观察值。

### 5.2 Short-End Rate Corridor

| Canonical ID | 指标 | Primary | Fallback | Frequency | Unit |
|---|---|---|---|---|---|
| `fed_target_lower` | Fed Target Lower | FRED | Federal Reserve | Daily/event | percent |
| `fed_target_upper` | Fed Target Upper | FRED | Federal Reserve | Daily/event | percent |
| `iorb` | IORB | FRED | Federal Reserve | Daily/event | percent |
| `on_rrp_award` | ON RRP Award Rate | FRED | NY Fed / Fed | Daily/event | percent |
| `effr` | EFFR | NY Fed | FRED | Daily | percent |
| `sofr` | SOFR | NY Fed | FRED | Daily | percent |

---

## 6. Global M2 Source Map【公式与 Series 已核验】

### 6.1 公式

```text
globalM2 =
  cnm2 * cnyusd
  + usm2
  + eum2 * eurusd
  + jpm2 * jpyusd
  + gbm2 * gbpusd
```

目标统一单位：USD（建议存储层统一 `USD billion`，展示层可转 `USD trillion`）。

所有组成项使用最近共同可用月份；FX 使用对应月份的月均汇率。

### 6.2 Components

| Component | Canonical ID | Primary | Fallback | Frequency | Notes |
|---|---|---|---|---|---|
| US M2 | `us_m2` | FRED `M2NS` | Federal Reserve H.6 | Monthly | NSA；USD billion |
| China M2 | `cn_m2` | AKShare-compatible Sina adapter | PBOC mandatory validation | Monthly | 亿元；2026-07 必须通过 PBOC 355.51 万亿元基准 |
| Euro Area M2 | `eu_m2` | ECB BSI | `M.U2.Y.V.M20.X.1.U2.2300.Z01.E` | Monthly | Working-day / seasonally adjusted stock；EUR million |
| Japan M2 | `jp_m2` | BOJ API `MD02` | `MAM1NAM2M2MO` | Monthly | Average amounts outstanding；100 million yen |
| UK broad money | `gb_m2` | BoE IADB | `LPMAUYM` | Monthly | M4 amount outstanding NSA；GBP million |

拒绝使用 IMF/FRED 的 `MYAGM2CNM189N`（停于 2019-08）以及 BOJ / BoE 已停更的旧 IMF 镜像。Global M2 不允许以停更镜像补齐当前值。

### 6.3 FX Conversion

Primary：ECB Reference Rates。

Canonical FX：

- `cnyusd`
- `eurusd`
- `jpyusd`
- `gbpusd`

每日官方汇率 → 对月度 M2 观察期求月均 → 转换为 USD。

ECB keys：`D.USD.EUR.SP00.A`、`D.CNY.EUR.SP00.A`、`D.JPY.EUR.SP00.A`、`D.GBP.EUR.SP00.A`。非欧元货币按同日 `USD/EUR ÷ local/EUR` 先转成 USD/local，再取月均；禁止用两条月均汇率之比替代同日交叉汇率月均。

### 6.4 Global M2 输出

至少输出：

- `global_m2_usd`
- `global_m2_yoy`
- 各地区 USD-equivalent component
- 各地区 component share
- common observation month
- methodology version

实现状态（2026-09-02）：132 个共同月份通过端到端刷新，最新共同月份 2026-07；总量、YoY、五区 USD component 与 component share 均保存为 canonical series。方法版本 `global_m2_five_region_monthly_fx_v1`。

---

## 7. Risk Appetite Source Map【冻结】

| Canonical ID | 指标 | Primary | Fallback | Frequency | Notes |
|---|---|---|---|---|---|
| `us_hy_oas` | US High Yield OAS | FRED / ICE BofA | OPEN | Daily | 免费访问但再分发权利需审查；内部研究优先 |
| `hyg_adjclose` | HYG Adj Close | Yahoo v8 Chart | OPEN | Daily | 免费 public-web，无 SLA |
| `lqd_adjclose` | LQD Adj Close | Yahoo v8 Chart | OPEN | Daily | 与 HYG 使用完全相同价格口径 |
| `hyg_lqd_ratio` | HYG/LQD | Derived | — | Daily | 同日 adjusted close 本地计算 |

若未来平台对外商业分发，`us_hy_oas` 必须重新做 rights review。

---

## 8. Market Expectations / Event Probability【冻结】

Primary：Polymarket 官方公共 API。

### 8.1 Metadata / discovery

- Gamma API
- 仅用于读取配置白名单对应 Event / Market metadata
- 后台允许产生 candidate list，但 candidate 不自动发布到看板

### 8.2 Probability History

- CLOB `prices-history`
- 通过 market/outcome 对应 token 获取真实历史概率曲线

### 8.3 发布规则

真正进入前端必须存在于：

`platform-data/config/macro_events.yaml`

页面 active event 数量控制在约 6–8 个。

优先类别：

1. Monetary Policy
2. Macro Economy
3. Major Financial Markets
4. Major Policy / Geopolitics

卡片至少包含：

- event title
- outcome label
- current probability
- history
- 1D probability change
- 7D probability change
- liquidity
- volume（可稳定获取时）
- expiry / resolution date
- source
- updated_at
- status

Election 不作为固定一级分类；只有明确影响金融市场时进入白名单。

---

## 9. Macro Market Detail Source Map【部分冻结】

### 9.1 A类：优先完整真实化

| Row | Canonical ID | Primary | Fallback | Status |
|---|---|---|---|---|
| VIX | `vix` | Cboe | FRED/OPEN | target_ready |
| DXY | `dxy` | Yahoo v8 Chart（V1） | OPEN | target_ready |
| US 2Y | `us_tsy_2y` | U.S. Treasury | FRED | target_ready |
| US 10Y | `us_tsy_10y` | U.S. Treasury | FRED | target_ready |
| US 30Y | `us_tsy_30y` | U.S. Treasury | FRED | target_ready |
| CN 2Y | `cn_tsy_2y` | AKShare if exact tenor verified | ChinaBond | OPEN |
| CN 10Y | `cn_tsy_10y` | AKShare | ChinaBond | target_ready |
| CN 30Y | `cn_tsy_30y` | AKShare | ChinaBond | target_ready |
| USDCNH | `usdcnh` | Yahoo v8 Chart | OPEN | target_ready |
| TLT | `tlt` | Yahoo v8 Chart | OPEN | target_ready |
| HYG | `hyg` | Yahoo v8 Chart | OPEN | target_ready |
| 10Y TIPS | `us_10y_real_yield` | FRED | Treasury real curve | target_ready |
| 10Y Breakeven | `us_10y_breakeven` | FRED | OPEN | target_ready |

对以上日频市场数据，尽量由同一 canonical history 计算：

- latest / close
- 1D
- 1W
- 1M
- QTD
- YTD
- 1Y
- 52W High
- latest ~30 valid daily observations

### 9.2 B类：低频/政策数据，Frequency-Aware

现有行继续保留：

- DFF
- SOFR
- CPI
- PCE
- UNRATE
- US M2
- WALCL
- TGA
- RRP
- Net Dollar Liquidity

规则：

- 不删除；
- 不用假 0 变化；
- 低频数据在窗口内没有新 observation 时，1D/1W 等显示 `—`，而不是 `0.00%`；
- 30D 内不足 2 个真实观测时，不画假平线；
- 利率变化优先使用 bp 语义，而非机械 percent return。

### 9.3 暂不配置

| Row | 原因 | V1处理 |
|---|---|---|
| MOVE | 未冻结可信稳定免费历史链路 | 保留行，`not_configured` |
| DSPX | 免费自动化历史源待确认 | 保留行，`not_configured` |

不得为补齐这两行而抓 TradingView 或使用不可靠数据站。

---

## 10. AKShare Health Rules【冻结】

所有 AKShare Series 每次抓取后执行：

1. endpoint/function 是否成功；
2. 行数是否异常下降；
3. latest observation 是否比 Last Known Good 更旧；
4. latest date 是否超过该频率允许的 stale threshold；
5. 单位/字段名是否发生变化；
6. 关键值是否出现不合理数量级跳变；
7. upstream source 是否仍与配置一致。

AKShare 调用成功但 latest date 明显陈旧时：

`status = stale`

而不是 `ready`。

Primary AKShare 失败而官方 fallback 成功：

`status = degraded`

并记录 `fallbacks_used`。

---

## 11. Fallback / Last Known Good【冻结】

```text
fetch primary
    ↓
normalize
    ↓
validate
    ↓
quality checks
    ↓
compare LKG
```

### Primary成功

发布新数据。

### Primary失败 + Fallback成功

- 发布 fallback 数据；
- `status = degraded`；
- 记录 Primary error；
- 记录 `fallbacks_used`。

### 全部失败

- 不使用空数组覆盖上一版有效历史；
- LKG继续服务；
- 标记 `stale` / `error`；
- 保存 failure metadata。

---

## 12. Freshness / Display Rules【方向冻结，阈值待实施验证】

页面新增轻量元信息：

- Latest observation date
- Frequency
- Updated / retrieved time
- stale status
- Latest vs Previous（适用时）

默认时间窗口：

| 数据类型 | 默认窗口 |
|---|---|
| Treasury / SOFR / Breakeven | 1Y |
| Initial Claims | 2Y |
| CPI / PCE / PPI | 5Y |
| CFNAI | 5Y |
| GDP | 10Y |
| Global M2 | 10Y |
| Polymarket | 30D / All |

不增加 Release / Event Marker。

---

## 13. 数据更新工程方案【方向冻结】

`platform-data` 建议职责结构：

```text
config/
schemas/
src/platform_data/providers/
src/platform_data/transforms/
src/platform_data/pipelines/
src/platform_data/storage/
public/v1/macro/
tests/
.github/workflows/
```

### 13.1 Macro Core

建议定时：

- Asia/Taipei 08:30
- Asia/Taipei 18:30

用途：覆盖隔夜美国数据与当日中国市场/债市更新。

### 13.2 Polymarket

建议每 6 小时更新一次。

### 13.3 低频数据

不为 CPI/GDP/M2 单独维护复杂发布日期调度。

每天查询：

- observation 未变化 → no commit
- observation 更新 → validate + publish + commit

### 13.4 Git 持久化

不建立每日 snapshot 目录。

每个 Canonical Series 保存完整必要历史：

`public/v1/macro/series/<series_id>.json`

Git 历史本身承担版本审计。

---

## 14. 当前 OPEN 项

1. 中国 2Y 国债在 AKShare 中的精确稳定接口与 tenor mapping；
2. DXY 是否存在比 Yahoo 更稳定的免费 Provider，同时保持真正 DXY 定义；
3. MOVE 的可信免费历史数据链；
4. DSPX 的可信免费历史数据链；
5. High Yield OAS 对当前平台实际使用范围的最终 rights classification；
6. US M2 最终使用的非季调 Series ID；
7. Euro/Japan/UK M2 的最终官方 series code 与单位校验；
8. 各 series 的精确 stale threshold；
9. Yahoo / AKShare Public Web 来源的生产级 retry / backoff 参数；
10. Macro Market Detail 现有所有 row 的最终 source audit。

---

## 15. 禁止事项【冻结】

- 不为了统一而强迫所有数据走 AKShare；
- 不为了全覆盖使用付费 API；
- 不抓 TradingView 市场数据；
- 不用随机/placeholder 数据；
- 不将 stale 数据伪装为 ready；
- 不因 Provider 失败覆盖 Last Known Good；
- 不将数据源改造扩大为 UI 重构；
- 不擅自删除或改变用户现有 Hedge Board 设计。
