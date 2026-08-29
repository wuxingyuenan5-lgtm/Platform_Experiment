# 对冲基金看板｜数据可行性与维护策略

> 状态：Planning Baseline v0.3 / Engineering NOT STARTED  
> 上位文档：`docs/hedge-board/HEDGE_BOARD_OPTIMIZATION_MASTER_PLAN.md`  
> 实施文档：`docs/hedge-board/HEDGE_BOARD_IMPLEMENTATION_PLAN.md`  
> Phase F 审计：`docs/hedge-board/HEDGE_BOARD_PHASE_F_AUDIT.md`  
> 数据仓库：`wuxingyuenan5-lgtm/platform-data`  
> 作用：在实际开发前审计数据可获取性、自动化稳定性、存储成本，以及目标数据/子模块应采用“自己落地”还是“外链跳转”。

---

## 1. 当前最高优先级【冻结】

在正式进入大规模工程实施前，优先解决：

1. 数据是否能够长期、免费、稳定获取；
2. 数据是否具备足够历史序列；
3. 数据是否能够自动更新；
4. 数据频率与更新时点是否明确；
5. 数据源失效时是否有 fallback / LKG；
6. 数据是否适合存入 GitHub 文件仓库；
7. 用户已整理的参考网站/子模块，哪些值得自己落地；
8. 不好稳定落地的项目，对应哪个原站链接最适合作为跳转入口。

核心产品原则固定为：

> **好落地的自己落地；不好落地的保留参考网站入口，做成按钮直接跳转原站。**

因此，“无法稳定抓取”不自动等于删除功能，也不意味着必须继续投入大量时间逆向第三方网站。

---

## 2. Data Feasibility Gate【冻结】

任何准备由本平台自己展示真实数据的新指标，在进入工程 Phase 前，至少检查：

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
- Provider 失败不会覆盖 LKG；
- 预计维护复杂度在 V1 可接受范围内。

通过 Gate：进入本平台真实数据链路。

未通过 Gate：**优先转为 External Reference Button，而不是继续强行抓取。**

只有以下两项同时成立才使用 `not_configured`：

1. 暂无可维护的自有数据链；
2. 也没有用户认可的稳定参考网站/原站入口。

---

## 3. 网站子模块的最终产品策略【冻结】

### A. Native / Own Data Implementation

当数据容易稳定落地时：

```text
official / reliable public source
→ platform-data
→ canonical data
→ platform-api
→ existing UI / additive chart
```

适用条件：

- 数据免费或满足当前免费策略；
- 自动化稳定；
- 历史足够；
- 口径明确；
- 维护成本合理；
- 使用条件允许。

这是优先方案。

### B. External Reference Button

当成熟网站已经提供高质量子模块，但我们自己抓取/重建存在以下任一问题时：

- 无稳定免费 API；
- 历史数据难拿；
- 页面内部接口维护风险高；
- 需要复杂动态 token / 登录；
- 授权或再分发不清晰；
- 数据复杂但原站体验已经成熟；
- V1 自建数据链投入产出比过低；

则不继续强行实现数据链，直接在对应位置提供参考入口：

```text
[查看原站 / 查看详细数据 / 查看完整期限结构]
            ↓
新标签页打开原站具体子页面
```

External Reference Button 是正式产品能力，不是失败占位。

按钮应尽量指向具体数据子页面，而不是网站首页。

---

## 4. Trading Tools 的只读参考库角色【冻结】

当前 Hedge Board 的 Trading Tools 已经整理了大量宏观、金属、加密等参考网站。

本轮不再建立第二套 Reference Links 数据库。

Trading Tools 在本项目中的当前定位：

```text
Trading Tools
= 用户现有参考网站目录
= Phase F 可只读检索
= External Reference Button 的优先候选来源
≠ 当前要继续开发/维护的业务模块
```

具体规则：

- Trading Tools 继续保持 Deferred；
- 不修改 Trading Tools 页面；
- 不重构其分类；
- 不要求处理/修复其元数据生成来源；
- 不因本轮审计去清理书签；
- Phase F 只读取当前已经存在的 `name / url / description / domain / tags`；
- Native 不合适时，优先从 Trading Tools 中寻找对应的精确参考页面。

如果未来 External Reference Button 需要配置，可直接引用已有 Trading Tool item / URL，避免再人工维护一套重复书签。

---

## 5. 子页旧“交易工具”模块与 External Link 的区别【冻结】

Macro / Commodity / Crypto 子页此前存在从 Trading Tools 读取并展示一整块“本页工具”的设计。

当对应子页 V1 完善后，该整块通用工具目录不再需要。

最终产品应是：

```text
子页
├─ Native核心数据/图表
├─ Native核心Market Detail
└─ 个别难落地指标的精准External Reference Button
```

而不是：

```text
子页
├─ Native内容
└─ 再复制一整块Trading Tools目录
```

注意：

- 当前不立即删除现有子页工具模块；
- 删除/隐藏属于线下最终验收后的页面整理事项；
- 目标方向已冻结：当 V1 内容完善后，旧的整块子页 Trading Tools 不再保留；
- 精准 External Reference Button 与旧的整块工具目录不是同一产品能力。

---

## 6. Embed / Widget 的定位【冻结】

官方 Embed / Widget 可以使用，但不是必须优先于外链按钮。

仅当以下条件同时满足时考虑嵌入：

