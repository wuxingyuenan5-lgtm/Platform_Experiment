"""Bounded tick interval reader used inside the already owned account Worker."""

from datetime import UTC, datetime

from app.gateway_errors import GatewayConfigurationError, GatewayResultUnknownError
from app.mt5_read_coordinator import with_mt5_read_session
from app.mt5_symbol_resolver import resolve_mt5_symbol


def read_ticks(adapter, *, account_id, symbol, start, end, historical=False):
    limit = 300 if historical else 1
    if (
        start.tzinfo is None
        or end.tzinfo is None
        or not 0 <= (end - start).total_seconds() <= limit
    ):
        raise GatewayConfigurationError("research tick window exceeds its bounded interval")
    adapter._assert_account(account_id)
    mt5 = adapter._connect()

    def read(_session):
        info = mt5.account_info()
        terminal = mt5.terminal_info()
        if info is None or terminal is None or not terminal.connected:
            raise GatewayResultUnknownError("MT5 research source disconnected")
        resolution = resolve_mt5_symbol(
            mt5_module=mt5,
            base_symbol=symbol,
            preferred=symbol,
            cache_key=(str(info.login), str(info.server)),
        )
        if resolution is None:
            raise GatewayConfigurationError("MT5 research symbol unavailable")
        native = resolution.symbol
        ticks = mt5.copy_ticks_range(
            native, start.astimezone(UTC), end.astimezone(UTC), mt5.COPY_TICKS_ALL
        )
        if ticks is None:
            raise GatewayResultUnknownError("MT5 tick range unavailable")
        if len(ticks) > 20000:
            raise GatewayConfigurationError("MT5 tick window exceeds research budget")
        spec = mt5.symbol_info(native)
        fields = (
            "swap_long",
            "swap_short",
            "swap_mode",
            "swap_rollover3days",
            "point",
            "digits",
            "trade_contract_size",
            "currency_profit",
            "volume_min",
            "volume_step",
            "volume_max",
            "trade_tick_size",
        )
        # Numeric SDK values remain their observed repr. No inferred extra precision.
        rows = [{key: str(row[key]) for key in ticks.dtype.names} for row in ticks]
        return {
            "symbol": native,
            "server": str(info.server),
            "broker": str(info.company),
            "instrumentId": adapter.settings.mt5_instruments.get(native.upper()),
            "specification": {
                key: str(getattr(spec, key))
                for key in fields
                if getattr(spec, key, None) is not None
            },
            "ticks": rows,
            "readCompletedAt": datetime.now(UTC).isoformat(),
            "timeConversionVersion": None,
            "timeQuality": "clock_unverified",
            "dedupLimit": "identical native records have no global tick id",
        }

    return with_mt5_read_session(
        mt5=mt5, settings=adapter.settings, account_id=account_id, callback=read
    )
