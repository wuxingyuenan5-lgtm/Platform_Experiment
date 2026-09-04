# 合同索引

合同定义跨模块可依赖的当前行为、数据语义和失败处理。项目状态不写入合同；实现细节以代码和可执行测试为证据。

| 领域 | 当前合同 |
|---|---|
| 浏览器访问与产品数据 | [BROWSER_ACCESS_AND_PRODUCT_DATA.md](BROWSER_ACCESS_AND_PRODUCT_DATA.md) |
| 身份、权限和会话 | [AUTHORIZATION.md](AUTHORIZATION.md) · [AUTH_ERRORS.md](AUTH_ERRORS.md) · [ACCESS_MATRIX.md](ACCESS_MATRIX.md) |
| Platform API | [API.md](API.md) |
| 执行风险 | [EXECUTION_RISK.md](EXECUTION_RISK.md) |
| 跨所执行 | [CROSS_SPREAD_EXECUTION.md](CROSS_SPREAD_EXECUTION.md) |
| Runtime Command/Event | `runtime-v1.json` 可执行快照及双方 `runtime_contracts.py` |
| Venue Adapter | [VENUE_ADAPTERS.md](VENUE_ADAPTERS.md) |
| 外部账户可观测性 | [LIVE_ACCOUNT_OBSERVABILITY.md](LIVE_ACCOUNT_OBSERVABILITY.md) |
| Venue 对账 | [VENUE_RECONCILIATION.md](VENUE_RECONCILIATION.md) |
| EOD 与扩容门禁 | [EOD_RECONCILIATION.md](EOD_RECONCILIATION.md) |
| FinancialFact 与正式账务 | [FINANCIAL_FACTS.md](FINANCIAL_FACTS.md) |
| 会员持仓与单位净值 | [MEMBER_HOLDINGS.md](MEMBER_HOLDINGS.md) |
| 研究数据 | [RESEARCH_DATA.md](RESEARCH_DATA.md) |

## 维护规则

- 一项跨模块语义只有一个合同 Owner；其他文档链接它，不复制字段和状态机。
- 不兼容变更提升合同版本并提供迁移或兼容测试。
- 金融数值保持 Decimal、明确币种和单位；时间保持带时区语义。
- 未知输入、未知外部结果和无法确认的权限默认 fail closed。
- JSON 快照是可执行边界，不是另一份人工需求文档。
