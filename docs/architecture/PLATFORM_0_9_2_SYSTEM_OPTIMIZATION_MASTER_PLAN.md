# Platform 0.9.2 全平台系统性优化总方案

> Issue: #136
> Draft PR: #137
> 稳定基线分支：`feature/issue-134-platform-0-9-1-unified-delivery`
> 冻结基线：`8114fce45e46e7920f316f49d03db12dc424acf1`
> 优化分支：`refactor/platform-0.9.2-system-optimization`
> 开发与验收版本：`0.9.2`
> 全量验收后的正式候选：`0.10.1`
> 状态：Phase A证据化审计完成，尚未进入大规模业务重构。

---

## 1. 执行结论

本次审计不支持“推倒重写”或“服务数量过多”这一判断。

当前平台最合理的总体形态仍是：

```text
Platform Web
    ↓ HTTPS / Browser Session / REST
Platform API（模块化单体）
    ↓ 受控Runtime合同
Execution Runtime
    ↓
Venue / Broker / MT5 / Bybit
```

应继续保留三个部署和安全边界，不合并Platform API与Execution Runtime，也不继续拆出微服务。当前Vue、FastAPI、Python 3.12、SQLite和REST方案适合初创阶段，不需要引入Kubernetes、Kafka、GraphQL、CQRS、Event Sourcing、微前端、Service Mesh或复杂依赖注入。

用户感受到的维护和Token负担是真实的，但主要来源不是三服务架构，而是以下问题叠加：

1. “当前状态”存在多个权威文件，并且已经发生分支事实漂移；检查器还会把过时事实验证为正确。
2. 前端保留了大量模板工作区、演示页面、Mock、第三方资源、旧包元数据和无关工程入口。
3. 若干高频页面、Provider、用户服务、风险和运维模块职责过密，普通修改必须读取大文件。
4. 根级`docs/`、`platform-web/docs/`、`tasks/`、历史DRAFT、交接文档和规划文件共同存在，默认检索容易命中历史而非现状。
5. 当前部署材料同时描述新的三服务架构和旧Go/MySQL `projects/risk-control`架构，真实运行入口不唯一。
6. 0.9.2 Draft PR的Base不是`main`，而多数正式CI只监听以`main`为Base的PR，导致当前工作线不会自动获得完整质量门禁。
7. 代码质量门禁采用“局部覆盖+不新增债务”的合理过渡策略，但类型覆盖仍明显不足，尤其是Execution Runtime。
8. 路径和包名仍保留`platform-web`、`vben-admin`、`Variable-Global`等模板或阶段性名称，目录与真实职责不一致。

因此，0.9.2的正确方向是：**先修权威与工程入口，再做命名和低风险模块化；最后才处理高风险交易、风控、会计、Runtime和删除工作。**

---

## 2. 审计方法与可信边界

### 2.1 审计对象

冻结产品基线为：

```text
feature/issue-134-platform-0-9-1-unified-delivery
8114fce45e46e7920f316f49d03db12dc424acf1
```

审计证据在0.9.2分支通过只读GitHub Actions采集。采集分支仅比冻结产品基线增加任务包、审计脚本和审计工作流，不包含产品行为变化。

校正后的证据快照：

```text
cbe4e97fb3b179608e9b95633a84d88627793d0e
```

首轮采集曾将少数二进制资源误判为文本；该方法学问题已明确修正并重跑。本文只采用校正后的结果。

### 2.2 已执行验证

- GitHub 0.9.1统一交付PR已有成功的Platform CI、用户系统E2E、对冲基金看板E2E、Secret Scan、Version Consistency和Research Provider Smoke证据。
- 当前源码快照的四项治理检查通过：版本一致性、Codex上下文、仓库结构、文档一致性。
- Platform API测试：`418 passed`。
- Execution Runtime测试：`76 passed`。
- Python源码和治理脚本静态编译通过。
- 当前环境没有安装pnpm，因此未在本地重复执行前端构建；前端基线以0.9.1 PR的成功CI证据为准。
- Windows真实本地运行、四档浏览器截图、真实Provider、真实Venue/Broker和生产HTTPS仍属于后续验收门槛，本文不把它们误报为已完成。

### 2.3 Token估算含义

Token数据使用UTF-8文本字符数除以4的近似值，只用于前后相对比较，不代表任何特定模型的精确计费Token。

全仓文本规模是“最坏情况下扫描整个仓库”的上限，不是建议Agent每次读取的内容。真正的优化指标是典型任务所需的文件数、行数、跨域数量和重复事实。

---

## 3. 基线量化

### 3.1 冻结产品树规模

扣除0.9.2审计工具本身后，0.9.1冻结产品树约为：

| 指标 | 基线 |
|---|---:|
| 文本文件 | 1,776 |
| 文本行 | 276,992 |
| 估算文本Token上限 | 2,014,104 |
| 自动化测试 | Platform API 418项；Runtime 76项；另有前端结构守卫与浏览器E2E |

0.9.2审计分支（包含审计工具）校正结果：

