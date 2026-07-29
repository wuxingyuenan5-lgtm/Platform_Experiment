# 用户系统本地集成交接

状态：`handoff ready`

- 仓库：`wuxingyuenan5-lgtm/Platform_Experiment`
- 交付分支：`feature/issue-117-user-system`
- 基线：`main@71603bcc6807284ef3a6da26ad3f43c541bc99c2`
- 交付原则：不由本分支直接合并 `main`；由项目负责人在本地项目中完成合并和冲突处理。

## 已交付范围

- 浏览器注册、登录、退出、密码修改和一次性密码重置凭证。
- HttpOnly Cookie Session、CSRF/Origin 校验和 Session 撤销。
- 固定业务角色：CEO、技术负责人、员工、会员。
- 用户列表、搜索、筛选、详情、状态与角色管理。
- 运营备注，且备注正文不进入会员端或审计详情。
- 会员基金持仓、单位净值、资产估值和收益展示。
- 8 个可复用测试账号初始化能力：1 个 CEO、1 个技术负责人、3 个员工、3 个 VIP。
- 用户数据、Session、持仓、NAV 与头像的备份/恢复边界。
- Human Session 与 API Key、Live Write 的权限隔离。

## 自动化验收结果

交付 HEAD `242cc03966bc437da08dd6a35b448d09ebc0c932` 已通过：

- Platform CI：`30374949395`
- User System Browser E2E：`30374950288`
- Secret Scan：`30374949706`
- Version Consistency：`30374949357`
- Platform Backend：403 项测试通过

浏览器 E2E 实际覆盖固定 8 个账号逐一登录、角色校验、CEO 编辑 VIP 运营备注、3 个 VIP 资产视图，以及注册审批、头像、CSRF、修改密码和其他设备 Session 失效。

## 本地合并

```bash
git fetch origin feature/issue-117-user-system
git switch <你的本地目标分支>
git merge --no-ff origin/feature/issue-117-user-system
```

合并后建议立即执行：

```bash
cd platform-backend
python -m pip install -e '.[dev]'
python -m ruff check app tests
python -m pyright
python -m pytest -m "architecture or unit or integration or live_safety"

cd ../admin-risk
pnpm install --frozen-lockfile
pnpm test:user-system
pnpm exec vue-tsc -p tsconfig.user-system.json --noEmit --skipLibCheck
pnpm build
```

若本地项目已经修改认证、路由、用户页面、数据库迁移或 `platform-ci.yml`，优先人工处理这些文件的冲突，不要简单选择整文件覆盖。

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

## 不属于本地代码合并的事项

以下仅在准备正式生产部署时执行，不阻塞本地集成：

- HTTPS 同源反向代理与 Secure Cookie 实机验证。
- 受控主机 Backup、Restore Drill、只读恢复启动与回退演练。
- 确认旧 Go/MySQL 是否存在需要迁移的真实用户。
- 确认首批正式持仓的数据来源。
- 确认生产继续采用同源 `/api/v1`。

## 安全边界

- 不要在生产环境初始化 `demo_*` 账号。
- 不要把密码、Cookie、CSRF、重置凭证或真实客户数据写入 Git、日志和截图。
- 合并用户系统不等于开启 Platform Live Write 或 Runtime Live Write。
- 本交付分支保持独立，不在 GitHub 上合并 `main`。
