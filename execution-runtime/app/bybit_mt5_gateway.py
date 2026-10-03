from __future__ import annotations

import logging
from concurrent.futures import Future
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Lock
from time import monotonic
from typing import Any, Literal, cast

from app.bybit_live_adapter import BybitLiveAdapter
from app.config import Settings, get_settings
from app.gateway_errors import GatewayConfigurationError, GatewayRequestRejectedError
from app.live_route_store import get_order_route
from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    GatewayAccountCapability,
    GatewayCapabilitiesResponse,
    InternalCapitalTransferReadinessResponse,
    InternalCapitalTransferStepCommand,
    InternalCapitalTransferStepResponse,
    SubmitOrderCommand,
    VenueAccountRiskSnapshot,
    VenueAccountSnapshot,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillHistoryPage,
    VenueFillSnapshot,
    VenueInstrumentSpecification,
    VenueOrderHistoryPage,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)
from app.mt5_account_worker import Mt5AccountWorkerSupervisor
from app.mt5_live_adapter import Mt5LiveAdapter
from app.mt5_read_coordinator import with_mt5_read_session
from app.strict_live_acceptance_adapters import (
    StrictBybitAcceptanceAdapter,
    StrictMt5AcceptanceAdapter,
)

LOG = logging.getLogger(__name__)


