# 对冲基金看板｜数据可行性与维护策略

> 状态：Planning Baseline v0.1 / Engineering NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 实施文档：`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`  
> 数据仓库：`wuxingyuenan5-lgtm/platform-data`  
> 作用：在实际开发前审计数据可获取性、自动化稳定性、存储成本、网站子模块复用方式与长期维护风险。

---

## 1. 当前最高优先级

在正式进入大规模工程实施前，优先解决：

1. 数据是否能够长期、免费、稳定获取；
2. 数据是否具备足够历史序列；
3. 数据是否能够自动更新；
4. 数据频率与更新时点是否明确；
5. 数据源失效时是否有 fallback / LKG；
6. 数据是否适合存入 GitHub 文件仓库；
7. 现成网站子模块是否能合法、稳定复用；
8. 哪些页面只能作为参考，不能成为生产依赖。

产品规格已经冻结，不应为了某个数据源拿不到而擅自改变产品设计；若某指标暂时没有稳定免费数据，应先标记 `not_configured`，再由用户决定是否删减或替换。

---

## 2. Data Feasibility Gate【冻结】

任何新指标在进入工程 Phase 前，必须至少经过以下检查：

- canonical identity 明确；
- Primary Source 明确；
- Fallback 或 no-fallback 状态明确；
- 免费访问条件明确；
- 自动化访问可行；
- 历史区间满足页面需要；
- 更新频率 / 发布时间明确；
- 单位 / 货币 / 交易日 / 时区明确；
- stale threshold 可定义；
- 页面需要的 latest / history / 30D / derived fields 可计算；
- rights_scope 可记录；
- Provider 失败不会覆盖 LKG。

只有通过该 Gate 的指标才进入正式实现。

未通过的指标分类为：

- `OPEN`：仍需研究；
- `not_configured`：V1 暂无可靠免费链路；
- `manual_reference_only`：只能人工查看，不进入自动数据链；
- `embed_only`：只能通过官方嵌入方式展示，不作为项目自有数据源。

---

## 3. 现成网站“子模块 / 图表”的复用原则【冻结】

很多网站已经有漂亮的图表、排行榜、资金流、期限结构等子模块，但“网页上能看到”不等于“能直接搬进自己的平台”。

统一按以下顺序判断：

### A. 官方 / 文档化 API

优先级最高。

如果子模块背后有官方公开 API：

```text
official API
→ platform-data
→ canonical data
→ 自有 UI / 现有 UI
```

优先自己取数据并在现有平台组件内重画，而不是依赖原网站页面。

### B. 官方 Embed / Widget

如果网站明确提供官方 Widget / Embed：

- 可以作为展示组件；
- 不将其内部数据当作项目自有数据；
- 不尝试从 iframe / Widget 反向抓取；
- 需确认 CSP / frame-ancestors / X-Frame-Options 是否允许嵌入；
- UI 不一致时仍优先自有数据重画。

TradingView 属于这一类：主要用于图表展示，而不是项目数据源。

### C. 网页内部公开数据接口

若网站子模块通过公开 HTTP/JSON 请求加载数据，但没有正式 API 文档：

只有满足以下条件才允许作为 B-tier / fallback：

- 无登录 / 无 token 绕过；
- 无 CAPTCHA / WAF 绕过；
- endpoint 长期稳定性可验证；
- 请求参数和数据口径可解释；
- 使用条件允许；
- 有 cache / parser health check / LKG；
- Provider 失效时页面能降级。

不得把这种内部接口假装成“官方稳定 API”。

### D. 仅网页图表 / JS 模块

如果只能看到 JS 图表，且没有可稳定获取的数据接口：

- 只作为研究参考；
- 不做 DOM 抓取作为长期生产链；
- 不依赖浏览器自动化长期维护；
- 不为复制视觉而破坏现有 UI；
- 优先寻找其底层 Source of Record / AKShare 封装 / 官方替代源。

### E. iframe 无法嵌入

常见原因：

- `X-Frame-Options`；
- CSP `frame-ancestors`；
- 登录 Cookie；
- 跨域限制；
- 动态 token；
- 页面禁止第三方嵌入。

这种模块直接视为“不能嵌入”，不要反复尝试绕过。

### F. 截图 / 手工导出

只能作为人工研究辅助，不作为自动看板数据链。

---

## 4. 为什么很多网站子模块“不好直接用”

技术上主要有四类原因：

1. **显示层与数据层耦合**：网页组件只负责渲染，真实数据通过内部接口异步加载；复制 HTML 没有数据。
2. **跨域隔离**：即使 iframe 能显示，项目也不能直接读取 iframe 内 DOM / 数据。
3. **访问控制**：CORS、Cookie、签名、token、WAF、CSP 会阻止第三方复用。
4. **维护风险**：网站一改字段、URL、前端 bundle，非官方抓取就可能失效。

因此本项目默认策略是：

> **参考网站子模块的产品形态与信息组织；优先找到其底层公开数据源，然后在自己的 UI 中重建。**

而不是“把别人的网页模块直接搬过来”。

---

## 5. 网站子模块分类台账【实施前建立】

用户已有整理的网站 / 子模块后续逐项进入台账：

