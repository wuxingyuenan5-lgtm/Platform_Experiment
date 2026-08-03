# Platform 0.9.1 本地验收交接（Windows）

> 适用系统：Windows 10/11 + PowerShell，本地只读验收
> 仓库：`wuxingyuenan5-lgtm/Platform_Experiment`
> Issue：`#134`
> Draft PR：`#135`
> 统一交付分支：`feature/issue-134-platform-0-9-1-unified-delivery`
> 已完成全套自动化验证的最低功能基线：`00574a8f10a3fc3723ae78c97aacbff075ff803b`
> 状态：`ready for local acceptance`
> 强制约束：只验收，不改代码、不提交、不推送、不合并 `main`

## 1. 文档用途

本文档用于把 Platform 0.9.1 的本地验收完整交给另一位执行人或本地 AI。执行完成后，应形成可复核的日志、截图和验收结论，而不是口头表示“看起来正常”。

本地验收重点覆盖：

- Platform 0.9.1 能否在 Windows 上安装、构建和运行；
- Platform Backend、用户系统、对冲基金看板和前端的自动化检查；
- A 股研究页面、申万统计、一键个股、账号级自选股和宏观概率页面；
- 数据来源、上游时间、Platform 抓取时间以及 `ready / partial / stale / no_data / error` 状态；
- 1440、1024、768、390 四档响应式页面；
- 免费 Provider 部分失败时的模块化降级与 Last Known Good 语义。

本文档不验收：

- 真实下单、成交、持仓、会计账本或风险权威数据；
- Bybit、MT5 或其他 Venue 的真实连接；
- Platform Live Write 或 Execution Runtime Live Write；
- 第三方免费数据源的永久可用性；
- 生产 HTTPS、Secure Cookie、正式备份恢复和生产部署。

## 2. 可直接交给本地 AI 的执行指令

将下面整段复制给本地 Codex 或其他本地执行代理：

```text
你是 Platform 0.9.1 本地验收执行代理。

仓库：wuxingyuenan5-lgtm/Platform_Experiment
验收分支：feature/issue-134-platform-0-9-1-unified-delivery
最低功能验证基线：00574a8f10a3fc3723ae78c97aacbff075ff803b
Issue：#134
Draft PR：#135
操作系统：Windows 10/11，使用 PowerShell

本次只做本地验收，不做开发。

强制规则：
1. 必须使用独立 detached worktree，不得直接在现有开发目录验收。
2. 不得修改任何受 Git 跟踪的文件，不得执行 git add、git commit、git push、git merge、git rebase、git reset --hard 或 git clean -fd。
3. 不得切换、修改或合并 main；不得把 Draft PR 标记为 Ready 或合并。
4. VG_LIVE_TRADING_ENABLED 必须始终为 false；不得测试真实下单、Live Write、Bybit 或 MT5。
5. 外部免费 Provider 的 partial、stale、no_data 或 error 必须按实际记录，不能描述为全部健康。
6. E2E 研究数据夹具只证明交互和布局，不得作为真实行情验收证据。
7. 所有日志、截图、数据库和验收报告写入仓库外的 evidence 目录，不得写入 Git。
8. 发现问题时只记录复现步骤、证据和严重级别，不得顺手修改代码。
9. 结束前必须确认 git diff 和 git diff --cached 均为空。
10. 按本文档顺序执行，并最终输出“通过 / 有条件通过 / 不通过”。
```

## 3. 已知基线与外部风险

GitHub 自动化已记录两份真实 Provider 样本：

| 时段 | 结果 | 600519 腾讯 | 600519 东方财富 | 双源差值 |
|---|---|---:|---:|---:|
| 交易时段 | `partial`，5/8 通过 | 1358.23 | 1358.20 | 0.03 |
| 非交易时段 | `partial`，5/8 通过 | 1361.76 | 1361.76 | 0.00 |

两个时段均出现以下外部依赖问题：

- 全市场 A 股现货接口被远端中断连接；
- 指数历史数据不可用；
- 申万官方批量分类文件 TLS 证书链无法验证。

这些外部问题本身不等于本地验收失败。真正的阻断条件包括：

- 页面把失败模块显示为 `ready`；
- 页面以 0、空数组或错误数据覆盖上一份有效数据；
- 单一 Provider 失败导致整页白屏；
- 页面不显示真实来源和时间；
- 前端绕过 Platform Backend 直连研究数据源；
- 为了通过验收关闭 TLS 校验；
- 自选股在不同账号之间串数据；
- Live Write 被开启。

