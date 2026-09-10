from decimal import Decimal

import pytest

from app.config import Settings, get_settings
from app.gateway_errors import GatewayConfigurationError
from app.journal import initialize_journal
from app.live_safety import validate_live_write
from app.models import SubmitOrderCommand


def command(command_id: str = "cmd-live-1", quantity: str = "1") -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id=command_id,
        platform_order_id=f"order-{command_id}",
        strategy_instance_id="strategy-live-1",
        account_id="account-live-1",
        instrument_id="instrument-xau",
        symbol="XAUTUSDT",
        side="buy",
        order_type="market",
        quantity=quantity,
    )


def settings(**overrides) -> Settings:
    values = {
        "environment": "live",
        "live_write_enabled": True,
        "live_account_allowlist": "account-live-1",
        "live_strategy_allowlist": "strategy-live-1",
        "live_symbol_allowlist": "XAUTUSDT",
        "live_max_order_notional": Decimal("2000"),
        "live_max_daily_notional": Decimal("2500"),
    }
    values.update(overrides)
    return Settings(**values)


def test_live_write_is_disabled_by_default(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "live-disabled.db")
    initialize_journal()
    with pytest.raises(GatewayConfigurationError, match="live write gate is disabled"):
        validate_live_write(
            command(),
            adapter="bybit_live",
            reference_price=Decimal("1000"),
            settings=settings(live_write_enabled=False),
        )


def test_live_write_requires_writable_account(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "live-allowlist.db")
    initialize_journal()
    with pytest.raises(GatewayConfigurationError, match="Account"):
        validate_live_write(
            command(),
            adapter="bybit_live",
            reference_price=Decimal("1000"),
            settings=settings(live_account_allowlist="other-account"),
        )


def test_live_write_claim_is_idempotent_without_legacy_daily_cap(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "live-claim.db")
    initialize_journal()
    configured = settings()
    first = validate_live_write(
        command(),
        adapter="bybit_live",
        reference_price=Decimal("1000"),
        settings=configured,
    )
    repeated = validate_live_write(
        command(),
        adapter="bybit_live",
        reference_price=Decimal("1000"),
        settings=configured,
    )
    assert first.already_claimed is False
    assert repeated.already_claimed is True
    assert repeated.notional == Decimal("1000")

    next_claim = validate_live_write(
        command(command_id="cmd-live-2", quantity="20"),
        adapter="bybit_live",
        reference_price=Decimal("1000"),
        settings=configured,
    )
    assert next_claim.notional == Decimal("20000")
    assert not next_claim.already_claimed


def test_live_write_without_legacy_notional_caps(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "live-nocap.db")
    initialize_journal()
    claim = validate_live_write(
        command(command_id="cmd-live-nocap", quantity="5"),
        adapter="bybit_live",
        reference_price=Decimal("1000"),
        settings=settings(
            live_max_order_notional=Decimal("0"),
            live_max_daily_notional=Decimal("0"),
        ),
    )
    assert claim.already_claimed is False
    assert claim.notional == Decimal("5000")


def test_legacy_strategy_and_symbol_lists_do_not_limit_normal_trading(tmp_path):
    get_settings().journal_path = str(tmp_path / "normal-scope.db")
    initialize_journal()
    request = command().model_copy(update={
        "strategy_instance_id": "strategy_funding_arbitrage_instance_default",
        "symbol": "BTCUSDT", "instrument_id": "instrument_btc_usdt",
    })
    claim = validate_live_write(
        request, adapter="bybit_live", reference_price=Decimal("60000"), settings=settings()
    )
    assert claim.notional == Decimal("60000")
    with pytest.raises(GatewayConfigurationError, match="payload"):
        validate_live_write(
            request.model_copy(update={"quantity": Decimal("2")}),
            adapter="bybit_live", reference_price=Decimal("60000"), settings=settings(),
        )
