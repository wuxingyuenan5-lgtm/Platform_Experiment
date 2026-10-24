"""Closed native XAUUSD D1 bars through the existing fixed-account Worker."""

from datetime import UTC, datetime

from app.gateway_errors import GatewayConfigurationError, GatewayResultUnknownError
from app.mt5_read_coordinator import with_mt5_read_session
from app.mt5_symbol_resolver import resolve_mt5_symbol


def read_daily_rates(adapter, *, account_id, count=1500):
    if not 1 <= count <= 2000 or adapter.settings.live_write_enabled:
        raise GatewayConfigurationError("MT5 daily research is bounded and yields to Live Write")
    adapter._assert_account(account_id)
    mt5 = adapter._connect()

    def read(_session):
        info, terminal = mt5.account_info(), mt5.terminal_info()
        if info is None or terminal is None or not terminal.connected:
            raise GatewayResultUnknownError("MT5 daily source disconnected")
        resolution = resolve_mt5_symbol(
            mt5_module=mt5,
            base_symbol="XAUUSD",
            preferred="XAUUSD",
            cache_key=(str(info.login), str(info.server)),
        )
        if resolution is None:
            raise GatewayConfigurationError("MT5 XAUUSD unavailable")
        # Position zero is the forming bar. Never infer daily closes from sampled ticks.
        rates = mt5.copy_rates_from_pos(resolution.symbol, mt5.TIMEFRAME_D1, 1, count)
        if rates is None or not len(rates) or len(rates) > count:
            raise GatewayResultUnknownError("MT5 closed daily history unavailable")
        return {
            "schemaVersion": "mt5-daily-bars.v1",
            "symbol": resolution.symbol,
            "server": str(info.server),
            "broker": str(info.company),
            "timeframe": "D1",
            "closedOnly": True,
            "startPosition": 1,
            "rows": [{key: str(row[key]) for key in rates.dtype.names} for row in rates],
            "retrievedAt": datetime.now(UTC).isoformat(),
        }

    return with_mt5_read_session(
        mt5=mt5, settings=adapter.settings, account_id=account_id, callback=read
    )