| 顶层范围 | 文本文件 | 行数 | 估算Token |
|---|---:|---:|---:|
| `platform-web/` | 1,267 | 199,553 | 1,360,784 |
| `platform-api/` | 237 | 43,578 | 370,820 |
| `execution-runtime/` | 60 | 11,422 | 101,829 |
| 根级`docs/` | 68 | 11,822 | 82,050 |
| `tasks/` | 47 | 4,045 | 44,681 |
| `scripts/` | 18 | 3,373 | 29,578 |
| `projects/` | 58 | 2,154 | 12,725 |

关键结论：前端目录占全仓文本Token约67%，是上下文减负的主战场；但其中相当部分是锁文件、模板框架、第三方资源、历史文档、演示和静态目录，不能简单等同于有效产品复杂度。

### 3.2 默认可排除噪音

以下内容不一定需要删除，但应从普通任务默认上下文中排除：

| 类别 | 估算Token | 处理原则 |
|---|---:|---|
| 锁文件 | 133,552 | 构建或依赖任务才读 |
| 历史规划、DRAFT和任务包 | 114,363 | 归档，不作为当前权威 |
| 模板、第三方资源和内部框架 | 95,505 | 产品任务默认不读；保留许可证 |
| 大型静态目录和工具书签数据 | 86,142 | 只在对应数据任务读取 |
| Demo与Mock | 37,470 | 产品任务默认排除；验证无引用后清理 |
| 旧部署和`risk-control`项目 | 14,350 | 先隔离和定性，不直接删除 |

以上约48万Token，占全仓文本上限约24%。这部分首先通过上下文路由和目录治理减负，不需要立即冒险删除。

### 3.3 典型任务当前阅读包

以下是按现有Agent规则、权威文档和直接代码路径构造的可复核任务包，不采用全仓关键词搜索的夸大结果：

| 典型任务 | 文件数 | 行数 | 估算Token |
|---|---:|---:|---:|
| 修改对冲基金看板主要样式 | 5 | 4,936 | 35,405 |
| 修改A股研究字段 | 12 | 2,856 | 26,321 |
| 修改用户权限 | 15 | 1,991 | 16,598 |
| 修改会员持仓API合同 | 12 | 2,083 | 17,644 |
| 修改跨所价差交易展示 | 12 | 2,570 | 17,880 |
| 新增研究Provider | 12 | 2,527 | 23,970 |
| 修复用户系统E2E | 11 | 2,123 | 17,043 |

UI任务异常昂贵，主要因为`hedgeBoard/index.vue`为3,772行，UI规范为1,000行，而不是因为必须阅读三个服务。

---

## 4. 用户感受与技术证据

### 4.1 被证据确认的问题

#### 多个“当前状态”并存

当前至少存在：

- `AGENTS.md`
- `docs/codex/current-state.md`
- `docs/codex/context-map.md`
- `README.md`

其中多份文件仍把`feature/issue-117-platform-0-9-1`写成活动分支，而真实0.9.1统一交付线是`feature/issue-134-platform-0-9-1-unified-delivery`。

`check-codex-context.py`又把旧`main`提交和旧版本事实硬编码成期望值，因此检查通过只能证明“文档彼此一致地过时”，不能证明它们符合GitHub真实状态。

#### 前端模板负担明显

- 应用包仍名为`vben-admin`，版本为`2.10.1`，homepage、bugs、repository和author仍指向上游模板。
- 当前前端实际产品版本为`0.9.1`，包版本和产品版本语义冲突。
- 工作区保留`@vben/*`内部包、test-server、完整组件库、Demo、Mock和上游GitHub配置。
- `src/views/demo`有38个文件、4,327行；正式路由模块没有Demo路由，所有环境的`VITE_USE_MOCK`均为false，但动态视图glob仍会发现这些文件。

这证明模板清理有真实收益，但不能机械删除整个Vben框架：当前代码仍依赖`@vben/hooks`、`@vben/*-config`、布局和公共组件。

#### 高频大文件确实增加局部修改成本

重点文件：

- `platform-web/src/views/hedgeBoard/index.vue`：3,772行；脚本约2,235行，样式约1,486行。
- `marketTools.ts`：3,522行静态工具目录。
- `CrossVenueExecutionReplica.vue`：1,581行。
- `DomesticOverseasExecutionReplica.vue`：1,518行。
- `MarketTerminalPage.vue`：1,547行。
- `platform-api/app/execution_risk.py`：1,137行。
- `platform-api/app/research_providers.py`：999行，其中单一Provider类约881行。
- `platform-api/app/production_monitoring.py`：985行。
- `platform-api/app/user_service.py`：856行。
- `platform-api/app/user_admin_service.py`：803行。

这些文件并非都应按行数拆分。`hedgeBoard/index.vue`、`research_providers.py`和`production_monitoring.py`存在明显多职责；Runtime适配器虽大，但外部字段映射保持显式对审计有价值，应更保守。

#### 后端模块化单体已成形，但物理结构过平

Platform API有108个顶层Python模块，主要都堆在`app/`根目录。Repository、Service、Policy、Schema和Route概念已经存在，但按业务域定位仍需依赖文件名前缀。

静态导入图发现一个与交易、风控、Live Session和Security相关的八模块循环簇。该循环不是立刻重写理由，但说明高风险域的依赖方向需要在后期谨慎解耦。

#### 部署入口存在真实冲突

当前本地权威入口启动：

```text
platform-web
platform-api
execution-runtime
```

但`deploy/install-native.sh`仍构建和部署：

