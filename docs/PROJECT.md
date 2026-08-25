# 项目驾驶舱

> 这是项目跟进的唯一日常入口，更新时间：2026-08-25。它记录当前方向、状态和待决问题，不承载详细合同、测试证据或 Git 状态。

## 一句话目标

构建一个由创始人主导、默认只读且交易写入严格受控的投研、策略管理与执行平台；先完成少数真实闭环，再扩展策略、账户和外部用户。

## Now

| 工作流 | 当前结果 | 完成定义 | 下一动作 |
|---|---|---|---|
| 文档与项目跟进 | `pending_cleanup`：新结构、AI 回填和活跃文档已收敛；旧材料已移入清理隔离区 | 项目只从本页跟进；产品、架构、合同和前端各有明确位置；旧过程材料退出仓库 | Owner 手动删除 `.codex-cleanup-quarantine/docs-retire-20260825`，随后执行最终复核 |
| Platform 0.11.2 候选 | `in_progress`：真实 Bybit/MT5 只读监控链路已打通，Funding/Cross/Bottom/Short A 的 logical account 绑定和同步合同已收敛；本地开发启动器现已常驻复用并带登录烟测，但 Funding 页面仍存在同一 Bybit UTA 的 spot/perp category 读取阻断 | 独立验收、浏览器访问回归和 Capability 对齐完成，已知限制明确 | 保持只读链路稳定；先完成 Funding 多 category 只读合同，再进入 Owner 页面小额受控测试 |
| 受控交易闭环 | `blocked_by_authorization/evidence`：真实只读验收不等于交易授权；Live Write 仍关闭，Funding controlled-live 仍默认 `423`，且不存在 approved LiveTradingSession | 每个外部连接或写入步骤具有单独授权、外部证据、对账和强制回只读 | 继续保持只读；等待 Owner 提供下一步明确操作授权 |

## Next

- 把 0.11.2 剩余工作压缩成可验收结果，不再用新的阶段文档复制当前状态。
- 保持真实只读监控链路：Funding/Cross 共享 `bybit-live-main`，Bottom 使用独立 Bybit 只读账号，Cross/Short A 共用单 Terminal MT5 只读切换，Short B 继续 `unbound`。
- 保持本地三服务常驻：`scripts/dev-platform.ps1` 负责健康复用、失败清理、状态文件和登录烟测，不再接受“前端还在、API/Runtime 已被回收”的半残状态。
- 在任何下一步外部操作前，继续要求 `liveWriteEnabled=false`、无 approved `LiveTradingSession`、Funding controlled-live 默认 `423`。
- 当产品方向出现新想法时，先放入下方发现箱；确认后再进入正式 PRD 或策略文档。

## Later

- 在已有闭环稳定后再决定海内外价差、抄底、短线交易员、更多 Venue、生产部署和自动化范围。
- 只有出现真实检索压力时才引入站点生成器、文档数据库或更复杂的元数据系统。
- 历史过程材料是否清理，等确认其中没有独有规则后由 Owner 单独决定；不批量删除。

## 发现箱

AI 可以自动记录不完整需求、缺口和不确定性。条目在 Owner 明确说出“确认进入范围”前都不是正式产品需求，也不能授权外部连接、部署或真实交易。

| 想法或问题 | 当前判断 | 需要确认 |
|---|---|---|
| 如何让 AI 自动维护项目跟进 | 已采用“任务结束前文档影响检查 + 本页唯一跟进入口” | 连续使用若干任务后，确认字段是否足够、是否需要更直观的 UI |
| 早期需求无法一次写好 | 采用“发现箱 → Now/Next/Later → 稳定权威”的渐进流程 | 哪些新产品方向进入近期优先级，由 Owner 逐项确认 |

## 当前不可突破的边界

- `platform-api` 保持模块化单体；Venue SDK 与订单副作用留在 `execution-runtime`。
- 金融边界保持 `Decimal` 与带时区时间戳。
- Live Write 默认关闭；本地测试、文档、CI 或合并都不能产生真实交易授权。
- Kill Switch、幂等、单一业务意图、防重复、累计成交上限、对账和 `result_unknown` fail-closed 语义不得弱化。
- 外部部署、凭据、账户、连通性、订单、持仓和生产状态没有独立证据时一律视为未证明。

详细规则分别以 [AGENTS.md](../AGENTS.md)、[系统地图](architecture/SYSTEM_MAP.md)、[当前工程基线](BASELINE.md)和[受控实盘验收](operations/LIVE_ACCEPTANCE_RUNBOOK.md)为准。

## 更新约定

- AI 可以根据代码、测试或外部证据，自动更新既有工作流的状态、阻塞、已验证结果和下一技术动作。
- AI 可以自动向发现箱增加待确认条目。
- 产品优先级、里程碑选择和风险容忍度由 Owner 决定；AI 不从开发行为推断。
- 只有 Owner 明确说出“确认进入范围”，相关需求才可以写入 `product/` 正式产品文档。
- 不更新本页：纯重构、补测试、格式调整以及不改变项目判断的内部实现。
- 每个表格条目只写“结果、完成定义、下一动作”，不粘贴日志、提交号或长篇设计。
- 新需求先进入发现箱；范围和优先级分别确认后，再移动到 Now、Next 或 Later，并同步真正的产品权威。
- 已完成事项不在这里累积成长日志；把稳定结论并入权威文档，历史由 Git 保存。
