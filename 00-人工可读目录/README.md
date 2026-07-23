# 人工可读目录

状态：`active`  
用途：打开项目文件夹后，第一眼能找到业务模块、需求文档、策略文档、规划和架构入口。  
原则：先看业务，再看需求，再看规划和架构，最后才看代码。

## 1. 当前最重要结论

平台一级模块名称和定位不再调整。当前开发重点是把“策略”模块做实。

V1 优先级：

1. 策略模块。
2. 资费套利完整闭环。
3. 跨所价差完整闭环。
4. 策略管理承接账户、订单、成交、持仓、费用、PnL、固定时间净值。
5. 对冲基金看板、新闻日历与理财后续再优化后端和功能。
6. 金融AI分析暂缓研发。

## 2. 六个一级模块怎么找

| 一级模块 | 当前定位 | 先读 | 再读 | 当前阶段 |
|---|---|---|---|---|
| 首页 | 品牌入口、核心摘要和模块导航 | `../admin-risk/docs/modules/首页-模块定位.md` | `../admin-risk/docs/modules/首页-需求文档.md` | 保持入口，不作为当前主战场 |
| 对冲基金看板 | 宏观、资产类别、跨市场研究和工具聚合 | `../admin-risk/docs/modules/对冲基金看板-模块定位.md` | `../admin-risk/docs/modules/对冲基金看板-需求文档.md` | 后续优化后端和功能 |
| 新闻日历与理财 | 新闻、日历、理财信息整理和筛选 | `../admin-risk/docs/modules/新闻日历与理财-模块定位.md` | `../admin-risk/docs/modules/新闻日历与理财-需求文档.md` | 后续优化后端和功能 |
| 策略 | 具体策略的分析、交易、管理、统计和复盘 | `../admin-risk/docs/modules/策略-模块定位.md` | `../admin-risk/docs/modules/策略-需求文档.md` | 当前第一优先级 |
| 风险管理 | 风险、账户、资金、权限、审计、监控等内部管理入口 | `../admin-risk/docs/modules/风控管理-模块定位.md` | `../admin-risk/docs/modules/风控管理-需求文档.md` | 先支撑策略 V1，后续系统化 |
| 金融AI分析 | 授权数据的归纳、问答、推演和结构化输出 | `../admin-risk/docs/modules/金融AI分析-模块定位.md` | `../admin-risk/docs/modules/金融AI分析-需求文档.md` | 暂缓研发，只保留边界 |

总表入口：`../admin-risk/docs/modules/一级模块定位总表.md`

## 3. 策略模块内部怎么找

策略模块下面有两个实际业务子模块：

| 子模块 | 负责什么 | 定位文档 | 需求文档 | V1 状态 |
|---|---|---|---|---|
| 交易平台 | 行情分析、交易准备、模拟/真实交易指令、执行状态 | `../admin-risk/docs/modules/交易平台-模块定位.md` | `../admin-risk/docs/modules/交易平台-需求文档.md` | 资费套利、跨所价差需要闭环 |
| 策略管理 | 策略实例、账户绑定、订单成交、持仓、费用、PnL、净值、复盘 | `../admin-risk/docs/modules/策略管理-模块定位.md` | `../admin-risk/docs/modules/策略管理-需求文档.md` | 承接全部策略，但 V1 重点是资费套利和跨所价差 |

策略主文档：

- `../admin-risk/docs/modules/策略-模块定位.md`
- `../admin-risk/docs/modules/策略-需求文档.md`

## 4. 六类策略怎么找

| 策略 | 文档 | V1 要求 |
|---|---|---|
| 资费套利 | `../admin-risk/docs/strategies/资费套利.md` | 完整闭环，必须能从分析走到模拟执行、成交、持仓、Funding、费用、PnL、固定时间净值 |
| 跨所价差 | `../admin-risk/docs/strategies/跨所价差.md` | 完整闭环，必须能表达 Crypto 腿和 MT5 腿的订单、Deal、持仓、Swap、费用、PnL、净值 |
| 海内外价差 | `../admin-risk/docs/strategies/海内外价差.md` | V1 只做分析、模拟、字段预留；不做 CTP、真实国内交易、正式汇率损益和完整四层 PnL |
| 抄底 | `../admin-risk/docs/strategies/抄底.md` | V1 只做策略管理入口和外部数据占位 |
| 短线交易员 L | `../admin-risk/docs/strategies/短线交易员L.md` | V1 只做策略管理入口和外部数据占位 |
| 短线交易员 W | `../admin-risk/docs/strategies/短线交易员W.md` | V1 只做策略管理入口和外部数据占位 |

