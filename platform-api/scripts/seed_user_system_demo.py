from __future__ import annotations

import os

from app.config import get_settings
from app.database import initialize_database
from app.schema_migrations import apply_platform_migrations
from app.user_product_migrations import apply_user_product_migrations
from user_demo_seed import seed_demo_users


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _assert_safe_environment() -> None:
    settings = get_settings()
    if os.environ.get("USER_SYSTEM_DEMO_SEED") != "1":
        raise RuntimeError("Set USER_SYSTEM_DEMO_SEED=1 to confirm demo account creation")
    if settings.environment.casefold() not in {"development", "local", "test", "testing"}:
        raise RuntimeError("Demo accounts may only be seeded in development or test environments")
    if settings.live_trading_enabled:
        raise RuntimeError("Refusing to seed demo accounts while Platform Live Trading is enabled")


def main() -> int:
    _assert_safe_environment()
    password = _required_environment("USER_SYSTEM_DEMO_PASSWORD")
    prefix = os.environ.get("USER_SYSTEM_DEMO_PREFIX", "demo").strip() or "demo"
    refresh_existing = os.environ.get("USER_SYSTEM_DEMO_REFRESH") == "1"

    initialize_database()
    apply_platform_migrations()
    apply_user_product_migrations()
    accounts = seed_demo_users(
        password=password,
        prefix=prefix,
        refresh_existing=refresh_existing,
    )

    print("Reusable user-system demo accounts are ready:")
    for account in accounts:
        state = "created" if account.created else "refreshed" if account.refreshed else "kept"
        print(f"- {account.username:<24} {account.role:<10} {state}")
    print("Password source: USER_SYSTEM_DEMO_PASSWORD (not stored in source control)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
