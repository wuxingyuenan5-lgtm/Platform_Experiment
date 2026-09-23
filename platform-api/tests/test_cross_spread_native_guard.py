from decimal import Decimal

from app import cross_spread_limit_execution as module
from app.cross_spread import CrossSpreadLiveSizing
from app.schemas import CrossSpreadMarketCommandRequest


def test_post_only_chase_persists_guard_with_bound_mt5_spec(monkeypatch):
    captured = {}
    sizing = CrossSpreadLiveSizing(
        bybit_account_id="bybit-test",
        mt5_account_id="mt5-bound",
        bybit_min=Decimal("0.01"),
        bybit_step=Decimal("0.01"),
        bybit_max=None,
        mt5_min=Decimal("0.01"),
        mt5_step=Decimal("0.01"),
        mt5_max=None,
        mt5_multiplier=Decimal("100"),
    )
    monkeypatch.setattr(module, "assert_cross_spread_live_execution_enabled", lambda: None)
    monkeypatch.setattr(module, "_load_live_cross_spread_sizing", lambda: sizing)
    monkeypatch.setattr(
        module,
        "create_instruction",
        lambda *args, **kwargs: captured.update(request=args[1]) or {"instructionId": "i"},
    )
    monkeypatch.setattr(module, "execute_instruction", lambda _: "batch")

    result = module.submit_cross_spread_limit_command(
        CrossSpreadMarketCommandRequest(action="OPEN_LONG", quantityOz=Decimal("1")),
        bybit_limit_price=Decimal("2350"),
        target_spread=Decimal("-10"),
        max_adverse_spread=Decimal("5"),
        limit_strategy="post_only_chase",
        idempotency_key="guard-test",
    )

    guard = captured["request"].parameters["crossSpreadGuard"]
    assert result == "batch"
    assert guard == {
        "targetSpread": Decimal("-10"),
        "maxAdverseSpread": Decimal("5"),
        "mt5AccountId": "mt5-bound",
        "mt5Symbol": "XAUUSD.s",
        "mt5Close": False,
        "mt5MinQuantity": Decimal("0.01"),
        "mt5QuantityStep": Decimal("0.01"),
        "mt5ContractMultiplier": Decimal("100"),
    }


def test_fok_does_not_create_guard(monkeypatch):
    captured = {}
    sizing = CrossSpreadLiveSizing(
        "bybit",
        "mt5",
        Decimal(".01"),
        Decimal(".01"),
        None,
        Decimal(".01"),
        Decimal(".01"),
        None,
        Decimal("100"),
    )
    monkeypatch.setattr(module, "assert_cross_spread_live_execution_enabled", lambda: None)
    monkeypatch.setattr(module, "_load_live_cross_spread_sizing", lambda: sizing)
    monkeypatch.setattr(
        module,
        "create_instruction",
        lambda *args, **kwargs: captured.update(request=args[1]) or {"instructionId": "i"},
    )
    monkeypatch.setattr(module, "execute_instruction", lambda _: "batch")
    module.submit_cross_spread_limit_command(
        CrossSpreadMarketCommandRequest(action="OPEN_LONG", quantityOz=Decimal("1")),
        bybit_limit_price=Decimal("2350"),
        limit_strategy="fok",
        idempotency_key="fok-test",
    )
    assert "crossSpreadGuard" not in captured["request"].parameters
