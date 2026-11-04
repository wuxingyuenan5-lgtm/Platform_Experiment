# 回归风险与测试记录（2026-11-03—04）

对象：本地工作区，基准提交 `fcaeb9f1`。工作区在任务开始前已有研究模块、首页和测试修改，本次保留它们，以当前代码进行验证。本次只补测试、测试隔离夹具与记录，未修改生产代码、既有断言或日常服务的交易开关，未提交或发布。

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

新增合计 **13 个用例，首次定向与最终全量运行全部通过**。五个相关文件的整组定向结果：**49 通过、3 失败**；3 个失败均为原有 A 股用例，见下文。新增测试覆盖真实本地 API / SQLite / 调度与 Provider 调用路径；外部网络使用 mock，不能据此宣称外部来源或真实交易通过。

ETF 正向恢复断言补齐后，该文件完整复验 **15 通过**。此外修复通用测试夹具的一处隔离缺口：`tests/conftest.py` 默认关闭无关研究后台刷新，测试可显式开启；没有覆写采集函数、跳过用例或更改断言。相应运行约定更新到 `platform-api/tests/README.md`。

## 执行范围与记录

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

## 已复现的失败与生产代码判断

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

本次没有为测试结果修改生产代码。任何后续生产修复应逐项明确原因与影响，并在相应拥有层处理；此报告不把测试失败自动转成产品范围或实盘授权。