| Module | Website | 用途 | 官方 API | 官方 Embed | 内部公开接口 | 免费 | 自动化 | Rights | 最终策略 |
|---|---|---|---|---|---|---|---|---|---|
| 示例 | Example | ETF Flow | yes/no | yes/no | yes/no | yes/no | ready/open | scope | API / embed / rebuild / reference-only |

最终策略只允许：

- `canonical_api`；
- `official_embed`；
- `public_endpoint_with_lkg`；
- `rebuild_from_upstream`；
- `manual_reference_only`；
- `not_configured`。

不允许“先爬下来再说”。

---

## 6. `platform-data` 的定位【冻结】

`platform-data` 是：

> **版本化数据生产与分发仓库**

不是：

> 高频实时交易数据库。

它适合保存：

- 月频 / 周频 / 日频宏观数据；
- 日频 Market Detail 历史；
- ETF Flow；
- CFTC；
- 库存；
- 日频 On-chain；
- 日频 Stablecoin；
- Polymarket 适度采样后的历史概率；
- Crypto derivatives 的适度聚合 / snapshot。

不适合长期保存：

- tick；
- order book；
- 秒级；
- 每分钟全市场 OI / Funding / Basis 全量原始数据；
- 高频实时交易流。

V1 不建设这些高频数据库能力。

---

## 7. GitHub 存储策略【冻结为 V1 基线】

### 7.1 最新数据 / 前端消费

使用 JSON：

```text
public/v1/<module>/manifest.json
public/v1/<module>/dashboard.json
public/v1/<module>/market-detail.json
public/v1/<module>/series/*.json
```

用途：

- Platform API 快速读取；
- 人工审计；
- diff 可读；
- status / source / freshness 透明。

### 7.2 长历史

对于较长历史序列：

优先：

- CSV（数据量较小）；
- Parquet（数据量较大 / 多列 / 高频一些）。

避免：

- 一个巨大 JSON 文件每天整体重写；
- 每个日期建立大量小文件；
- 把 SQLite / DuckDB 二进制数据库频繁 commit 到 Git。

建议历史按稳定区间分区，例如：

```text
history/<series_id>/2025.parquet
history/<series_id>/2026.parquet
```

或数据量较大时按月分区。

### 7.3 高频 Crypto

Funding / OI / Basis：

V1 只保存页面实际需要的聚合粒度，例如：

- latest snapshot；
- 1H / 4H 采样或聚合（如确有需要）；
- Daily aggregate；
- 滚动历史。

不在 GitHub 中存每分钟全量 raw feed。

如果未来产品明确需要分钟级 / tick 历史，再单独引入真正的时序存储，不在 V1 里提前建设。

---

## 8. 数据维护规则【冻结】

每个 Provider 必须有：

- adapter；
- source registry；
- parser/schema check；
- latest-date check；
- freshness threshold；
- timeout；
- finite retry；
- fallback；
- LKG；
- quality flags；
- provenance；
- usage / rights note。

### 8.1 不变不提交

```text
fetch
→ normalize
→ compare
→ no material change
→ no commit
```

避免 GitHub commit 噪音。

### 8.2 失败不清空

```text
fetch failed
→ retain last known good
→ status stale/error/degraded
→ log failure
```

禁止空数组覆盖有效历史。

### 8.3 Schema Drift

网页 / public endpoint 类 Provider 必须额外检查：

- 字段是否消失；
- 行数是否异常；
- 最新日期是否倒退；
- 数值量级是否异常；
- content-type 是否变化；
- HTML 是否替代原 JSON。

发现异常时停止写入，保留 LKG。

---

## 9. 数据库维护结论【当前基线】

V1 暂时**不引入传统数据库**。

原因：

- 当前核心用途是日常扫盘与复盘，不是高频交易；
- Macro / Commodity 大部分是日 / 周 / 月频；
- Crypto 高频数据只保留页面必要的聚合粒度；
- GitHub 文件 + Git 历史已经能够承担版本化、追溯、回滚和分发；
- 数据量在 V1 仍可控制。

但必须承认：

> GitHub 不是通用数据库，也不是实时数据服务。

未来出现以下条件之一时，再升级存储层：

- 需要分钟级以上长期历史；
- 数据文件明显膨胀；
- Git clone / Actions / API 读取性能明显恶化；
- 需要复杂 SQL / 横截面查询；
- 需要实时 websocket 入库；
- 多用户同时写入；
- 数据量达到 Git 文件维护明显不合理的程度。

升级时保持 canonical contract 不变，使前端与 Platform API 无需跟随大改。

---

## 10. 实施前下一步【Current】

在 Phase 0 之前增加一个：

### Phase F — Data Feasibility Audit

对 Macro / Commodity / Crypto Data Source Map 中每个 Primary / Fallback 逐项 live validate：

1. 实际能否请求；
2. 是否需要 key；
3. 免费额度；
4. 最新日期；
5. 历史区间；
6. 字段结构；
7. 更新频率；
8. 访问限制；
9. rights_scope；
10. 预计维护复杂度；
11. 是否存在用户已整理的网站子模块可作为入口线索；
12. 最终标记 `READY / FALLBACK / EMBED_ONLY / REFERENCE_ONLY / NOT_CONFIGURED`。

Phase F 不改业务页面，只输出真实可执行的数据可行性结果。

Phase F 完成以后，才进入 Phase 0 Shared Data Foundation。
