from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"expected one target in {path}, found {count}: {old[:100]!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


plan = Path("docs/planning/V6-Production-Gate-监控备份恢复.md")
replace_once(plan, "更新时间：`2026-07-24`", "更新时间：`2026-07-28`")
replace_once(
    plan,
    "- Runtime Journal SQLite Database。\n- Redacted `manifest.json`。\n",
    "- Runtime Journal SQLite Database。\n- 用户头像安全归档 `avatars.zip`。\n- Redacted `manifest.json`。\n",
)
replace_once(
    plan,
    "- SHA-256、sizeBytes、`PRAGMA integrity_check`。\n- 关键 Table Count。\n- Safe Restore Defaults。\n",
    "- SHA-256、sizeBytes、`PRAGMA integrity_check`。\n"
    "- 关键 Table Count，包括用户、Session、重置凭证、基金、持仓和 NAV。\n"
    "- 头像文件数与总字节数；不在 Manifest 暴露头像文件名。\n"
    "- Safe Restore Defaults。\n",
)
replace_once(
    plan,
    "4. 执行 `PRAGMA integrity_check`。\n"
    "5. 核对关键 Table Count。\n"
    "6. 在恢复副本中强制 Global Kill Switch enabled。\n"
    "7. 生成 `safe-startup.env`：Platform/Runtime Live Write false、allowlist 空、limit 为零。\n"
    "8. 确认 Production Paths 未被修改。\n",
    "4. 执行 `PRAGMA integrity_check`。\n"
    "5. 核对关键 Table Count。\n"
    "6. 安全解压头像归档，核对文件数和总字节数，并拒绝路径穿越、软链接、重复或异常文件。\n"
    "7. 在恢复副本中强制 Global Kill Switch enabled。\n"
    "8. 生成 `safe-startup.env`：Platform/Runtime Live Write false、allowlist 空、limit 为零。\n"
    "9. 确认 Production Paths 未被修改。\n",
)
replace_once(
    plan,
    "VG_RUNTIME_JOURNAL_PATH=../execution-runtime/data/runtime_journal.db\n"
    "VG_OPERATIONS_BACKUP_ROOT=./data/backups\n",
    "VG_RUNTIME_JOURNAL_PATH=../execution-runtime/data/runtime_journal.db\n"
    "VG_AVATAR_DATA_DIRECTORY=./data/avatars\n"
    "VG_OPERATIONS_BACKUP_ROOT=./data/backups\n",
)
replace_once(
    plan,
    "- [x] Platform/Runtime 使用 SQLite Online Backup。\n"
    "- [x] Manifest 包含 checksum、size、integrity 和关键计数。\n"
    "- [x] Restore Drill 使用新目录并核对 checksum/count/integrity。\n",
    "- [x] Platform/Runtime 使用 SQLite Online Backup。\n"
    "- [x] 用户头像使用受限根目录归档，异常目录项 fail-closed。\n"
    "- [x] Manifest 包含 checksum、size、integrity、用户域关键计数和头像统计。\n"
    "- [x] Restore Drill 使用新目录并核对 checksum/count/integrity 与头像归档。\n",
)
replace_once(
    plan,
    "- [ ] 受控主机确认活动 Platform DB 与 Runtime Journal 路径。\n"
    "- [ ] 设置独立 Backup/Restore Root。\n"
    "- [ ] 手工执行一次健康扫描、Backup 和 Restore Drill。\n"
    "- [ ] 核对 Manifest、Checksum、Integrity、Table Count。\n",
    "- [ ] 受控主机确认活动 Platform DB、Runtime Journal 与头像目录路径。\n"
    "- [ ] 设置独立 Backup/Restore Root。\n"
    "- [ ] 手工执行一次健康扫描、Backup 和 Restore Drill。\n"
    "- [ ] 核对 Manifest、Checksum、Integrity、用户域 Table Count 和头像统计。\n",
)

auth = Path("docs/technical/AUTH_RBAC_LIVE_SESSIONS.md")
replace_once(
    auth,
    "- Draft PR #118 的 Repository Safety、Backend、Runtime 和 Frontend 全矩阵已通过；\n"
    "- Backend Ruff、Pyright 与 398 项分类 Pytest 已通过；\n"
    "- 前端权限/Decimal 测试、ESLint、无新增债务检查、两套类型检查和生产构建已通过；\n"
    "- Version Consistency 与 Secret Scan 已通过；\n"
    "- 仍需完成真实浏览器同源验收、Cookie Secure/反向代理验证、备份恢复演练和三项生产切换决策。\n",
    "- Draft PR #118 的 Repository Safety、Backend、Runtime 和 Frontend 全矩阵已通过；\n"
    "- Backend Ruff、Pyright 与 399 项分类 Pytest 已通过；\n"
    "- 前端权限/Decimal 测试、ESLint、无新增债务检查、两套类型检查和生产构建已通过；\n"
    "- Version Consistency 与 Secret Scan 已通过；\n"
    "- 用户域 Table Count 与头像归档/恢复已纳入现有生产灾备自动化；\n"
    "- 浏览器验收入口：`../operations/USER_SYSTEM_BROWSER_ACCEPTANCE.md`；\n"
    "- 部署、SQLite/头像恢复入口：`../operations/USER_SYSTEM_DEPLOYMENT_READINESS.md`；\n"
    "- 仍需在受控主机完成浏览器同源验收、Cookie Secure/反向代理验证、备份恢复演练和三项生产切换决策。\n",
)

for path in (plan, auth):
    text = path.read_text(encoding="utf-8")
    path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8")
