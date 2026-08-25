from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TypedDict
from uuid import uuid4

from fastapi import HTTPException

from app.database import connection
from app.live_venue_snapshot_sync import ensure_sync_schema
from app.schemas import (
    AccountResponse,
    AccountRiskSnapshotResponse,
    BalanceSnapshotResponse,
    ContractSpecificationResponse,
    CreateOrderRequest,
    CreateTradeCommandRequest,
    FillResponse,
    InstrumentResponse,
    OrderDetailResponse,
    PnlResponse,
    PositionResponse,
    StrategyAccountBindingResponse,
    StrategyAccountSnapshotResponse,
    StrategyDefinitionResponse,
    StrategyInstanceResponse,
    StrategyManagementOverviewResponse,
    StrategyNavSnapshotResponse,
    StrategyPnlResponse,
    TradeCommandResponse,
)
from app.trading import decimal_text, submit_order
from app.v1_readiness import get_strategy_v1_readiness


class ManagementDeskMetadata(TypedDict):
    desk_key: str
    category: str
    sort_order: int


MANAGEMENT_DESK_METADATA: dict[str, ManagementDeskMetadata] = {
    "funding_arbitrage": {"desk_key": "funding", "category": "arbitrage", "sort_order": 10},
    "cross_venue_spread": {
        "desk_key": "crossSpread",
        "category": "arbitrage",
        "sort_order": 20,
    },
    "home_abroad_spread": {
        "desk_key": "domesticOverseas",
        "category": "arbitrage",
        "sort_order": 30,
    },
    "bottom_fishing": {"desk_key": "dip", "category": "directional", "sort_order": 40},
    "short_term_l": {
        "desk_key": "shortLineTraderL",
        "category": "intraday",
        "sort_order": 50,
    },
    "short_term_w": {
        "desk_key": "shortLineTraderW",
        "category": "intraday",
        "sort_order": 60,
    },
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def optional_decimal(value: object) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def list_strategy_definitions() -> list[StrategyDefinitionResponse]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT id, strategy_key, name, v1_scope, status, description
            FROM strategy_definitions
            ORDER BY
                CASE v1_scope
                    WHEN 'closed_loop' THEN 1
                    WHEN 'reserved' THEN 2
                    ELSE 3
                END,
                name
            """
        ).fetchall()
    return [
        StrategyDefinitionResponse(
            strategyId=row["id"],
            strategyKey=row["strategy_key"],
            name=row["name"],
            v1Scope=row["v1_scope"],
            status=row["status"],
            description=row["description"],
        )
        for row in rows
    ]


def list_strategy_instances() -> list[StrategyInstanceResponse]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT si.id, si.strategy_definition_id, sd.strategy_key, sd.name AS strategy_name,
                   sv.version, si.name, si.trading_mode, si.status, si.capital_base,
                   si.base_currency, si.data_quality_state
            FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            JOIN strategy_versions sv ON sv.id = si.strategy_version_id
            ORDER BY sd.strategy_key
            """
        ).fetchall()
    return [strategy_instance_from_row(row) for row in rows]