```text
projects/risk-control/auth-service
projects/risk-control/data-service
```

并安装旧`variable-global-auth`和`variable-global-data` systemd服务。这不是单纯命名问题，而是两套后端架构并存。必须先确认旧Go/MySQL是否保存真实生产数据或仍被某台主机使用，才能归档或删除。

#### 当前0.9.2 PR缺少完整自动门禁

正式工作流的`pull_request.branches`大多只包含`main`。PR #137的Base是0.9.1统一交付分支，因此Platform CI、Secret Scan、Version Consistency、两个E2E和Provider Smoke不会按现有条件自动完整触发。

这是Phase A必须立即修复的工程安全问题，优先级高于代码重构。

### 4.2 用户判断中不需要扩大处理的问题

#### 三服务不是过度工程化

Web、Platform API和Execution Runtime的边界与安全职责清晰。Runtime没有发现内部循环依赖，且Venue SDK没有进入Platform API。合并服务会增加交易副作用、密钥、用户权限和正式会计之间的耦合，收益低、风险高。

#### SQLite当前仍适合

现有SQLite包含事务管理、Foreign Key、迁移账本、不可变checksum、备份恢复和大量测试。当前没有并发量、水平扩展或数据规模证据要求迁移PostgreSQL。0.9.2不更换数据库。

#### 不是所有大文件都应拆

显式Venue字段映射、有限状态机和可审计SQL可能合理地保持集中。拆分标准必须是职责、变化频率、依赖和测试边界，不是行数。

#### 不是所有模板名称都应替换

- 第三方许可证、上游版权、历史记录和测试fixture保留原文。
- `@vben/*`若仍是内部框架包的真实导入名，可以暂时保留。
- `RTA`精确匹配主要位于旧`risk-control`代理地址和一处样式注释；不能使用不带词边界的全仓替换。
- “私募”在当前安全文档中有合法业务语义；只清理旧项目标题和不准确品牌，不删除合法金融概念。

---

## 5. 目标架构

### 5.1 部署边界

最终仍维持：

```text
platform-web/
platform-api/
execution-runtime/
```

- `platform-web`：Vue页面、路由、交互、显示状态、API Client、可见组件和设计体系。
- `platform-api`：身份、用户、投研、投资组合、交易编排、风险、正式会计、对账、运维和数据库的模块化单体。
- `execution-runtime`：Venue/Broker适配、外部副作用、Runtime Journal、订单/成交/持仓观测、凭据解析和Live安全。

`execution-runtime`名称准确，建议保持。

### 5.2 Platform API内部形态

采用渐进式业务域包，不一次性搬迁108个文件：

```text
app/
  application.py              # 仅应用组装和顶层兼容入口
  shared/                     # 真正跨域的配置、数据库连接、错误和基础合同
  identity/                   # 用户、Session、角色、权限、头像、找回
  research/                   # Provider、Cache、Schema、Watchlist、A股政策
  portfolio/                  # 会员持仓、资产、NAV读模型
  trading/                    # 策略、命令、批次、跨所价差编排
  risk/                       # Kill Switch、风险政策、Live审批
  accounting/                 # Financial Fact、正式Projection和NAV
  reconciliation/             # Venue与EOD对账
  operations/                 # 监控、备份、恢复、受控操作
```

这只是职责地图，不要求每个域拥有完全对称的`routes/service/repository/policy/schema`文件。只有真实职责存在时才创建。

迁移规则：

1. 每次只迁移一个业务域。
2. 先建立行为测试和导入边界，再移动文件。
3. 旧导入路径可以保留短期兼容Facade，但必须标注删除版本和引用数。
4. 禁止形成永久双实现。
5. 交易、风险、会计、对账最后迁移。

### 5.3 前端内部形态

不更换Vue框架，不做UI改版。逐步收敛为：

```text
src/
  app/                        # 启动、路由、全局Provider
  shared/                     # 通用组件、显示formatter、HTTP基础设施
  modules/
    identity/
    portfolio/
    research/
    strategy/
    risk/
    accounting/
    operations/
```

迁移时不要求立即移动成熟的模板基础组件。第一步先为现有路径建立模块地图和所有权；只有高频业务代码进入`modules/`，低频Vben基础设施可以保留原位。

页面职责：

- 页面Shell：路由参数、布局和区域编排。
- 业务组件：一个用户可见区域。
- Composable：请求、状态机、刷新和交互状态。
- API Client：合同和错误映射。
- Mapper/Formatter：Provider到页面模型、Decimal和显示转换。
- Store：仅保存真正跨页面状态。
- Fixture：只用于测试或明确降级。

禁止在Vue模板中直接解析Provider原始字段或复制交易规则。

---

## 6. 命名和模板治理决策

### 6.1 推荐目录名

| 当前 | 结论 | 理由 |
|---|---|---|
| `platform-web` | 0.9.2内改为`platform-web` | 与实际Vue全平台前端职责明显不符；误导Agent和脚本 |
| `platform-api` | 0.9.2内改为`platform-api` | 真实职责是平台业务API和模块化单体；比泛称backend更准确 |
| `execution-runtime` | 保持 | 名称与隔离Venue/Broker副作用的职责一致 |
| `projects/risk-control` | 暂不直接改名或删除 | 旧部署脚本仍引用；先确认生产依赖，再归档为`legacy/risk-control-go` |
| GitHub仓库`Platform_Experiment` | 0.10.1验收后再建议改 | 会影响外部链接、Actions和本地Remote；必须用户明确批准 |