## 4. 环境要求

推荐环境：

```text
Windows 10/11
PowerShell 5.1 或 PowerShell 7
Git 2.x
Python 3.12
Node.js 20 或更高版本
pnpm 9.15.9（通过 npx 调用，无需全局安装）
Chromium（由 Playwright 安装）
```

先在 PowerShell 检查：

```powershell
git --version
py -3.12 --version
node --version
npx --version
```

任何一项不存在时，先安装对应工具，再开始验收。

默认端口：

```text
Platform Backend  8000
Frontend          4373
Execution Runtime 8100（本次不进行实盘验收）
```

检查端口：

```powershell
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $_.LocalPort -in 8000, 4373, 8100 } |
  Format-Table LocalAddress, LocalPort, OwningProcess
```

如 8000 或 4373 已被占用，先确认进程身份并正常停止。不得直接结束不明进程，也不得让 Vite 自动改用其他端口后继续验收。

## 5. 创建独立只读 Worktree

将 `$SourceRepo` 改为你电脑上现有仓库的实际路径：

```powershell
$SourceRepo = "D:\Projects\Platform_Experiment"
$AcceptRoot = "D:\Projects\Platform_Experiment-0.9.1-acceptance"
$EvidenceDir = Join-Path $env:USERPROFILE (
  "Platform_Experiment-0.9.1-evidence\" + (Get-Date -Format "yyyyMMdd-HHmmss")
)

New-Item -ItemType Directory -Path $EvidenceDir -Force | Out-Null

if (-not (Test-Path $SourceRepo)) {
  throw "源仓库不存在：$SourceRepo"
}
if (Test-Path $AcceptRoot) {
  throw "验收目录已经存在：$AcceptRoot。请人工确认后处理，不要覆盖。"
}

git -C $SourceRepo fetch origin --prune
if ($LASTEXITCODE -ne 0) { throw "git fetch 失败" }

git -C $SourceRepo worktree add --detach `
  $AcceptRoot `
  origin/feature/issue-134-platform-0-9-1-unified-delivery
if ($LASTEXITCODE -ne 0) { throw "创建验收 worktree 失败" }

Set-Location $AcceptRoot

git rev-parse HEAD | Tee-Object -FilePath (Join-Path $EvidenceDir "git-head.txt")
git log -1 --oneline | Tee-Object -FilePath (Join-Path $EvidenceDir "git-head-summary.txt")
git status --porcelain=v1 --untracked-files=no |
  Tee-Object -FilePath (Join-Path $EvidenceDir "git-status-before.txt")

git merge-base --is-ancestor `
  00574a8f10a3fc3723ae78c97aacbff075ff803b `
  HEAD
if ($LASTEXITCODE -ne 0) {
  throw "当前 HEAD 不包含最低已验证功能基线，停止验收"
}

$Version = (Get-Content .\VERSION -Raw).Trim()
if ($Version -ne "0.9.1") {
  throw "VERSION 不是 0.9.1，实际值：$Version"
}
```

验收前必须满足：

- 当前为 detached HEAD；
- `VERSION`为`0.9.1`；
- `00574a8f...`是当前 HEAD 的祖先；
- `git-status-before.txt`没有受跟踪文件变化；
- 当前 worktree 来自统一交付分支，而不是`main`。

记录环境：

```powershell
@(
  "OS: $((Get-CimInstance Win32_OperatingSystem).Caption)"
  "PowerShell: $($PSVersionTable.PSVersion)"
  "Git: $(git --version)"
  "Python: $(py -3.12 --version 2>&1)"
  "Node: $(node --version)"
  "npx: $(npx --version)"
  "Acceptance HEAD: $(git rev-parse HEAD)"
) | Set-Content -Path (Join-Path $EvidenceDir "environment.txt") -Encoding UTF8
```

## 6. 安装依赖

### 6.1 Platform Backend

```powershell
$BackendRoot = Join-Path $AcceptRoot "platform-api"
$BackendVenv = Join-Path $BackendRoot ".venv-acceptance"
$BackendPython = Join-Path $BackendVenv "Scripts\python.exe"

py -3.12 -m venv $BackendVenv
if ($LASTEXITCODE -ne 0) { throw "创建 Backend Python 环境失败" }

& $BackendPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "升级 pip 失败" }

Set-Location $BackendRoot
& $BackendPython -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "安装 Platform Backend 依赖失败" }

& $BackendPython -m pip check
if ($LASTEXITCODE -ne 0) { throw "Platform Backend 依赖图检查失败" }
```