def list_strategy_management_overview() -> list[StrategyManagementOverviewResponse]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT si.id,
                   si.strategy_definition_id,
                   sd.strategy_key,
                   sd.name AS strategy_name,
                   si.name AS instance_name,
                   si.trading_mode,
                   si.status,
                   si.data_quality_state,
                   sd.v1_scope,
                   COUNT(sab.id) AS binding_count,
                   latest_run.status AS latest_run_status,
                   latest_run.created_at AS latest_run_at,
                   COALESCE(
                       MAX(
                           CASE
                               WHEN sab.status = 'active' AND sab.capability = 'trade_and_read'
                               THEN 'trade_and_read'
                           END
                       ),
                       MAX(
                           CASE
                               WHEN sab.status = 'active' AND sab.capability = 'read_only'
                               THEN 'read_only'
                           END
                       ),
                       'unbound'
                   ) AS active_capability,
                   MAX(
                       CASE
                           WHEN sab.role = 'primary' AND sab.status = 'active'
                           THEN a.account_code
                       END
                   ) AS primary_account_code,
                   MAX(
                       CASE
                           WHEN sab.role = 'primary' AND sab.status = 'active'
                           THEN a.status
                       END
                   ) AS primary_account_status,
                   MAX(
                       CASE
                           WHEN sab.role = 'primary' AND sab.status = 'active'
                           THEN a.data_quality_state
                       END
                   ) AS primary_account_data_quality_state
            FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            LEFT JOIN strategy_runs latest_run
              ON latest_run.id = (
                  SELECT sr.id
                  FROM strategy_runs sr
                  WHERE sr.strategy_instance_id = si.id
                  ORDER BY sr.created_at DESC, sr.id DESC
                  LIMIT 1
              )
            LEFT JOIN strategy_account_bindings sab ON sab.strategy_instance_id = si.id
            LEFT JOIN accounts a ON a.id = sab.account_id
            GROUP BY
                si.id,
                si.strategy_definition_id,
                sd.strategy_key,
                sd.name,
                si.name,
                si.trading_mode,
                si.status,
                si.data_quality_state,
                sd.v1_scope
            """
        ).fetchall()
        binding_rows = db.execute(
            """
            SELECT
                sab.strategy_instance_id,
                sab.role,
                sab.status,
                a.account_code,
                a.status AS account_status,
                a.data_quality_state
            FROM strategy_account_bindings sab
            JOIN accounts a ON a.id = sab.account_id
            WHERE sab.status = 'active'
            ORDER BY sab.strategy_instance_id,
                     CASE sab.role
                         WHEN 'primary' THEN 1
                         WHEN 'venue_a' THEN 2
                         WHEN 'mt5_leg' THEN 3
                         WHEN 'local_test' THEN 9
                         ELSE 5
                     END,
                     a.account_code
            """
        ).fetchall()

    bindings_by_strategy: dict[str, list[dict[str, str | None]]] = {}
    for binding in binding_rows:
        bindings_by_strategy.setdefault(str(binding["strategy_instance_id"]), []).append(
            {
                "role": str(binding["role"]),
                "account_code": str(binding["account_code"]),
                "account_status": (
                    str(binding["account_status"])
                    if binding["account_status"] is not None
                    else None
                ),
                "data_quality_state": (
                    str(binding["data_quality_state"])
                    if binding["data_quality_state"] is not None
                    else None
                ),
            }
        )

    overview: list[StrategyManagementOverviewResponse] = []
    for row in rows:
        metadata = MANAGEMENT_DESK_METADATA.get(row["strategy_key"])
        if metadata is None:
            continue
        active_bindings = bindings_by_strategy.get(str(row["id"]), [])
        display_account_code = row["primary_account_code"]
        display_account_status = row["primary_account_status"]
        display_account_quality = row["primary_account_data_quality_state"]
        if display_account_code is None:
            non_local_test = [
                binding for binding in active_bindings if binding["role"] != "local_test"
            ]
            if non_local_test:
                display_account_code = " / ".join(
                    str(binding["account_code"]) for binding in non_local_test
                )
                display_account_status = next(
                    (
                        binding["account_status"]
                        for binding in non_local_test
                        if binding["account_status"] is not None
                    ),
                    None,
                )
                display_account_quality = next(
                    (
                        binding["data_quality_state"]
                        for binding in non_local_test
                        if binding["data_quality_state"] is not None
                    ),
                    None,
                )
        execution_readiness = (
            None
            if row["v1_scope"] == "read_only"
            else get_strategy_v1_readiness(row["id"])
        )
        overview.append(
            StrategyManagementOverviewResponse(
                deskKey=str(metadata["desk_key"]),
                sortOrder=int(metadata["sort_order"]),
                strategyInstanceId=row["id"],
                strategyId=row["strategy_definition_id"],
                strategyKey=row["strategy_key"],
                strategyName=row["strategy_name"],
                instanceName=row["instance_name"],
                category=str(metadata["category"]),
                v1Scope=row["v1_scope"],
                operatingStatus=row["status"],
                tradingMode=row["trading_mode"],
                dataQualityState=row["data_quality_state"],
                activeCapability=row["active_capability"],
                bindingCount=int(row["binding_count"]),
                latestRunStatus=row["latest_run_status"],
                latestRunAt=row["latest_run_at"],
                primaryAccountCode=display_account_code,
                primaryAccountStatus=display_account_status,
                primaryAccountDataQualityState=display_account_quality,
                executionReadiness=execution_readiness,
            )
        )
    overview.sort(key=lambda item: (item.sort_order, item.strategy_name))
    return overview


def get_strategy_instance(strategy_instance_id: str) -> StrategyInstanceResponse:
    with connection() as db:
        row = db.execute(
            """
            SELECT si.id, si.strategy_definition_id, sd.strategy_key, sd.name AS strategy_name,
                   sv.version, si.name, si.trading_mode, si.status, si.capital_base,
                   si.base_currency, si.data_quality_state
            FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            JOIN strategy_versions sv ON sv.id = si.strategy_version_id
            WHERE si.id = ?
            """,
            (strategy_instance_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy instance not found")
    return strategy_instance_from_row(row)


def strategy_instance_from_row(row) -> StrategyInstanceResponse:
    return StrategyInstanceResponse(
        strategyInstanceId=row["id"],
        strategyId=row["strategy_definition_id"],
        strategyKey=row["strategy_key"],
        strategyName=row["strategy_name"],
        version=row["version"],
        name=row["name"],
        tradingMode=row["trading_mode"],
        status=row["status"],
        capitalBase=optional_decimal(row["capital_base"]),
        baseCurrency=row["base_currency"],
        dataQualityState=row["data_quality_state"],
    )


def list_strategy_account_bindings(
    strategy_instance_id: str,
) -> list[StrategyAccountBindingResponse]:
    get_strategy_instance(strategy_instance_id)
    with connection() as db:
        rows = db.execute(
            """
            SELECT sab.id, sab.strategy_instance_id, sab.account_id, a.account_code,
                   sab.role, sab.capability, sab.max_notional, sab.status
            FROM strategy_account_bindings sab
            JOIN accounts a ON a.id = sab.account_id
            WHERE sab.strategy_instance_id = ?
            ORDER BY sab.role
            """,
            (strategy_instance_id,),
        ).fetchall()
    return [
        StrategyAccountBindingResponse(
            bindingId=row["id"],
            strategyInstanceId=row["strategy_instance_id"],
            accountId=row["account_id"],
            accountCode=row["account_code"],
            role=row["role"],
            capability=row["capability"],
            maxNotional=optional_decimal(row["max_notional"]),
            status=row["status"],
        )
        for row in rows
    ]


def get_strategy_account_snapshot(
    strategy_instance_id: str,
) -> StrategyAccountSnapshotResponse:
    ensure_sync_schema()
    bindings = list_strategy_account_bindings(strategy_instance_id)
    binding = next(
        (item for item in bindings if item.role == "primary" and item.status == "active"),
        None,
    )
    if binding is None:
        return StrategyAccountSnapshotResponse(
            strategyInstanceId=strategy_instance_id,
            accountId=None,
            accountCode=None,
            capability=None,
            dataQualityState="unbound",
            asOf=None,
            balance=None,
            positions=[],
            orders=[],
            fills=[],
            pnl=None,
            syncStatus="unbound",
            syncErrorCode="account_unbound",
        )

    with connection() as db:
        sync_row = db.execute(
            """
            SELECT status, error_code, last_attempt_at, last_success_at, updated_at
            FROM account_sync_status
            WHERE account_id = ?
            """,
            (binding.account_id,),
        ).fetchone()
        balance_row = db.execute(
            """
            SELECT id, account_id, currency, equity, available_balance, source,
                   data_quality_state, as_of
            FROM balance_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC
            LIMIT 1
            """,
            (binding.account_id,),
        ).fetchone()
        pnl_rows = db.execute(
            """
            SELECT realized_pnl, trading_pnl, fees
            FROM pnl_results
            WHERE account_id = ?
            """,
            (binding.account_id,),
        ).fetchall()
        risk_row = db.execute(
            """
            SELECT account_id, as_of, currency, equity, margin, free_margin, margin_level,
                   data_quality_state
            FROM account_risk_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC
            LIMIT 1
            """,
            (binding.account_id,),
        ).fetchone()

    balance = (
        BalanceSnapshotResponse(
            snapshotId=balance_row["id"],
            accountId=balance_row["account_id"],
            currency=balance_row["currency"],
            equity=Decimal(balance_row["equity"]),
            availableBalance=Decimal(balance_row["available_balance"]),
            source=balance_row["source"],
            dataQualityState=balance_row["data_quality_state"],
            asOf=balance_row["as_of"],
        )
        if balance_row is not None
        else None
    )
    positions = [
        PositionResponse(
            accountId=row["account_id"],
            instrumentId=row["instrument_id"],
            netQuantity=Decimal(row["net_quantity"]),
            averagePrice=optional_decimal(row["average_price"]),
        )
        for row in list_positions(binding.account_id)
    ]
    orders = [item for item in list_orders() if item.account_id == binding.account_id]
    fills = [item for item in list_fills() if item.account_id == binding.account_id]
    pnl = (
        PnlResponse(
            accountId=binding.account_id,
            instrumentId="account_total",
            # SQLite's SUM can coerce DECIMAL text through binary float. Keep
            # financial aggregation in Decimal from the persisted strings.
            realizedPnl=sum((Decimal(row["realized_pnl"]) for row in pnl_rows), Decimal("0")),
            tradingPnl=sum((Decimal(row["trading_pnl"]) for row in pnl_rows), Decimal("0")),
            fees=sum((Decimal(row["fees"]) for row in pnl_rows), Decimal("0")),
        )
        if pnl_rows
        else None
    )
    account_risk = (
        AccountRiskSnapshotResponse(
            accountId=risk_row["account_id"],
            currency=risk_row["currency"],
            equity=optional_decimal(risk_row["equity"]),
            margin=optional_decimal(risk_row["margin"]),
            freeMargin=optional_decimal(risk_row["free_margin"]),
            marginLevel=optional_decimal(risk_row["margin_level"]),
            dataQualityState=risk_row["data_quality_state"],
            asOf=risk_row["as_of"],
        )
        if risk_row is not None
        else None
    )
    sync_status = str(sync_row["status"]) if sync_row is not None else "waiting_initial_sync"
    sync_error = (
        str(sync_row["error_code"])
        if sync_row is not None and sync_row["error_code"]
        else None
    )
    quality = (
        balance.data_quality_state
        if balance is not None
        else (
            sync_status
            if sync_status in {"unbound", "waiting_initial_sync", "syncing", "stale"}
            else "unavailable"
        )
    )
    return StrategyAccountSnapshotResponse(
        strategyInstanceId=strategy_instance_id,
        accountId=binding.account_id,
        accountCode=binding.account_code,
        capability=binding.capability,
        dataQualityState=quality,
        asOf=(
            balance.as_of
            if balance is not None
            else (account_risk.as_of if account_risk is not None else None)
        ),
        balance=balance,
        accountRisk=account_risk,
        positions=positions,
        orders=orders,
        fills=fills,
        pnl=pnl,
        syncStatus=sync_status,
        syncErrorCode=sync_error,
    )


def list_accounts() -> list[AccountResponse]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT a.id, a.account_code, a.name, a.venue_id, v.venue_code,
                   a.account_type, a.environment, a.base_currency, a.credential_ref,
                   a.status, a.data_quality_state
            FROM accounts a
            JOIN venues v ON v.id = a.venue_id
            ORDER BY a.account_code
            """
        ).fetchall()
    return [account_from_row(row) for row in rows]