目录改名必须是独立阶段，不与业务逻辑重构混在同一提交。

### 6.2 包和产品元数据

前端应用包建议：

```json
{
  "name": "vg-platform-web",
  "private": true,
  "version": "0.9.2"
}
```

后端包建议：

```text
vg-platform-api
vg-execution-runtime
```

产品版本由根级`VERSION`统一生成或校验；不再让前端包保留无关的模板版本`2.10.1`。

上游Vben来源不得删除。新增或收敛：

```text
THIRD_PARTY_NOTICES.md
```

记录上游项目、许可证、保留代码范围和修改声明。`platform-web/LICENSE`中的合法MIT归属继续保留。

`@vben/*`内部包名称暂不机械改名。先确认引用和发布边界；若只在单仓内部使用，可在后续低风险阶段逐步改为`@vg-platform/*`，但该工作不是0.9.2成功的必要条件。

### 6.3 品牌边界

“VG Investment Platform / VG投研交易资管平台 / VG Platform”可作为候选，但可见品牌属于用户确认事项。0.9.2可以清除明显模板网页标题和上游链接，但不得自行决定最终品牌或仓库名称。

---

## 7. AI上下文与Token优化

### 7.1 单一权威体系

建议最终只保留三个默认入口：

```text
AGENTS.md
Docs/AI/START_HERE.md
Docs/AI/CURRENT_STATE.md
```

实际路径统一采用小写目录：

```text
docs/ai/start-here.md
docs/ai/current-state.md
docs/ai/context-map.yaml
```

职责：

- `AGENTS.md`：长期稳定的安全、工程和禁止事项；不记录Commit、活动分支和PR进度。
- `start-here.md`：按任务类型告诉Agent先读什么、不必读什么、运行什么检查。
- `current-state.md`：当前产品版本、正式架构、已知生产约束；不复制实时CI状态和具体HEAD。
- `context-map.yaml`：业务域到代码、合同、测试和权威文档的机器可读索引。
- GitHub Issue/PR：唯一活动分支、HEAD、阶段进度和CI状态来源。

只保留`docs/codex/current-state.md`作为当前状态权威，任务读取由`docs/codex/context-map.md`路由。

### 7.2 防漂移机制

重写`check-codex-context.py`：

- 从`VERSION`、pyproject和前端环境读取版本，不硬编码版本号。
- 不硬编码`main`提交。
- 验证当前状态文件不包含Commit SHA和活动分支等易变事实。
- 验证同一主题只有一个权威文档。
- 验证context map中的路径存在。
- 验证历史目录不会被默认入口推荐。

### 7.3 域级上下文包

提供轻量命令：

```powershell
python scripts/context-for.py research
python scripts/context-for.py identity
python scripts/context-for.py trading --change contract
```

脚本只输出推荐路径、所有权、检查命令和默认排除项，不拼接源码，不建立RAG、向量数据库或知识图谱。

每个业务域最多维护一个短`README.md`或`MODULE.md`，内容限制为：

- 业务边界；
- 代码入口；
- 合同；
- 测试；
- 不可破坏语义；
- 常用命令。

不记录实现日记和历史PR。

### 7.4 目标

| 任务 | 当前估算Token | 0.9.2目标 |
|---|---:|---:|
| 看板样式 | 35,405 | < 8,000 |
| A股研究字段 | 26,321 | < 14,000 |
| 用户权限 | 16,598 | < 10,000 |
| 会员持仓合同 | 17,644 | < 10,000 |
| 跨所价差展示 | 17,880 | < 12,000 |
| 新增Provider | 23,970 | < 12,000 |
| 修复E2E | 17,043 | < 12,000 |

目标通过减少必读文件、缩小热点文件和清除重复权威实现，不通过压缩重要安全规则或隐藏合同实现。

---

## 8. 前端优化方案

### 8.1 保持不变

- Vue 3、Vite、Pinia、Ant Design Vue和现有视觉体系。
- 页面路由、导航、主要操作路径、信息层级、表格列、字号、色彩和响应式行为。
- 现有用户可见功能和角色可见范围。
- 现有设计必须通过1440、1024、768、390四档截图对比。

### 8.2 第一批高收益热点

#### 对冲基金/Research看板

`hedgeBoard/index.vue`应拆为：

```text
index.vue                    # 页面Shell和分类编排
useHedgeBoardNavigation.ts   # 路由和分类状态
useWidgetRenderer.ts         # 渲染调度和生命周期
chartRange.ts                # 纯区间计算
components/*                 # 现有可见区域
styles/hedge-board.scss      # 页面专属样式，保持选择器和像素结果
```

不是按行数平均切割。图表纯函数、导航、渲染生命周期和页面样式具有独立职责和独立测试价值，适合拆分。

#### 跨所和海内外价差页面

两份Replica存在大量相似布局和样式。先冻结DOM和截图，再抽取：

- 共享页面壳；
- 顶部账户/状态条；
- 数字输入和Decimal格式；
- 执行日志区域；
- 状态Badge和错误显示。

交易含义、下单状态机和字段名称不进入纯UI共享组件。

