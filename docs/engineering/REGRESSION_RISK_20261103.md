# 回归风险与测试记录（2026-11-03—04）

对象：本地工作区。首次补测以 `fcaeb9f1` 为基准；随后 Owner 授权按失败分析修复。按 Owner 要求等待同工作区版本更新完成后，以 `52aac242` 及保留的工作区变更继续复验。原有与其他聊天的变更均保留，本轮没有额外提交、发布、连接真实交易场所或调整日常服务交易开关。

下方风险排序、前五条补测及“首次执行”结果是原始基线；当前修复与最终验证见文末。首次阶段仅补测试，授权后的修复阶段包含下列明确说明的生产修改。

## 风险排序

排序先考虑错误后果，再结合最近 12 个提交（`707810bd` 至 `fcaeb9f1`）、更早的修复提交、当前未提交改动和已有测试的盲区。触达次数是这 12 个提交中包含对应文件的次数，不是缺陷次数；下面是工程判断，不是统计预测概率。历史缺陷通过本地 Git 修复和现存回归测试交叉核对。

| 排名 | 易回归路径与后果 | Git / 历史证据 | 现有覆盖与主要缺口 |
|---|---|---|---|
| 1 | 交易 API → 幂等键 → Runtime → `result_unknown` → 重启后重试。重复副作用可能造成真实超量成交 | `408094e4` 资源先占用、`b9d6e00c` 未决结果保留占用、`f4737921` 腿顺序计入幂等身份；当前 `auth.py` 亦有改动 | `test_idempotency_conflicts.py` 覆盖已成交请求冲突，`test_order_recovery.py` 覆盖未知结果的相同请求重放；欠缺「未知结果 + 重启 + 改变经济参数」的 API 与数据库联合断言 |
| 2 | 浏览器会话 / CSRF → 私人工作台 → SQLite 版本比较。串号、跨会话写入或丢失并发更新 | 当前新增 `personal_workspace.py`、迁移 47，并改动 `application.py` / `auth.py`；历史 `1e2d6c8a`、现有 `test_auth_concurrency.py` 和用户权限测试说明身份生命周期易回归 | 已有工作台测试多数覆写 Principal 或直接调用存储；欠缺真实登录、两份有效会话的 CSRF 隔离，以及真实同时保存 |
| 3 | A 股后台采集 → 单飞锁 → 原子发布 → 中断恢复。半份快照、永久 busy 或错误宣称 ready | `research_a_share_refresh.py` 最近 12 提交触达 8 次，`fa74f373` 及当前工作区均有变更；已有失败源保留旧数据、发布失败回滚测试 | `test_a_share_delivery.py` 已覆盖源异常、数据库失败、重叠采集；欠缺真正任务取消后旧快照不变、失败状态可见且可重新采集 |
| 4 | macro / commodity / crypto 本地文件 → 版本缓存 → stale 副本 → 数据恢复。损坏缓存被当作有效数据或过期值继续 ready | `research_provider_macro_dashboard.py` 触达 6 次，当前新增分组投影；历史 `67afd72d` 缺失宏观来源、`88e94bd5` 有界 fallback | 现有 `test_research_dashboard_cache.py` 覆盖并发、文件消失和改版；欠缺损坏新版本后同版本修复、失败不污染最后成功快照、文件不变但时间推进 |
| 5 | ETF 多标的分钟线 + 即时报价 → 校验 → 快照 / 历史 / 读取投影。拼接不同交易日或开盘前重置报价扭曲研究结论 | `fcaeb9f1` 新增 ETF observation；当前 renderer / panel 继续修改；历史 `f6c08e14`、`d387fca0` 修复伪造 / 错接市场明细，现有 ETF 测试专门保留缺值与精度 | 已有解析器、503 保留旧值、只读 GET 测试；欠缺响应全是 HTTP 200 但篮子日期冲突、报价重置或缺标的的集成验证 |
| 6 | 研究数据库迁移 → manifest rowid / 游标 → Parquet → 分批投影续跑。漏数、重复或污染业务表 | `fa74f373` 拆研究库及存储生命周期，`fcaeb9f1` 和当前迁移继续扩展；历史 `7507c1a9` 修复迁移与嵌套连接 | `test_research_storage_lifecycle.py`、`test_strategy_research_projection.py` 已覆盖稀疏 rowid、精度与游标；跨多分片中断恢复、升级后再续跑仍应重点防守 |
| 7 | 登录切换 / 请求竞态 → 保存的市场布局 → Vue 组件 / 图表挂载与缩放。旧账号响应覆盖新账号、用户布局混入行情、图表重置 | `dashboardClean.ts` 触达 11 次，`LocalChartWidget.ts` 10 次，`MacroSeriesChart.ts` 8 次；`89416d12` 滚动重置、`aa753281` 保存布局覆盖最新数据；当前多图表改动 | 已有 layout persistence、navigation lifecycle、chart lifecycle、source series 测试；运行发现布局测试 loader 无法加载新增 composable，必须先恢复可执行覆盖，不能当成 4 个业务断言已验证 |
| 8 | 成交 / 费用 / 资金流水 → 财务投影 → 策略账户与损益。重复记账、错误归属、缺账当零 | `1c756963` live accounting 投影修复、`c96b196d` 权威平仓账务；`6760dd11` / `707810bd` 包含财务路径改动 | `test_live_venue_accounting.py`、`test_financial_projection_service.py`、前端 financial states 已覆盖；重放、跨账户身份和 incomplete 的跨层一致性仍是高损失路径 |
| 9 | Runtime 账户路由 → MT5 worker / Bybit → 缓存与实时权限 → 执行准入。读错账户或复用已撤销权限 | `6801799c` MT5 worker 隔离、`b82d1184` 只读切换 fail-closed、`706416c0` 账户显式路由；最近 `cbc5f22b` 仍改动网关 | 已有 `test_mt5_account_workers.py`、`test_execution_read_concurrency.py`、`test_live_safety_failure_injection.py`；全量发现 warmup 测试仍假定权限规格可缓存，与当前准入代码冲突 |
| 10 | 原始日期 / 缺值 / 单位 → 交易日收益、估值和滚动相关性 → 展示。错用自然日、缺值变零、短窗口伪造完整结果 | `fcaeb9f1` 扩展估值 / 风险 / 监测，当前新增 `research_rolling_correlation.py`；`a8c051a7` 修复概率数值口径 | `test_personal_workspace.py` 已验证共同交易日与断窗，另有 cumulative volatility / valuation 测试；当前 A 股日历输入变化已让旧收益夹具失效，图表和指标跨层口径仍易漂移 |

