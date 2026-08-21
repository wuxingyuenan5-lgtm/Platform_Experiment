from decimal import Decimal

from app.cross_spread_exit_policy import (
    evaluate_exit_threshold,
    select_executable_close_spread,
)


def test_long_spread_uses_short_quote_and_closes_higher_for_profit() -> None:
    close_spread = select_executable_close_spread(
        "LONG_SPREAD",
        long_spread=Decimal("-2.0"),
        short_spread=Decimal("-0.5"),
    )
    assert close_spread == Decimal("-0.5")
    assert (
        evaluate_exit_threshold(
            "LONG_SPREAD",
            close_spread=Decimal("0.2"),
            take_profit_spread=Decimal("0"),
            stop_loss_spread=Decimal("-3"),
        )
        == "take_profit"
    )
    assert (
        evaluate_exit_threshold(
            "LONG_SPREAD",
            close_spread=Decimal("-3.2"),
            take_profit_spread=Decimal("0"),
            stop_loss_spread=Decimal("-3"),
        )
        == "stop_loss"
    )


def test_short_spread_uses_long_quote_and_closes_lower_for_profit() -> None:
    close_spread = select_executable_close_spread(
        "SHORT_SPREAD",
        long_spread=Decimal("-3.1"),
        short_spread=Decimal("-1.0"),
    )
    assert close_spread == Decimal("-3.1")
    assert (
        evaluate_exit_threshold(
            "SHORT_SPREAD",
            close_spread=Decimal("-3.1"),
            take_profit_spread=Decimal("-3"),
            stop_loss_spread=Decimal("0"),
        )
        == "take_profit"
    )
    assert (
        evaluate_exit_threshold(
            "SHORT_SPREAD",
            close_spread=Decimal("0.2"),
            take_profit_spread=Decimal("-3"),
            stop_loss_spread=Decimal("0"),
        )
        == "stop_loss"
    )


def test_exit_threshold_returns_none_when_take_profit_and_stop_loss_are_not_configured() -> None:
    assert (
        evaluate_exit_threshold(
            "LONG_SPREAD",
            close_spread=Decimal("-0.2"),
            take_profit_spread=None,
            stop_loss_spread=None,
        )
        is None
    )
    assert (
        evaluate_exit_threshold(
            "SHORT_SPREAD",
            close_spread=Decimal("-2.5"),
            take_profit_spread=None,
            stop_loss_spread=None,
        )
        is None
    )