#### 用户系统

用户页面重复“敏感操作→最近重新认证→重试”的流程。抽取`useSensitiveUserAction` composable，减少三处重复，但保持最近重认证、权限和错误合同不变。

### 8.3 静态数据和目录

`marketTools.ts`、`cryptoTools.ts`和nativeData属于大静态目录。按市场域拆为数据文件并延迟加载；不将静态目录继续堆入页面脚本，也不为每一条数据建立文件。

交易工具书签由Markdown同步生成时，应保留一个权威源和一个生成物，并在文件头明确：

```text
GENERATED — DO NOT EDIT
Source: ...
Command: ...
```

生成物默认不进入Agent上下文。

### 8.4 Demo、Mock和模板组件

处理顺序：

1. 生成路由清单、动态import清单和构建产物证据。
2. 证明Demo不在正式路由、测试和降级链路。
3. 删除或移至`tools/template-reference/`，不留在产品`src/views`。
4. Mock若仅用于上游示例，删除；真实E2E fixture保留在`e2e/fixtures`。
5. 公共组件按实际导入做可达性审计，不因名字像模板就删除。
6. 删除依赖前运行构建、目标E2E和bundle对比。

粗略搜索显示`driver.js`、`print-js`、`showdown`、`vuedraggable`等可能无直接引用，但这只是候选，必须结合动态加载、插件注册和构建分析后决定。

### 8.5 类型和Lint

当前`tsconfig.full.json`仍为`strict: false`，并排除Store和部分基础设施；“full”并不是真正全量严格类型检查。

采用Ratchet：

- 不立刻全仓开启strict。
- 新建或重构的业务域采用更严格的独立tsconfig。
- 每阶段减少exclude，不增加`@ts-ignore`。
- 保留changed-file零警告门禁。
- 最终至少让所有活动路由、API Client、Store和高风险交易组件进入类型检查。

---

## 9. Platform API优化方案

### 9.1 保持模块化单体

当前FastAPI模块化单体符合初创平台。`main.py`仅51行，应用组装清晰，不需要替换框架。

重点是降低平铺目录和高频大模块成本，而不是重写所有业务。

### 9.2 Research域作为低风险试点

`research_providers.py`的单一Provider类约881行，混合多个外部源、字段转换和业务输出。

目标：

```text
research/
  schemas.py
  service.py
  cache.py
  registry.py
  providers/
    akshare_market.py
    macro.py
    a_share.py
    metals.py
  normalization.py
```

要求：

- Provider只处理外部请求和原始映射。
- normalization处理Decimal、日期和缺失值。
- service负责聚合、状态和Last Known Good。
- `partial/stale/no_data/error`保持显式。
- 每个Provider独立超时、TLS和Smoke证据。
- 不为每个小函数建立接口或工厂。

### 9.3 Identity域

用户系统已有较完整的Repository、Policy、Service和测试，适合第二个试点。

拆分目标按真实用例：

- 注册与初始CEO；
- 登录、Session和登出；
- 自助资料与密码；
- 管理员用户生命周期；
- 最近重新认证和敏感操作；
- 头像和运营备注。

必须保持：

- Browser Session与API-Key隔离；
- CSRF/Origin；
- 最后CEO并发保护；
- 目标用户范围和会员数据隔离；
- Session撤销、auth_version和密码变更语义。

### 9.4 Portfolio域

会员持仓、资产和NAV已有独立Schema、Repository、Service和Route。优先做目录收敛和合同地图，不重写金额逻辑。

保持：

- Decimal字符串；
- 会计资产与展示资产区分；
- 目标用户权限；
- 来源合同；
- NAV口径。

### 9.5 高风险域后置

`execution_risk.py`、`production_monitoring.py`、正式会计和对账只在低风险域模式稳定后处理。

`execution_risk.py`可以按Schema/Policy/Repository/Service/Route职责拆分，但风险动作事务、审计、Kill Switch和批次状态变更必须继续在一个受控事务边界内。

`production_monitoring.py`可以拆为状态采集、告警评估、告警Repository和受控操作；不能改变报警指纹、状态迁移和双人审批。

### 9.6 类型覆盖

当前按文件计算：

- Platform API：Pyright显式覆盖59/108模块，约54.6%。
- Execution Runtime：3/28模块，约10.7%。

目标不是一次性达到100%，而是：

- 每个被重构域100%进入Pyright范围；
- Provider动态边界使用显式TypedDict/Pydantic/adapter，不整体ignore；
- 不新增per-file ignore；
- 每阶段减少现有ignore并记录原因。

---

## 10. Execution Runtime优化方案

### 10.1 保持边界和目录名

Runtime当前28个模块、约7,900行应用代码，未发现内部循环依赖。总体结构比Platform API更清晰，不进行大规模目录迁移。

### 10.2 允许优化的内容

- 扩大Pyright覆盖：先覆盖contracts、models、safety、stores和纯政策，再覆盖Venue adapters。
- 抽取Bybit和MT5重复的纯字段规范化、Decimal转换、时间转换和错误分类。
- 将外部SDK调用与纯映射分离，方便无SDK测试。
- 统一Runtime日志字段、external identity和Result Unknown证据。
- 对大Adapter只抽取有独立测试价值的纯函数，不把显式Venue字段映射拆成大量碎片文件。