## 前五条补充的最小回归测试

| 路径 | 新增用例 | 有效性断言 |
|---|---|---|
| 1 | `test_idempotency_conflicts.py::test_unknown_command_rejects_changed_retry_after_restart_without_new_effects`，3 个参数化用例 | 初次下发丢失响应后重新进入应用 lifespan（非独立进程重启），改数量 / 方向 / 价格都返回 409；原请求重放返回原订单和命令，仍为未知结果；Runtime 下发恰好一次，数据库恰好一命令、一订单、零成交 |
| 2 | `test_workspace_auth_regression.py`，2 个用例 | 真实登录 + 路由 + CSRF + SQLite；缺 CSRF / 他人 CSRF 为 403 且不写入；同 ID 事件按用户隔离，旧版本为 409 且数据不变；两个线程直接调用存储函数，同版本保存恰好一个成功，持久值等于胜者（并发部分不经过 HTTP） |
| 3 | `test_a_share_delivery.py::test_cancelled_refresh_preserves_publication_and_releases_single_flight`，1 个用例 | Event 确认采集已进入后再取消，不靠 sleep；并发请求为 busy，中断状态为 error / refresh_interrupted；整份已发布快照逐行不变，下一次刷新能够 ready |
| 4 | `test_research_dashboard_cache.py`，4 个用例 | 三类 Provider 的无效 Decimal 使新版本失败；旧数据精度保留并标 stale，原成功对象不被改写；同一失败版本修复后重新读盘并恢复 ready；固定时钟跨过日频期限后缓存命中仍变 stale 且不伪造获取时间 |
| 5 | `test_research_etf_observation.py::test_incoherent_etf_basket_keeps_last_good_native_session`，3 个参数化用例 | MockTransport 的 HTTP 200 内容故障覆盖分钟日期冲突、报价重置、缺标的；只标 stale，保留原始日期 / 获取时间 / 数据；独立 reference 成功，未生成假的当日成功历史，读取投影同样 stale；故障消除后完整篮子必须成功发布，防止“所有响应一律拒绝”通过测试 |

新增合计 **13 个用例，首次定向与该阶段全量运行全部通过**。五个相关文件的整组定向结果：**49 通过、3 失败**；3 个失败均为原有 A 股用例，见下文。新增测试覆盖真实本地 API / SQLite / 调度与 Provider 调用路径；外部网络使用 mock，不能据此宣称外部来源或真实交易通过。

ETF 正向恢复断言补齐后，该文件完整复验 **15 通过**。此外修复通用测试夹具的一处隔离缺口：`tests/conftest.py` 默认关闭无关研究后台刷新，测试可显式开启；没有覆写采集函数、跳过用例或更改断言。相应运行约定更新到 `platform-api/tests/README.md`。

