# 用户系统固定演示账号

状态：仅用于本地、测试和验收环境；不得在生产环境初始化。

## 默认账号

| 角色 | 用户名 |
| --- | --- |
| CEO | `demo_ceo` |
| 技术负责人 | `demo_tech` |
| 员工 1 | `demo_employee_1` |
| 员工 2 | `demo_employee_2` |
| 员工 3 | `demo_employee_3` |
| VIP 1 | `demo_vip_1` |
| VIP 2 | `demo_vip_2` |
| VIP 3 | `demo_vip_3` |

三个 VIP 账号会自动写入不同的演示持仓和收益数据，用于验证会员账户页面。

## 初始化

在 `platform-api` 目录设置环境变量后运行：

```bash
export VG_ENVIRONMENT=development
export VG_LIVE_TRADING_ENABLED=false
export USER_SYSTEM_DEMO_SEED=1
export USER_SYSTEM_DEMO_PASSWORD='自行设置的统一临时密码'
python scripts/seed_user_system_demo.py
```

密码只从 `USER_SYSTEM_DEMO_PASSWORD` 读取，不写入代码、数据库日志或文档。

## 后续改名或统一改密

默认重复运行只补齐缺失数据，不覆盖已经人工修改的账号。需要统一更新时：

```bash
export USER_SYSTEM_DEMO_PREFIX=pilot
export USER_SYSTEM_DEMO_PASSWORD='新的统一临时密码'
export USER_SYSTEM_DEMO_REFRESH=1
python scripts/seed_user_system_demo.py
```

上述示例会把账号前缀由 `demo` 改为 `pilot`，并统一更新密码，同时撤销这些账号的旧 Session。

单个用户密码也可以通过后台的一次性重置凭证流程修改。

## 安全限制

初始化脚本会拒绝以下情况：

- 未显式设置 `USER_SYSTEM_DEMO_SEED=1`；
- 环境不是 development、local、test 或 testing；
- Platform Live Write 已启用。