### 10.3 绝对禁止变化

- Live Write默认关闭。
- Kill Switch和两人审批。
- Market确认Fill后再释放后续路径。
- FOK必须精确全成；partial、mismatch、unknown保持不同。
- PostOnly Chase的TTL、mutation、cooldown和边界。
- TP/SL复用同一Close Action。
- Bybit reduce-only和Position Index。
- MT5 Position Ticket绑定。
- Unknown外部结果不得盲目重试。
- TLS验证和凭据脱敏。

---

## 11. 数据库、迁移、会计和对账

### 11.1 保持SQLite

0.9.2不迁移数据库。当前已有：

- 共享连接和事务边界；
- Foreign Key；
- Seed checksum；
- Schema migration ledger；
- 单调版本和不可变checksum；
- fresh/existing/repeated/checksum drift测试；
- 备份、恢复和只读恢复边界。

### 11.2 DDL治理

现有DDL分散在多个明确Owner模块，这是历史形成但已被文档和结构检查约束。

0.9.2不把所有DDL强制集中到一个巨型文件。规则调整为：

- 新增或改变Schema只能新增不可变Migration。
- 现有模块内`CREATE TABLE IF NOT EXISTS`作为兼容初始化暂时保留。
- 每张表在数据库权威文档中只有一个Owner和Authority Class。
- 不可逆迁移必须暂停并由用户确认。

### 11.3 会计保护

保持：

- Financial Fact不可变事实；
- Operational Position/PnL与Formal Position/PnL/NAV分离；
- Decimal；
- Projection可重建；
- EOD和Venue reconciliation；
- 对账Difference和审阅证据；
- 资金费、手续费、Swap、FX和总PnL口径。

目录移动不得改变SQL、表名、字段含义、舍入、资本基数或Projection算法。

---

## 12. 投研、A股、策略和Provider

### 12.1 Research不是单页中心

Research域包含宏观、黄金、加密、全球、A股、申万、个股、Provider状态、Watchlist和对冲基金研究展示。对冲基金看板只是其中一个页面集合。

### 12.2 A股和申万

现有`a_share_research_policy.py`使用Decimal和显式聚合，前端已有A股独立composable和区域组件。优先保持业务逻辑，主要优化：

- Provider原始字段不进入Vue模板；
- 申万行业映射只有一个权威；
- 阈值、单位和更新时间进入合同；
- `partial/stale/no_data/error`在组件层统一；
- Watchlist与市场宽度、行业和个股快照分开加载。

### 12.3 Provider状态

每个Provider统一输出：

```text
status
as_of
fetched_at
source
is_stale
partial_reasons
last_known_good_at
error_code
```

业务值与数据质量状态分离，页面不能把请求失败误显示为零。

Provider Smoke保留为真实网络证据，但不能替代单元和合同测试；外部不稳定时允许标记Provider失败，不通过跳过TLS或吞掉错误使CI变绿。

---

## 13. CI和测试优化

### 13.1 立即修复0.9.2工作线门禁

在任何业务重构前，让以下工作流同时监听0.9.1统一交付Base：

- Platform CI；
- Secret Scan；
- Version Consistency；
- User System E2E；
- Hedge Board E2E；
- Research Provider Smoke。

0.10.1转向`main`后再删除临时Base配置。

### 13.2 保留的门禁

- Repository Safety；
- Secret Scan；
- 版本一致性；
- Browser Session、权限和用户流程；
- Runtime live safety；
- Migration checksum和数据库测试；
- Execution/Live安全；
- 关键浏览器E2E；
- 最终全量矩阵。

### 13.3 降低重复安装

当前多个E2E和Provider工作流重复checkout、Python安装、Backend安装、pnpm安装和Playwright安装。

采用一个轻量Composite Action：

```text
.github/actions/setup-platform-test/
```

参数仅包括：

- backend是否安装；
- frontend是否安装；
- browser是否安装。

不建立复杂Reusable Workflow网络。保持每个E2E文件可直接阅读。

### 13.4 Scope优化

扩展`ci-scope.py`：

- 文档改动只跑Repository Safety和文档一致性。
- 域内后端改动运行目标域测试+后端静态检查。
- Runtime合同改动强制Backend+Runtime+E2E。
- 权限、交易、会计、迁移和Live相关改动强制高风险矩阵。
- 前端路由/API合同改动触发相应E2E。
- 最终0.10.1候选无条件运行全量矩阵。

### 13.5 测试结构

不追求100%覆盖率。重点增加：

- 高风险不变量测试；
- Provider合同和状态测试；
- 目录移动后的导入和路由测试；
- 视觉截图回归；
- 前后端合同测试；
- 迁移和恢复测试；
- 依赖删除的构建证据。

---

## 14. 文档治理

### 14.1 权威层级

```text
README.md                  # 30秒入口，不承载详细架构
AGENTS.md                  # 长期规则
docs/ai/                   # Agent入口和当前状态
docs/architecture/         # 稳定架构和所有权
docs/contracts/            # 跨服务合同
docs/database/             # 数据权威与迁移
docs/operations/           # 运行、验收、恢复
docs/releases/             # 发布说明
docs/archive/              # 历史，不进入默认上下文
```

### 14.2 `platform-web/docs`处理

