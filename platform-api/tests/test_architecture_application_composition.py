from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[1]
APPLICATION = ROOT / "app" / "application.py"
MAIN = ROOT / "app" / "main.py"


def test_application_is_a_bounded_composition_root() -> None:
    source = APPLICATION.read_text(encoding="utf-8")

    assert len(source.splitlines()) <= 150
    assert "@app." not in source
    assert "@application." not in source
    assert "db.execute(" not in source
    assert "SELECT " not in source
    assert "httpx." not in source
    assert "Decimal(" not in source
    assert "create_system_router(settings, PLATFORM_VERSION)" in source
    assert "create_catalog_router(settings.api_prefix)" in source
    assert "create_trading_router(settings.api_prefix)" in source
    assert "AuthenticationMiddleware" in source
    assert "UserNoStoreMiddleware" in source


def test_main_is_only_the_asgi_export_boundary() -> None:
    source = MAIN.read_text(encoding="utf-8")

    assert source == 'from app.application import app\n\n__all__ = ["app"]\n'
