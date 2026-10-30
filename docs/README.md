# 项目文档入口

文档服务于三个问题：现在做什么、系统当前如何工作、某项变更应改哪里。按任务读取负责该事实的最少文档；不要顺序通读整个 `docs/` 或 `platform-web/docs/`。

## 先从这里进入

| 你要解决的问题 | 唯一入口 |
|---|---|
| 当前目标、优先级、阻塞、下一步 | [PROJECT.md](PROJECT.md) |
| 一个跨任务阶段如何继续 | 对应的 `workstreams/<stage-slug>.md`；仅在存在活跃阶段时读取 |
| 已发布基线、候选范围、外部事实限制 | [BASELINE.md](BASELINE.md) |
| 产品范围和跨模块口径 | [product/PRD.md](product/PRD.md) |
| 系统拓扑、依赖方向、数据权威 | [architecture/SYSTEM_MAP.md](architecture/SYSTEM_MAP.md) |
| 代码、策略与持久化 Owner | [architecture/OWNERSHIP.md](architecture/OWNERSHIP.md) |
| API 与领域合同索引 | [contracts/README.md](contracts/README.md) |
| 数据库与迁移纪律 | [database/README.md](database/README.md) |
| 启停、健康检查和恢复 | [operations/RUNBOOK.md](operations/RUNBOOK.md) |
| 受控实盘验收 | [operations/LIVE_ACCEPTANCE_RUNBOOK.md](operations/LIVE_ACCEPTANCE_RUNBOOK.md) |
| Git、评审和 CI | [engineering/GIT_WORKFLOW.md](engineering/GIT_WORKFLOW.md) |
| 日常启动和使用入口 | [根 README](../README.md#日常使用) |
| 视觉、交互和前端组件约定 | [前端文档入口](../platform-web/docs/README.md)中的 DESIGN / FRONTEND / ACCEPTANCE |

产品范围与策略位于 `product/`；UI 和前端实现细节位于 [platform-web/docs/README.md](../platform-web/docs/README.md)。历史任务卡、evidence、program 和旧阶段计划已经退出当前文档树，必要追溯由 Git 历史承担。

## 按任务读取

| 任务类型 | 默认上下文 |
|---|---|
| 文案、样式或局部组件 | 根 `AGENTS.md`、目标代码和邻近测试 |
| 单模块产品功能 | 再读对应模块产品文档 |
| 跨前后端业务功能 | 再读系统地图及直接相关合同 |
| 订单、成交、持仓或恢复 | 再读策略产品文档、执行合同和相关模块 `AGENTS.md` |
| 真实交易或外部写入 | 再读 Live Runbook 和对应活跃阶段；仍需逐项授权 |
| 阶段性项目续接 | `PROJECT.md`、对应唯一 workstream 及其直接链接的权威文档 |

读取范围由任务边界决定，验证范围由影响和风险决定：局部低风险修改运行直接相关检查，公共合同、权限、持久化、跨模块或交易安全修改扩大回归。不要为此建立 Context Pack、自动路由器或新的流程文档。

## 文档分层

| 层级 | 回答什么 | 更新时机 |
|---|---|---|
| 项目驾驶舱 | 现在做什么，卡在哪里，接下来做什么 | 优先级、状态、阻塞、决策或下一步变化时 |
| 活跃阶段 | 一个跨任务结果如何继续、验收门是否满足 | 子任务取得证据、出现阻断或下一动作变化时 |
| 稳定权威 | 产品、架构、合同、数据库、运维的当前规则 | 对外行为或长期边界变化时 |
| 专项参考 | 模块需求、策略说明、UI、实现设计 | 对应专项发生变化时 |
| 历史证据 | 为什么曾这样做、当时如何验收 | 原则上不更新；由 Git、PR、ADR 追溯 |

文档的状态不由所在目录推断。没有被本页或专项入口列为权威的文档，默认是按需参考，不得覆盖代码、测试和上述权威文档所证明的当前事实。

## 阶段与更新纪律

执行模式、必要提问、文档影响检查和阶段收尾统一遵循[根 AGENTS.md](../AGENTS.md)。本页只维护阅读入口，不另写一套执行流程或验收门槛。

一个独立验收结果只保留一个活跃阶段快照；完成后把稳定事实归回 Owner，状态归回 `PROJECT.md`，历史由 Git 保留。需求尚未被 Owner 确认时只进入驾驶舱发现箱。

项目的持久记忆就是本页所列权威与活跃阶段。工具生成的记忆、旧 `.workbuddy` 日志和聊天可帮助检索，但不能覆盖当前规则、充当运行证明或授予权限。没有每次变更自动同步全部记忆的保证；任务涉及的事实由AI在原Owner内更新，无需创始人手动维护技术记录。

文档检查重点阻断缺失入口、坏链接、失联阶段和明确的旧候选版本；不要求固定英文句子或章节排版，迁移说明仅作内容复核提醒。版本一致性归 `scripts/check-version-consistency.py`，代码架构归 `scripts/check-repository-structure.py`，不重复维护同一检查。检查通过不代表语义或外部运行已全部验收；只核对本次受影响的事实。

## 保持文档精简

- 当前状态放驾驶舱，稳定规则放对应权威，测试和实现证据留在代码与 Git。
- 引用事实 Owner，不复制合同、长期记忆或另一份阶段进度。
- 普通开发不新增任务卡、计划、回执、审计报告或流程框架。
- 按已有用途更新，不照模板新建 TODO、项目概览、设计、组件或用户手册的同义副本。使用说明先补根 README 或现有模块文档；面向用户的发布说明仅在确有发布需要时整理，开发历史由 Git 保留。
