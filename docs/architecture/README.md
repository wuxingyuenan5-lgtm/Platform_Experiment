# 架构文档入口

架构文档只维护长期稳定的系统边界，不记录当前排期、任务过程、发布状态或测试日志。

| 问题 | 权威文档 |
|---|---|
| 系统由什么组成、依赖如何流动、数据由谁负责 | [SYSTEM_MAP.md](SYSTEM_MAP.md) |
| 哪段代码、策略与持久化由谁负责 | [OWNERSHIP.md](OWNERSHIP.md) |
| 为什么作出一项长期且难逆的决定 | [decisions/README.md](../decisions/README.md) |
| 当前跨模块合同 | [contracts/README.md](../contracts/README.md) |
| 数据库、DDL 与迁移纪律 | [database/README.md](../database/README.md) |

## 架构底线

- 仓库只有三个可部署工程主体：`platform-web`、`platform-api`、`execution-runtime`。
- `platform-api` 保持模块化单体；不要为了目录对称引入微服务、消息队列、事件总线或全局 DI。
- Venue SDK、外部订单副作用、Runtime Journal 与外部结果标准化留在 `execution-runtime`。
- 跨边界使用版本化合同；未知结果必须保持 `result_unknown`，不能推断失败后自动重下。
- 运营投影不替代不可变 FinancialFact 及可重建的正式 Position/PnL/NAV。
- 金融边界保持 `Decimal`、明确币种/单位和带时区时间戳。

详细关系以 `SYSTEM_MAP.md` 为准，具体文件 Owner 以 `OWNERSHIP.md` 为准。本页不复制两者的完整内容。

## 何时写 ADR

只有决策同时满足“影响多个模块、会长期约束后续工作、未来难以无成本撤销”时才新增 ADR。普通重构、字段补充、测试策略和阶段性方案留在代码、合同或 PR，不新增架构总览。

前端分层与布局只在 `platform-web/docs/FRONTEND.md` 和 `platform-web/docs/DESIGN.md` 维护。后端、领域模型、Runtime 与跨层合同统一归本目录和 `docs/contracts/`，不在前端目录建立平行架构。