- 官方明确支持第三方 Embed；
- 页面稳定；
- CSP / X-Frame-Options 允许；
- 与现有 UI 冲突不大；
- 用户体验明显优于跳转原站。

否则直接采用 External Reference Button，更简单、更稳定。

TradingView 仍主要作为现有图表展示 / 大图入口使用；不从 Widget 反向抓取数据。

---

## 7. 网站内部公开接口的处理【冻结】

如果某参考网站子模块背后存在公开 HTTP/JSON endpoint，但没有正式 API 文档，只有在以下条件都满足时才允许进入自有数据链：

- 无登录绕过；
- 无 token / CAPTCHA / WAF 绕过；
- endpoint 可重复稳定访问；
- 参数和字段口径可解释；
- 使用条件允许；
- 有 parser/schema health check；
- 有 cache / LKG；
- 上游失效时可降级。

如果维护风险明显偏高：

> **不要因为技术上暂时能抓就强行使用，直接保留原站按钮。**

---

## 8. Phase F 分类台账【冻结】

每个目标输出：

| Module | Reference Website | Exact URL | Own Data Feasible | Primary Source | History | Automation | Maintenance | Final Product |
|---|---|---|---|---|---|---|---|---|
| 示例 | Example | direct-url | yes/no | source | enough/limited | ready/open | low/med/high | NATIVE / EXTERNAL_LINK |

最终状态优先使用：

- `NATIVE_READY`；
- `NATIVE_CANDIDATE`；
- `EXTERNAL_LINK`；
- `OFFICIAL_EMBED`；
- `OPEN`；
- `NOT_CONFIGURED`。

真实审计结果统一进入：

`docs/hedge-board/HEDGE_BOARD_PHASE_F_AUDIT.md`

---

## 9. UI 规则：外链按钮【冻结】

External Reference Button 必须遵守现有 Hedge Board UI，不重新设计页面。

原则：

- Additive Only；
- 放在对应 Section / Card 合理位置；
- 文案清晰，例如“查看原站”“查看完整期限结构”“查看详细链上数据”；
- 默认新标签页打开；
- 不伪装成平台自有数据；
- 可显示来源网站名称；
- 不因第三方网站变化影响本平台其他模块运行。

---

## 10. `platform-data` 的定位【冻结】

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

## 11. GitHub 存储策略【冻结为 V1 基线】

### 11.1 最新数据 / 前端消费

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

### 11.2 长历史

较长历史序列优先：

- CSV（数据量较小）；
- Parquet（数据量较大 / 多列 / 高频一些）。

避免：

- 一个巨大 JSON 每天整体重写；
- 每个日期建立大量小文件；
- 把 SQLite / DuckDB 二进制数据库频繁 commit 到 Git。

建议按年或按月分区。

### 11.3 高频 Crypto

Funding / OI / Basis V1 只保存页面实际需要的聚合粒度，例如：

- latest snapshot；
- 1H / 4H 采样或聚合；
- Daily aggregate；
- 滚动历史。

不在 GitHub 保存每分钟全量 raw feed。

未来产品明确需要分钟级 / tick 历史时，再单独引入真正时序存储。

---

## 12. 数据维护规则【冻结】

每个 Native Provider 必须有：

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

### 12.1 不变不提交

```text
fetch
→ normalize
→ compare
→ no material change
→ no commit
```

### 12.2 失败不清空

```text
fetch failed
→ retain last known good
→ status stale/error/degraded
→ log failure
```

禁止空数组覆盖有效历史。

### 12.3 External Link 维护

外链入口不需要数据抓取，只需要最小维护：

- 优先读取 Trading Tools 已有链接；
- 只记录业务页选中了哪个精确入口；
- 定期检查 URL 可达性；
- 原站迁移时更新引用/URL，不改页面结构。

---

## 13. 数据库维护结论【当前基线】

V1 暂时**不引入传统数据库**。

原因：

- 当前核心用途是日常扫盘与复盘，不是高频交易；
- Macro / Commodity 大部分是日 / 周 / 月频；
- Crypto 高频数据只保留页面必要聚合粒度；
- GitHub 文件 + Git 历史能够承担版本化、追溯、回滚和分发；
- 数据量在 V1 仍可控制。

但 GitHub 不是通用数据库，也不是实时数据服务。

未来出现以下条件之一时再升级存储层：

- 需要分钟级以上长期历史；
- 数据文件明显膨胀；
- Git clone / Actions / API 读取性能明显恶化；
- 需要复杂 SQL / 横截面查询；
- 需要实时 websocket 入库；
- 多用户同时写入；
- 数据量达到 Git 文件维护明显不合理的程度。

升级时保持 canonical contract 不变，使前端与 Platform API 无需跟随大改。

---

## 14. Phase F 最终目标【Current】

Phase F 给每一个目标模块确定最终落地方式：

```text
产品需要某数据 / 子模块
        ↓
能否低维护、免费、稳定自己落地？
        ↓
YES → NATIVE
        ↓
NO → Trading Tools/其他用户认可来源中是否已有成熟参考页面？
        ↓
YES → EXTERNAL_LINK
        ↓
NO → OPEN / NOT_CONFIGURED
```

Phase F 完成后：

- Phase 0 只为 `NATIVE` 项建设数据基础设施；
- `EXTERNAL_LINK` 项只建设精准外链按钮；
- 不再建设脆弱抓取链；
- 不再在业务子页重复展示整块 Trading Tools 目录。