### 6.2 Execution Runtime 静态测试环境

这里只运行 Lint、类型和测试，不启动真实 Venue 或 Live Write。

```powershell
$RuntimeRoot = Join-Path $AcceptRoot "execution-runtime"
$RuntimeVenv = Join-Path $RuntimeRoot ".venv-acceptance"
$RuntimePython = Join-Path $RuntimeVenv "Scripts\python.exe"

py -3.12 -m venv $RuntimeVenv
if ($LASTEXITCODE -ne 0) { throw "创建 Runtime Python 环境失败" }

& $RuntimePython -m pip install --upgrade pip
Set-Location $RuntimeRoot
& $RuntimePython -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "安装 Execution Runtime 依赖失败" }

& $RuntimePython -m pip check
if ($LASTEXITCODE -ne 0) { throw "Execution Runtime 依赖图检查失败" }
```

### 6.3 前端与 Chromium

```powershell
$FrontendRoot = Join-Path $AcceptRoot "platform-web"
Set-Location $FrontendRoot

$env:HUSKY = "0"
npx --yes pnpm@9.15.9 install --frozen-lockfile
if ($LASTEXITCODE -ne 0) { throw "前端依赖安装失败" }

npx --yes pnpm@9.15.9 exec playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "Chromium 安装失败" }
```

安装过程允许产生`.venv-acceptance`、`node_modules`、`dist`和测试结果等未跟踪或被忽略文件，但不得改变`pnpm-lock.yaml`或其他受 Git 跟踪文件。

## 7. 日志执行辅助函数

在当前 PowerShell 定义：

```powershell
function Invoke-Logged {
  param(
    [Parameter(Mandatory = $true)][string]$LogPath,
    [Parameter(Mandatory = $true)][scriptblock]$Command
  )

  & $Command 2>&1 | Tee-Object -FilePath $LogPath
  $ExitCode = $LASTEXITCODE
  if ($null -ne $ExitCode -and $ExitCode -ne 0) {
    throw "命令失败，退出码 $ExitCode，日志：$LogPath"
  }
}
```

任一检查失败时，不得继续给出“通过”结论。先保存日志并记录缺陷。

## 8. 自动化验收

### 8.1 仓库治理

```powershell
Set-Location $AcceptRoot

Invoke-Logged (Join-Path $EvidenceDir "check-documentation-consistency.log") {
  py -3.12 scripts\check-documentation-consistency.py
}
Invoke-Logged (Join-Path $EvidenceDir "check-repository-structure.log") {
  py -3.12 scripts\check-repository-structure.py
}
Invoke-Logged (Join-Path $EvidenceDir "check-version-consistency.log") {
  py -3.12 scripts\check-version-consistency.py
}
Invoke-Logged (Join-Path $EvidenceDir "check-codex-context.log") {
  py -3.12 scripts\check-codex-context.py
}
Invoke-Logged (Join-Path $EvidenceDir "scan-secrets.log") {
  py -3.12 scripts\scan-secrets.py
}
```

### 8.2 Platform Backend

```powershell
Set-Location $BackendRoot

Invoke-Logged (Join-Path $EvidenceDir "backend-pip-check.log") {
  & $BackendPython -m pip check
}
Invoke-Logged (Join-Path $EvidenceDir "backend-ruff.log") {
  & $BackendPython -m ruff check app tests scripts
}
Invoke-Logged (Join-Path $EvidenceDir "backend-pyright.log") {
  & $BackendPython -m pyright
}
Invoke-Logged (Join-Path $EvidenceDir "backend-pytest.log") {
  & $BackendPython -m pytest
}
```

### 8.3 Execution Runtime 静态检查

```powershell
Set-Location $RuntimeRoot
$env:VG_LIVE_TRADING_ENABLED = "false"

Invoke-Logged (Join-Path $EvidenceDir "runtime-pip-check.log") {
  & $RuntimePython -m pip check
}
Invoke-Logged (Join-Path $EvidenceDir "runtime-ruff.log") {
  & $RuntimePython -m ruff check app tests
}
Invoke-Logged (Join-Path $EvidenceDir "runtime-pyright.log") {
  & $RuntimePython -m pyright
}
Invoke-Logged (Join-Path $EvidenceDir "runtime-pytest.log") {
  & $RuntimePython -m pytest -m "architecture or unit or integration or live_safety"
}
```

