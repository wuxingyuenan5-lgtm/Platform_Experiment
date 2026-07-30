# Platform 0.9.1 本地验收交接

> 适用系统：macOS / zsh，本地只读验收  
> 仓库：`wuxingyuenan5-lgtm/Platform_Experiment`  
> Issue：`#134`  
> Draft PR：`#135`  
> 统一交付分支：`feature/issue-134-platform-0-9-1-unified-delivery`  
> 已完成自动化验证的功能基线：`00574a8f10a3fc3723ae78c97aacbff075ff803b`  
> 状态：`ready for local acceptance`  
> 约束：本地只验收，不修改代码、不提交、不推送、不合并 `main`

## 1. 给本地 AI 的执行指令

将下面这段作为本地 AI 的任务指令：

```text
你是 Platform 0.9.1 本地验收执行代理。

仓库：wuxingyuenan5-lgtm/Platform_Experiment
验收分支：feature/issue-134-platform-0-9-1-unified-delivery
功能验证基线：00574a8f10a3fc3723ae78c97aacbff075ff803b
Issue：#134
Draft PR：#135

本次只做本地验收，不做开发。

强制规则：
1. 必须使用独立 detached worktree，不得直接在现有开发目录验收。
2. 不得修改任何受 Git 跟踪的文件，不得执行 git add、git commit、git push、git merge、git rebase、git reset --hard 或 git clean -fd。
3. 不得切换、修改或合并 main；不得把 Draft PR 标记为 Ready 或合并。
4. VG_LIVE_TRADING_ENABLED 必须保持 false；不得启动或测试真实下单、Live Write、Bybit、MT5 或 Execution Runtime 实盘能力。
5. 外部免费 Provider 的 partial、stale、no_data 或 error 必须按实际记录，不能描述为全部健康。
6. E2E 研究数据夹具只证明交互和布局，不得作为真实行情验收证据。
7. 所有日志、截图和验收结论写到仓库外的独立 evidence 目录，不得写入 Git。
8. 发现问题时只记录复现步骤、证据和严重级别，不得顺手改代码。
9. 结束前必须确认 git diff 和 git diff --cached 都为空。

按本文档顺序执行：环境核对 → 自动化检查 → 浏览器 E2E → 本地真实 Provider 页面验收 → 响应式截图 → 输出验收结论。
```

## 2. 本次验收目标

本地验收只回答以下问题：

1. 当前统一分支能否在一台干净的 Mac 上安装、构建和运行；
2. Platform Backend、浏览器用户系统和对冲基金看板的自动化检查能否通过；
3. A 股页面是否通过 Platform API 获取数据，而不是前端直连第三方；
4. 页面是否正确展示数据来源、上游时间、Platform 抓取时间及 `ready / partial / stale / no_data / error` 状态；
5. 申万、成交额阈值、一键个股、自选股和响应式页面是否满足业务使用要求；
6. 外部 Provider 部分失败时，页面是否模块化降级，而不是整页崩溃、显示伪造的 0 或覆盖 Last Known Good；
7. 是否具备进入 Platform 0.9.1 Release Candidate 冻结阶段的条件。

本次不验收：

- 真实下单、成交、持仓、会计账本或风险权威数据；
- Bybit、MT5 或其他 Venue 实盘连接；
- Execution Runtime Live Write；
- 第三方免费数据源的永久可用性；
- 生产 HTTPS、Secure Cookie、备份恢复和正式部署。

## 3. 已知基线与预期风险

当前 GitHub 自动化已记录两份真实 Provider 样本：

| 时段 | 结果 | 600519 腾讯 | 600519 东方财富 | 双源差值 |
|---|---|---:|---:|---:|
| 交易时段 | `partial`，5/8 通过 | 1358.23 | 1358.20 | 0.03 |
| 非交易时段 | `partial`，5/8 通过 | 1361.76 | 1361.76 | 0.00 |

两个时段均出现以下外部依赖问题：

- 全市场 A 股现货接口被远端中断连接；
- 指数历史数据不可用；
- 申万官方批量分类文件 TLS 证书链无法验证。

这些问题本身不等于本地验收失败。真正的阻断条件是：

