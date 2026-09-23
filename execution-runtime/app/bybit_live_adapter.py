from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import RLock
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, uuid5

from app.bybit_connection import BybitConnections
from app.bybit_market_data import BybitMarketData
from app.config import Settings
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.live_route_store import (
    get_order_route,
    record_order_route,
    stable_external_client_id,
    update_external_order_id,
)
from app.live_safety import validate_live_cancel, validate_live_write
from app.models import (
    CancelOrderResponse,
    ExecutionEvent,
    GatewayAdapterCapability,
    InternalCapitalTransferStepCommand,
    InternalCapitalTransferStepResponse,
    SubmitOrderCommand,
    VenueAccountRiskSnapshot,
    VenueAccountSnapshot,
    VenueBalanceSnapshot,
    VenueEconomicEventSnapshot,
    VenueFillSnapshot,
    VenueMarketQuoteSnapshot,
    VenueOrderMarginEstimate,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)
from app.order_semantics import normalize_bybit_order_status
from app.secret_resolver import inspect_credential_reference


class BybitLiveAdapter:
    name = "bybit_live"

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self._injected_client = client
        self._connections = BybitConnections(settings)
        self._market_readers: dict[str, BybitMarketData] = {}
        self._market_reader_lock = RLock()
        # A full account snapshot fans out into several authenticated Bybit
        # reads. Keep snapshots for different accounts serialized so a shared
        # pybit timestamp helper and venue rate limits cannot corrupt one read
        # while another account is being assembled.
        self._account_snapshot_lock = RLock()

    def capability(self) -> GatewayAdapterCapability:
        missing: list[str] = []
        for account_id in self.settings.bybit_accounts:
            inspection = inspect_credential_reference(
                self.settings.bybit_credential_for_account(account_id),
                required_fields=("API_KEY", "SECRET"),
            )
            missing.extend(f"{account_id}:{field}" for field in inspection.missing_fields)
        if not self.settings.bybit_accounts:
            missing.append("BYBIT_ACCOUNT_IDS")
        if not self.settings.bybit_instruments:
            missing.append("BYBIT_INSTRUMENT_MAP")
        configured = not missing
        operational = configured and self._dependency_available()
        if configured and not operational:
            missing.append("PYBIT_DEPENDENCY")
        return GatewayAdapterCapability(
            adapter=self.name,
            environment="live",
            configured=configured,
            operational=operational,
            writeEnabled=operational and self.settings.live_write_enabled,
            accountIds=sorted(self.settings.bybit_accounts),
            capabilities=[
                "order_query",
                "fill_query",
                "position_query",
                "balance_query",
                "funding_query",
                "submit_order_gated",
                "post_only_single_attempt_submit",
                "cancel_order_gated",
                "account_risk_query",
            ],
            missingRequirements=sorted(set(missing)),
        )

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        self._assert_account(command.account_id)
        self._assert_write_account(command.account_id)
        client = self._client(command.account_id)
        reference_price = command.price or self._market_reference_price(client, command)
        validate_live_write(
            command,
            adapter=self.name,
            reference_price=reference_price,
            settings=self.settings,
        )
        client_id = stable_external_client_id("VG", command.platform_order_id, length=36)
        record_order_route(command, self.name, client_id)
        payload: dict[str, object] = {
            **self._order_market_fields(command),
            "symbol": command.symbol.upper(),
            "side": "Buy" if command.side == "buy" else "Sell",
            "orderType": "Market" if command.order_type == "market" else "Limit",
            "qty": format(command.quantity, "f"),
            "orderLinkId": client_id,
        }
        if command.order_type == "limit":
            if command.price is None:
                raise GatewayRequestRejectedError("Bybit limit order requires price")
            payload["price"] = format(command.price, "f")
            payload["timeInForce"] = (
                "PostOnly" if command.execution_policy == "post_only_single_attempt" else "GTC"
            )
        try:
            response = client.place_order(**payload)
        except Exception as exc:
            raise self._unknown_error("Bybit place_order result is unknown", exc) from exc
        self._require_success(response, "Bybit rejected order")
        result = response.get("result") or {}
        external_order_id = str(result.get("orderId") or "")
        if not external_order_id:
            raise GatewayResultUnknownError("Bybit accepted order without orderId")
        update_external_order_id(command.platform_order_id, external_order_id)
        return [
            ExecutionEvent(
                command_id=command.command_id,
                platform_order_id=command.platform_order_id,
                event_type="order_acknowledged",
                external_order_id=external_order_id,
                occurred_at=datetime.now(UTC),
            )
        ]

    def set_leverage(self, *, account_id: str, symbol: str, leverage: Decimal) -> dict[str, object]:
        self._assert_account(account_id)
        self._assert_write_account(account_id)
        if self.settings.environment.lower() != "live" or not self.settings.live_write_enabled:
            raise GatewayConfigurationError("Runtime live write gate is disabled")
        if account_id not in self.settings.allowed_live_accounts:
            raise GatewayConfigurationError("Account is not enabled for live trading")
        if not leverage.is_finite() or leverage < 1 or leverage > Decimal("100"):
            raise GatewayRequestRejectedError("Bybit leverage must be between 1 and 100")
        try:
            response = self._client(account_id).set_leverage(
                category=self.settings.bybit_category,
                symbol=symbol.upper(),
                buyLeverage=format(leverage, "f"),
                sellLeverage=format(leverage, "f"),
            )
            if response.get("retCode") != 110043:
                self._require_success(response, "Bybit rejected leverage update")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            if getattr(exc, "status_code", None) != 110043:
                raise self._unknown_error("Bybit leverage update result is unknown", exc) from exc
        result = self.get_leverage(account_id=account_id, symbol=symbol)
        if result.get("leverage") != str(leverage):
            if Decimal(str(result.get("leverage") or "0")) != leverage:
                raise GatewayResultUnknownError(
                    "Bybit leverage update is not yet confirmed; query before retry"
                )
        return result

    def get_leverage(self, *, account_id: str, symbol: str) -> dict[str, object]:
        self._assert_account(account_id)
        try:
            response = self._client(account_id).get_positions(
                category=self.settings.bybit_category, symbol=symbol.upper()
            )
            self._require_success(response, "Bybit leverage query failed")
            values = {
                Decimal(str(row["leverage"]))
                for row in self._result_list(response)
                if str(row.get("symbol", "")).upper() == symbol.upper() and row.get("leverage")
            }
            leverage = next(iter(values)) if len(values) == 1 else None
            if leverage is not None and (not leverage.is_finite() or leverage < 1):
                leverage = None
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit leverage query result is unknown", exc) from exc
        return {
            "accountId": account_id,
            "symbol": symbol.upper(),
            "leverage": str(leverage) if leverage is not None else None,
            "source": self.name,
        }

    def estimate_order_margin(
        self,
        *,
        account_id: str,
        symbol: str,
        side: Literal["buy", "sell"],
        quantity: Decimal,
        reference_price: Decimal,
    ) -> VenueOrderMarginEstimate:
        self._assert_account(account_id)
        normalized_symbol = symbol.upper()
        try:
            response = self._client(account_id).get_positions(
                category=self.settings.bybit_category,
                symbol=normalized_symbol,
            )
            self._require_success(response, "Bybit leverage query failed")
            row = next(
                (
                    item
                    for item in self._result_list(response)
                    if str(item.get("symbol") or "").upper() == normalized_symbol
                ),
                None,
            )
            leverage = Decimal(str((row or {}).get("leverage") or "0"))
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit leverage query result is unknown", exc) from exc
        if leverage <= 0:
            raise GatewayConfigurationError("Bybit current symbol leverage is unavailable")
        margin = quantity * reference_price / leverage
        return VenueOrderMarginEstimate(
            source=self.name,
            accountId=account_id,
            instrumentType="crypto_perp",
            category=self.settings.bybit_category,
            symbol=normalized_symbol,
            side=side,
            quantity=quantity,
            referencePrice=reference_price,
            estimatedInitialMargin=margin,
            currency=self.settings.bybit_settle_coin.upper(),
            asOf=datetime.now(UTC),
            dataQualityState="venue_leverage_estimate",
        )

    def get_order(
        self,
        *,
        platform_order_id: str | None = None,
        external_order_id: str | None = None,
    ) -> VenueOrderSnapshot | None:
        route = self._resolve_route(
            platform_order_id=platform_order_id,
            external_order_id=external_order_id,
        )
        if route is None:
            return None
        client = self._client(route.account_id)
        query: dict[str, object] = {
            "category": self._route_category(route),
            "symbol": route.symbol,
        }
        if route.external_order_id:
            query["orderId"] = route.external_order_id
        else:
            query["orderLinkId"] = route.external_client_id
        try:
            realtime = client.get_open_orders(**query)
            self._require_success(realtime, "Bybit order query failed")
            rows = self._result_list(realtime)
            if not rows:
                history = client.get_order_history(**query)
                self._require_success(history, "Bybit order history query failed")
                rows = self._result_list(history)
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit order query result is unknown", exc) from exc
        if not rows:
            return None
        return self._order_snapshot(rows[0], route)

    def list_fills(
        self,
        *,
        account_id: str | None = None,
        external_order_id: str | None = None,
        platform_order_id: str | None = None,
    ) -> list[VenueFillSnapshot]:
        if account_id is not None:
            self._assert_account(account_id)
        route = None
        if platform_order_id is not None or external_order_id is not None:
            route = self._resolve_route(
                platform_order_id=platform_order_id,
                external_order_id=external_order_id,
            )
        resolved_account = account_id or (route.account_id if route is not None else None)
        if resolved_account is None:
            resolved_account = self._single_account()
        self._assert_account(resolved_account)
        query: dict[str, object] = {"category": self._route_category(route), "limit": 100}
        if route is not None:
            query["symbol"] = route.symbol
            if route.external_order_id:
                query["orderId"] = route.external_order_id
            else:
                query["orderLinkId"] = route.external_client_id
        try:
            response = self._client(resolved_account).get_executions(**query)
            self._require_success(response, "Bybit execution query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit execution query result is unknown", exc) from exc
        snapshots: list[VenueFillSnapshot] = []
        for row in self._result_list(response):
            if str(row.get("execType") or "Trade") != "Trade":
                continue
            row_category = str(query["category"])
            symbol = str(row.get("symbol") or "").upper()
            instrument_id = self.settings.bybit_instruments.get(symbol)
            if instrument_id is None:
                continue
            row_route = get_order_route(
                external_order_id=str(row.get("orderId") or ""), account_id=resolved_account
            )
            order_id = str(row.get("orderId") or "unknown")
            snapshots.append(
                VenueFillSnapshot(
                    source=self.name,
                    externalFillId=str(row.get("execId") or f"{order_id}:{row.get('execTime')}"),
                    externalOrderId=order_id,
                    platformOrderId=(
                        row_route.platform_order_id
                        if row_route
                        else f"external:{self.name}:{resolved_account}:{order_id}"
                    ),
                    commandId=(
                        row_route.command_id
                        if row_route
                        else f"external:{self.name}:{resolved_account}:{order_id}"
                    ),
                    accountId=(row_route.account_id if row_route else resolved_account),
                    instrumentId=(row_route.instrument_id if row_route else instrument_id),
                    symbol=symbol,
                    side="buy" if str(row.get("side")) == "Buy" else "sell",
                    quantity=Decimal(str(row.get("execQty") or "0")),
                    price=Decimal(str(row.get("execPrice") or "0")),
                    fee=Decimal(str(row["execFee"]))
                    if row.get("execFee") not in (None, "")
                    else None,
                    currency=str(
                        row.get("feeCurrency")
                        or (
                            self.settings.bybit_settle_coin
                            if row_category == "linear"
                            else "UNKNOWN"
                        )
                    ),
                    feeCurrencyQuality="reported"
                    if row.get("feeCurrency")
                    else "inferred_settlement"
                    if row_category == "linear"
                    else "unavailable",
                    occurredAt=self._millis(row.get("execTime")),
                )
            )
        return snapshots

    def list_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        try:
            response = self._read_with_retry(
                account,
                lambda client: client.get_positions(
                    category=self.settings.bybit_category,
                    settleCoin=self.settings.bybit_settle_coin,
                ),
            )
            self._require_success(response, "Bybit position query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit position query result is unknown", exc) from exc
        snapshots: list[VenuePositionSnapshot] = []
        for row in self._result_list(response):
            size = Decimal(str(row.get("size") or "0"))
            if size == 0:
                continue
            symbol = str(row.get("symbol") or "").upper()
            instrument_id = self.settings.bybit_instruments.get(symbol)
            if instrument_id is None:
                continue
            side = str(row.get("side") or "")
            quantity = size if side == "Buy" else -size
            snapshots.append(
                VenuePositionSnapshot(
                    source=self.name,
                    externalPositionId=f"{account}:{symbol}",
                    accountId=account,
                    instrumentId=instrument_id,
                    instrumentType="crypto_perp",
                    category=self.settings.bybit_category.lower(),
                    symbol=symbol,
                    netQuantity=quantity,
                    averagePrice=self._optional_decimal(row.get("avgPrice")),
                    currency=self.settings.bybit_settle_coin,
                    asOf=self._millis(row.get("updatedTime")),
                    openTime=self._micros(row.get("openTime")),
                )
            )
        return snapshots

    def get_market_quote(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str | None = None,
        category: str | None = None,
    ) -> VenueMarketQuoteSnapshot:
        self._assert_account(account_id)
        normalized_symbol = symbol.strip().upper()
        resolved_instrument_type, resolved_category = self._market_identity(
            account_id=account_id,
            symbol=normalized_symbol,
            instrument_type=instrument_type,
            category=category,
        )
        try:
            market, ticker, funding, response = self._market_data(account_id).ticker(
                resolved_category, normalized_symbol
            )
            bid = Decimal(str(ticker.get("bid") or "0"))
            ask = Decimal(str(ticker.get("ask") or "0"))
            if not bid.is_finite() or not ask.is_finite() or bid <= 0 or ask <= 0:
                raise GatewayConfigurationError("Bybit ticker query returned an incomplete quote")
            # CCXT's current fundingTimestamp is Bybit's nextFundingTime;
            # nextFundingTimestamp would refer to the following funding period.
            funding_time_raw = funding.get("fundingTimestamp")
            funding_time = self._millis(funding_time_raw) if funding_time_raw else None
            return VenueMarketQuoteSnapshot(
                source=self.name,
                accountId=account_id,
                instrumentType=resolved_instrument_type,
                category=resolved_category,
                symbol=normalized_symbol,
                bid=bid,
                ask=ask,
                mid=(bid + ask) / Decimal("2"),
                last=self._optional_decimal(ticker.get("last")),
                fundingRate=(
                    self._optional_decimal(funding.get("fundingRate"))
                    if resolved_instrument_type == "crypto_perp"
                    else None
                ),
                nextFundingTime=(
                    funding_time if resolved_instrument_type == "crypto_perp" else None
                ),
                currency=str(market["quote"]),
                sourceAsOf=self._millis(response["time"]) if response.get("time") else None,
                rawPayload=response,
                asOf=datetime.now(UTC),
            )
        except GatewayConfigurationError:
            raise
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit ticker result is unknown", exc) from exc

    def list_funding_markets(
        self, *, account_id: str, search: str | None = None
    ) -> list[dict[str, object]]:
        """Return Bybit spot/perpetual pairs that can form a Funding hedge."""
        self._assert_account(account_id)
        needle = (search or "").strip().upper()
        try:
            spot_markets = self._market_data(account_id).markets("spot")
            perp_markets = self._market_data(account_id).markets("linear")
            spots = {
                (str(row.get("base") or "").upper(), str(row.get("quote") or "").upper()): row
                for row in spot_markets
                if str((row.get("info") or {}).get("status") or "Trading").lower()
                in {"trading", "online"}
            }
            pairs: list[dict[str, object]] = []
            for perp in perp_markets:
                info = perp.get("info") or {}
                if not perp.get("swap") or str(info.get("status") or "").lower() not in {
                    "trading",
                    "online",
                }:
                    continue
                base = str(perp.get("base") or "").upper()
                quote = str(perp.get("quote") or "").upper()
                spot = spots.get((base, quote))
                if spot is None or quote != self.settings.bybit_settle_coin.upper():
                    continue
                perp_symbol = str(perp.get("id") or "").upper()
                spot_symbol = str(spot.get("id") or "").upper()
                if needle and needle not in {base, perp_symbol, spot_symbol} and needle not in base:
                    continue

                def spec(
                    row: dict[str, object],
                    fallback_quote: str = quote,
                ) -> dict[str, object]:
                    limits = row.get("limits") or {}
                    amount_limits = limits.get("amount") or {}
                    precision = row.get("precision") or {}
                    return {
                        "priceTick": str(precision.get("price") or "0"),
                        "minQuantity": str(amount_limits.get("min") or "0"),
                        "quantityStep": str(precision.get("amount") or "0"),
                        "contractMultiplier": str(row.get("contractSize") or "1"),
                        "settlementCurrency": str(row.get("settle") or fallback_quote),
                    }

                pairs.append(
                    {
                        "baseAsset": base,
                        "quoteCurrency": quote,
                        "perpetualSymbol": perp_symbol,
                        "spotSymbol": spot_symbol,
                        "perpetualInstrumentId": self._instrument_id_for_symbol(
                            account_id=account_id,
                            symbol=perp_symbol,
                            instrument_type="crypto_perp",
                            category="linear",
                        ),
                        "spotInstrumentId": self._instrument_id_for_symbol(
                            account_id=account_id,
                            symbol=spot_symbol,
                            instrument_type="crypto_spot",
                            category="spot",
                        ),
                        "perpetual": spec(perp),
                        "spot": spec(spot),
                    }
                )
            return sorted(pairs, key=lambda item: (str(item["baseAsset"]), str(item["perpetualSymbol"])))
        except (GatewayConfigurationError, GatewayRequestRejectedError):
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit funding market catalog is unknown", exc) from exc

    def list_balances(self, account_id: str | None = None) -> list[VenueBalanceSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        return self._balances_from_wallet_response(account, self._wallet_response(account))

    def _wallet_response(self, account: str) -> dict[str, object]:
        try:
            response = self._read_with_retry(
                account, lambda client: client.get_wallet_balance(accountType="UNIFIED")
            )
            self._require_success(response, "Bybit wallet query failed")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit wallet query result is unknown", exc) from exc
        if not self._result_list(response):
            raise GatewayConfigurationError("Bybit wallet query returned no data")
        return response

    def _balances_from_wallet_response(
        self,
        account: str,
        response: dict[str, object],
    ) -> list[VenueBalanceSnapshot]:
        result_rows = self._result_list(response)
        if not result_rows:
            return []
        account_row = result_rows[0]
        as_of = datetime.now(UTC)
        account_available = self._optional_decimal(account_row.get("totalAvailableBalance"))
        snapshots: list[VenueBalanceSnapshot] = []
        raw_coins = account_row.get("coin")
        coins = raw_coins if isinstance(raw_coins, list) else []
        for coin in coins:
            if not isinstance(coin, dict):
                continue
            currency = str(coin.get("coin") or "").upper()
            equity = Decimal(str(coin.get("equity") or "0"))
            wallet = Decimal(str(coin.get("walletBalance") or "0"))
            if equity == 0 and wallet == 0:
                continue
            available = self._available_balance(coin, account_available=account_available)
            snapshots.append(
                VenueBalanceSnapshot(
                    source=self.name,
                    externalBalanceId=f"{account}:{currency}:{int(as_of.timestamp())}",
                    accountId=account,
                    instrumentType="crypto_spot",
                    category="spot",
                    equity=equity,
                    walletBalance=wallet,
                    locked=self._optional_decimal(coin.get("locked")),
                    usdValue=self._optional_decimal(coin.get("usdValue")),
                    availableBalance=available,
                    availableBalanceBasis="unborrowed_cash_capped_by_margin",
                    dataQualityState="complete" if available is not None else "partial",
                    currency=currency,
                    asOf=as_of,
                )
            )
        return snapshots

    def internal_transfer_readiness(
        self,
        *,
        account_id: str,
        from_account_type: str,
        to_account_type: str,
        currency: str,
    ) -> tuple[bool, Decimal | None, str | None]:
        self._assert_account(account_id)
        client = self._client(account_id)
        try:
            key_response = client.get_api_key_information()
            self._require_success(key_response, "Bybit API key query failed")
            key_result = key_response.get("result") or {}
            permissions = (
                key_result.get("permissions") if isinstance(key_result, dict) else {}
            ) or {}
            wallet_permissions = (
                permissions.get("Wallet") if isinstance(permissions, dict) else []
            ) or []
            if "AccountTransfer" not in wallet_permissions:
                return False, None, "BYBIT_WALLET_ACCOUNT_TRANSFER_PERMISSION_REQUIRED"
            response = client.get_coin_balance(
                accountType=from_account_type,
                toAccountType=to_account_type,
                coin=currency,
            )
            self._require_success(response, "Bybit transferable balance query failed")
            result = response.get("result") or {}
            balance = result.get("balance") if isinstance(result, dict) else {}
            raw_amount = balance.get("transferBalance") if isinstance(balance, dict) else None
            if raw_amount in (None, ""):
                return False, None, "BYBIT_TRADFI_TRANSFER_BALANCE_UNAVAILABLE"
            amount = Decimal(str(raw_amount))
            if amount < 0:
                return False, None, "BYBIT_TRADFI_TRANSFER_BALANCE_INVALID"
            return True, amount, None
        except GatewayRequestRejectedError as exc:
            return False, None, f"BYBIT_TRADFI_TRANSFER_REJECTED:{exc}"
        except Exception as exc:
            return False, None, f"BYBIT_TRADFI_TRANSFER_QUERY_UNAVAILABLE:{type(exc).__name__}"

    def transfer_tradfi_capital(
        self,
        command: InternalCapitalTransferStepCommand,
        *,
        account_id: str,
        from_account_type: str,
        to_account_type: str,
    ) -> InternalCapitalTransferStepResponse:
        self._assert_account(account_id)
        self._assert_write_account(account_id)
        if self.settings.environment.lower() != "live":
            raise GatewayConfigurationError("Runtime environment is not live")
        if not self.settings.live_write_enabled:
            raise GatewayConfigurationError("Runtime live write gate is disabled")
        transfer_id = str(
            uuid5(
                NAMESPACE_URL,
                f"variable-global:bybit-tradfi:{command.idempotency_key}",
            )
        )
        client = self._client(account_id)
        existing = self._query_internal_transfer(client, transfer_id)
        if existing is not None:
            return self._internal_transfer_response(command, transfer_id, existing)
        payload = {
            "transferId": transfer_id,
            "coin": command.source_currency.upper(),
            "amount": format(command.amount, "f"),
            "fromAccountType": from_account_type,
            "toAccountType": to_account_type,
        }
        try:
            response = client.create_internal_transfer(**payload)
            self._require_success(response, "Bybit TradFi transfer rejected")
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            recovered = self._query_internal_transfer(client, transfer_id)
            if recovered is not None:
                return self._internal_transfer_response(command, transfer_id, recovered)
            if exc.__class__.__name__ in {"InvalidRequestError", "FailedRequestError"}:
                raise GatewayRequestRejectedError(f"Bybit TradFi transfer rejected: {exc}") from exc
            raise self._unknown_error("Bybit TradFi transfer result is unknown", exc) from exc
        # Bybit's create response guarantees the transfer identity, not a final
        # settlement state. Resolve status through the authoritative record API;
        # if it is not visible yet, retain result_unknown and never resubmit.
        queried = self._query_internal_transfer(client, transfer_id)
        result = response.get("result") or {}
        row = queried or (result if isinstance(result, dict) else {})
        return self._internal_transfer_response(command, transfer_id, row)

    def _query_internal_transfer(
        self,
        client: Any,
        transfer_id: str,
    ) -> dict[str, object] | None:
        try:
            response = client.get_internal_transfer_records(transferId=transfer_id)
            self._require_success(response, "Bybit transfer query failed")
        except Exception:
            return None
        rows = self._result_list(response)
        return rows[0] if rows else None

    def query_tradfi_capital(
        self,
        command: InternalCapitalTransferStepCommand,
        *,
        account_id: str,
        external_transfer_id: str,
    ) -> InternalCapitalTransferStepResponse:
        self._assert_account(account_id)
        row = self._query_internal_transfer(self._client(account_id), external_transfer_id)
        if row is None:
            return InternalCapitalTransferStepResponse(
                externalTransferId=external_transfer_id,
                status="result_unknown",
                sourceAccountId=command.source_account_id,
                destinationAccountId=command.destination_account_id,
                sourceCurrency=command.source_currency,
                destinationCurrency=command.destination_currency,
                amount=command.amount,
            )
        return self._internal_transfer_response(command, external_transfer_id, row)

    @staticmethod
    def _internal_transfer_response(
        command: InternalCapitalTransferStepCommand,
        transfer_id: str,
        row: dict[str, object],
    ) -> InternalCapitalTransferStepResponse:
        status = str(row.get("status") or "").upper()
        if status == "SUCCESS":
            return InternalCapitalTransferStepResponse(
                externalTransferId=transfer_id,
                status="completed",
                sourceAccountId=command.source_account_id,
                destinationAccountId=command.destination_account_id,
                sourceCurrency=command.source_currency,
                destinationCurrency=command.destination_currency,
                amount=command.amount,
                completedAt=datetime.now(UTC),
            )
        if status == "FAILED":
            raise GatewayRequestRejectedError("Bybit TradFi transfer failed")
        if status in {"PENDING", "STATUS_UNKNOWN", ""}:
            return InternalCapitalTransferStepResponse(
                externalTransferId=transfer_id,
                status="result_unknown",
                sourceAccountId=command.source_account_id,
                destinationAccountId=command.destination_account_id,
                sourceCurrency=command.source_currency,
                destinationCurrency=command.destination_currency,
                amount=command.amount,
                completedAt=None,
            )
        raise GatewayResultUnknownError(f"Bybit TradFi transfer returned unknown status: {status}")

    def list_economic_events(
        self,
        *,
        account_id: str | None = None,
        instrument_id: str | None = None,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[VenueEconomicEventSnapshot]:
        account = account_id or self._single_account()
        self._assert_account(account)
        if event_type not in {None, "funding", "fee", "realized_pnl"}:
            return []
        end = end_time or datetime.now(UTC)
        start = start_time or (end - timedelta(days=7) + timedelta(milliseconds=1))
        try:
            rows = self._snapshot_pages(
                account,
                "get_transaction_log",
                {
                    "accountType": "UNIFIED",
                    "limit": 50,
                    "startTime": int(start.timestamp() * 1000),
                    "endTime": int(end.timestamp() * 1000),
                },
            )
        except GatewayRequestRejectedError:
            raise
        except Exception as exc:
            raise self._unknown_error("Bybit transaction log result is unknown", exc) from exc
        events: list[VenueEconomicEventSnapshot] = []
        for row in rows:
            symbol = str(row.get("symbol") or "").upper()
            category = str(row.get("category") or self.settings.bybit_category)
            mapped_instrument = (
                self._instrument_id_for_symbol(
                    account_id=account,
                    symbol=symbol,
                    instrument_type=self._instrument_type_for_category(category),
                    category=category,
                )
                if symbol
                else None
            )
            if instrument_id is not None and mapped_instrument != instrument_id:
                continue
            occurred_at = self._millis(row.get("transactionTime"))
            identity = row.get("id") or row.get("tradeId")
            if not identity:
                raise GatewayConfigurationError("Bybit transaction lacks authoritative identity")
            currency = str(row.get("currency") or "UNKNOWN")
            realized = Decimal(str(row.get("cashFlow") or "0"))
            if (
                category in {"linear", "inverse"}
                and row.get("type") == "TRADE"
                and realized != 0
                and event_type in {None, "realized_pnl"}
            ):
                events.append(
                    VenueEconomicEventSnapshot(
                        source=self.name,
                        externalEventId=f"realized:{identity}",
                        eventType="realized_pnl",
                        accountId=account,
                        instrumentId=mapped_instrument,
                        symbol=symbol or None,
                        amount=realized,
                        currency=currency,
                        occurredAt=occurred_at,
                        payload=dict(row),
                    )
                )
            funding = Decimal(str(row.get("funding") or "0"))
            if funding != 0 and event_type in {None, "funding"}:
                events.append(
                    VenueEconomicEventSnapshot(
                        source=self.name,
                        externalEventId=(f"funding:{identity}"),
                        eventType="funding",
                        accountId=account,
                        instrumentId=mapped_instrument,
                        symbol=symbol or None,
                        amount=funding,
                        currency=currency,
                        occurredAt=occurred_at,
                        payload=dict(row),
                    )
                )
            fee = Decimal(str(row.get("fee") or "0"))
            if fee != 0 and event_type in {None, "fee"}:
                events.append(
                    VenueEconomicEventSnapshot(
                        source=self.name,
                        externalEventId=(f"fee:{identity}"),
                        eventType="fee",
                        accountId=account,
                        instrumentId=mapped_instrument,
                        symbol=symbol or None,
                        amount=-fee,
                        currency=currency,
                        occurredAt=occurred_at,
                        payload=dict(row),
                    )
                )
        return events

    def cancel_order(
        self,
        external_order_id: str,
        idempotency_key: str,
        reason: str | None,
    ) -> CancelOrderResponse:
        route = get_order_route(external_order_id=external_order_id)
        if route is None or route.adapter != self.name:
            return CancelOrderResponse(
                source=self.name,
                externalOrderId=external_order_id,
                platformOrderId="unknown",
                status="not_found",
                reason="Live order route not found",
                asOf=datetime.now(UTC),
            )
        self._assert_write_account(route.account_id)
        validate_live_cancel(route, self.settings)
        try:
            response = self._client(route.account_id).cancel_order(
                category=self._route_category(route),
                symbol=route.symbol,
                orderId=external_order_id,
                orderLinkId=route.external_client_id,
            )
        except Exception as exc:
            raise self._unknown_error("Bybit cancel result is unknown", exc) from exc
        self._require_success(response, "Bybit cancel rejected")
        return CancelOrderResponse(
            source=self.name,
            externalOrderId=external_order_id,
            platformOrderId=route.platform_order_id,
            status="canceled",
            reason=reason,
            asOf=datetime.now(UTC),
        )

    def get_account_snapshot(
        self,
        account_id: str,
        *,
        include_history: bool = True,
        history_start: datetime | None = None,
    ) -> VenueAccountSnapshot:
        if not include_history:
            return self._get_account_snapshot(
                account_id, include_history=False, history_start=history_start
            )
        with self._account_snapshot_lock:
            return self._get_account_snapshot(
                account_id, include_history=True, history_start=history_start
            )

    def _get_account_snapshot(
        self,
        account_id: str,
        *,
        include_history: bool = True,
        history_start: datetime | None = None,
    ) -> VenueAccountSnapshot:
        self._assert_account(account_id)
        wallet_response = self._wallet_response(account_id)
        balances = self._balances_from_wallet_response(account_id, wallet_response)
        history_end = datetime.now(UTC)
        requested_history_start = history_start
        history_start = history_end - timedelta(days=7) + timedelta(milliseconds=1)
        if requested_history_start is not None:
            history_start = requested_history_start
        categories = self.settings.bybit_categories_for_account(account_id)
        queries: dict[tuple[str, str], dict[str, object]] = {}
        for category in categories:
            if category in {"linear", "inverse"}:
                position_query: dict[str, object] = {"category": category, "limit": 200}
                if category == "linear":
                    position_query["settleCoin"] = self.settings.bybit_settle_coin
                queries[category, "get_positions"] = position_query
            if include_history:
                for method, limit in (
                    ("get_open_orders", 50),
                    ("get_order_history", 50),
                    ("get_executions", 100),
                ):
                    query = self._account_snapshot_order_query_kwargs(category, limit=limit)
                    # Bybit order history uses created-time filtering; keep its
                    # established seven-day window so recently closed older
                    # orders remain visible. Fills use the requested window.
                    if method == "get_order_history":
                        query["startTime"] = int(
                            (history_end - timedelta(days=7) + timedelta(milliseconds=1)).timestamp()
                            * 1000
                        )
                        query["endTime"] = int(history_end.timestamp() * 1000)
                    elif method != "get_open_orders":
                        query.update(
                            startTime=int(history_start.timestamp() * 1000),
                            endTime=int(history_end.timestamp() * 1000),
                        )
                    queries[category, method] = query
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="bybit-account-read") as pool:
            futures = {
                key: pool.submit(self._snapshot_pages, account_id, key[1], query)
                for key, query in queries.items()
            }
            sections = {key: future.result() for key, future in futures.items()}
        positions: list[VenuePositionSnapshot] = []
        orders_by_id: dict[str, VenueOrderSnapshot] = {}
        fills_by_id: dict[str, VenueFillSnapshot] = {}
        for category in categories:
            if category in {"linear", "inverse"}:
                for row in sections[category, "get_positions"]:
                    size = Decimal(str(row.get("size") or "0"))
                    if size == 0:
                        continue
                    symbol = str(row.get("symbol") or "").upper()
                    side = str(row.get("side") or "")
                    quantity = size if side == "Buy" else -size
                    # The venue already values the position and reports the margin
                    # it occupies. Monitoring must carry those figures through
                    # instead of rebuilding them, so the platform can show the
                    # authoritative exposure and liquidation distance.
                    liquidation = self._optional_decimal(row.get("liqPrice"))
                    if liquidation is not None and liquidation <= 0:
                        liquidation = None
                    positions.append(
                        VenuePositionSnapshot(
                            source=self.name,
                            externalPositionId=f"{account_id}:{category}:{symbol}:{row.get('positionIdx', 0)}",
                            accountId=account_id,
                            instrumentId=self._instrument_id_for_symbol(
                                account_id=account_id,
                                symbol=symbol,
                                instrument_type="crypto_perp",
                                category=category,
                            ),
                            instrumentType="crypto_perp",
                            category=category,
                            symbol=symbol,
                            netQuantity=quantity,
                            averagePrice=self._optional_decimal(row.get("avgPrice")),
                            currentPrice=self._optional_decimal(row.get("markPrice")),
                            markPrice=self._optional_decimal(row.get("markPrice")),
                            positionValue=self._optional_decimal(row.get("positionValue")),
                            leverage=self._optional_decimal(row.get("leverage")),
                            initialMargin=self._optional_decimal(
                                row.get("positionIM") or row.get("positionIMByMp")
                            ),
                            maintenanceMargin=self._optional_decimal(
                                row.get("positionMM") or row.get("positionMMByMp")
                            ),
                            unrealizedPnl=self._optional_decimal(row.get("unrealisedPnl")),
                            currency=(
                                self.settings.bybit_settle_coin
                                if category == "linear"
                                else symbol.removesuffix("USD")
                            ),
                            stopLossPrice=self._optional_decimal(row.get("stopLoss")),
                            takeProfitPrice=self._optional_decimal(row.get("takeProfit")),
                            liquidationPrice=liquidation,
                            liquidationPriceSource=(
                                "venue_reported" if liquidation is not None else "venue_not_finite"
                            ),
                            fieldAvailability={
                                "liquidationPrice": (
                                    "venue_reported"
                                    if liquidation is not None
                                    else "not_finite_for_mode"
                                ),
                                "marginCallLevel": "account_level_only",
                                "stopOutLevel": "account_level_only",
                            },
                            asOf=self._millis(row.get("updatedTime")),
                        )
                    )
            for query_name in ("get_open_orders", "get_order_history"):
                for row in sections.get((category, query_name), []):
                    symbol = str(row.get("symbol") or "").upper()
                    row_category = str(row.get("category") or category).lower()
                    instrument_type = self._instrument_type_for_category(row_category)
                    instrument_id = self._instrument_id_for_symbol(
                        account_id=account_id,
                        symbol=symbol,
                        instrument_type=instrument_type,
                        category=row_category,
                    )
                    external_order_id = str(row.get("orderId") or "")
                    route = get_order_route(
                        external_order_id=external_order_id, account_id=account_id
                    ) or get_order_route(
                        external_client_id=str(row.get("orderLinkId") or ""), account_id=account_id
                    )
                    if route is not None and route.account_id != account_id:
                        raise GatewayConfigurationError(
                            "Bybit order route account identity mismatch"
                        )
                    platform_order_id = (
                        route.platform_order_id
                        if route is not None
                        else f"external:{self.name}:{account_id}:{external_order_id}"
                    )
                    command_id = route.command_id if route is not None else platform_order_id
                    orders_by_id[external_order_id] = VenueOrderSnapshot(
                        source=self.name,
                        externalOrderId=external_order_id,
                        platformOrderId=platform_order_id,
                        commandId=command_id,
                        accountId=route.account_id if route is not None else account_id,
                        instrumentId=route.instrument_id if route is not None else instrument_id,
                        symbol=symbol,
                        side="buy" if str(row.get("side")) == "Buy" else "sell",
                        orderType="market" if str(row.get("orderType")) == "Market" else "limit",
                        quantity=Decimal(str(row.get("qty") or "0")),
                        price=self._optional_decimal(row.get("price")),
                        status=normalize_bybit_order_status(row.get("orderStatus")),
                        filledQuantity=Decimal(str(row.get("cumExecQty") or "0")),
                        remainingQuantity=Decimal(str(row.get("leavesQty") or "0")),
                        averageFillPrice=self._optional_decimal(row.get("avgPrice")),
                        reduceOnly=bool(row["reduceOnly"]) if "reduceOnly" in row else None,
                        timeInForce=str(row.get("timeInForce") or "") or None,
                        rejectReason=str(row.get("rejectReason") or "") or None,
                        cancelReason=str(row.get("cancelType") or "") or None,
                        occurredAt=self._millis(row.get("createdTime")),
                        asOf=self._millis(row.get("updatedTime")),
                        dataQualityState="complete" if route is not None else "external_only",
                    )
            for row in sections.get((category, "get_executions"), []):
                # Funding settlements share the executions endpoint but are not fills.
                if str(row.get("execType") or "Trade") != "Trade":
                    continue
                symbol = str(row.get("symbol") or "").upper()
                row_category = str(row.get("category") or category).lower()
                instrument_type = self._instrument_type_for_category(row_category)
                instrument_id = self._instrument_id_for_symbol(
                    account_id=account_id,
                    symbol=symbol,
                    instrument_type=instrument_type,
                    category=row_category,
                )
                external_order_id = str(row.get("orderId") or "unknown")
                external_fill_id = str(
                    row.get("execId") or f"{external_order_id}:{row.get('execTime')}"
                )
                route = get_order_route(external_order_id=external_order_id, account_id=account_id)
                if route is not None and route.account_id != account_id:
                    raise GatewayConfigurationError("Bybit fill route account identity mismatch")
                platform_order_id = (
                    route.platform_order_id
                    if route is not None
                    else f"external:{self.name}:{account_id}:{external_order_id}"
                )
                command_id = route.command_id if route is not None else platform_order_id
                fills_by_id[external_fill_id] = VenueFillSnapshot(
                    source=self.name,
                    externalFillId=external_fill_id,
                    externalOrderId=external_order_id,
                    platformOrderId=platform_order_id,
                    commandId=command_id,
                    accountId=route.account_id if route is not None else account_id,
                    instrumentId=route.instrument_id if route is not None else instrument_id,
                    symbol=symbol,
                    side="buy" if str(row.get("side")) == "Buy" else "sell",
                    quantity=Decimal(str(row.get("execQty") or "0")),
                    price=Decimal(str(row.get("execPrice") or "0")),
                    fee=Decimal(str(row["execFee"]))
                    if row.get("execFee") not in (None, "")
                    else None,
                    currency=str(
                        row.get("feeCurrency")
                        or (
                            self.settings.bybit_settle_coin
                            if row_category == "linear"
                            else "UNKNOWN"
                        )
                    ),
                    feeCurrencyQuality="reported"
                    if row.get("feeCurrency")
                    else "inferred_settlement"
                    if row_category == "linear"
                    else "unavailable",
                    occurredAt=self._millis(row.get("execTime")),
                    dataQualityState="complete" if route is not None else "external_only",
                )
        risk = (
            cast(Any, self).get_account_risk(
                account_id, wallet_response=wallet_response, include_asset_overview=True
            )
            if hasattr(self, "get_account_risk")
            else VenueAccountRiskSnapshot(
                source=self.name,
                accountId=account_id,
                currency="USD",
                equity=self._optional_decimal(
                    self._result_list(wallet_response)[0].get("totalEquity")
                ),
                availableBalance=self._optional_decimal(
                    self._result_list(wallet_response)[0].get("totalAvailableBalance")
                ),
                asOf=datetime.now(UTC),
                dataQualityState="partial",
            )
        )
        economic_events: list[VenueEconomicEventSnapshot] = []
        economic_quality = "complete"
        if include_history:
            try:
                economic_events = self.list_economic_events(
                    account_id=account_id,
                    start_time=requested_history_start,
                    end_time=history_end,
                )
            except Exception:
                economic_quality = "unavailable"
        else:
            history_start = history_end = None
            economic_quality = "not_requested"
        return VenueAccountSnapshot(
            source=self.name,
            accountId=account_id,
            venue="bybit",
            identity={
                "accountId": account_id,
                "categories": "|".join(categories),
            },
            balances=balances,
            positions=positions,
            orders=(
                sorted(orders_by_id.values(), key=lambda item: item.as_of, reverse=True)
                if include_history
                else []
            ),
            fills=(
                sorted(fills_by_id.values(), key=lambda item: item.occurred_at, reverse=True)
                if include_history
                else []
            ),
            accountRisk=risk,
            historyStart=history_start,
            historyEnd=history_end,
            economicEvents=economic_events,
            economicEventsQuality=economic_quality,
            asOf=risk.as_of,
            dataQualityState=risk.data_quality_state,
        )

    def get_capital_flows(self, *, account_id, start_time, end_time):
        from app.capital_flows import bybit_capital_flows

        return bybit_capital_flows(self, account_id, start_time, end_time)

    def _snapshot_pages(
        self,
        account_id: str,
        method_name: str,
        query: dict[str, object],
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        cursors: set[str] = set()
        current = dict(query)
        for _ in range(100):
            response = self._read_with_retry(
                account_id,
                lambda client: getattr(client, method_name)(**current),
            )
            self._require_success(response, f"Bybit {method_name} query failed")
            rows.extend(self._result_list(response))
            cursor = str((response.get("result") or {}).get("nextPageCursor") or "")
            if not cursor:
                return rows
            if cursor in cursors:
                raise GatewayConfigurationError("Bybit snapshot pagination did not advance")
            cursors.add(cursor)
            current["cursor"] = cursor
        raise GatewayConfigurationError("Bybit snapshot pagination limit exceeded")

    def _account_snapshot_order_query_kwargs(
        self,
        category: str,
        *,
        limit: int,
    ) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "category": category,
            "limit": limit,
        }
        if category == "linear":
            kwargs["settleCoin"] = self.settings.bybit_settle_coin
        return kwargs

    def _market_identity(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str | None,
        category: str | None,
    ) -> tuple[str, str]:
        normalized_category = (category or "").strip().lower() or None
        normalized_type = (instrument_type or "").strip().lower() or None
        if normalized_category is None:
            if normalized_type in {"crypto_spot", "spot"}:
                normalized_category = "spot"
            elif normalized_type in {"crypto_perp", "perp", "perpetual"}:
                normalized_category = self.settings.bybit_category.lower()
        if normalized_category is None:
            categories = self.settings.bybit_categories_for_account(account_id)
            normalized_category = (
                self.settings.bybit_category.lower()
                if self.settings.bybit_category.lower() in categories
                else categories[0]
            )
        resolved_type = self._instrument_type_for_category(normalized_category)
        if normalized_type and normalized_type not in {resolved_type, normalized_category}:
            raise GatewayConfigurationError(f"Bybit instrumentType/category mismatch for {symbol}")
        return resolved_type, normalized_category

    def _instrument_type_for_category(self, category: str) -> str:
        return "crypto_spot" if category == "spot" else "crypto_perp"

    def _instrument_id_for_symbol(
        self,
        *,
        account_id: str,
        symbol: str,
        instrument_type: str,
        category: str,
    ) -> str:
        normalized = symbol.upper()
        categories = self.settings.bybit_categories_for_account(account_id)
        candidates = (
            f"{normalized}|{category}",
            f"{normalized}|{instrument_type}",
            normalized,
        )
        for candidate in candidates:
            instrument_id = self.settings.bybit_instruments.get(candidate.upper())
            if instrument_id is None:
                continue
            if candidate == normalized and len(categories) > 1:
                break
            return instrument_id
        from app.live_route_store import list_instrument_routes

        # A symbol alone cannot join Spot and Perpetual. The account and the
        # original command's market together identify the native instrument.
        routed_ids = {
            route.instrument_id
            for route in list_instrument_routes(
                account_id=account_id, symbol=normalized, adapter=self.name
            )
            if self._route_category(route) == category
        }
        if len(routed_ids) > 1:
            raise GatewayConfigurationError(
                "Bybit account market has conflicting instrument routes"
            )
        if routed_ids:
            return next(iter(routed_ids))
        return f"monitor:bybit:{account_id}:{category}:{normalized}"

    def _command_category(self, command: SubmitOrderCommand) -> str:
        _, category = self._market_identity(
            account_id=command.account_id,
            symbol=command.symbol,
            instrument_type=command.instrument_type,
            category=None,
        )
        return category

    def _route_category(self, route) -> str:
        if route is not None:
            from app.journal import get_command

            record = get_command(route.command_id)
            if record is not None:
                return self._command_category(record.command)
        return self.settings.bybit_category

    def _order_market_fields(self, command: SubmitOrderCommand) -> dict[str, object]:
        category = self._command_category(command)
        if category == "spot":
            if command.reduce_only or command.execution_policy == "post_only_chase":
                raise GatewayRequestRejectedError("Bybit spot order has derivative-only settings")
            fields: dict[str, object] = {"category": "spot", "isLeverage": 0}
            if command.order_type == "market":
                fields["marketUnit"] = "baseCoin"
            return fields
        return {"category": category, "reduceOnly": command.reduce_only}

    def _client(self, account_id: str | None = None) -> Any:
        if self._injected_client is not None:
            return self._injected_client
        return self._connections.client(account_id or self._single_account())

    def _read_with_retry(self, account_id_or_operation, operation=None):
        from time import sleep

        from requests.exceptions import ConnectionError, Timeout

        if operation is None:
            account_id = self._single_account()
            operation = account_id_or_operation
        else:
            account_id = account_id_or_operation or self._single_account()
        try:
            return operation(self._client(account_id))
        except (ConnectionError, Timeout):
            # A reset can poison the requests connection pool. Rebuild the
            # account-owned session before the single bounded read retry;
            # invalid credentials and venue rejections are still not retried.
            if self._injected_client is None:
                self._connections.reset(account_id)
                sleep(0.2)
            return operation(self._client(account_id))

    def _market_data(self, account_id: str) -> BybitMarketData:
        with self._market_reader_lock:
            reader = self._market_readers.get(account_id)
            if reader is None:

                def read(method: str, **params):
                    response = self._read_with_retry(
                        account_id, lambda client: getattr(client, method)(**params)
                    )
                    self._require_success(response, "Bybit market read failed")
                    return response

                reader = BybitMarketData(read)
                self._market_readers[account_id] = reader
            return reader

    def close(self) -> None:
        with self._market_reader_lock:
            for reader in self._market_readers.values():
                reader.close()
            self._market_readers.clear()
        self._connections.close()

    def _assert_account(self, account_id: str) -> None:
        if account_id not in self.settings.bybit_accounts:
            raise GatewayConfigurationError("Account is not mapped to Bybit live adapter")

    def _assert_write_account(self, account_id: str) -> None:
        if account_id in self.settings.bybit_read_only_accounts:
            raise GatewayRequestRejectedError("Bybit account is configured read-only")

    def _single_account(self) -> str:
        accounts = sorted(self.settings.bybit_accounts)
        if len(accounts) != 1:
            raise GatewayConfigurationError("Bybit query requires an explicit accountId")
        return accounts[0]

    def _resolve_route(
        self,
        *,
        platform_order_id: str | None,
        external_order_id: str | None,
    ):
        if platform_order_id is not None:
            route = get_order_route(platform_order_id=platform_order_id)
        elif external_order_id is not None:
            route = get_order_route(external_order_id=external_order_id)
        else:
            raise ValueError("Order identity is required")
        if route is not None and route.adapter != self.name:
            return None
        return route

    def _market_reference_price(self, client, command: SubmitOrderCommand) -> Decimal:
        try:
            response = client.get_tickers(
                category=self._command_category(command),
                symbol=command.symbol.upper(),
            )
            self._require_success(response, "Bybit ticker query failed")
            rows = self._result_list(response)
            if not rows:
                raise GatewayConfigurationError("Bybit ticker query returned no data")
            row = rows[0]
            price = row.get("markPrice") or row.get("lastPrice") or row.get("indexPrice")
            return Decimal(str(price))
        except GatewayConfigurationError:
            raise
        except Exception as exc:
            raise GatewayConfigurationError("Unable to obtain Bybit reference price") from exc

    def _order_snapshot(self, row: dict[str, object], route) -> VenueOrderSnapshot:
        return VenueOrderSnapshot(
            source=self.name,
            externalOrderId=str(row.get("orderId") or route.external_order_id or "unknown"),
            platformOrderId=route.platform_order_id,
            commandId=route.command_id,
            accountId=route.account_id,
            instrumentId=route.instrument_id,
            symbol=route.symbol,
            side="buy" if str(row.get("side")) == "Buy" else "sell",
            orderType="market" if str(row.get("orderType")) == "Market" else "limit",
            quantity=Decimal(str(row.get("qty") or "0")),
            price=self._optional_decimal(row.get("price")),
            status=normalize_bybit_order_status(row.get("orderStatus")),
            filledQuantity=Decimal(str(row.get("cumExecQty") or "0")),
            averageFillPrice=self._optional_decimal(row.get("avgPrice")),
            occurredAt=self._millis(row.get("createdTime")),
            asOf=self._millis(row.get("updatedTime")),
        )

    @staticmethod
    def _require_success(response: dict[str, object], message: str) -> None:
        raw_code = response.get("retCode")
        code = int(cast(str | int | float, raw_code or 0))
        if code != 0:
            detail = str(response.get("retMsg") or message)
            raise GatewayRequestRejectedError(f"{message}: {detail}")

    @staticmethod
    def _unknown_error(message: str, exc: Exception) -> GatewayResultUnknownError:
        detail = str(exc).strip()
        if detail:
            return GatewayResultUnknownError(f"{message}: {exc.__class__.__name__}: {detail}")
        return GatewayResultUnknownError(f"{message}: {exc.__class__.__name__}")

    @staticmethod
    def _result_list(response: dict[str, object]) -> list[dict[str, object]]:
        result = response.get("result") or {}
        rows = result.get("list") if isinstance(result, dict) else None
        return list(rows or [])

    @staticmethod
    def _optional_decimal(value: object) -> Decimal | None:
        if value in {None, ""}:
            return None
        return Decimal(str(value))

    @staticmethod
    def _available_balance(
        coin: dict[str, object],
        *,
        account_available: Decimal | None,
    ) -> Decimal | None:
        # Deprecated withdraw/borrow fields and account-wide USD are not coin cash.
        fields = (
            "walletBalance",
            "locked",
            "totalOrderIM",
            "totalPositionIM",
            "bonus",
            "spotBorrow",
        )
        if any(coin.get(field) in {None, ""} for field in fields):
            return None
        cash = Decimal(str(coin["walletBalance"])) - sum(
            (Decimal(str(coin[field])) for field in fields[1:]),
            Decimal("0"),
        )
        if cash <= 0:
            return Decimal("0")
        if account_available is None:
            # Isolated margin exposes the coin-level initial margins above.
            return cash
        equity = Decimal(str(coin.get("equity") or "0"))
        usd_value = Decimal(str(coin.get("usdValue") or "0"))
        if equity <= 0 or usd_value <= 0:
            return None
        return max(Decimal("0"), min(cash, account_available * equity / usd_value))

    @staticmethod
    def _millis(value: object) -> datetime:
        if value in {None, ""}:
            return datetime.now(UTC)
        timestamp_ms = int(cast(str | int | float, value))
        return datetime.fromtimestamp(timestamp_ms / 1000, UTC)

    def _micros(self, value: object) -> datetime | None:
        if value in {None, ""}:
            return None
        try:
            return datetime.fromtimestamp(int(str(value)) / 1_000_000, UTC)
        except (TypeError, ValueError, OSError):
            return None

    def _dependency_available(self) -> bool:
        if self._injected_client is not None:
            return True
        try:
            import pybit  # noqa: F401
        except ImportError:
            return False
        return True