不得设置真实 Venue 凭证，不得运行实盘连接测试。

### 8.4 前端结构、类型和构建

```powershell
Set-Location $FrontendRoot
$env:HUSKY = "0"

Invoke-Logged (Join-Path $EvidenceDir "frontend-user-system-policy.log") {
  npx --yes pnpm@9.15.9 test:user-system
}
Invoke-Logged (Join-Path $EvidenceDir "frontend-homepage-layout.log") {
  npx --yes pnpm@9.15.9 test:homepage-layout
}
Invoke-Logged (Join-Path $EvidenceDir "frontend-hedge-board-layout.log") {
  npx --yes pnpm@9.15.9 test:hedge-board-layout
}
Invoke-Logged (Join-Path $EvidenceDir "frontend-funding-order-layout.log") {
  npx --yes pnpm@9.15.9 test:funding-order-layout
}
Invoke-Logged (Join-Path $EvidenceDir "frontend-cross-spread-layout.log") {
  npx --yes pnpm@9.15.9 test:cross-spread-layout
}
Invoke-Logged (Join-Path $EvidenceDir "frontend-user-system-typecheck.log") {
  npx --yes pnpm@9.15.9 exec vue-tsc -p tsconfig.user-system.json --noEmit --skipLibCheck
}
Invoke-Logged (Join-Path $EvidenceDir "frontend-strategy-typecheck.log") {
  npx --yes pnpm@9.15.9 type:check
}
Invoke-Logged (Join-Path $EvidenceDir "frontend-full-typecheck.log") {
  npx --yes pnpm@9.15.9 type:check:full
}
Invoke-Logged (Join-Path $EvidenceDir "frontend-build.log") {
  npx --yes pnpm@9.15.9 build
}
```

### 8.5 对冲基金看板浏览器 E2E

E2E 会自行启动隔离的 Backend、前端和测试数据库。执行前确认 8000 和 4373 没有手工服务运行。

```powershell
Set-Location $FrontendRoot

$OriginalPath = $env:Path
$env:Path = "$(Join-Path $BackendVenv 'Scripts');$OriginalPath"
$env:E2E_CEO_USERNAME = "e2e_employee_1"
$env:E2E_CEO_PASSWORD = "Cc9!" + [guid]::NewGuid().ToString("N")

Invoke-Logged (Join-Path $EvidenceDir "hedge-board-e2e.log") {
  npx --yes pnpm@9.15.9 test:e2e:hedge-board
}

if (Test-Path ".\test-results\hedge-board") {
  Copy-Item ".\test-results\hedge-board" `
    (Join-Path $EvidenceDir "hedge-board-test-results") `
    -Recurse -Force
}
if (Test-Path ".\playwright-report\hedge-board") {
  Copy-Item ".\playwright-report\hedge-board" `
    (Join-Path $EvidenceDir "hedge-board-playwright-report") `
    -Recurse -Force
}
```

该 E2E 必须覆盖：

- 真实登录和 Cookie Session；
- A 股页面主要模块；
- 申万搜索、排序和成交额阈值；
- 一键个股；
- 账号级自选股持久化；
- 1440、1024、768、390 四档宽度；
- 页面级横向溢出；
- 每档“大盘表现”“申万板块”“自选股”截图。

### 8.6 用户系统浏览器 E2E

```powershell
Set-Location $FrontendRoot
$env:E2E_CEO_USERNAME = "e2e_ceo"

Invoke-Logged (Join-Path $EvidenceDir "user-system-e2e.log") {
  npx --yes pnpm@9.15.9 test:e2e:user-system
}

if (Test-Path ".\test-results\user-system") {
  Copy-Item ".\test-results\user-system" `
    (Join-Path $EvidenceDir "user-system-test-results") `
    -Recurse -Force
}
if (Test-Path ".\playwright-report\user-system") {
  Copy-Item ".\playwright-report\user-system" `
    (Join-Path $EvidenceDir "user-system-playwright-report") `
    -Recurse -Force
}

Remove-Item Env:E2E_CEO_USERNAME -ErrorAction SilentlyContinue
Remove-Item Env:E2E_CEO_PASSWORD -ErrorAction SilentlyContinue
$env:Path = $OriginalPath
```

不得把临时 E2E 密码写入报告、日志说明、截图或 Git。