- 页面把失败模块显示为 `ready`；
- 页面用 0、空数组或错误数据覆盖上一份有效数据；
- 某一 Provider 失败导致整页白屏；
- 页面不显示真实来源和时间；
- 为了通过验收关闭 TLS 校验或绕过 Platform Backend。

## 4. 环境要求

推荐工具版本：

```text
macOS
Git 2.x
Python 3.12
Node.js 20
pnpm 9.15.9
Chromium（由 Playwright 安装）
```

默认端口：

```text
Platform Backend  8000
Frontend          4373
Execution Runtime 8100（本次不启动）
```

开始前确认 8000 和 4373 未被其他进程占用：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN || true
lsof -nP -iTCP:4373 -sTCP:LISTEN || true
```

如端口已被占用，先确认并正常停止对应进程，不得让 Vite 静默改用其他端口继续验收。

## 5. 创建独立只读 Worktree

先将 `SOURCE_REPO` 改为现有仓库目录：

```bash
export SOURCE_REPO="$HOME/Projects/Platform_Experiment"
export ACCEPT_ROOT="$HOME/Projects/Platform_Experiment-0.9.1-acceptance"
export EVIDENCE_DIR="$HOME/Platform_Experiment-0.9.1-evidence/$(date +%Y%m%d-%H%M%S)"

mkdir -p "$EVIDENCE_DIR"
cd "$SOURCE_REPO"

git fetch origin --prune

test ! -e "$ACCEPT_ROOT" || {
  echo "验收目录已存在：$ACCEPT_ROOT，请人工处理后重新开始。"
  exit 1
}

git worktree add --detach \
  "$ACCEPT_ROOT" \
  origin/feature/issue-134-platform-0-9-1-unified-delivery

cd "$ACCEPT_ROOT"

git rev-parse HEAD | tee "$EVIDENCE_DIR/git-head.txt"
git log -1 --oneline | tee "$EVIDENCE_DIR/git-head-summary.txt"
git status --porcelain=v1 | tee "$EVIDENCE_DIR/git-status-before.txt"

git merge-base --is-ancestor \
  00574a8f10a3fc3723ae78c97aacbff075ff803b \
  HEAD
```

验收前必须满足：

- `git merge-base --is-ancestor` 返回 0；
- `git status --porcelain=v1` 没有输出；
- 当前处于 detached HEAD；
- 当前提交属于统一交付分支，而不是 `main`。

`00574a8f...`是已完成全套功能与自动化验证的最低功能基线；本地验收应使用统一分支最新HEAD，并通过祖先检查确认没有退回到旧版本。

记录环境：

```bash
{
  sw_vers
  git --version
  python3.12 --version
  node --version
  corepack --version
} | tee "$EVIDENCE_DIR/environment.txt"
```

## 6. 安装依赖

### 6.1 Python 环境

```bash
cd "$ACCEPT_ROOT/platform-backend"
python3.12 -m venv .venv-acceptance
source .venv-acceptance/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pip check
```

`.venv-acceptance` 只属于本地 worktree，不得提交。

### 6.2 Node 与前端依赖

```bash
cd "$ACCEPT_ROOT/admin-risk"
corepack enable
corepack prepare pnpm@9.15.9 --activate
pnpm --version
HUSKY=0 pnpm install --frozen-lockfile
pnpm exec playwright install chromium
```

必须保持 `pnpm-lock.yaml` 不变。

## 7. 自动化验收

所有命令均需保留退出码。任一命令失败时，停止进入“发布通过”结论，先记录失败日志。

### 7.1 仓库治理检查

```bash
cd "$ACCEPT_ROOT"

set -o pipefail
python3.12 scripts/check-documentation-consistency.py \
  2>&1 | tee "$EVIDENCE_DIR/check-documentation-consistency.log"
python3.12 scripts/check-repository-structure.py \
  2>&1 | tee "$EVIDENCE_DIR/check-repository-structure.log"
python3.12 scripts/check-version-consistency.py \
  2>&1 | tee "$EVIDENCE_DIR/check-version-consistency.log"
python3.12 scripts/check-codex-context.py \
  2>&1 | tee "$EVIDENCE_DIR/check-codex-context.log"
python3.12 scripts/scan-secrets.py \
  2>&1 | tee "$EVIDENCE_DIR/scan-secrets.log"
