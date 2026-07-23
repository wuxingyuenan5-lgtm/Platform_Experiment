from __future__ import annotations

from decimal import Decimal

from app.config import Settings
from app.gateway_errors import GatewayConfigurationError
from app.live_route_store import LiveOrderRoute, LiveWriteClaim, claim_live_write
from app.models import SubmitOrderCommand


def validate_live_write(
    command: SubmitOrderCommand,
    *,
    adapter: str,
    reference_price: Decimal,
    settings: Settings,
) -> LiveWriteClaim:
    if settings.environment.lower() != "live":
        raise GatewayConfigurationError("Runtime environment is not live")
    if not settings.live_write_enabled:
        raise GatewayConfigurationError("Runtime live write gate is disabled")
    if command.strategy_instance_id is None:
        raise GatewayConfigurationError("Live command has no StrategyInstance identity")
    if command.account_id not in settings.allowed_live_accounts:
        raise GatewayConfigurationError("Account is not in the live allowlist")
    if command.strategy_instance_id not in settings.allowed_live_strategies:
        raise GatewayConfigurationError("StrategyInstance is not in the live allowlist")
    if command.symbol.upper() not in settings.allowed_live_symbols:
        raise GatewayConfigurationError("Symbol is not in the live allowlist")
    if reference_price <= 0:
        raise GatewayConfigurationError(
            "A positive reference price is required for live risk checks"
        )
    if settings.live_max_order_notional <= 0:
        raise GatewayConfigurationError("Live maximum order notional is not configured")
    if settings.live_max_daily_notional <= 0:
        raise GatewayConfigurationError("Live maximum daily notional is not configured")

    notional = command.quantity * reference_price
    if notional > settings.live_max_order_notional:
        raise GatewayConfigurationError("Live maximum order notional would be exceeded")
    try:
        return claim_live_write(
            command,
            adapter,
            notional,
            settings.live_max_daily_notional,
        )
    except ValueError as exc:
        raise GatewayConfigurationError(str(exc)) from exc


def validate_live_cancel(route: LiveOrderRoute, settings: Settings) -> None:
    if settings.environment.lower() != "live":
        raise GatewayConfigurationError("Runtime environment is not live")
    if not settings.live_write_enabled:
        raise GatewayConfigurationError("Runtime live write gate is disabled")
    if route.account_id not in settings.allowed_live_accounts:
        raise GatewayConfigurationError("Account is not in the live allowlist")
    if route.strategy_instance_id not in settings.allowed_live_strategies:
        raise GatewayConfigurationError("StrategyInstance is not in the live allowlist")
    if route.symbol.upper() not in settings.allowed_live_symbols:
        raise GatewayConfigurationError("Symbol is not in the live allowlist")