## 首次执行范围与记录

原始日志、JUnit 和启动前工作区差异位于 `outputs/regression-20261103/`（本地忽略目录）。日志保留失败，不用只截取成功重跑结果替代首次全量结果。

- API 初次：在 `platform-api` 使用 `.venv/Scripts/python.exe -m pytest -q -o faulthandler_timeout=90 --junitxml=../outputs/regression-20261103/api.xml`，不按 marker 或关键字排除测试。运行在 `test_cross_spread_execution_quantity.py` 的 TestClient 关闭阶段挂起，保留 90 秒线程转储 `api.log` 后终止该测试进程，不能给它记为完整通过。
- API 隔离：先按文件定位同类挂起；控制实验关闭无关后台研究刷新后，原先阻塞的 execution quantity 和 auth RBAC 两文件 **13 通过**。补上通用夹具隔离后，使用 `run-api-modules.py api-modules-final` 重新执行全部 242 个测试文件，三个独立进程并行、每文件最多 240 秒，未按通过率筛选文件。逐文件命令、退出码、超时与 JUnit 留在 `api-modules-final/`。按文件运行不证明跨文件共享状态或生产关闭逻辑已修复。
- Runtime：项目自己的 `.venv/Scripts/python.exe -m pytest -c execution-runtime/pyproject.toml execution-runtime/tests -q`。
- 运维脚本：API Python 执行 `-m pytest scripts/tests -q`。
- 前端：`node --test --test-reporter=tap`，传入全部 54 个 `scripts/test-*.cjs`，单独排出需要浏览器服务的 `test-strategy-query-browser.cjs`；完整文件列表在 `frontend-manifest.txt`。列表包含部分聚合入口，所以 TAP 数量不能解释为去重后的独立需求数。
- 浏览器：既有 platform-visual、hedge-board、strategy 配置；用户系统测试临时副本只把硬编码 4373 地址改成隔离主机，使用既有 platform-visual 的临时数据库、假 Runtime 和禁用 Runtime Live Write 启动器。转换脚本与 SHA-256 清单在 `prepare-user-e2e.py` / `user-e2e-manifest.json`，没有改变任何断言。部分初次运行在 webServer 等待阶段超时；保留首轮日志，后续串行重试并把临时 hedge / user 配置的前端就绪地址改为 `/index.html`，最终进入全部四组浏览器用例。
- 补充：完整 `vue-tsc -p tsconfig.full.json --noEmit` 和已声明的前端边界 / 布局检查。类型检查、静态断言与浏览器结果分别记录。
- 独立浏览器辅助脚本：`test-strategy-query-browser.cjs` 在隔离策略服务上运行，因找不到 `funding-order-panel` 失败。图表高度脚本硬编码日常 4373 地址，停在缺少 `E2E_CEO_USERNAME` 的登录前置条件，未形成页面验收；新闻 / 财富辅助检查同样依赖日常端口，未将其算作已完成业务验证。没有索取或写入真实账号凭据。

| 测试范围 | 通过 | 失败 | 错误 / 跳过 | 记录 |
|---|---:|---:|---|---|
| API：全部 242 文件隔离执行 | 1591 | 50 | 0 / 0，0 文件级超时 | `api-modules-final/summary.json`、逐文件 JUnit |
| Execution Runtime | 344 | 1 | 0 / 0 | `runtime.xml`、`runtime.log` |
| 运维 Python 脚本 | 23 | 2 | 0 / 0 | `scripts.xml`、`scripts.log` |
| 前端 Node：54 个测试入口 | 229 | 13 | 0 取消 / 0 跳过 | `frontend.log`；失败包含 3 个入口进程异常 |
| 浏览器 platform-visual | 17 | 13 | 0 跳过 | `e2e-platform-visual.log` |
| 浏览器 hedge-board | 0 | 2 | 0 跳过 | `e2e-hedge-board-index.log` |
| 浏览器 user-system | 1 | 2 | 0 跳过 | `e2e-user-system-final.log` |
| 浏览器 strategy | 2 | 4 | 0 跳过 | `e2e-strategy-final.log` |

四组浏览器套件共 41 个用例，20 通过、21 失败；前端完整类型检查另有 3 个错误。边界、跨场所布局、资金费率布局检查通过；Hedge Board 与首页静态布局检查失败。独立 strategy-query 浏览器脚本失败，不混入上述 41 个用例。