当前该目录121份文档、约47,874行，是重要业务历史，但不适合作为与根级docs并列的第二权威中心。

处理方式：

1. 先建立文档清单，标记Authority、Reference、Historical、Generated。
2. 活动权威逐步迁到根级`docs/`。
3. 页面需求文档若仍有效，提炼为短模块合同；原长文归档。
4. DRAFT全部移入`docs/archive/planning/`。
5. 脚本读取的文档必须明确标为Source，不随意移动。
6. 不复制整段规则；非权威文档只链接权威。

### 14.3 任务包

根级`tasks/`当前大量已完成Issue仍平铺。调整为：

```text
tasks/current/              # 最多一个或少数活动Critical任务
tasks/completed/            # 已完成，默认排除
tasks/templates/            # 一个模板
```

GitHub Issue/PR是活动进度权威，任务包只记录跨会话所需的最小本地上下文。

---

## 15. 运维、部署和监控

### 15.1 统一运行入口

保留Windows本地入口：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

为Linux/服务器建立对应的三服务部署入口，明确：

- Platform Web静态构建；
- Platform API；
- Execution Runtime；
- 同源反向代理；
- HTTPS、Secure Cookie、Origin和CSRF；
- 独立环境变量和凭据；
- Live Write默认关闭；
- 健康检查、日志、备份和回滚。

### 15.2 旧Go部署线

在确认前：

- 不删除`projects/risk-control`；
- 将`deploy/install-native.sh`标记为Legacy/Not Current；
- 禁止README把它作为默认部署；
- 盘点是否存在真实用户、MySQL数据、systemd主机或DNS依赖。

若无生产依赖：

```text
projects/risk-control → legacy/risk-control-go
```

若有生产数据：制定独立迁移Issue，不把数据迁移夹在0.9.2目录重构中。

### 15.3 监控

`production_monitoring.py`拆分后仍保持：

- Last Known Good；
- alert fingerprint；
- acknowledge/close状态机；
- controlled operation；
- 备份恢复证据；
- 真实Provider状态；
- Runtime状态与Platform业务状态分离。

---

## 16. 分阶段执行计划

## Phase A — 基线、门禁和主方案

目标：让0.9.2成为可安全工作的独立开发线。

范围：

- 冻结0.9.1基线；
- Issue #136和Draft PR #137；
- 只读审计；
- 后端和Runtime基线测试；
- 本主方案；
- 修复0.9.2 PR的CI触发；
- 创建视觉基线清单。

验证：

- Audit workflow成功；
- Platform API 418项测试；
- Runtime 76项测试；
- 正式CI、Secret Scan和Version在PR #137可见；
- 无产品代码变化。

回滚：删除审计工作流、脚本和任务包，分支回到`8114fce...`。

## Phase B — 权威文档和AI上下文

目标：在后续重构前先降低每一步的上下文成本。

范围：

- 单一current-state；
- 动态事实退出静态文档；
- context map；
- 域级阅读入口；
- tasks和DRAFT归档；
- 重写上下文检查器；
- 记录典型任务基线。

验证：

- 所有链接存在；
- 无重复当前状态；
- 检查器不硬编码Commit；
- 七类任务能输出确定阅读包；
- 文档改动不触发无关E2E。

回滚：文档和脚本独立提交，可整组回退，不影响运行代码。

## Phase C — 命名和目录

目标：让目录和真实职责一致。

顺序：

1. 第三方归属文件和产品元数据；
2. 前端顶层目录统一为 `platform-web`；
3. 全部脚本、CI、Playwright、PowerShell、文档和环境路径；
4. 全量构建和浏览器验收；
5. `platform-api → platform-api`；
6. 后端测试、迁移和启动验收；
7. Runtime保持原名。

每个目录只做一次`git mv`，一次提交只改一个目录，不同时重构业务。

回滚：对单一命名提交执行revert；数据库和业务数据无变化。

## Phase D — 前端减负试点

目标：证明可以在视觉不变前提下降低热点上下文。

范围：

- 看板Shell、渲染和纯图表逻辑拆分；
- 静态目录延迟加载；
- 用户敏感操作composable；
- 清理已证明不可达的Demo/Mock；
- 依赖可达性报告。

验证：

- 1440/1024/768/390截图；
- 路由和角色可见范围；
- TypeScript、Lint、Build；
- Hedge Board和User E2E；
- bundle大小和首屏变化；
- 典型UI任务Token下降。

## Phase E — Research、Identity、Portfolio模块化

目标：用低风险业务域建立Platform API目标模式。

顺序：Research → Identity → Portfolio。

验证：

- 每域目标测试；
- 前后端合同；
- Provider状态；
- 权限和最后CEO；
- Decimal和NAV；
- 旧导入Facade引用归零计划。

## Phase F — 交易、风险、会计、对账和Runtime

目标：只处理证据证明有收益的高风险热点。

范围：

- 解除高风险循环依赖；
- execution risk职责拆分；
- monitoring职责拆分；
- 扩大Runtime类型覆盖；
- 提取纯Adapter映射；
- 不改变执行和会计语义。

验证：高风险完整矩阵、失败注入、Result Unknown、Kill Switch、双人审批、Migration、Financial Fact、PnL/NAV、EOD和对账。