## 5. 要看“规划”读哪些

当前规划还没有单独沉淀成正式 `planning` 目录，所以先按下面顺序读：

1. `../admin-risk/docs/START-HERE.md`
2. `../admin-risk/docs/architecture/platform-target-architecture.md`
3. `../admin-risk/docs/architecture/implementation-roadmap.md`
4. `../admin-risk/docs/architecture/2026-07-17-策略模块V1详细落地规划-DRAFT.md`
5. `../admin-risk/docs/quality/release-gate.md`
6. `../admin-risk/docs/quality/smoke-checklist.md`

带 `DRAFT` 的文档是讨论稿，不是最终实施依据。确认后的内容应该进入 active 文档、ADR 或后续正式规划文档。

## 6. 要看“架构”读哪些

如果只想判断项目架构是否合理，优先读：

1. `../admin-risk/docs/architecture/platform-target-architecture.md`
2. `../admin-risk/docs/architecture/domain/domain-overview.md`
3. `../admin-risk/docs/architecture/backend/backend-overview.md`
4. `../admin-risk/docs/architecture/backend/service-boundaries.md`
5. `../admin-risk/docs/architecture/backend/trading-execution-reliability.md`
6. `../admin-risk/docs/architecture/integration/runtime-command-event-contract.md`
7. `../admin-risk/docs/architecture/module-ownership-matrix.md`

如果只关心“未来接真实交易所 API 会不会埋雷”，重点读：

1. `../admin-risk/docs/architecture/backend/execution-runtime-and-gateway.md`
2. `../admin-risk/docs/architecture/backend/trading-execution-reliability.md`
3. `../admin-risk/docs/architecture/integration/runtime-command-event-contract.md`
4. `../admin-risk/docs/architecture/integration/realtime-events-and-recovery.md`

## 7. 要看“前端体验和页面”读哪些

1. 对应一级模块的 `模块定位`。
2. 对应一级模块的 `需求文档`。
3. `../admin-risk/docs/design/platform-ui-guidelines.md`
4. `../admin-risk/docs/architecture/frontend/frontend-overview.md`
5. `../admin-risk/docs/architecture/frontend/routing-permission-and-environment.md`
6. `../admin-risk/docs/architecture/frontend/data-adapter-and-view-model.md`

## 8. 哪些文档先不要读

以下目录不是第一阅读入口：

| 目录 | 说明 |
|---|---|
| `../admin-risk/docs/archive/` | 历史资料，只在追溯时看 |
| `../admin-risk/docs/audit/` | 资产盘点、技术债务、旧代码检查 |
| `../admin-risk/docs/architecture/decisions/` | 架构决策记录，适合需要理解“为什么这么定”时看 |
| `../admin-risk/docs/architecture/*DRAFT.md` | 讨论稿，不能直接当实施依据 |
| `../admin-risk/docs/strategy/` | 历史或专题文档，当前主策略定义以 `../admin-risk/docs/strategies/` 为准 |

## 9. 后续建议增加的正式规划板块

现在先不移动旧文件。等核心需求过完后，建议新增：

```text
admin-risk/docs/planning/
  README.md
  V1-范围与验收.md
  V1-实施路线图.md
  V1-策略模块任务拆解.md
  V1-后端对象与接口清单.md
  V1-前端页面与交互清单.md
```

这个目录应该只放“确认后要执行”的内容，不放讨论稿。

## 10. 当前人工审阅顺序

建议接下来按这个顺序过文档：

1. `../admin-risk/docs/modules/策略-模块定位.md`
2. `../admin-risk/docs/modules/策略-需求文档.md`
3. `../admin-risk/docs/modules/交易平台-需求文档.md`
4. `../admin-risk/docs/modules/策略管理-需求文档.md`
5. `../admin-risk/docs/strategies/资费套利.md`
6. `../admin-risk/docs/strategies/跨所价差.md`
7. `../admin-risk/docs/architecture/platform-target-architecture.md`
8. `../admin-risk/docs/architecture/domain/domain-overview.md`

这条线过完，V1 的业务闭环、页面边界、后端对象和未来真实交易 API 的风险基本就能定下来。