浏览器截图和 trace 保留在 `platform-web/test-results/` 的各套件运行目录。Python 失败明细和新增 13 个用例的最终结果汇总到 `outputs/regression-20261103/final-evidence.json`；前端与浏览器逐项失败保留在表中对应日志，原始首次挂起、环境超时和串行重试日志同时保留。API 的 50 个失败分布于 27 个文件，242 个文件均已执行结束。全量结果没有达到全绿，不能作为生产或实盘验收结论。

## 首次失败诊断（历史基线）

- API 全量还暴露架构约束 / 直接 SQL allowlist、数据库 bootstrap / seed 基线、CEO 权限预期、跨场所资金划转与会话恢复失败。部分测试因 `strategy_account_bindings` 表缺失中断；会话恢复用例未在 3 秒内观测到后台监控恢复。这里只记录实际失败，尚不能将它们统一归因于测试过时或认定生产逻辑正确。性能工具子进程也有自身 30 秒超时，与逐文件 240 秒超时分开记录。
- 文档一致性失败指向任务开始前已有的 `docs/reviews/readonly-technical-audit-2026-11-04.md` 中绝对用户目录路径。该规则将路径中的用户目录片段识别为禁止的 macOS 用户目录。本次未改写该独立审计文件，也未放松检查规则。
- Runtime `test_execution_reads_are_reused_within_the_short_admission_window` 首次全量和单独重跑均失败。`BybitMt5Gateway.get_instrument_specification` 明确重新读取账户 / 终端交易权限，没有走规格快照缓存；旧测试仍要求规格只读取一次。**不应为了变绿恢复权限缓存**，这会影响撤销权限后的交易准入。本次保留断言与失败证据。
- A 股两个历史收益用例：`_stock_session_days` 没有交易日历时返回空集合，`_history_return` 因窗口不足返回 `None`；旧 `research_db` 夹具没有提供对应交易日历。第三处旧测试要求提示包含“机器人”，当前提示是缺失指数代码列表。未把缺值改零，也未删除旧断言。
- `test_hedge_backend_completion.py` 的三个旧缓存失败用例只将 `read_local_json` 替换为抛错，未改变文件 revision；缓存命中未再次读盘，实际返回 ready。新增缓存用例显式推进 revision 后注入损坏内容，验证的是确实重新加载失败后的 stale 与恢复；两组测试输入条件不同。旧失败保留，没有修改断言。
- 前端市场布局 4 项在执行断言前失败：旧测试 loader 无法解析组件新增的 `../composables/researchWorkspace`。这是测试夹具阻塞，不能推断账户布局竞态已通过。
- 前端三个 formal manifest / registry 入口退出码 `3221226505`（`0xC0000409`），串行重跑仍发生。记录为本机 Node 进程异常，不能称业务断言通过；JS 日志不足以判定原生崩溃原因。
- 运维脚本两项仍要求旧手册中的固定英文文本；当前权威手册已经改成正常交易语义。保留失败，未通过复制旧文字改变当前授权规则。
- 全量类型检查仍报告 `SelectAndInput.vue` 的 `defineProps` 冲突和 `Preview/src/Functional.vue` 的两个 Event / MouseEvent 类型错误。本次没有修改这些组件。
- 浏览器失败包括旧宏观 / A 股标题定位不到、会员页的 Ant Design Modal `visible` 弃用警告被错误收集器捕获、账户状态和研究图表断言不满足。用户系统的两处失败分别要求旧“示例策略”提示及 CEO 权限中不出现 live 字样；不是新增工作台隔离用例的失败。策略 UI 四项失败保留截图与 trace，不替换定位器来绕过。

测试启动器曾重新生成 `marketTools.ts` 的格式；该文件在任务开始时是干净的，已恢复原始内容，不将这项测试副作用夹带进交付。

首次补测阶段没有修改生产代码；以下是 Owner 授权后的修复结果。


## 授权修复结果（2026-11-04）

### 生产行为与影响

- A 股历史状态区分“没有要求重新下载”和“已请求但未取得历史”。有效存量历史与报价日期对齐时仍可 ready；本轮请求失败则 partial，保留原日期、数值与可计算收益；过期报价仍 stale。真实刷新传入本轮请求集合，已有失败断言与存量恢复断言同时通过。
- 黄金本地文件缓存从只比较修改时间改为复用 `local_json_revision`（时间、大小、文件身份）。固定相同修改时间的文件替换也能刷新内容，原来的过期与 unavailable 语义保留。
- 策略管理后台预生成覆盖未绑定账户的实例，首次读取能得到正式“未绑定”投影，避免遗漏任务造成 503。绑定账户的摘要仍独立生成。
- Vue 组件移除冲突的宏导入，选择框 JSX 改为等价 `h()` 调用；图片预览的 JSX 脚本提取至同目录 `Functional.tsx` 并纳入完整类型检查，鼠标拖动使用声明的 MouseEvent 参数。会员页 Modal 改用现行 `open` 属性，消除浏览器组件警告。A 股入口样式提取至同目录 Less 文件，维持 400 行检查与原布局。
- 旧理财入口重定向补回 `view=wealth`，避免进入加密默认页；派生路由清单同步生成并校验。
- 应用路由注册合并为有序循环，保留路由顺序及鉴权中间件。只登记已经审查的有限 SQL owner；没有关闭架构边界检查。