```

### 7.2 Platform Backend

```bash
cd "$ACCEPT_ROOT/platform-backend"
source .venv-acceptance/bin/activate
set -o pipefail

python -m pip check \
  2>&1 | tee "$EVIDENCE_DIR/backend-pip-check.log"
python -m ruff check app tests scripts \
  2>&1 | tee "$EVIDENCE_DIR/backend-ruff.log"
python -m pyright \
  2>&1 | tee "$EVIDENCE_DIR/backend-pyright.log"
python -m pytest \
  2>&1 | tee "$EVIDENCE_DIR/backend-pytest.log"
```

### 7.3 前端结构、类型和构建

```bash
cd "$ACCEPT_ROOT/admin-risk"
set -o pipefail

pnpm test:user-system \
  2>&1 | tee "$EVIDENCE_DIR/frontend-user-system-policy.log"
pnpm test:homepage-layout \
  2>&1 | tee "$EVIDENCE_DIR/frontend-homepage-layout.log"
pnpm test:hedge-board-layout \
  2>&1 | tee "$EVIDENCE_DIR/frontend-hedge-board-layout.log"
pnpm test:funding-order-layout \
  2>&1 | tee "$EVIDENCE_DIR/frontend-funding-order-layout.log"
pnpm test:cross-spread-layout \
  2>&1 | tee "$EVIDENCE_DIR/frontend-cross-spread-layout.log"
pnpm exec vue-tsc -p tsconfig.user-system.json --noEmit --skipLibCheck \
  2>&1 | tee "$EVIDENCE_DIR/frontend-user-system-typecheck.log"
pnpm type:check \
  2>&1 | tee "$EVIDENCE_DIR/frontend-strategy-typecheck.log"
pnpm build \
  2>&1 | tee "$EVIDENCE_DIR/frontend-build.log"
```

### 7.4 对冲基金看板浏览器 E2E

E2E 会启动隔离的 Platform Backend、前端和测试数据库。执行前不要在 8000 或 4373 运行手工服务。

```bash
cd "$ACCEPT_ROOT/admin-risk"

export E2E_CEO_USERNAME="e2e_employee_1"
export E2E_CEO_PASSWORD="Cc9!$(python3.12 -c 'import secrets; print(secrets.token_urlsafe(24))')"

set -o pipefail
pnpm test:e2e:hedge-board \
  2>&1 | tee "$EVIDENCE_DIR/hedge-board-e2e.log"

cp -R test-results/hedge-board \
  "$EVIDENCE_DIR/hedge-board-test-results"
cp -R playwright-report/hedge-board \
  "$EVIDENCE_DIR/hedge-board-playwright-report"
```

该 E2E 必须覆盖：

- 登录和 Cookie Session；
- A 股页面主要区块；
- 申万搜索、排序和阈值；
- 一键个股；
- 账号级自选股持久化；
- 1440、1024、768、390 四档宽度；
- 页面级横向溢出检查；
- 每档“大盘表现”“申万板块”“自选股”截图。

### 7.5 用户系统浏览器 E2E

```bash
cd "$ACCEPT_ROOT/admin-risk"

export E2E_CEO_USERNAME="e2e_ceo"
# 继续使用上一节生成的临时 E2E_CEO_PASSWORD

set -o pipefail
pnpm test:e2e:user-system \
  2>&1 | tee "$EVIDENCE_DIR/user-system-e2e.log"

cp -R test-results/user-system \
  "$EVIDENCE_DIR/user-system-test-results"
cp -R playwright-report/user-system \
  "$EVIDENCE_DIR/user-system-playwright-report"
```

不得把临时密码写入验收文档、截图、Git 或最终报告。

## 8. 启动本地实际页面

自动化全部完成后，再启动本地实际页面。A 股投研页面不依赖 Execution Runtime，本次只启动 Backend 与 Frontend。

### 8.1 Terminal A：Platform Backend

```bash
cd "$ACCEPT_ROOT/platform-backend"
source .venv-acceptance/bin/activate

