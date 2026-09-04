# 对冲基金看板｜数据可行性与维护策略

> 状态：Planning Baseline v0.4 / Engineering NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 实施文档：`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`  
> Phase F 审计：`docs/hedge-board/HEDGE_BOARD_PHASE_F_AUDIT.md`  
> 数据仓库：`wuxingyuenan5-lgtm/platform-data`  
> 作用：实际开发前，同时审计数据可获取性、自动化稳定性、**使用/再分发权利**、存储成本，以及目标数据应自己落地还是外链跳转。

---

## 1. 当前最高优先级【冻结】

正式工程实施前，优先解决：

1. 数据能否长期、稳定获取；
2. 数据是否具备足够历史；
3. 数据是否能无人值守自动更新；
4. 更新频率、发布时间、交易日与时区是否明确；
5. 数据源失效时是否有 fallback / LKG；
6. 数据是否适合 GitHub 文件化存储；
7. **免费访问是否同时具备当前使用场景需要的 rights_scope**；
8. 用户已整理的参考网站中，哪些值得 Native，哪些直接 External Link。

核心产品原则：

> **好落地的自己落地；不好落地的保留参考网站入口，做按钮跳转原站。**

其中“好落地”同时意味着：技术低维护 + 口径清楚 + 权利边界可接受。

---

## 2. Data Feasibility Gate【冻结】

任何准备由本平台自己展示真实数据的指标，进入工程 Phase 前至少检查：

- canonical identity；
- Primary / Fallback；
- 免费/付费访问条件；
- 自动化可行性；
- 历史区间；
- frequency / publish timing；
- unit / currency / timezone / trading day；
- stale threshold；
- 页面所需 latest / history / derived fields；
- Provider failure 不覆盖 LKG；
- 预计维护复杂度；
- `rights_scope`。

通过 Gate → 可进入 Native 数据链。  
未通过 Gate → **优先 External Reference Button**。

只有“没有可维护 Native 链 + 没有合适参考入口”才使用 `NOT_CONFIGURED`。

---

## 3. Rights Gate【最高优先级之一 / 冻结】

### 3.1 免费可访问 ≠ 可自由生产/展示

必须严格区分：

```text
free access
≠
free automated extraction
≠
free internal organizational use
≠
free redistribution / public display
≠
free derived-data use
```

因此：

- 网站能打开，不代表可以脚本化抓取；
- XLSX/CSV 能下载，不代表可以长期复制进平台；
- API 无费用，不代表第三方版权数据可以任意复用；
- 通过 FRED/聚合商拿到的数据，不会覆盖原始数据所有者的版权限制。

### 3.2 Native 的 rights_scope 必须明确

每个 Native Provider 至少记录：

- `access_cost`；
- `usage_scope`；
- `redistribution_scope`；
- `derived_use_scope`（适用时）；
- `attribution_required`；
- `rights_review_required`；
- `rights_source_url`。

如果数据源明确限制系统化抓取、组织内使用、再分发、公开展示或派生数据使用，则默认：

```text
EXTERNAL_LINK
```

除非取得许可或找到权利更清晰的替代 Source of Record。

### 3.3 Source of Record 优先

当 FRED、商业聚合站与政府/央行官方源同时存在时，优先直接用官方 Source of Record。

例如美国宏观：

- BLS → CPI / Core CPI / PPI / unemployment；
- BEA → GDP / PCE / Core PCE；
- Federal Reserve Board → M2 / Industrial Production；
- Chicago Fed → CFNAI / CFNAIMA3；
- U.S. Treasury → nominal / real Treasury curves；
- New York Fed → SOFR / EFFR。

FRED 更适合作为：

- 研究参考；
- 快速交叉核验；
- rights_scope 允许时的 fallback；

而不是默认把所有序列都从 FRED 进入生产链。

---

## 4. Native / External Link / Embed【冻结】

### A. Native

```text
official / reliable permitted source
→ platform-data
→ canonical data
→ platform-api
→ existing UI / additive chart
```

适用条件：

- 自动化稳定；
- 历史足够；
- 口径明确；
- 维护成本合理；
- rights_scope 可接受。

### B. External Reference Button

当存在以下任一情形时优先外链：

- 无稳定低维护接口；
- 登录/动态 token/WAF；
- 历史难取；
- 数据许可/再分发不清晰；
- 商业数据所有者明确限制自动提取或展示；
- 原站已经提供成熟专业模块，V1 自建投入产出比低。

按钮直接指向具体子页面，新标签页打开。

### C. Official Embed

仅在官方明确允许嵌入、体验明显优于外链、且不破坏现有 UI 时使用。

TradingView 继续主要作为展示层，不反向抓取数据。

---

## 5. Trading Tools 只读参考库【冻结】