def get_account(account_id: str) -> AccountResponse:
    with connection() as db:
        row = db.execute(
            """
            SELECT a.id, a.account_code, a.name, a.venue_id, v.venue_code,
                   a.account_type, a.environment, a.base_currency, a.credential_ref,
                   a.status, a.data_quality_state
            FROM accounts a
            JOIN venues v ON v.id = a.venue_id
            WHERE a.id = ?
            """,
            (account_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account_from_row(row)


def account_from_row(row) -> AccountResponse:
    return AccountResponse(
        accountId=row["id"],
        accountCode=row["account_code"],
        name=row["name"],
        venueId=row["venue_id"],
        venueCode=row["venue_code"],
        accountType=row["account_type"],
        environment=row["environment"],
        baseCurrency=row["base_currency"],
        credentialRef=row["credential_ref"],
        status=row["status"],
        dataQualityState=row["data_quality_state"],
    )


def get_latest_balance(account_id: str) -> BalanceSnapshotResponse:
    account = get_account(account_id)
    with connection() as db:
        latest = db.execute(
            """
            SELECT as_of
            FROM balance_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC
            LIMIT 1
            """,
            (account_id,),
        ).fetchone()
        if latest is None:
            raise HTTPException(status_code=404, detail="Balance snapshot not found")
        rows = db.execute(
            """
            SELECT id, account_id, currency, equity, available_balance, source,
                   data_quality_state, as_of
            FROM balance_snapshots
            WHERE account_id = ? AND as_of = ?
            ORDER BY id ASC
            """,
            (account_id, latest["as_of"]),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Balance snapshot not found")
    representative = rows[0]
    currencies = {str(row["currency"]) for row in rows if row["currency"]}
    equity = sum((Decimal(str(row["equity"])) for row in rows), Decimal("0"))
    available_balance = max(
        (Decimal(str(row["available_balance"])) for row in rows),
        default=Decimal("0"),
    )
    data_quality_state = (
        "partial"
        if any(str(row["data_quality_state"]) != "complete" for row in rows)
        else str(representative["data_quality_state"])
    )
    currency = next(iter(currencies)) if len(currencies) == 1 else account.base_currency
    return BalanceSnapshotResponse(
        snapshotId=representative["id"],
        accountId=representative["account_id"],
        currency=currency,
        equity=equity,
        availableBalance=available_balance,
        source=representative["source"],
        dataQualityState=data_quality_state,
        asOf=representative["as_of"],
    )


def list_instruments() -> list[InstrumentResponse]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT i.id, i.instrument_code, i.name, i.instrument_type, i.base_currency,
                   i.quote_currency, i.settle_currency, i.quantity_unit,
                   i.data_quality_state, cs.version, cs.price_tick, cs.min_order_quantity,
                   cs.quantity_step, cs.contract_multiplier,
                   cs.data_quality_state AS contract_quality
            FROM instruments i
            LEFT JOIN contract_specifications cs ON cs.instrument_id = i.id
            ORDER BY i.instrument_code
            """
        ).fetchall()
    return [instrument_from_row(row) for row in rows]


def get_instrument(instrument_id: str) -> InstrumentResponse:
    with connection() as db:
        row = db.execute(
            """
            SELECT i.id, i.instrument_code, i.name, i.instrument_type, i.base_currency,
                   i.quote_currency, i.settle_currency, i.quantity_unit,
                   i.data_quality_state, cs.version, cs.price_tick, cs.min_order_quantity,
                   cs.quantity_step, cs.contract_multiplier,
                   cs.data_quality_state AS contract_quality
            FROM instruments i
            LEFT JOIN contract_specifications cs ON cs.instrument_id = i.id
            WHERE i.id = ?
            """,
            (instrument_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return instrument_from_row(row)


def instrument_from_row(row) -> InstrumentResponse:
    contract = None
    if row["version"] is not None:
        contract = ContractSpecificationResponse(
            version=row["version"],
            priceTick=Decimal(row["price_tick"]),
            minOrderQuantity=Decimal(row["min_order_quantity"]),
            quantityStep=Decimal(row["quantity_step"]),
            contractMultiplier=Decimal(row["contract_multiplier"]),
            dataQualityState=row["contract_quality"],
        )
    return InstrumentResponse(
        instrumentId=row["id"],
        instrumentCode=row["instrument_code"],
        name=row["name"],
        instrumentType=row["instrument_type"],
        baseCurrency=row["base_currency"],
        quoteCurrency=row["quote_currency"],
        settleCurrency=row["settle_currency"],
        quantityUnit=row["quantity_unit"],
        dataQualityState=row["data_quality_state"],
        contract=contract,
    )


def list_positions(account_id: str) -> list:
    get_account(account_id)
    with connection() as db:
        return db.execute(
            """
            SELECT account_id, instrument_id, net_quantity, average_price
            FROM positions
            WHERE account_id = ?
            ORDER BY instrument_id
            """,
            (account_id,),
        ).fetchall()


def create_trade_command(request: CreateTradeCommandRequest) -> TradeCommandResponse:
    created_at = now_iso()

    get_strategy_instance(request.strategy_instance_id)
    get_account(request.account_id)
    get_instrument(request.instrument_id)

    with connection() as db:
        existing = db.execute(
            """
            SELECT tc.id, tc.idempotency_key, tc.strategy_instance_id, tc.account_id,
                   tc.instrument_id, tc.status, tc.created_at, tc.updated_at, o.id AS order_id
            FROM trade_commands tc
            LEFT JOIN orders o ON o.command_id = tc.id
            WHERE tc.idempotency_key = ?
            """,
            (request.idempotency_key,),
        ).fetchone()
    if existing is not None:
        return trade_command_from_row(existing)

    trade_command_id = str(uuid4())
    with connection() as db:
        db.execute(
            """
            INSERT INTO trade_commands (
                id, idempotency_key, strategy_instance_id, account_id, instrument_id,
                command_type, side, order_type, quantity, price, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_command_id,
                request.idempotency_key,
                request.strategy_instance_id,
                request.account_id,
                request.instrument_id,
                "create_order",
                request.side,
                request.order_type,
                decimal_text(request.quantity),
                decimal_text(request.price) if request.price is not None else None,
                "accepted",
                created_at,
                created_at,
            ),
        )
        db.execute(
            """
            INSERT INTO risk_decisions (id, subject_type, subject_id, decision, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "trade_command",
                trade_command_id,
                "approved",
                "p1_minimal_check",
                created_at,
            ),
        )
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "trade_command_created",
                "trade_command",
                trade_command_id,
                "{}",
                created_at,
            ),
        )

    order = submit_order(
        CreateOrderRequest(
            accountId=request.account_id,
            instrumentId=request.instrument_id,
            symbol=request.symbol,
            side=request.side,
            orderType=request.order_type,
            quantity=request.quantity,
            price=request.price,
        ),
        command_id=trade_command_id,
    )

    with connection() as db:
        db.execute(
            "UPDATE trade_commands SET status = ?, updated_at = ? WHERE id = ?",
            (order.status, now_iso(), trade_command_id),
        )
        row = db.execute(
            """
            SELECT tc.id, tc.idempotency_key, tc.strategy_instance_id, tc.account_id,
                   tc.instrument_id, tc.status, tc.created_at, tc.updated_at, o.id AS order_id
            FROM trade_commands tc
            LEFT JOIN orders o ON o.command_id = tc.id
            WHERE tc.id = ?
            """,
            (trade_command_id,),
        ).fetchone()
    return trade_command_from_row(row)


def get_trade_command(trade_command_id: str) -> TradeCommandResponse:
    with connection() as db:
        row = db.execute(
            """
            SELECT tc.id, tc.idempotency_key, tc.strategy_instance_id, tc.account_id,
                   tc.instrument_id, tc.status, tc.created_at, tc.updated_at, o.id AS order_id
            FROM trade_commands tc
            LEFT JOIN orders o ON o.command_id = tc.id
            WHERE tc.id = ?
            """,
            (trade_command_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Trade command not found")
    return trade_command_from_row(row)


def trade_command_from_row(row) -> TradeCommandResponse:
    return TradeCommandResponse(
        tradeCommandId=row["id"],
        idempotencyKey=row["idempotency_key"],
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        platformOrderId=row["order_id"],
        status=row["status"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def list_orders() -> list[OrderDetailResponse]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT id, command_id, account_id, instrument_id, symbol, side, order_type,
                   quantity, price, status, external_order_id, created_at, updated_at
            FROM orders
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [order_from_row(row) for row in rows]


def get_order(order_id: str) -> OrderDetailResponse:
    with connection() as db:
        row = db.execute(
            """
            SELECT id, command_id, account_id, instrument_id, symbol, side, order_type,
                   quantity, price, status, external_order_id, created_at, updated_at
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order_from_row(row)


def order_from_row(row) -> OrderDetailResponse:
    return OrderDetailResponse(
        orderId=row["id"],
        commandId=row["command_id"],
        status=row["status"],
        externalOrderId=row["external_order_id"],
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        symbol=row["symbol"],
        side=row["side"],
        orderType=row["order_type"],
        quantity=Decimal(row["quantity"]),
        price=optional_decimal(row["price"]),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def list_fills() -> list[FillResponse]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT id, order_id, account_id, instrument_id, side, quantity, price, occurred_at
            FROM fills
            ORDER BY occurred_at DESC
            """
        ).fetchall()
    return [
        FillResponse(
            fillId=row["id"],
            orderId=row["order_id"],
            accountId=row["account_id"],
            instrumentId=row["instrument_id"],
            side=row["side"],
            quantity=Decimal(row["quantity"]),
            price=Decimal(row["price"]),
            occurredAt=row["occurred_at"],
        )
        for row in rows
    ]


def get_strategy_pnl(strategy_instance_id: str) -> StrategyPnlResponse:
    instance = get_strategy_instance(strategy_instance_id)
    with connection() as db:
        rows = db.execute(
            """
            SELECT pr.realized_pnl, pr.trading_pnl, pr.fees
            FROM strategy_account_bindings sab
            JOIN pnl_results pr ON pr.account_id = sab.account_id
            WHERE sab.strategy_instance_id = ?
            """,
            (strategy_instance_id,),
        ).fetchall()
    realized_pnl = sum((Decimal(row["realized_pnl"]) for row in rows), Decimal("0"))
    trading_pnl = sum((Decimal(row["trading_pnl"]) for row in rows), Decimal("0"))
    fees = sum((Decimal(row["fees"]) for row in rows), Decimal("0"))
    return StrategyPnlResponse(
        strategyInstanceId=strategy_instance_id,
        realizedPnl=realized_pnl,
        tradingPnl=trading_pnl,
        fees=fees,
        currency=instance.base_currency,
        dataQualityState="complete",
    )


def list_nav_snapshots(strategy_instance_id: str) -> list[StrategyNavSnapshotResponse]:
    get_strategy_instance(strategy_instance_id)
    with connection() as db:
        rows = db.execute(
            """
            SELECT id, strategy_instance_id, valuation_time, equity, capital_base,
                   nav, currency, data_quality_state
            FROM strategy_nav_snapshots
            WHERE strategy_instance_id = ?
            ORDER BY valuation_time DESC
            """,
            (strategy_instance_id,),
        ).fetchall()
    return [nav_from_row(row) for row in rows]


def run_nav_snapshot(strategy_instance_id: str) -> StrategyNavSnapshotResponse:
    instance = get_strategy_instance(strategy_instance_id)
    if instance.capital_base is None or instance.capital_base <= 0:
        raise HTTPException(status_code=422, detail="Strategy instance has no valid capital base")

    with connection() as db:
        balance = db.execute(
            """
            SELECT bs.equity
            FROM strategy_account_bindings sab
            JOIN balance_snapshots bs ON bs.account_id = sab.account_id
            WHERE sab.strategy_instance_id = ?
            ORDER BY bs.as_of DESC
            LIMIT 1
            """,
            (strategy_instance_id,),
        ).fetchone()

    equity = Decimal(balance["equity"]) if balance is not None else Decimal("0")
    nav = equity / instance.capital_base
    created_at = now_iso()
    snapshot_id = str(uuid4())

    with connection() as db:
        db.execute(
            """
            INSERT INTO strategy_nav_snapshots (
                id, strategy_instance_id, valuation_time, equity, capital_base,
                nav, currency, data_quality_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                strategy_instance_id,
                created_at,
                decimal_text(equity),
                decimal_text(instance.capital_base),
                decimal_text(nav),
                instance.base_currency,
                "complete" if balance is not None else "partial",
                created_at,
            ),
        )
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "strategy_nav_snapshot_created",
                "strategy_instance",
                strategy_instance_id,
                "{}",
                created_at,
            ),
        )
        row = db.execute(
            """
            SELECT id, strategy_instance_id, valuation_time, equity, capital_base,
                   nav, currency, data_quality_state
            FROM strategy_nav_snapshots
            WHERE id = ?
            """,
            (snapshot_id,),
        ).fetchone()
    return nav_from_row(row)


def nav_from_row(row) -> StrategyNavSnapshotResponse:
    return StrategyNavSnapshotResponse(
        snapshotId=row["id"],
        strategyInstanceId=row["strategy_instance_id"],
        valuationTime=row["valuation_time"],
        equity=Decimal(row["equity"]),
        capitalBase=Decimal(row["capital_base"]),
        nav=Decimal(row["nav"]),
        currency=row["currency"],
        dataQualityState=row["data_quality_state"],
    )