## 9. 启动本地实际页面

自动化全部完成后，再启动用于人工验收的本地页面。使用三个 PowerShell 窗口。

### 9.1 PowerShell A：Platform Backend

```powershell
$AcceptRoot = "D:\Projects\Platform_Experiment-0.9.1-acceptance"
$EvidenceDir = "请填写第 5 节创建的 evidence 目录绝对路径"
$BackendRoot = Join-Path $AcceptRoot "platform-api"
$BackendPython = Join-Path $BackendRoot ".venv-acceptance\Scripts\python.exe"

Set-Location $BackendRoot

$env:VG_ENVIRONMENT = "development"
$env:VG_DATABASE_PATH = Join-Path $EvidenceDir "platform-acceptance.db"
$env:VG_AVATAR_DATA_DIRECTORY = Join-Path $EvidenceDir "avatars"
$env:VG_RUNTIME_BASE_URL = "http://127.0.0.1:8100"
$env:VG_CORS_ORIGINS = "http://127.0.0.1:4373,http://localhost:4373"
$env:VG_AUTH_MODE = "development"
$env:VG_BROWSER_SESSIONS_ENABLED = "true"
$env:VG_LIVE_TRADING_ENABLED = "false"
$env:VG_DEFAULT_TRADING_ENVIRONMENT = "simulation"

$env:USER_SYSTEM_DEMO_SEED = "1"
$DemoPassword = "Aa9!" + [guid]::NewGuid().ToString("N")
$env:USER_SYSTEM_DEMO_PASSWORD = $DemoPassword

& $BackendPython scripts\seed_user_system_demo.py
if ($LASTEXITCODE -ne 0) { throw "演示账号初始化失败" }

Write-Host "本地验收账号：demo_ceo" -ForegroundColor Cyan
Write-Host "第二账号：demo_employee_1" -ForegroundColor Cyan
Write-Host "本次临时凭据：$DemoPassword" -ForegroundColor Yellow
Write-Host "密码只保留在当前终端，不得写入截图和报告。" -ForegroundColor Yellow

& $BackendPython -m uvicorn app.main:app `
  --host 127.0.0.1 `
  --port 8000 `
  2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "platform-api-runtime.log")
```

确认日志中没有启用 Live Trading。

### 9.2 PowerShell B：Frontend

```powershell
$AcceptRoot = "D:\Projects\Platform_Experiment-0.9.1-acceptance"
$EvidenceDir = "请填写第 5 节创建的 evidence 目录绝对路径"
$FrontendRoot = Join-Path $AcceptRoot "platform-web"

Set-Location $FrontendRoot
$env:HUSKY = "0"
$env:VITE_PLATFORM_API_BASE_URL = "http://127.0.0.1:8000/api/v1"

npx --yes pnpm@9.15.9 sync:trading-tools
if ($LASTEXITCODE -ne 0) { throw "交易工具同步失败" }

npx --yes pnpm@9.15.9 exec vite `
  --host 127.0.0.1 `
  --port 4373 `
  2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "frontend-runtime.log")
```

必须访问：

```text
http://127.0.0.1:4373/
```

如 Vite 自动改用其他端口，停止验收并释放 4373，不得在错误的 CORS 环境下继续。

### 9.3 PowerShell C：健康检查和真实 Provider 探测

```powershell
$AcceptRoot = "D:\Projects\Platform_Experiment-0.9.1-acceptance"
$EvidenceDir = "请填写第 5 节创建的 evidence 目录绝对路径"
$BackendRoot = Join-Path $AcceptRoot "platform-api"
$BackendPython = Join-Path $BackendRoot ".venv-acceptance\Scripts\python.exe"

$Health = Invoke-RestMethod "http://127.0.0.1:8000/health"
$Health | ConvertTo-Json -Depth 10 |
  Set-Content (Join-Path $EvidenceDir "backend-health.json") -Encoding UTF8

Set-Location $BackendRoot

& $BackendPython scripts\validate_research_sources.py `
  --base-url http://127.0.0.1:8000 `
  --stock-code 600519 `
  --threshold-yuan 10000000000 `
  --output (Join-Path $EvidenceDir "hedge-board-live-source-check.json") `
  2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "validate-research-sources.log")

& $BackendPython scripts\smoke_research_providers.py --timeout 60 `
  2>&1 | Tee-Object -FilePath (Join-Path $EvidenceDir "research-provider-smoke.json")