Trading Tools 继续 Deferred，不开发、不改 UI、不处理其元数据。

Phase F 只读现有：

- `name`
- `url`
- `description`
- `domain`
- `tags`

作为 External Link 的优先候选来源。

不再建立第二套 Reference Links。

对应 V1 完成后，Macro / Commodity / Crypto 子页此前“整块 Trading Tools”模块最终不再需要；届时由 Native 内容 + 精准 External Link 取代。当前不删除，待线下验收后处理。

---

## 6. 未文档化网页接口【冻结】

网页背后的 HTTP/JSON endpoint 没有官方 API 文档时，只有同时满足以下条件才考虑 Native：

- 无登录/绕过行为；
- 无 CAPTCHA/WAF/token 绕过；
- endpoint 稳定；
- 参数和字段口径可解释；
- rights_scope 允许；
- parser/schema health check；
- cache / LKG；
- 失效可降级。

只要维护或权利风险明显偏高，直接外链。

---

## 7. Phase F 分类台账【冻结】

每个目标至少记录：

| Field | 含义 |
|---|---|
| Module / Metric | 对应模块与指标 |
| Reference Website / Exact URL | 参考原站 |
| Primary / Fallback | Native来源 |
| History / Frequency | 历史与频率 |
| Automation | 自动化状态 |
| Maintenance | low / medium / high |
| Rights Scope | internal / attribution / review / restricted 等 |
| Final Product | Native / External Link / Embed |

最终状态：

- `NATIVE_READY`
- `NATIVE_CANDIDATE`
- `EXTERNAL_LINK`
- `OFFICIAL_EMBED`
- `OPEN`
- `NOT_CONFIGURED`

真实结果统一写入 `HEDGE_BOARD_PHASE_F_AUDIT.md`。

---

## 8. UI：External Reference Button【冻结】

- Additive Only；
- 放在对应 Section / Card；
- 文案明确，例如“查看原站”“查看完整期限结构”“查看详细链上数据”；
- 新标签页打开；
- 不伪装成平台自有数据；
- 可显示网站名称；
- 原站失效不影响本平台其它模块。

---

## 9. `platform-data` 定位【冻结】

`platform-data` 是**版本化数据生产与分发仓库**，不是高频实时交易数据库。

适合：

- 宏观月/周/日频；
- Market Detail 日频历史；
- ETF Flow（rights允许时）；
- CFTC/官方库存；
- 日频 On-chain / Stablecoin；
- Polymarket适度采样概率；
- Crypto derivatives 适度聚合/snapshot。

不保存：

- tick；
- order book；
- 秒级；
- 每分钟全市场 raw feed；
- 高频实时交易流。

---

## 10. GitHub 存储策略【冻结】

最新前端消费：JSON。

```text
public/v1/<module>/manifest.json
public/v1/<module>/dashboard.json
public/v1/<module>/market-detail.json
public/v1/<module>/series/*.json
```

长历史：CSV / Parquet，按年或月分区。

避免：

- 巨型 JSON 每天整体重写；
- 大量日粒度小文件；
- SQLite / DuckDB 二进制数据库频繁 commit。

Crypto Funding/OI/Basis V1 只存 latest + 页面需要的适度采样/聚合历史。

---

## 11. 数据维护规则【冻结】

每个 Native Provider 必须有：

- adapter；
- source registry；
- schema / latest-date check；
- freshness threshold；
- timeout / finite retry；
- fallback / LKG；
- quality flags；
- provenance；
- rights note。

### 不变不提交

```text
fetch → normalize → compare → no material change → no commit
```

### 失败不清空

```text
fetch failed → retain LKG → stale/degraded/error → log
```

External Link 只需复用 Trading Tools 精确入口并做最小可达性维护。

---

## 12. 数据库维护结论【当前基线】

V1 不引入传统数据库。

未来出现以下任一情况再升级专业存储：

- 分钟级以上长期历史；
- 文件量明显膨胀；
- Git / Actions / API读取性能恶化；
- 复杂 SQL/横截面查询；
- WebSocket实时入库；
- 多用户并发写入。

升级时保持 canonical contract 稳定，避免前端大改。

---

## 13. Phase F 最终目标【Current】

```text
产品需要某数据
        ↓
技术 + 维护 + rights 都适合 Native？
        ↓
YES → NATIVE
        ↓
NO → Trading Tools / 官方原站有成熟入口？
        ↓
YES → EXTERNAL_LINK
        ↓
NO → OPEN / NOT_CONFIGURED
```

Phase F 完成后：

- Phase 0 只为 Native 项建设数据基础设施；
- External Link 只建设精准按钮；
- 不为商业/受限数据建立脆弱抓取链；
- 不再在业务子页重复展示整块 Trading Tools 目录。