export VG_ENVIRONMENT=development
export VG_DATABASE_PATH="$EVIDENCE_DIR/platform-acceptance.db"
export VG_AVATAR_DATA_DIRECTORY="$EVIDENCE_DIR/avatars"
export VG_RUNTIME_BASE_URL="http://127.0.0.1:8100"
export VG_CORS_ORIGINS="http://127.0.0.1:4373,http://localhost:4373"
export VG_AUTH_MODE=development
export VG_BROWSER_SESSIONS_ENABLED=true
export VG_LIVE_TRADING_ENABLED=false
export VG_DEFAULT_TRADING_ENVIRONMENT=simulation

export USER_SYSTEM_DEMO_SEED=1
export USER_SYSTEM_DEMO_PASSWORD="Aa9!$(python3.12 -c 'import secrets; print(secrets.token_urlsafe(24))')"
python scripts/seed_user_system_demo.py

printf '本地验收账号：demo_ceo\n'
printf '临时密码仅显示在当前终端，不得写入证据文件：%s\n' "$USER_SYSTEM_DEMO_PASSWORD"

python -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  2>&1 | tee "$EVIDENCE_DIR/platform-backend-runtime.log"
```

确认日志中没有启用 Live Trading。

### 8.2 Terminal B：Frontend

```bash
cd "$ACCEPT_ROOT/admin-risk"

HUSKY=0 pnpm dev --host 127.0.0.1 \
  2>&1 | tee "$EVIDENCE_DIR/frontend-runtime.log"
```

必须使用：

```text
http://127.0.0.1:4373/
```

如 Vite 改用其他端口，停止验收并释放 4373，不得继续使用错误的 CORS 环境。

### 8.3 Terminal C：健康检查和真实 Provider 探测

```bash
curl -fsS http://127.0.0.1:8000/health \
  | tee "$EVIDENCE_DIR/backend-health.json"

cd "$ACCEPT_ROOT/platform-backend"
source .venv-acceptance/bin/activate

python scripts/validate_research_sources.py \
  --base-url http://127.0.0.1:8000 \
  --stock-code 600519 \
  --threshold-yuan 10000000000 \
  --output "$EVIDENCE_DIR/hedge-board-live-source-check.json" \
  2>&1 | tee "$EVIDENCE_DIR/validate-research-sources.log"

python scripts/smoke_research_providers.py --timeout 60 \
  2>&1 | tee "$EVIDENCE_DIR/research-provider-smoke.json"