class BybitMt5Gateway:
    """Account-routed live gateway with independent Bybit and MT5 adapters."""

    name = "bybit_mt5"
    _QUOTE_CACHE_SECONDS = 1.0
    _MARGIN_CACHE_SECONDS = 15.0

    def __init__(
        self,
        settings: Settings | None = None,
        bybit: BybitLiveAdapter | None = None,
        mt5: Mt5LiveAdapter | None = None,
        mt5_supervisor: Mt5AccountWorkerSupervisor | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.bybit: Any = bybit or StrictBybitAcceptanceAdapter(self.settings)
        self._injected_mt5: Any | None = mt5
        self._mt5_supervisor = (
            None if mt5 is not None else mt5_supervisor or Mt5AccountWorkerSupervisor(self.settings)
        )
        # Keep construction side-effect free. Production MT5 workers are created
        # lazily from the explicit account id on the first account-scoped call.
        self.mt5: Any = mt5 or StrictMt5AcceptanceAdapter(self.settings)
        self._execution_read_cache: dict[tuple[object, ...], tuple[float, Any]] = {}
        self._execution_read_lock = Lock()
        self._execution_reads: dict[tuple[object, ...], Future[Any]] = {}
        self._execution_read_generation: dict[str, int] = {}
        if hasattr(self.bybit, "market_quote_reader"):
            self.bybit.market_quote_reader = lambda **kwargs: self._adapter_for_account(
                kwargs["account_id"]
            ).get_market_quote(**kwargs)

    def warm_live_execution(self) -> None:
        """Pay connection and identity startup costs before the first order.

        This performs authenticated reads only. Startup remains available when
        one configured account cannot warm; that account's own reads and writes
        still fail closed at their normal account-scoped checks.
        """
        for account_id in sorted(self.settings.allowed_live_accounts):
            try:
                if account_id in self.settings.bybit_accounts:
                    self.bybit.get_account_risk(account_id)
                elif account_id in self.settings.mt5_accounts:
                    # Worker startup proves account identity without loading
                    # full history a second time.
                    self._mt5_adapter(account_id).capability()
            except Exception as exc:
                LOG.warning(
                    "Live account warm-up failed for %s (%s); other accounts remain available",
                    account_id,
                    type(exc).__name__,
                )

    def place_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        return self.submit_order(command)

    def get_account(
        self,
        account_id: str,
        *,
        include_history: bool = True,
        history_start: datetime | None = None,
    ) -> VenueAccountSnapshot:
        return self.get_account_snapshot(
            account_id, include_history=include_history, history_start=history_start
        )

    def get_capital_flows(self, *, account_id, start_time, end_time):
        return self._adapter_for_account(account_id).get_capital_flows(
            account_id=account_id, start_time=start_time, end_time=end_time
        )

    def set_bybit_leverage(
        self, *, account_id: str, symbol: str, leverage: Decimal
    ) -> dict[str, object]:
        try:
            return self.bybit.set_leverage(account_id=account_id, symbol=symbol, leverage=leverage)
        finally:
            # Even an uncertain update invalidates old margin estimates. Reads
            # must re-query the venue; the setting is never automatically replayed.
            with self._execution_read_lock:
                self._execution_read_generation[account_id] = (
                    self._execution_read_generation.get(account_id, 0) + 1
                )
                for key in list(self._execution_read_cache):
                    if len(key) > 1 and key[1] == account_id:
                        self._execution_read_cache.pop(key, None)

    def get_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        return self.list_positions(account_id)

    def get_open_orders(
        self,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[VenueOrderSnapshot]:
        return [
            order
            for order in self.list_orders(account_id=account_id, symbol=symbol, limit=limit)
            if order.status in {"accepted", "partially_filled"}
        ][:limit]

    def get_order_history(self, **kwargs) -> VenueOrderHistoryPage:
        return self.query_order_history(**kwargs)

    def get_fill_history(self, **kwargs) -> VenueFillHistoryPage:
        return self.query_fill_history(**kwargs)

    def health(self) -> GatewayCapabilitiesResponse:
        return self.capabilities()

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        adapter = self._adapter_for_account(command.account_id)
        return adapter.submit_order(command)

    def get_order(
        self,
        *,
        platform_order_id: str | None = None,
        external_order_id: str | None = None,
    ) -> VenueOrderSnapshot | None:
        if platform_order_id is not None:
            route = get_order_route(platform_order_id=platform_order_id)
            if route is None:
                return None
            adapter = self._adapter_by_name(route.adapter, account_id=route.account_id)
            return adapter.get_order(platform_order_id=platform_order_id)
        if external_order_id is None:
            raise ValueError("Order identity is required")
        route = get_order_route(external_order_id=external_order_id)
        if route is not None:
            adapter = self._adapter_by_name(route.adapter, account_id=route.account_id)
            return adapter.get_order(external_order_id=external_order_id)
        if external_order_id.isdigit():
            return self.mt5.get_order(external_order_id=external_order_id)
        return self.bybit.get_order(external_order_id=external_order_id)

    def list_orders(
        self,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[VenueOrderSnapshot]:
        if account_id is not None:
            return self._adapter_for_account(account_id).list_orders(
                account_id=account_id, symbol=symbol, limit=limit
            )
        snapshots = [*self.bybit.list_orders(symbol=symbol, limit=limit)]
        for mt5_account_id in sorted(self.settings.mt5_accounts):
            snapshots.extend(
                self._mt5_adapter(mt5_account_id).list_orders(
                    account_id=mt5_account_id, symbol=symbol, limit=limit
                )
            )
        snapshots.sort(key=lambda item: item.as_of, reverse=True)
        return snapshots[: max(1, limit)]

    def query_order_history(
        self,
        *,
        account_id: str,
        symbol: str | None,
        start_time: datetime,
        end_time: datetime,
        cursor: str | None,
        limit: int,
        scope: Literal["active", "closed"],
    ) -> VenueOrderHistoryPage:
        adapter = self._adapter_for_account(account_id)
        return adapter.query_order_history(
            account_id=account_id,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            cursor=cursor,
            limit=limit,
            scope=scope,
        )

    def list_fills(
        self,
        *,
        account_id: str | None = None,
        external_order_id: str | None = None,
        platform_order_id: str | None = None,
    ) -> list[VenueFillSnapshot]:
        if account_id is not None:
            adapter = self._adapter_for_account(account_id)
            return adapter.list_fills(
                account_id=account_id,
                external_order_id=external_order_id,
                platform_order_id=platform_order_id,
            )
        if platform_order_id is not None:
            route = get_order_route(platform_order_id=platform_order_id)
            if route is None:
                return []
            return self._adapter_by_name(route.adapter, account_id=route.account_id).list_fills(
                account_id=route.account_id,
                platform_order_id=platform_order_id,
            )
        if external_order_id is not None:
            route = get_order_route(external_order_id=external_order_id)
            if route is not None:
                return self._adapter_by_name(route.adapter, account_id=route.account_id).list_fills(
                    account_id=route.account_id,
                    external_order_id=external_order_id,
                )
            if external_order_id.isdigit():
                return self.mt5.list_fills(external_order_id=external_order_id)
            return self.bybit.list_fills(external_order_id=external_order_id)
        snapshots = [*self.bybit.list_fills()]
        for mt5_account_id in sorted(self.settings.mt5_accounts):
            snapshots.extend(
                self._mt5_adapter(mt5_account_id).list_fills(account_id=mt5_account_id)
            )
        return snapshots

    def query_fill_history(
        self,
        *,
        account_id: str,
        symbol: str | None,
        start_time: datetime,
        end_time: datetime,
        cursor: str | None,
        limit: int,
    ) -> VenueFillHistoryPage:
        adapter = self._adapter_for_account(account_id)
        return adapter.query_fill_history(
            account_id=account_id,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            cursor=cursor,
            limit=limit,
        )

    def list_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        if account_id is not None:
            return self._adapter_for_account(account_id).list_positions(account_id)
        snapshots = [*self.bybit.list_positions()]
        for mt5_account_id in sorted(self.settings.mt5_accounts):
            snapshots.extend(self._mt5_adapter(mt5_account_id).list_positions(mt5_account_id))
        return snapshots

    def list_balances(self, account_id: str | None = None) -> list[VenueBalanceSnapshot]:
        if account_id is not None:
            return self._adapter_for_account(account_id).list_balances(account_id)
        snapshots = [*self.bybit.list_balances()]
        for mt5_account_id in sorted(self.settings.mt5_accounts):
            snapshots.extend(self._mt5_adapter(mt5_account_id).list_balances(mt5_account_id))
        return snapshots

    def get_account_risk(self, account_id: str) -> VenueAccountRiskSnapshot:
        return self._adapter_for_account(account_id).get_account_risk(account_id)

    def get_account_snapshot(
        self,
        account_id: str,
        *,
        include_history: bool = True,
        history_start: datetime | None = None,
    ) -> VenueAccountSnapshot:
        if history_start is not None:
            if history_start.tzinfo is None or history_start.utcoffset() is None:
                raise GatewayConfigurationError("historyStart must include a timezone")
            now = datetime.now(UTC)
            if history_start > now:
                raise GatewayConfigurationError("historyStart cannot be in the future")
            max_days = (
                7
                if account_id in self.settings.bybit_accounts
                else self.settings.mt5_history_lookback_days
            )
            if history_start < now - timedelta(days=max_days):
                raise GatewayConfigurationError("historyStart exceeds the supported history window")
        adapter: Any = self._adapter_for_account(account_id)
        if account_id in self.settings.bybit_accounts:
            if hasattr(adapter, "get_account_snapshot"):
                if include_history and history_start is None:
                    return adapter.get_account_snapshot(account_id)
                return adapter.get_account_snapshot(
                    account_id,
                    include_history=include_history,
                    history_start=history_start,
                )
            risk = adapter.get_account_risk(account_id)
            balances = adapter.list_balances(account_id)
            return VenueAccountSnapshot(
                source=adapter.name,
                accountId=account_id,
                venue="bybit",
                identity={"accountId": account_id},
                balances=balances,
                positions=adapter.list_positions(account_id),
                orders=(
                    adapter.list_orders(account_id=account_id, limit=100) if include_history else []
                ),
                fills=(
                    adapter.query_fill_history(
                        account_id=account_id,
                        symbol=None,
                        start_time=datetime.now(UTC) - timedelta(days=30),
                        end_time=datetime.now(UTC),
                        cursor=None,
                        limit=200,
                    ).items
                    if include_history
                    else []
                ),
                accountRisk=risk,
                asOf=risk.as_of,
                dataQualityState=risk.data_quality_state,
                economicEventsQuality=("unavailable" if include_history else "not_requested"),
            )
        if hasattr(adapter, "get_account_snapshot"):
            if include_history and history_start is None:
                return adapter.get_account_snapshot(account_id)
            return adapter.get_account_snapshot(
                account_id,
                include_history=include_history,
                history_start=history_start,
            )
        return self._mt5_account_snapshot(
            account_id, include_history=include_history, history_start=history_start
        )

    def transfer_internal_capital(
        self,
        command: InternalCapitalTransferStepCommand,
    ) -> InternalCapitalTransferStepResponse:
        bybit_account_id, from_type, to_type = self._tradfi_transfer_route(
            command.source_account_id,
            command.destination_account_id,
        )
        if "TradFi" in {from_type, to_type}:
            raise GatewayConfigurationError("BYBIT_TRADFI_WRITE_API_UNAVAILABLE")
        if command.source_currency.upper() != "USDT":
            raise GatewayConfigurationError("Bybit TradFi transfer requires USDT")
        if command.destination_currency.upper() not in {"USDT", "USD"}:
            raise GatewayConfigurationError("Bybit TradFi destination currency is unsupported")
        for account_id in (command.source_account_id, command.destination_account_id):
            if account_id not in self.settings.allowed_live_accounts:
                raise GatewayConfigurationError("Transfer account is not in the live allowlist")
        ready, transferable, reason = self.bybit.internal_transfer_readiness(
            account_id=bybit_account_id,
            from_account_type=from_type,
            to_account_type=to_type,
            currency="USDT",
        )
        if not ready or transferable is None:
            raise GatewayConfigurationError(
                reason or "Bybit TradFi transfer readiness is unavailable"
            )
        if command.amount > transferable:
            raise GatewayRequestRejectedError("Bybit TradFi transfer exceeds transferable balance")
        return self.bybit.transfer_tradfi_capital(
            command,
            account_id=bybit_account_id,
            from_account_type=from_type,
            to_account_type=to_type,
        )

    def get_internal_capital_transfer_readiness(
        self,
        *,
        source_account_id: str,
        destination_account_id: str,
        currency: str,
    ) -> InternalCapitalTransferReadinessResponse:
        try:
            bybit_account_id, from_type, to_type = self._tradfi_transfer_route(
                source_account_id,
                destination_account_id,
            )
        except GatewayConfigurationError as exc:
            return InternalCapitalTransferReadinessResponse(
                ready=False,
                sourceAccountId=source_account_id,
                destinationAccountId=destination_account_id,
                currency=currency.upper(),
                reason=str(exc),
            )
        if "TradFi" in {from_type, to_type}:
            return InternalCapitalTransferReadinessResponse(
                ready=False,
                sourceAccountId=source_account_id,
                destinationAccountId=destination_account_id,
                currency=currency.upper(),
                fromAccountType=from_type,
                toAccountType=to_type,
                reason="BYBIT_TRADFI_WRITE_API_UNAVAILABLE",
            )
        ready, transferable, reason = self.bybit.internal_transfer_readiness(
            account_id=bybit_account_id,
            from_account_type=from_type,
            to_account_type=to_type,
            currency=currency.upper(),
        )
        return InternalCapitalTransferReadinessResponse(
            ready=ready,
            sourceAccountId=source_account_id,
            destinationAccountId=destination_account_id,
            currency=currency.upper(),
            transferableBalance=transferable,
            fromAccountType=from_type,
            toAccountType=to_type,
            reason=reason,
        )

    def query_internal_capital_transfer(
        self,
        command: InternalCapitalTransferStepCommand,
        *,
        external_transfer_id: str,
    ) -> InternalCapitalTransferStepResponse:
        bybit_account_id, _, _ = self._tradfi_transfer_route(
            command.source_account_id,
            command.destination_account_id,
        )
        return self.bybit.query_tradfi_capital(
            command,
            account_id=bybit_account_id,
            external_transfer_id=external_transfer_id,
        )

    def _tradfi_transfer_route(
        self,
        source_account_id: str,
        destination_account_id: str,
    ) -> tuple[str, str, str]:
        pairs = self.settings.tradfi_transfer_pairs
        if pairs.get(source_account_id) == destination_account_id:
            return source_account_id, "UNIFIED", "TradFi"
        if pairs.get(destination_account_id) == source_account_id:
            return destination_account_id, "TradFi", "UNIFIED"
        raise GatewayConfigurationError(
            "Accounts are not explicitly mapped to one Bybit UTA/TradFi relationship"
        )

    def get_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str | None = None,
        category: str | None = None,
    ) -> VenueInstrumentSpecification:
        # The market parser already caches static specifications. The returned
        # snapshot also contains current account/terminal trading permissions,
        # which must be reread for pre-dispatch admission.
        return self._load_instrument_specification(
            account_id=account_id,
            symbol=symbol,
            instrument_type=instrument_type,
            category=category,
        )

    def get_research_ticks(self, *, account_id, symbol, start, end, historical=False):
        return self._mt5_adapter(account_id).get_research_ticks(
            account_id=account_id, symbol=symbol, start=start, end=end, historical=historical
        )

    def get_market_quote(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str | None = None,
        category: str | None = None,
    ):
        key = (
            "quote",
            account_id,
            symbol.upper(),
            instrument_type or "",
            category or "",
        )
        return self._cached_execution_read(
            key,
            self._QUOTE_CACHE_SECONDS,
            lambda: self._adapter_for_account(account_id).get_market_quote(
                account_id=account_id,
                symbol=symbol,
                instrument_type=instrument_type,
                category=category,
            ),
        )

    def list_funding_markets(
        self, *, account_id: str, search: str | None = None
    ) -> list[dict[str, object]]:
        adapter = self._adapter_for_account(account_id)
        reader = getattr(adapter, "list_funding_markets", None)
        if reader is None:
            raise GatewayConfigurationError("Funding market catalog is unavailable")
        return reader(account_id=account_id, search=search)

    def estimate_order_margin(
        self,
        *,
        account_id: str,
        symbol: str,
        side,
        quantity,
        reference_price,
    ):
        key = (
            "margin",
            account_id,
            symbol.upper(),
            str(side),
            format(Decimal(quantity), "f"),
            format(Decimal(reference_price), "f"),
        )
        return self._cached_execution_read(
            key,
            self._MARGIN_CACHE_SECONDS,
            lambda: self._adapter_for_account(account_id).estimate_order_margin(
                account_id=account_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                reference_price=reference_price,
            ),
        )

    def _load_instrument_specification(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str | None,
        category: str | None,
    ):
        adapter = self._adapter_for_account(account_id)
        if account_id in self.settings.mt5_accounts:
            return adapter.get_instrument_specification(
                account_id=account_id,
                symbol=symbol,
            )
        return adapter.get_instrument_specification(
            account_id=account_id,
            symbol=symbol,
            instrument_type=instrument_type,
            category=category,
        )

    def _cached_execution_read(self, key, ttl_seconds: float, loader):
        # Merge simultaneous reads of exactly the same account/market/inputs.
        # Independent keys and writes never wait behind this bookkeeping lock.
        with self._execution_read_lock:
            now = monotonic()
            cached = self._execution_read_cache.get(key)
            if cached is not None and now - cached[0] <= ttl_seconds:
                return cached[1]
            generation = self._execution_read_generation.get(key[1], 0)
            flight_key = (*key, generation)
            pending = self._execution_reads.get(flight_key)
            owner = pending is None
            if owner:
                pending = Future()
                self._execution_reads[flight_key] = pending
        assert pending is not None
        if not owner:
            return pending.result()
        try:
            value = loader()
            with self._execution_read_lock:
                if self._execution_read_generation.get(key[1], 0) == generation:
                    self._execution_read_cache[key] = (now, value)
            pending.set_result(value)
            return value
        except BaseException as exc:
            pending.set_exception(exc)
            raise
        finally:
            with self._execution_read_lock:
                self._execution_reads.pop(flight_key, None)

    def list_economic_events(
        self,
        *,
        account_id: str | None = None,
        instrument_id: str | None = None,
        event_type: str | None = None,
    ) -> list[VenueEconomicEventSnapshot]:
        if account_id is not None:
            return self._adapter_for_account(account_id).list_economic_events(
                account_id=account_id,
                instrument_id=instrument_id,
                event_type=event_type,
            )
        snapshots = [
            *self.bybit.list_economic_events(
                instrument_id=instrument_id,
                event_type=event_type,
            )
        ]
        for mt5_account_id in sorted(self.settings.mt5_accounts):
            snapshots.extend(
                self._mt5_adapter(mt5_account_id).list_economic_events(
                    account_id=mt5_account_id,
                    instrument_id=instrument_id,
                    event_type=event_type,
                )
            )
        return snapshots

    def cancel_order(
        self,
        external_order_id: str,
        idempotency_key: str,
        reason: str | None,
    ) -> CancelOrderResponse:
        route = get_order_route(external_order_id=external_order_id)
        if route is None:
            raise GatewayConfigurationError("Live order route not found")
        return self._adapter_by_name(route.adapter, account_id=route.account_id).cancel_order(
            external_order_id, idempotency_key, reason
        )

    def capabilities(self) -> GatewayCapabilitiesResponse:
        mt5_capability = self.mt5.capability()
        if self._mt5_supervisor is not None:
            account_ids = sorted(self.settings.mt5_accounts)
            account_missing: dict[str, set[str]] = {account_id: set() for account_id in account_ids}
            shared_missing: set[str] = set()
            for requirement in mt5_capability.missing_requirements:
                account_id = next(
                    (item for item in account_ids if requirement.startswith(f"{item}:")),
                    None,
                )
                if account_id is None:
                    shared_missing.add(requirement)
                else:
                    account_missing[account_id].add(requirement)
            for account_id in account_ids:
                account_missing[account_id].update(
                    self._mt5_supervisor.missing_requirements(account_id)
                )

            environment_only = {"WINDOWS_RUNTIME", "METATRADER5_DEPENDENCY"}
            shared_configured = not (shared_missing - environment_only)
            shared_operational = not shared_missing
            account_statuses = [
                GatewayAccountCapability(
                    accountId=account_id,
                    configured=shared_configured and not account_missing[account_id],
                    operational=shared_operational and not account_missing[account_id],
                    writeEnabled=(
                        shared_operational
                        and not account_missing[account_id]
                        and self.settings.live_write_enabled
                        and account_id in self.settings.allowed_live_accounts
                    ),
                    missingRequirements=sorted(account_missing[account_id]),
                )
                for account_id in account_ids
            ]
            missing = sorted(shared_missing | set().union(*account_missing.values()))
            mt5_capability = mt5_capability.model_copy(
                update={
                    # Adapter-wide readiness describes shared MT5 support. A
                    # broken account path is retained in accountStatuses and
                    # must not disable healthy accounts using this adapter.
                    "configured": shared_configured and any(
                        item.configured for item in account_statuses
                    ),
                    "operational": shared_operational and any(
                        item.operational for item in account_statuses
                    ),
                    "write_enabled": any(item.write_enabled for item in account_statuses),
                    "account_statuses": account_statuses,
                    "missing_requirements": missing,
                }
            )
        return GatewayCapabilitiesResponse(
            gateway=self.name,
            environment=self.settings.environment,
            liveWriteEnabled=self.settings.live_write_enabled,
            adapters=[self.bybit.capability(), mt5_capability],
        )

    def close(self) -> None:
        close = getattr(self.bybit, "close", None)
        if close is not None:
            close()
        if self._mt5_supervisor is not None:
            self._mt5_supervisor.close()

    def _adapter_for_account(self, account_id: str):
        in_bybit = account_id in self.settings.bybit_accounts
        in_mt5 = account_id in self.settings.mt5_accounts
        if in_bybit and in_mt5:
            raise GatewayConfigurationError("Account is ambiguously mapped to multiple adapters")
        if in_bybit:
            return self.bybit
        if in_mt5:
            return self._mt5_adapter(account_id)
        raise GatewayConfigurationError("Account is not mapped to a live adapter")

    def _mt5_adapter(self, account_id: str):
        if self._injected_mt5 is not None:
            return self._injected_mt5
        assert self._mt5_supervisor is not None
        return self._mt5_supervisor.adapter(account_id)

    def _adapter_by_name(self, name: str, *, account_id: str | None = None):
        if name == self.bybit.name:
            return self.bybit
        if name == self.mt5.name:
            if account_id is None:
                raise GatewayConfigurationError("MT5 order route has no account identity")
            return self._mt5_adapter(account_id)
        raise GatewayConfigurationError(f"Unknown live adapter route: {name}")

    def _mt5_account_snapshot(
        self,
        account_id: str,
        *,
        include_history: bool = True,
        history_start: datetime | None = None,
    ) -> VenueAccountSnapshot:
        mt5 = cast(Any, self.mt5._runtime_mt5())

        def read(_session) -> VenueAccountSnapshot:
            info = mt5.account_info()
            terminal = mt5.terminal_info()
            if info is None or terminal is None:
                raise GatewayConfigurationError(f"MT5 account snapshot failed: {mt5.last_error()}")
            if not bool(getattr(terminal, "connected", False)):
                raise GatewayConfigurationError("MT5 account snapshot terminal is not connected")
            currency = self.mt5._account_currency(mt5)
            as_of = datetime.now(UTC)
            balances = [
                VenueBalanceSnapshot(
                    source=self.mt5.name,
                    externalBalanceId=(
                        f"{account_id}:{getattr(info, 'login', '')}:{int(as_of.timestamp())}"
                    ),
                    accountId=account_id,
                    instrumentType="mt5_cash",
                    category="mt5",
                    equity=Decimal(str(getattr(info, "equity", 0) or 0)),
                    availableBalance=Decimal(str(getattr(info, "margin_free", 0) or 0)),
                    currency=currency,
                    asOf=as_of,
                )
            ]
            positions = []
            warnings: list[str] = []
            position_rows = mt5.positions_get()
            if position_rows is None:
                raise GatewayConfigurationError("MT5 positions query failed")
            for row in position_rows:
                symbol = str(getattr(row, "symbol", "")).upper()
                mapped_instrument_id = self.settings.mt5_instruments.get(symbol)
                instrument_id, quality = self.mt5._resolve_read_instrument(
                    account_id=account_id,
                    symbol=symbol,
                    instrument_id=mapped_instrument_id,
                    prefer_route=False,
                )
                if quality == "external_unmapped":
                    warnings.append(f"read_only_monitoring_unmapped:{symbol}")
                volume = Decimal(str(getattr(row, "volume", 0) or 0))
                if int(getattr(row, "type", -1)) == int(getattr(mt5, "POSITION_TYPE_SELL", 1)):
                    volume = -volume
                positions.append(
                    VenuePositionSnapshot(
                        source=self.mt5.name,
                        externalPositionId=str(getattr(row, "ticket", 0)),
                        accountId=account_id,
                        instrumentId=instrument_id,
                        instrumentType="mt5_contract",
                        category="mt5",
                        symbol=symbol,
                        netQuantity=volume,
                        averagePrice=Decimal(str(getattr(row, "price_open", 0) or 0)),
                        currentPrice=Decimal(str(getattr(row, "price_current", 0) or 0)),
                        unrealizedPnl=Decimal(str(getattr(row, "profit", 0) or 0)),
                        swap=Decimal(str(getattr(row, "swap", 0) or 0)),
                        stopLossPrice=Decimal(str(getattr(row, "sl", 0) or 0)) or None,
                        takeProfitPrice=Decimal(str(getattr(row, "tp", 0) or 0)) or None,
                        currency=currency,
                        asOf=self.mt5._position_time(row),
                        dataQualityState=quality,
                    )
                )
            orders: list[VenueOrderSnapshot] = []
            fills: list[VenueFillSnapshot] = []
            economic_events: list[VenueEconomicEventSnapshot] = []
            requested_history_start = history_start
            history_start_used = history_end_used = None
            if include_history:
                start, end = self.mt5._history_window()
                if requested_history_start is not None:
                    start = requested_history_start
                seen_order_ids: set[str] = set()
                active_orders = mt5.orders_get()
                history_orders = mt5.history_orders_get(start, end)
                deals = mt5.history_deals_get(start, end)
                if active_orders is None or history_orders is None or deals is None:
                    raise GatewayConfigurationError("MT5 order or deal history query failed")
                for row in [*active_orders, *history_orders]:
                    snapshot = self.mt5._snapshot(mt5, row, account_id)
                    if snapshot is None or snapshot.external_order_id in seen_order_ids:
                        continue
                    seen_order_ids.add(snapshot.external_order_id)
                    orders.append(snapshot)
                seen_fill_ids: set[str] = set()
                for deal in deals:
                    if not self.mt5._is_trade_deal(mt5, deal):
                        continue
                    snapshot = self.mt5._fill_snapshot(
                        mt5, deal, account_id, target=None, fallback_route=None
                    )
                    if snapshot is None or snapshot.external_fill_id in seen_fill_ids:
                        continue
                    seen_fill_ids.add(snapshot.external_fill_id)
                    fills.append(snapshot)
                economic_events = self.mt5._economic_event_snapshots(mt5, account_id, deals)
                history_start_used, history_end_used = start, end
            risk = VenueAccountRiskSnapshot(
                source=self.mt5.name,
                accountId=account_id,
                currency=currency,
                assetScope="mt5_trading",
                equity=Decimal(str(getattr(info, "equity", 0) or 0)),
                walletBalance=Decimal(str(getattr(info, "balance", 0) or 0)),
                marginBalance=Decimal(str(getattr(info, "equity", 0) or 0)),
                availableBalance=Decimal(str(getattr(info, "margin_free", 0) or 0)),
                initialMargin=Decimal(str(getattr(info, "margin", 0) or 0)),
                maintenanceMargin=(
                    Decimal(str(getattr(info, "margin_maintenance", 0) or 0))
                    if getattr(info, "margin_maintenance", None) is not None
                    else None
                ),
                unrealizedPnl=Decimal(str(getattr(info, "profit", 0) or 0)),
                marginLevel=(
                    Decimal(str(getattr(info, "margin_level", 0)))
                    if getattr(info, "margin_level", None) is not None
                    else None
                ),
                marginCallLevel=(
                    Decimal(str(getattr(info, "margin_so_call", 0)))
                    if getattr(info, "margin_so_call", None) is not None
                    else None
                ),
                stopOutLevel=(
                    Decimal(str(getattr(info, "margin_so_so", 0)))
                    if getattr(info, "margin_so_so", None) is not None
                    else None
                ),
                marginThresholdMode=str(int(getattr(info, "margin_so_mode", -1))),
                leverage=(
                    Decimal(str(getattr(info, "leverage", 0)))
                    if getattr(info, "leverage", None) is not None
                    else None
                ),
                marginMode=str(int(getattr(info, "margin_mode", -1))),
                tradeAllowed=bool(getattr(info, "trade_allowed", False)),
                expertTradingAllowed=bool(getattr(terminal, "trade_allowed", False)),
                fieldAvailability={
                    "accountSnapshot": "single_session",
                    "liquidationPrice": "not_available_mt5_api",
                },
                asOf=as_of,
                dataQualityState="complete",
            )
            return VenueAccountSnapshot(
                source=self.mt5.name,
                accountId=account_id,
                venue="mt5",
                identity={
                    "accountId": account_id,
                    "login": str(getattr(info, "login", "") or ""),
                    "server": str(getattr(info, "server", "") or ""),
                    "company": str(getattr(info, "company", "") or "") or None,
                },
                balances=balances,
                positions=positions,
                orders=orders,
                fills=fills,
                economicEvents=economic_events,
                economicEventsQuality=("complete" if include_history else "not_requested"),
                historyStart=history_start_used,
                historyEnd=history_end_used,
                accountRisk=risk,
                warnings=sorted(set(warnings)),
                asOf=as_of,
                dataQualityState=("external_unmapped" if warnings else "complete"),
            )

        return with_mt5_read_session(
            mt5=mt5,
            settings=self.settings,
            account_id=account_id,
            callback=read,
        )
