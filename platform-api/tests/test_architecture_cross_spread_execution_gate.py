from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.cross_spread import (
    _cross_spread_live_execution_gate_allows_write,
    submit_cross_spread_market_command,
)
from app.schemas import CrossSpreadMarketCommandRequest


@pytest.mark.parametrize(
    ("environment", "default_environment", "live_enabled"),
    list(
        product(
            ["development", "test", "live"],
            ["simulation", "paper", "live"],
            [False, True],
        )
    ),
)
def test_cross_spread_write_gate_depends_only_on_explicit_live_flag(
    monkeypatch,
    environment: str,
    default_environment: str,
    live_enabled: bool,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", environment)
    monkeypatch.setattr(settings, "default_trading_environment", default_environment)
    monkeypatch.setattr(settings, "live_trading_enabled", live_enabled)

    assert _cross_spread_live_execution_gate_allows_write(settings) is live_enabled


@pytest.mark.parametrize(
    ("environment", "default_environment"),
    list(product(["development", "test", "live"], ["simulation", "paper", "live"])),
)
def test_all_cross_spread_combinations_fail_closed_without_live_write(
    monkeypatch,
    tmp_path: Path,
    environment: str,
    default_environment: str,
) -> None:
    settings = get_settings()
    settings.database_path = str(
        tmp_path / f"cross-spread-{environment}-{default_environment}.db"
    )
    monkeypatch.setattr(settings, "environment", environment)
    monkeypatch.setattr(settings, "default_trading_environment", default_environment)
    monkeypatch.setattr(settings, "live_trading_enabled", False)
    monkeypatch.setattr(settings, "auth_mode", "development")

    with pytest.raises(HTTPException) as exc_info:
        submit_cross_spread_market_command(
            CrossSpreadMarketCommandRequest(action="OPEN_LONG", quantityOz="1")
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Live cross-spread execution is disabled"


def test_cross_spread_source_has_no_contradictory_live_gate_branch() -> None:
    source = (Path(__file__).resolve().parents[1] / "app/cross_spread.py").read_text(
        encoding="utf-8"
    )
    assert "_cross_spread_execution_gate_allows_simulation" not in source
    assert "and not settings.live_trading_enabled" not in source
    assert "CrossSpreadLiveSizing(\n            bybit_min=Decimal(\"0.001\")" not in source
