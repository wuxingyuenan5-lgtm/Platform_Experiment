# Platform V6 文档治理规则

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：文档治理

## 1. 目标

建立唯一、可追溯、适合人工、AI 和 Codex 协作的文档体系，避免产品需求、架构原则、实施计划、历史交接和临时讨论互相替代。

## 2. 目录职责

```text
docs/
├─ README.md
├─ governance/
├─ audit/
├─ architecture/
│  ├─ frontend/
│  ├─ backend/
│  ├─ integration/
│  ├─ domain/
│  └─ decisions/
├─ modules/
├─ strategies/
├─ design/
├─ quality/
└─ archive/
```

- `README.md`：唯一总入口和有效文档索引。
- `governance/`：术语、文档状态和维护规则。
- `audit/`：资产盘点、遗留清单和审查结果。
- `architecture/`：技术架构、跨层边界和 ADR。
- `modules/`：产品模块定位和需求。
- `strategies/`：策略定位、口径和需求。
- `design/`：全平台 UI 和交互规范。
- `quality/`：发布门槛和检查清单。
- `archive/`：已废弃或仅供历史查询的文件。

## 3. 文档状态

### `active`

当前有效，可以作为产品、架构、设计或开发依据。

规则：

- 同一主题只有一份主 active 文档。
- `docs/README.md` 或架构入口必须列出。
- 其他文档引用其路径，不复制完整规则。

### `draft`

正在讨论，尚未成为正式口径。

规则：

- 不替代 active 文档。
- 不作为默认开发和实施依据。
- 进入实施前需要用户确认并转为 active，或将结论合并进 active 文档和 ADR。

### `superseded`

已经被新文档替代。

规则：

- 顶部注明替代文档。
- 不再作为当前依据。
- 可以保留一段时间后归档。

### `archived`

仅用于历史查询。

规则：

- 不参与当前产品和开发判断。
- AI 默认不得读取其内容作为当前要求。

## 4. 标准文档头部

正式文档根据适用范围使用以下字段：

```text
状态：active | draft | superseded | archived
产品基线：Platform V5
架构版本：Platform V6
适用分支：refactor/frontend-architecture-v6
文档层级：产品模块 | 策略 | UI 设计 | 前端架构 | 后端架构 | 前后端协作 | 公共领域模型 | 跨层治理
```

按需要增加：

```text
策略 ID：funding
主责产品模块：策略管理
主责技术领域：Trading and Execution
替代文档：docs/...
最后确认日期：YYYY-MM-DD
```

字段含义：

- 产品基线描述当前用户可见产品版本。
- 架构版本描述治理和目标架构版本。
- 适用分支描述当前 Git 实施分支。
- 三者不得互相替代。

现有旧文档可以在后续修改时逐步补齐，不要求只为元数据一次性改动全部文件。

## 5. 命名规则

### 模块文档

- `模块名称-模块定位.md`
- `模块名称-需求文档.md`

### 策略文档

使用稳定策略名称，例如：

- `资费套利.md`
- `跨所价差.md`
- `海内外价差.md`

### 架构文档

使用英文小写连字符或清晰中文名称，同一目录保持一致。

### ADR

使用：

```text
ADR-序号-决策名称.md
```

### 临时文档

临时交接和讨论稿带日期或 DRAFT，并在结论确认后：

- 合并进 active 文档。
- 形成 ADR。
- 标记 superseded。
- 移入 archive。

## 6. 唯一事实来源

| 内容 | 唯一主文档或来源 |
|---|---|
| 总文档索引 | `docs/README.md` |
| 中文术语 | `docs/governance/glossary.md` |
| 产品模块定位 | `docs/modules/*-模块定位.md` |
| 模块需求 | `docs/modules/*-需求文档.md` |
| 策略口径 | `docs/strategies/*.md` |
| 全平台 UI | `docs/design/platform-ui-guidelines.md` |
| 产品归属和数据权威 | `docs/architecture/module-ownership-matrix.md` |
| 公共业务对象 | `docs/architecture/domain-model-boundaries.md` |
| 状态枚举和生命周期 | `docs/architecture/domain/status-enums-and-lifecycles.md` |
| 后端模块所有权 | `docs/architecture/backend/service-boundaries.md` |
| 交易可靠性流程 | `docs/architecture/backend/trading-execution-reliability.md` |
| API 错误、幂等和版本 | `docs/architecture/integration/api-contract-and-versioning.md` |
| 实时事件和恢复 | `docs/architecture/integration/realtime-events-and-recovery.md` |
| 审批和双人复核 | `docs/architecture/domain/approval-and-dual-control.md` |
| 研究、行情和内容数据边界 | `docs/architecture/backend/research-data-and-content-boundaries.md` |
| 后端 Read Model | `docs/architecture/backend/query-and-read-models.md` |
| 前端状态归属 | `docs/architecture/frontend-state-ownership.md` |
| 前端策略静态能力 | `src/views/strategy/shared/strategyRegistry.ts` |
| 策略产品能力 | `docs/architecture/strategy-capability-matrix.md` |
| 交易工具人工维护源 | `docs/trading-tools-bookmarks-review.md` |

