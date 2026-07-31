# Platform 0.9.1 用户系统集成交接

状态：`validation / handoff ready after green CI`

- 仓库：`wuxingyuenan5-lgtm/Platform_Experiment`
- 交付分支：`feature/issue-117-platform-0-9-1`
- 产品版本：`0.9.1`
- 基线：`main@a4e22021c71cf5cd703cb0bc35676ff5adbfec36`
- 交付原则：该分支已经包含最新上传 `main` 与用户系统的融合结果，不在 GitHub 上合并 `main`。

## 已交付范围

- 保留最新 `main` 的对冲基金看板、资金费、跨所价差、Runtime 和统一启动体系。
- 浏览器注册、登录、退出、密码修改和一次性密码重置凭证。
- HttpOnly Cookie Session、CSRF/Origin 校验和 Session 撤销。
- 固定业务角色：CEO、技术负责人、员工、会员。
- 用户列表、搜索、筛选、详情、状态与角色管理。
- 运营备注，且备注正文不进入会员端或审计详情。
- 会员基金持仓、单位净值、资产估值和收益展示。
- 8 个可复用测试账号初始化能力：1 个 CEO、1 个技术负责人、3 个员工、3 个 VIP。
- 用户数据、Session、持仓、NAV 与头像的备份/恢复边界。
- Human Session 与 API Key、Live Write 的权限隔离。

## 获取完整 0.9.1 项目

该分支已经是完整平台版本，不需要再次把旧用户系统分支手动合入本地新版项目。

```bash
git fetch origin feature/issue-117-platform-0-9-1
git switch -c platform-0.9.1 --track origin/feature/issue-117-platform-0-9-1
```

如果希望保留当前本地分支名称，也可以：

```bash
git switch <你的本地目标分支>
git merge --no-ff origin/feature/issue-117-platform-0-9-1
```

合并前必须先提交或备份本地未提交改动，不要使用 `git reset --hard origin/main` 或 `git clean -fd`。

## 本地验证

仓库根目录：

```bash
python scripts/check-documentation-consistency.py
python scripts/check-repository-structure.py
python scripts/check-version-consistency.py
python scripts/check-codex-context.py
python scripts/scan-secrets.py
```

后端：

```bash
cd platform-backend
python -m pip install -e '.[dev]'
python -m pip check
python -m ruff check app tests
python -m pyright
python -m pytest -m "architecture or unit or integration or live_safety"
```

Runtime：

```bash
cd ../execution-runtime
python -m pip install -e '.[dev]'
python -m pip check
python -m ruff check app tests
python -m pyright
python -m pytest -m "architecture or unit or integration or live_safety"
```

前端：

```bash
cd ../platform-web
pnpm install --frozen-lockfile
pnpm test:user-system
pnpm test:homepage-layout
pnpm test:hedge-board-layout
pnpm test:funding-order-layout
pnpm test:cross-spread-layout
pnpm exec vue-tsc -p tsconfig.user-system.json --noEmit --skipLibCheck
pnpm type:check
pnpm build
pnpm test:e2e:user-system
```

## 初始化固定测试账号

固定账号只允许在本地、开发或测试环境初始化。密码通过环境变量提供，不写入仓库。

```bash
cd platform-backend
export VG_ENVIRONMENT=development
export VG_LIVE_TRADING_ENABLED=false
export USER_SYSTEM_DEMO_SEED=1
export USER_SYSTEM_DEMO_PASSWORD='自行设置的统一临时密码'
python scripts/seed_user_system_demo.py
```

默认用户名：

- `demo_ceo`
- `demo_tech`
- `demo_employee_1`
- `demo_employee_2`
- `demo_employee_3`
- `demo_vip_1`
- `demo_vip_2`
- `demo_vip_3`

后续可通过后台逐个修改，也可使用 `USER_SYSTEM_DEMO_PREFIX`、`USER_SYSTEM_DEMO_PASSWORD` 和 `USER_SYSTEM_DEMO_REFRESH=1` 统一改名、改密并撤销旧 Session。

## 生产前仍需完成

以下仅在准备正式生产部署时执行，不阻塞本地代码使用：

- HTTPS 同源反向代理与 Secure Cookie 实机验证。
- 受控主机 Backup、Restore Drill、只读恢复启动与回退演练。
- 确认旧 Go/MySQL 是否存在需要迁移的真实用户。
- 确认首批正式持仓的数据来源。
- 确认生产继续采用同源 `/api/v1`。
- 完成真实 Windows、Bybit 与 MT5 受控验收。

## 安全边界

- 不要在生产环境初始化 `demo_*` 账号。
- 不要把密码、Cookie、CSRF、重置凭证或真实客户数据写入 Git、日志和截图。
- 用户系统不等于开启 Platform Live Write 或 Runtime Live Write。
- 本交付分支保持独立，不在 GitHub 上合并 `main`。