失败时停止，不在红色阶段上继续叠加改动。

## Phase G — 死代码、依赖、兼容层和Legacy

目标：在所有引用和运行证据清楚后删除。

范围：

- 无引用模板依赖；
- Demo/Mock；
- 旧Facade；
- 旧文档入口；
- 旧Go部署线或迁移计划；
- 临时审计工具整理。

每项删除都必须有引用证明、构建、测试和回滚提交。

## Phase H — 0.10.1全量验收

门槛：

- 全量CI；
- Windows本地启动；
- 四档响应式；
- 登录、注册、找回、用户管理、角色和会员数据隔离；
- 真实Provider状态；
- Runtime与交易安全；
- 数据库、迁移、备份、恢复；
- Financial Fact、PnL、NAV、会计和对账；
- 优化前后Token、目录、依赖、最大文件、CI和测试对比；
- 发布说明和回滚说明。

全部通过后才执行版本：

```text
0.9.2 → 0.10.1
```

PR仍保持Draft、Open、Unmerged，等待用户明确批准。

---

## 17. 阶段提交纪律

建议提交组：

```text
chore(audit): freeze 0.9.1 baseline and evidence
ci: enable full gates for 0.9.2 workstream
docs(ai): establish single context authority
chore(naming): rename frontend directory only
chore(naming): rename platform api directory only
refactor(web-research): split hedge board shell and renderer
refactor(api-research): modularize providers without contract changes
refactor(identity): reduce user-service responsibility
refactor(portfolio): consolidate holdings and nav domain
refactor(risk): isolate risk persistence and policy
refactor(runtime): expand typed pure adapter boundaries
chore(cleanup): remove proven dead template assets
release: prepare Platform 0.10.1 candidate
```

禁止一个提交同时包含目录重命名、格式化、业务逻辑和数据库迁移。

---

## 18. 验收指标

### 18.1 产品

- 三服务正常启动；
- 主要页面、角色和操作路径可用；
- 无非预期视觉变化；
- Provider失败按真实状态展示；
- 交易和资金安全边界不变。

### 18.2 架构

- 目录与职责一致；
- Platform API保持模块化单体；
- Runtime边界清晰；
- 无新增基础设施服务；
- 高风险循环依赖减少或有明确隔离理由。

### 18.3 AI和Token

- 默认入口不超过三个短文件；
- 活动状态只有一个权威；
- 普通任务无需全仓扫描；
- 七类任务阅读包达到本文件目标；
- 历史、锁文件、生成物、Demo和Legacy默认排除。

### 18.4 代码

- `hedgeBoard/index.vue`不再同时拥有页面编排、图表引擎和全部样式；
- Provider按真实外部源隔离；
- 用户敏感操作不重复实现；
- 类型覆盖按阶段提升；
- 无新增全文件类型或Lint豁免；
- 删除依赖均有无引用和构建证据。

### 18.5 CI

- 0.9.2 Draft PR获得完整门禁；
- 文档改动不跑无关浏览器矩阵；
- 高风险改动自动升级到完整矩阵；
- 重复安装减少；
- 最终候选无条件全量测试。

### 18.6 目录和文件目标

目标不是追求任意行数上限，但建议：

- 高频页面Shell尽量低于800行；
- 单个业务Composable/Service尽量低于500行；
- 大型Adapter可超过500行，但需证明职责单一并有测试；
- 当前状态文档低于120行；
- 域级入口低于150行；
- 不以制造大量50行碎片文件换取表面指标。

---

## 19. 停止条件

遇到以下情况立即暂停：

- 需要改变交易、会计、权限或用户可见业务含义；
- 需要不可逆迁移；
- 无法保持视觉；
- 关键E2E持续失败；
- 目录迁移出现无法解释的大量删除；
- 发现真实Secret；
- 需要关闭TLS、安全、类型或关键测试；
- 需要修改或合并`main`；
- 旧Go/MySQL被确认含真实生产数据；
- 需要用户确定最终品牌或仓库名称。

暂停报告必须包括问题、影响、已完成内容、当前HEAD、最小回滚和建议。

---

## 20. 需要用户最终确认但不阻塞当前技术优化的事项

1. 最终可见品牌是否采用“VG Investment Platform / VG投研交易资管平台”。
2. 0.10.1验收后是否把GitHub仓库从`Platform_Experiment`改名。
3. 旧`projects/risk-control`和对应服务器是否存在真实用户或MySQL数据。
4. 0.10.1是否最终批准合入`main`。

除此之外，目录、上下文、代码和CI的技术实施不应反复向用户询问纯技术选择。

---

## 21. 最终判断

这不是一个需要重建技术栈的平台，而是一个已经具备关键安全和业务骨架、但长期叠加了模板、历史、平铺模块和重复上下文的初创产品。

最优方案不是“重写”，而是：

```text
修复权威和CI
→ 建立轻量上下文入口
→ 隔离命名和目录迁移
→ 用Research/Identity/Portfolio验证渐进模块化
→ 保守处理交易、风险、会计和Runtime
→ 最后删除依赖和Legacy
→ 全量验收后形成0.10.1候选
```

该路径可以显著降低Agent阅读范围和日常维护成本，同时保留当前平台已经建立的Browser Session、权限、交易、风险、正式会计、迁移、对账和Runtime安全资产。