规则：

- 主文档完整定义规则。
- 引用文档只解释本层如何使用，不复制完整枚举和清单。
- 发现重复定义时，保留主文档内容，其他位置改为引用。

## 7. 产品和架构变更流程

### 产品需求变化

1. 判断影响模块或策略。
2. 更新对应 active 模块或策略文档。
3. 更新职责或能力矩阵，适用时。
4. 更新术语表，适用时。
5. 再修改代码。
6. 验证代码与文档一致。

### 架构边界变化

1. 更新公共领域或对应架构主文档。
2. 判断是否需要 ADR。
3. 更新受影响的前端、后端和协作引用。
4. 更新索引。
5. 再进入技术规划和代码实现。

### 技术选型变化

数据库、消息队列、交易内核、Gateway 和部署拓扑等重大选型必须形成专项方案和 ADR，不通过临时聊天直接成为 active 架构。

## 8. 规划文档规则

架构文档回答“系统应该如何设计和约束”。

规划文档回答：

- 先做什么。
- 谁负责。
- 任务如何拆分。
- 时间、依赖和验收。

在规划未确认前，实施路线、任务列表和阶段安排应标记为 draft。架构原则可以被规划引用，但不能用未经确认的 roadmap 反向修改架构。

## 9. AI 和 Codex 使用规则

开始任务时优先读取：

1. `docs/README.md`。
2. 对应模块和策略文档。
3. 对应架构主文档。
4. 相关 ADR。
5. 当前代码。

默认忽略：

- `archive/`。
- superseded 文档。
- 未列入入口的临时交接。
- DRAFT，除非用户明确要求讨论。

当代码与 active 文档冲突时：

- 先指出冲突。
- 不自动判断哪一方一定正确。
- 由用户确认实际口径。
- 确认后同时修正文档和代码。

## 10. DOCX 和交接文档

DOCX 可以保留，但不作为活跃需求主要格式。

处理顺序：

1. 识别仍有效的唯一信息。
2. 将内容迁移到对应 Markdown active 文档。
3. 记录替代关系。
4. 原文件归档。

交接文档只用于恢复上下文。任务结束后：

- 产品信息合并进模块或策略文档。
- 工程信息合并进架构或审计文档。
- 原交接标记 superseded 或 archived。

## 11. 文档审查清单

至少检查：

- 状态和元数据是否明确。
- 是否与已有 active 文档重复。
- 是否使用统一术语。
- 是否明确负责和不负责。
- 是否把草案或建议写成确定事实。
- 是否复制了其他主文档的完整枚举。
- 是否区分产品归属、技术领域和数据权威。
- 是否区分架构原则和实施计划。
- 是否与当前代码和路由存在明显冲突。

## 12. 删除和归档规则

删除前确认：

- 无路由和代码引用。
- 无唯一业务信息。
- 已有替代文档或实现。
- 已记录删除原因。
- 用户明确允许，或进入确认后的清理阶段。

文档不得仅因“看起来旧”直接删除。

## 13. 更新责任

用户最终确认产品口径和重大架构决策。AI 和 Codex 可以：

- 盘点冲突。
- 提议结构。
- 更新文档。
- 检查一致性。

未经确认不得自行改变：

- 一级产品架构。
- 策略范围。
- 损益口径。
- 风险规则。
- 交易执行规则。
- 实盘技术选型和上线安排。

## 14. 验收标准

- `docs/README.md` 是唯一总入口。
- 每个 active 文档具有明确状态和范围。
- 每类核心规则具有唯一主文档。
- 产品、架构和规划文档职责分开。
- DRAFT 和历史文档不会被误作当前实施依据。
- AI 开发任务可以通过固定阅读顺序获得当前口径。