```

Provider Smoke 命令成功不等于所有 Provider 健康。必须查看 JSON 中的`status`、`passed`、`failed`和每个检查项。

## 10. 本地人工业务验收

打开登录页面：

```powershell
Start-Process "http://127.0.0.1:4373/#/login"
```

使用：

```text
用户名：demo_ceo
临时凭据：PowerShell A 中显示的本次随机值
```

A 股页面：

```text
http://127.0.0.1:4373/#/hedge-board/a-share
```

宏观页面：

```text
http://127.0.0.1:4373/#/hedge-board/macro
```

### 10.1 来源、时间与状态

逐个检查“大盘表现、市场广度、申万板块、短线情绪、一键个股、宏观概率”：

- [ ] 显示真实数据源名称；
- [ ] 上游数据时间与 Platform 抓取时间能够区分；
- [ ] `ready / partial / stale / no_data / error`视觉状态能够区分；
- [ ] 上一交易日数据没有被描述为实时数据；
- [ ] 某一模块失败时，其他模块仍能使用；
- [ ] 错误没有被显示成 0；
- [ ] 空拉取没有覆盖上一份有意义的数据；
- [ ] 研究请求统一通过`/api/v1/research/**`；
- [ ] 浏览器没有直接向东方财富、腾讯行情或申万域名发出研究数据请求。

在浏览器开发者工具的 Network 中按`research`筛选，只记录请求路径、HTTP状态和页面状态。不得记录 Cookie、CSRF、Token 或认证头。

`stale`或 Last Known Good 如未自然触发，记录“本次未自然观察到”，不得修改系统时钟、数据库或代码伪造证据。

### 10.2 申万与成交额阈值

- [ ] 申万二级默认显示成交额 Top 10；
- [ ] 可展开全部申万二级行业；
- [ ] 一级行业筛选正常；
- [ ] 行业名称或代码搜索正常；
- [ ] 成交额、涨跌幅、市场占比升降序正常；
- [ ] 50亿元、100亿元、200亿元和自定义阈值均严格使用`>`；
- [ ] 点击行业数量可以展开对应股票；
- [ ] 复制结果和 CSV 导出结果一致；
- [ ] 未匹配申万分类的证券数量有明确显示；
- [ ] 抽样三只股票，将 Platform 的申万一级、二级与可信外部分类来源核对并记录。

建议抽样：

```text
600519  贵州茅台，沪市主板
000001  平安银行，深市主板
300750  宁德时代，创业板
```

不得凭记忆填写申万归属，必须记录外部核对来源和核对日期。

### 10.3 一键个股

依次测试：

```text
600519
SH600519
600519.SH
000001
300750
```

检查：

- [ ] 三种 600519 输入归一化为同一股票；
- [ ] 新查询后数据模块默认折叠；
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

### 10.4 账号级自选股

使用`demo_ceo`：

- [ ] 新增一只股票；
- [ ] 修改分组；
- [ ] 调整组内排序；
- [ ] 删除股票；
- [ ] 保存空列表；
- [ ] 页面显示“账号已同步”；
- [ ] 退出后在无痕窗口重新登录，数据能够恢复；
- [ ] 使用`demo_employee_1`登录，确认两个账号的自选股不串号；
- [ ] Backend 暂停时，不得显示“账号已同步”；
- [ ] Backend 恢复后，本地变更可以重新同步。

测试完成后可以通过页面恢复为空列表，不得直接修改 SQLite 数据库。

### 10.5 宏观事件概率

- [ ] 宏观事件列表能够加载；
- [ ] 事件分类、标题和概率曲线能够显示；
- [ ] 显示实际 Provider、上游时间和 Platform 抓取时间；
- [ ] 暂无数据与接口错误能够区分；
- [ ] 单一事件失败不会导致整个宏观页面白屏；
- [ ] 页面不把研究概率用于执行、风控或会计权威输入。

### 10.6 响应式与视觉

使用 Chrome 开发者工具的设备模拟，分别检查：

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

保存到仓库外：

```powershell
$ManualScreenshots = Join-Path $EvidenceDir "manual-screenshots"
New-Item -ItemType Directory -Path $ManualScreenshots -Force | Out-Null
```

检查：

- [ ] 无页面级横向溢出；
- [ ] 需要横向滚动的表格只在表格容器内滚动；
- [ ] 窄屏导航抽屉没有遮挡主体；
- [ ] 数值右对齐，名称左对齐；
- [ ] 空值统一显示为“—”；
- [ ] 红涨绿跌符合平台约定；
- [ ] 筛选、应用、复制、导出和展开按钮容易识别；
- [ ] 无重叠、截断、白屏和明显布局跳动；
- [ ] 390px 下仍能完成申万筛选、自选股和个股查询。

截图前确认没有临时密码、Cookie、CSRF、Token、API Key 或真实客户信息。

## 11. 验收结论标准

### 11.1 通过

同时满足：

1. 仓库、Backend、Runtime 静态检查、前端和两套浏览器 E2E 全部通过；
2. `VG_LIVE_TRADING_ENABLED=false`；
3. 真实 Provider 的实际状态被准确展示；
4. 已知`partial`不会引发整页失败、伪造 0 或覆盖 Last Known Good；
5. 申万、阈值、个股链接和自选股人工检查通过；
6. 四档响应式没有 P0/P1 问题；
7. 验收前后没有任何受 Git 跟踪文件变化。

### 11.2 有条件通过

仅存在已记录的免费上游可用性问题或少量 P2/P3 缺陷，并且：

- 页面准确标记`partial / stale / error`；
- 可用模块仍可使用；
- 不影响用户系统、权限和自选股持久化；
- 不存在 P0/P1 产品缺陷；
- 所有者明确接受已记录风险。

### 11.3 不通过

出现任一情况即不通过：

- 自动化检查失败；
- 页面白屏、关键交互不可用或 390px 无法操作；
- 来源、时间或状态标记错误；
- 外部错误被伪装为健康或 0；
- 研报、公告、新闻原文链接是假链接或核心链接全部无法打开；
- 自选股跨账号串数据；
- 页面绕过 Platform Backend 直连第三方研究数据源；
- Live Trading 被开启；
- 受 Git 跟踪文件被修改。

缺陷等级：

```text
P0  安全边界、权限、数据串号、Live Write 或整页不可用
P1  核心模块错误、关键数据口径错误、无法完成主要流程
P2  局部交互、状态提示、响应式或部分链接问题
P3  文案、间距、轻微视觉问题
```

## 12. 验收报告模板

在`$EvidenceDir\LOCAL_ACCEPTANCE_RESULT.md`填写：

```markdown
# Platform 0.9.1 本地验收结果

- 日期：
- 执行人/执行代理：
- 设备与系统：
- 分支：feature/issue-134-platform-0-9-1-unified-delivery
- 验收 HEAD：
- 最低功能验证基线：00574a8f10a3fc3723ae78c97aacbff075ff803b
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
| Runtime Ruff/Type/Test | PASS/FAIL | 文件名 |
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
| 宏观概率 | | | | | |

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

报告不得包含密码、Cookie、CSRF、Token、API Key 或真实客户数据。

## 13. 验收结束检查与清理

先关闭手工启动的 Backend 和 Frontend 窗口，再检查：

```powershell
Set-Location $AcceptRoot

git status --porcelain=v1 --untracked-files=no |
  Tee-Object -FilePath (Join-Path $EvidenceDir "git-status-after.txt")

git diff --exit-code
if ($LASTEXITCODE -ne 0) { throw "存在未提交的受跟踪文件变化" }

git diff --cached --exit-code
if ($LASTEXITCODE -ne 0) { throw "存在已暂存变化" }
```

安装和测试可能产生`.venv-acceptance`、`node_modules`、`dist`、`.e2e`和测试产物。最终判定要求受 Git 跟踪文件未被修改或暂存。

保存证据后，从源仓库移除独立 worktree：

```powershell
Set-Location $SourceRepo
git worktree remove --force $AcceptRoot
git worktree prune
```

这里的`--force`只用于移除包含未跟踪依赖和测试产物的独立验收 worktree。不得对现有开发目录执行强制清理，也不得使用`git clean -fd`。

## 14. 最终交接输出

本地执行人或本地 AI 最终只需返回：

1. 验收 HEAD；
2. 自动化通过/失败清单；
3. 真实 Provider 与页面状态；
4. 申万、原文链接、自选股和宏观页面结论；
5. 四档响应式结论；
6. P0–P3 缺陷清单；
7. `通过 / 有条件通过 / 不通过`；
8. 是否建议进入 Phase 5；
9. evidence 目录绝对路径。

不得自行修复缺陷、提交代码、推送分支、修改 PR 状态或合并`main`。
