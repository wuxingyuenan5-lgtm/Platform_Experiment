from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.config import get_settings
from app.database import initialize_database
from app.schema_migrations import apply_platform_migrations
from app.user_demo_seed import seed_demo_users
from app.user_product_migrations import apply_user_product_migrations

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_E2E_ROOT = _REPOSITORY_ROOT / ".e2e" / "user-system"


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for the user-system E2E bootstrap")
    return value


def _assert_e2e_path(path: Path, *, label: str) -> Path:
    resolved_root = _E2E_ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise RuntimeError(f"{label} must remain under {resolved_root}")
    return resolved_path


def _reset_test_data() -> None:
    if os.environ.get("USER_SYSTEM_E2E_RESET") != "1":
        return
    if _E2E_ROOT.is_symlink():
        raise RuntimeError("Refusing to reset a symlinked user-system E2E root")
    if _E2E_ROOT.exists():
        shutil.rmtree(_E2E_ROOT)


def main() -> int:
    settings = get_settings()
    database_path = _assert_e2e_path(Path(settings.database_path), label="VG_DATABASE_PATH")
    avatar_directory = _assert_e2e_path(
        Path(settings.avatar_data_directory),
        label="VG_AVATAR_DATA_DIRECTORY",
    )

    _reset_test_data()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    avatar_directory.mkdir(parents=True, exist_ok=True)

    initialize_database()
    apply_platform_migrations()
    apply_user_product_migrations()

    password = _required_environment("E2E_CEO_PASSWORD")
    accounts = seed_demo_users(
        password=password,
        prefix="e2e",
        refresh_existing=True,
    )
    print("Seeded isolated reusable user-system accounts:")
    for account in accounts:
        print(f"- {account.username}: {account.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