### 测试、工具与夹具修复

- CEO 权限及 Cross/Funding 入口按现行授权合同设置前置条件；会话恢复、未授权拒绝、CSRF、单次提交、重复恢复与平仓断言保留。旧迁移/种子/Schema 基线根据实际迁移、索引、账户别名及模型重新核对。
- 原生规格、交易日历、财务读取投影和交易命令 symbol 均补齐真实调用路径需要的输入。缓存失败测试推进 revision 后再注入读盘失败。性能脚本关闭无关后台任务并拦截现行 Runtime transport，保留原时间预算。
- 布局测试加载实际 composable 及依赖，继续验证账号切换、并发版本冲突、保存失败回滚。路由清单测试的本机 `fs.cpSync` 崩溃用显式逐文件复制夹具解决；拒绝符号链接，不批量删除临时目录，漂移与缺失视图断言保留。
- 浏览器从当前页签、按钮和延迟渲染入口操作；宏观事件夹具改为接口要求的数组，并加入类型检查。测试研究源均为隔离输入，未调用外部行情/AI 服务。
- Cross 浏览器隔离主机持续更新 Fake 报价时间，并把单个模拟 MT5 净持仓映射至开仓票据标识；实际 Fake Runtime 数量及价格不替换，超过一个持仓时明确报错。此夹具不验证真实 MT5 票据协议，生产持仓不一致拒绝规则保持不变。
- 正常构建脚本产生的交易工具数据格式变化，经编译导出值逐项相等验证后恢复；没有夹带生成器格式副作用。

### 复验结果与边界

原始及修复日志均保留在 `outputs/regression-fixes-20261104/`。API 全量逐文件运行 245 个文件，每文件 240 秒上限、两个独立进程并发，首轮 **1,666 通过、5 失败、0 错误、0 跳过、0 文件级超时**。5 个失败分别是两个架构入口检查、退出恢复缺 symbol、ETF 缺日历库初始化、A 股存量历史状态。修复后，对应文件及直接相关文件共 **74 个用例通过**（10 架构、30 退出恢复/损益、34 研究）。按每文件最新证据合并为 **1,671/1,671 通过**；这是完整运行加定向复验，未冒称再次完成单进程全量。清单见 `final-evidence.json`。

Runtime 全套 **347 通过**；运维脚本 **25 通过**；前端 Node 全量 **256 通过**。Node 数量仍包含聚合入口，不等于去重后的需求数。完整前端类型检查、浏览器夹具类型检查、正常生产构建、修改组件 ESLint、相关 Python Ruff、文档一致性、Hedge Board 静态布局检查均通过。

浏览器验证使用正常构建产物连接隔离 API/SQLite 与 Fake Runtime。策略 **6/6**（`browser-strategy-final.log`）、用户系统 **3/3**（`browser-user-built.log`）通过。产品视觉首轮 **24/30**，6 个失败经四尺寸员工页面 4 项、费率历史图表 1 项、产品权限边界 1 项复验全部通过（`browser-visual-recheck.log`、`browser-visual-proof.log`、`browser-product-accepted2.log`）。股票池数据与交互、四尺寸布局分别通过（`browser-hedge-accepted2.log`、`browser-responsive-final.log`）。按各用例最新证据共 **41/41 通过**，不是一次全绿运行；之前的失败、启动超时和 trace 均保留。

股票池验证包含真实隔离 API/SQLite 的核心池增删、私人关注隔离、重新登录/刷新、港股详情、范围和图例操作、失败反馈，以及 1440/1024/768/390 像素下无页面溢出。延迟图形先滚动触发再检查，未用强制点击绕过导航遮挡；390px 矩阵截图另经目视核对。A/HK 共用状态边界变更后，市场隔离 6 项额外复验通过。

这些结果证明当前本地修改与隔离调用路径，不代表日常服务已经加载本轮代码、外部来源已恢复或真实交易已验收。本轮没有重启业务服务或发布构建；长时运行、真实场所与外部源的原有限制继续保留。