```

Provider Smoke 工作流成功不等于所有 Provider 健康；必须查看 JSON 内的 `status`、`passed`、`failed` 和各检查结果。

## 9. 本地人工业务验收

打开：

```bash
open 'http://127.0.0.1:4373/#/hedge-board/a-share'
```

使用：

```text
用户名：demo_ceo
密码：Terminal A 中生成的 USER_SYSTEM_DEMO_PASSWORD
```

### 9.1 数据来源与状态

逐个检查“大盘表现、市场广度、申万板块、短线情绪、一键个股”模块：

- [ ] 显示真实数据源名称；
- [ ] 上游数据时间与 Platform 抓取时间能够区分；
- [ ] `ready / partial / stale / no_data / error`视觉状态能够区分；
- [ ] 上一交易日数据没有被描述为实时数据；
- [ ] 某一模块失败时，其他模块仍能使用；
- [ ] 错误没有被显示为 0；
- [ ] 连续刷新时，空结果没有覆盖上一份有意义的数据；
- [ ] 页面没有前端直连第三方域名的请求，研究请求统一通过`/api/v1/research/**`。

可在浏览器开发者工具 Network 中按`research`筛选。记录请求路径、HTTP状态和页面状态，不记录 Cookie、CSRF 或认证头。

`stale`或Last Known Good如在本次自然运行中未触发，应记录为“本次未自然观察到”，不得伪造通过证据，也不得修改代码或系统时钟强行触发。

### 9.2 申万与成交额阈值

- [ ] 申万二级默认显示成交额 Top 10；
- [ ] 展开全部申万二级；
- [ ] 一级行业筛选正常；
- [ ] 行业名称或代码搜索正常；
- [ ] 成交额、涨跌幅、市场占比升降序正常；
- [ ] 50亿元、100亿元、200亿元与自定义阈值均使用严格`>`；
- [ ] 点击行业数量能展开对应股票；
- [ ] 复制结果与 CSV 导出结果一致；
- [ ] 未匹配申万分类的证券数量有明确显示；
- [ ] 抽样三只股票，将 Platform 的申万一级/二级与可信外部分类来源核对并记录。

建议抽样代码：

```text
600519  沪市主板
000001  深市主板
300750  创业板
```

不得仅凭记忆填写申万归属，必须记录外部核对来源和核对日期。

### 9.3 一键个股

依次测试：

```text
600519
SH600519
600519.SH
000001
300750
```

检查：

- [ ] 三种 600519 输入被归一化到同一股票；
- [ ] 新查询后所有数据模块默认折叠；
- [ ] 快速连续切换股票时，旧响应不会覆盖最后一次查询；
- [ ] 单一模块失败不导致整页失败；
- [ ] 行情、财务、估值、研报、公告和新闻显示实际来源；
- [ ] 至少打开一条研报原文；
- [ ] 至少打开一条公告原文；
- [ ] 至少打开一条新闻原文；
- [ ] 原文链接不是空链接、前端假链接或本地夹具链接。

链接抽样记录：

| 股票 | 类型 | 页面标题 | 目标域名 | 能否打开 | 备注 |
|---|---|---|---|---|---|
| 600519 | 研报 | 待填写 | 待填写 | 待填写 | 待填写 |
| 600519 | 公告 | 待填写 | 待填写 | 待填写 | 待填写 |
| 600519 | 新闻 | 待填写 | 待填写 | 待填写 | 待填写 |

### 9.4 账号级自选股

使用 `demo_ceo`：

- [ ] 新增一只股票；
- [ ] 修改分组；
- [ ] 组内排序；
- [ ] 删除股票；
- [ ] 保存空列表；
- [ ] 页面显示“账号已同步”；
- [ ] 退出并新建无痕窗口，同账号重新登录后数据恢复；
- [ ] 使用另一个演示账号登录，确认自选股不串号；
- [ ] 后端不可用时，不得显示“账号已同步”；
- [ ] 后端恢复后可重新同步。

测试后可以恢复为空列表，但不要直接修改数据库。

### 9.5 响应式与视觉

分别使用浏览器设备模拟检查：

```text
1440 × 900
1024 × 768
768 × 1024
390 × 844
```

每档至少保存三张截图：

```text
<宽度>-overview.png
<宽度>-shenwan.png
<宽度>-watchlist.png
```

保存到：

```text
$EVIDENCE_DIR/manual-screenshots/
```

检查：

- [ ] 无页面级横向溢出；
- [ ] 需要横向滚动的表格只在表格容器内滚动；
- [ ] 导航抽屉没有遮挡主体；
- [ ] 数值右对齐，名称左对齐；
- [ ] 空值统一显示为“—”；
- [ ] 红涨绿跌符合平台约定；
- [ ] 筛选、应用、复制、导出、展开按钮容易识别；
- [ ] 无重叠、截断、白屏和明显布局跳动；
- [ ] 390px 下仍能完成申万筛选、自选股和个股查询。

截图前必须等待页面加载结束，并确认没有截入临时密码、Cookie、CSRF、Token 或真实客户信息。

## 10. 验收结论标准

### 10.1 通过

同时满足：

1. 仓库、后端、前端和两套浏览器 E2E 全部通过；
2. `VG_LIVE_TRADING_ENABLED=false`；
3. 真实 Provider 的实际状态被准确展示；
4. 已知 `partial` 不引发整页失败、伪造 0 或覆盖 Last Known Good；
5. 申万、阈值、个股链接和自选股人工检查通过；
6. 四档响应式无 P0/P1 问题；
7. 验收前后没有任何受 Git 跟踪文件变化。

### 10.2 有条件通过

仅存在已记录的免费上游可用性问题，并且：

- 页面准确标记`partial / stale / error`；
- 可用模块仍可使用；
- 不影响用户系统、权限和自选股持久化；
- 没有 P0/P1 产品缺陷；
- 所有者明确接受该外部依赖风险。

### 10.3 不通过

出现任一情况即不通过：

- 自动化检查失败；
- 页面白屏、关键交互不可用或 390px 无法操作；
- 来源、时间或状态标记错误；
- 外部错误被伪装成健康或 0；
- 研报、公告、新闻原文链接无法打开或是假链接；
- 自选股跨账号串数据；
- 页面绕过 Platform Backend 直连第三方；
- Live Trading 被开启；
- 受 Git 跟踪文件被修改。

缺陷等级：

```text
P0  安全边界、权限、数据串号、Live Write 或整页不可用
P1  核心模块错误、关键数据口径错误、无法完成主要流程
P2  局部交互、状态提示、响应式或链接问题
P3  文案、间距、轻微视觉问题
```

## 11. 输出验收报告

在`$EVIDENCE_DIR/LOCAL_ACCEPTANCE_RESULT.md`填写：

```markdown
# Platform 0.9.1 本地验收结果

- 日期：
- 执行人/执行代理：
- 设备与系统：
- 分支：feature/issue-134-platform-0-9-1-unified-delivery
- 验收 HEAD：
- 功能验证基线：00574a8f10a3fc3723ae78c97aacbff075ff803b
- Issue：#134
- Draft PR：#135
- VG_LIVE_TRADING_ENABLED：false

## 自动化结果

| 检查 | 结果 | 日志 |
|---|---|---|
| 仓库治理 | PASS/FAIL | 文件名 |
| Backend Ruff | PASS/FAIL | 文件名 |
| Backend Pyright | PASS/FAIL | 文件名 |
| Backend Pytest | PASS/FAIL | 文件名 |
| Frontend Type Check | PASS/FAIL | 文件名 |
| Frontend Build | PASS/FAIL | 文件名 |
| Hedge Board E2E | PASS/FAIL | 文件名 |
| User System E2E | PASS/FAIL | 文件名 |

## 实际 Provider 与页面状态

| 模块 | Provider/来源 | 上游时间 | 抓取时间 | 页面状态 | 结论 |
|---|---|---|---|---|---|
| 大盘表现 | | | | | |
| 市场广度 | | | | | |
| 申万板块 | | | | | |
| 短线情绪 | | | | | |
| 一键个股 | | | | | |

## 业务验收

- 申万与阈值：
- 个股输入归一化：
- 研报链接：
- 公告链接：
- 新闻链接：
- 自选股跨会话：
- 自选股账号隔离：
- stale / Last Known Good：已观察 / 本次未自然观察 / 失败

## 响应式

| 视口 | Overview | Shenwan | Watchlist | 结论 |
|---|---|---|---|---|
| 1440 × 900 | | | | |
| 1024 × 768 | | | | |
| 768 × 1024 | | | | |
| 390 × 844 | | | | |

## 缺陷

| 等级 | 标题 | 复现步骤 | 证据 | 是否阻断 |
|---|---|---|---|---|

## 最终结论

- 结论：通过 / 有条件通过 / 不通过
- 是否满足 Phase 4 本地验收：是 / 否
- 是否建议冻结 0.9.1 Release Candidate：是 / 否
- 未完成或不能声称完成的项目：
- 所有者仍需确认的项目：
```

报告中不得包含密码、Cookie、CSRF、Token、API Key 或真实客户数据。

## 12. 验收结束检查

```bash
cd "$ACCEPT_ROOT"

git status --porcelain=v1 | tee "$EVIDENCE_DIR/git-status-after.txt"
git diff --exit-code
git diff --cached --exit-code
```

安装和测试会产生未跟踪目录，例如`.venv-acceptance/`、`node_modules/`、`dist/`和`.e2e/`。这些目录可以出现在`git status`中；通过判定要求`git diff --exit-code`和`git diff --cached --exit-code`均返回0，即没有任何受Git跟踪文件被修改或暂存。

保存证据后清理worktree：

```bash
cd "$SOURCE_REPO"
git worktree remove --force "$ACCEPT_ROOT"
git worktree prune
```

这里的`--force`只用于移除包含未跟踪依赖和测试产物的独立验收worktree；不得使用`git clean -fd`，也不得对现有开发目录执行强制清理。

## 13. 最终交接要求

本地 AI 最终只返回：

1. 验收 HEAD；
2. 自动化通过/失败清单；
3. 真实 Provider 与页面状态；
4. 申万、原文链接、自选股和响应式结论；
5. P0–P3 缺陷清单；
6. `通过 / 有条件通过 / 不通过`结论；
7. 是否建议进入 Phase 5；
8. evidence 目录绝对路径。

本地 AI 不得自行修复缺陷、提交代码、推送分支、修改 PR 状态或合并 `main`。