from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import TypedDict
from uuid import uuid4

from fastapi import HTTPException

from app.database import connection
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
    StrategyDailyPnlPointResponse,
    StrategyDefinitionResponse,
    StrategyEquityHistoryPointResponse,
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
                   COUNT(CASE WHEN sab.status='active' AND sab.role!='local_test'
                              AND a.status='active' THEN sab.id END) AS binding_count,
                   latest_run.status AS latest_run_status,
                   latest_run.created_at AS latest_run_at,
                   COALESCE(
                       MAX(
                           CASE
                               WHEN sab.status = 'active' AND sab.capability = 'trade_and_read'
                                 AND sab.role != 'local_test' AND a.status = 'active'
                               THEN 'trade_and_read'
                           END
                       ),
                       MAX(
                           CASE
                               WHEN sab.status = 'active' AND sab.capability = 'read_only'
                                 AND sab.role != 'local_test' AND a.status = 'active'
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
                a.data_quality_state,
                a.environment,
                sync.status AS sync_status,
                sync.last_success_at,
                (
                    SELECT bs.data_quality_state
                    FROM balance_snapshots bs
                    WHERE bs.account_id = a.id
                    ORDER BY bs.as_of DESC, bs.id DESC
                    LIMIT 1
                ) AS latest_balance_quality,
                (
                    SELECT ars.data_quality_state
                    FROM account_risk_snapshots ars
                    WHERE ars.account_id = a.id
                    ORDER BY ars.as_of DESC
                    LIMIT 1
                ) AS latest_risk_quality,
                (SELECT ars.as_of FROM account_risk_snapshots ars
                 WHERE ars.account_id=a.id ORDER BY ars.as_of DESC LIMIT 1) AS latest_risk_as_of
            FROM strategy_account_bindings sab
            JOIN accounts a ON a.id = sab.account_id
            LEFT JOIN account_sync_status sync ON sync.account_id = a.id
            WHERE sab.status = 'active' AND sab.role != 'local_test' AND a.status='active'
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
        sync_status = str(binding["sync_status"]) if binding["sync_status"] else None
        if sync_status in {"ready", "syncing"}:
            effective_quality = (
                binding["latest_risk_quality"] or binding["latest_balance_quality"] or "unavailable"
            )
            stamp = binding["latest_risk_as_of"] or binding["last_success_at"]
            if (
                stamp is None
                or (
                    datetime.now(UTC) - datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
                ).total_seconds()
                > 90
            ):
                effective_quality = "stale"
        elif sync_status is not None:
            effective_quality = sync_status
        else:
            effective_quality = (
                "waiting_initial_sync"
                if binding["environment"] == "live"
                else binding["data_quality_state"]
            )
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
                    str(effective_quality) if effective_quality is not None else None
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
        primary_binding = next(
            (binding for binding in active_bindings if binding["role"] == "primary"),
            None,
        )
        if primary_binding is not None:
            display_account_code = primary_binding["account_code"]
            display_account_status = primary_binding["account_status"]
            display_account_quality = primary_binding["data_quality_state"]
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
                        if binding["data_quality_state"] not in {None, "complete"}
                    ),
                    "complete",
                )
        execution_readiness = (
            None if row["v1_scope"] == "read_only" else get_strategy_v1_readiness(row["id"])
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


_LINEAR_INSTRUMENT_TYPES = frozenset({"crypto_perp", "crypto_spot"})


def monitor_position_valued(
    positions: list[PositionResponse],
) -> tuple[list[PositionResponse], dict[str, object]]:
    """Value monitored legs and settle their account-level exposure.

    A monitoring account reports venue position tickets instead of a platform
    projection, so both the displayed legs and the account aggregate are settled
    here. The venue value wins; a leg without one is rebuilt from its mark price
    and contract multiplier, and a leg whose multiplier is unknown stays unvalued
    rather than guessed. Currencies are never mixed and no FX rate is invented.
    """

    from app.strategy_financial_readmodel import position_exposure, position_notional

    managed = sorted({item.instrument_id for item in positions if item.instrument_id})
    published: dict[str, str] = {}
    if managed:
        with connection() as db:
            published = {
                str(row["instrument_id"]): str(row["contract_multiplier"])
                for row in db.execute(
                    "SELECT instrument_id, contract_multiplier FROM contract_specifications "
                    f"WHERE instrument_id IN ({','.join('?' * len(managed))})",
                    tuple(managed),
                ).fetchall()
            }
    valued: list[PositionResponse] = []
    rows: list[dict[str, object]] = []
    for item in positions:
        multiplier = published.get(item.instrument_id)
        if multiplier is None and item.instrument_type in _LINEAR_INSTRUMENT_TYPES:
            multiplier = "1"
        value = position_notional(
            mark={"positionValue": item.position_value, "netQuantity": item.net_quantity},
            quantity=item.net_quantity,
            price=item.current_price if multiplier is not None else None,
            multiplier=multiplier,
        )
        currency = item.position_value_currency or item.currency
        valued.append(
            item.model_copy(
                update={
                    "position_value": value,
                    "position_value_currency": currency if value is not None else None,
                }
            )
        )
        rows.append(
            {
                "netQuantity": item.net_quantity,
                "positionValue": value,
                "positionValueCurrency": currency,
            }
        )
    return valued, position_exposure(rows)


def get_strategy_account_snapshot(
    strategy_instance_id: str,
    *,
    account_id: str | None = None,
) -> StrategyAccountSnapshotResponse:
    bindings = list_strategy_account_bindings(strategy_instance_id)
    binding = next(
        (
            item
            for item in bindings
            if item.status == "active"
            and item.role != "local_test"
            and (item.account_id == account_id if account_id else item.role == "primary")
        ),
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
            equityHistory=[],
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
        venue_row = db.execute(
            "SELECT * FROM account_venue_snapshots WHERE account_id=?",
            (binding.account_id,),
        ).fetchone()
        venue_snapshot = json.loads(venue_row["payload_json"]) if venue_row else {}
        balance_row = db.execute(
            """
            SELECT balance_snapshots.id, balance_snapshots.account_id,
                   balance_snapshots.currency, balance_snapshots.equity,
                   balance_snapshots.available_balance, balance_snapshots.source,
                   balance_snapshots.data_quality_state, balance_snapshots.as_of
            FROM balance_snapshots
            JOIN accounts a ON a.id = balance_snapshots.account_id
            WHERE balance_snapshots.account_id = ?
              AND upper(balance_snapshots.currency) = upper(a.base_currency)
            ORDER BY balance_snapshots.as_of DESC, balance_snapshots.id ASC
            LIMIT 1
            """,
            (binding.account_id,),
        ).fetchone()
        risk_row = db.execute(
            """
            SELECT account_id, as_of, currency, equity, margin, free_margin, margin_level,
                   data_quality_state, payload_json, total_assets, asset_scope
            FROM account_risk_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC
            LIMIT 1
            """,
            (binding.account_id,),
        ).fetchone()
        risk_history_rows = db.execute(
            """
            SELECT as_of, currency, equity, asset_scope, total_assets
            FROM (
                SELECT as_of, currency, equity, asset_scope, total_assets
                FROM account_risk_snapshots
                WHERE account_id = ?
                  AND equity IS NOT NULL
                  AND asset_scope = (
                      SELECT asset_scope FROM account_risk_snapshots WHERE account_id=?
                      ORDER BY as_of DESC LIMIT 1
                  )
                  AND upper(currency) = upper(
                      (
                          SELECT currency
                          FROM account_risk_snapshots
                          WHERE account_id = ?
                          ORDER BY as_of DESC
                          LIMIT 1
                      )
                  )
                ORDER BY as_of DESC
                LIMIT 1000
            )
            ORDER BY as_of ASC
            """,
            (binding.account_id, binding.account_id, binding.account_id),
        ).fetchall()
        history_rows = db.execute(
            """
            SELECT as_of, currency, equity FROM (
                SELECT as_of, currency, equity FROM balance_snapshots
                WHERE account_id = ? AND currency = (
                    SELECT base_currency FROM accounts WHERE id=?
                ) ORDER BY as_of DESC LIMIT 1000
            ) ORDER BY as_of ASC
            """,
            (binding.account_id, binding.account_id),
        ).fetchall()
        # One closing per UTC day on the account's current measurement scope and
        # currency, so day-over-day P&L never spans a scope or currency change.
        daily_rows = db.execute(
            """
            SELECT as_of, currency, equity, asset_scope FROM (
                SELECT as_of, currency, equity, asset_scope,
                       ROW_NUMBER() OVER (
                           PARTITION BY substr(as_of, 1, 10)
                           ORDER BY as_of DESC, created_at DESC
                       ) AS day_rank
                FROM account_risk_snapshots
                WHERE account_id = ?
                  AND equity IS NOT NULL
                  AND as_of >= date('now', '-400 days')
                  AND asset_scope = (
                      SELECT asset_scope FROM account_risk_snapshots WHERE account_id=?
                      ORDER BY as_of DESC LIMIT 1
                  )
                  AND upper(currency) = upper(
                      (
                          SELECT currency
                          FROM account_risk_snapshots
                          WHERE account_id = ?
                          ORDER BY as_of DESC LIMIT 1
                      )
                  )
            ) WHERE day_rank = 1 ORDER BY as_of ASC
            """,
            (binding.account_id, binding.account_id, binding.account_id),
        ).fetchall()

    account = get_account(binding.account_id)
    sync_status = str(sync_row["status"]) if sync_row is not None else None
    snapshot_usable = risk_row is not None or balance_row is not None
    snapshot_time = venue_row["as_of"] if venue_row else risk_row["as_of"] if risk_row else None
    is_stale = (
        snapshot_time is None
        or (
            datetime.now(UTC) - datetime.fromisoformat(str(snapshot_time).replace("Z", "+00:00"))
        ).total_seconds()
        > 90
        or sync_status not in {"ready", "syncing"}
    )
    display_risk_row = risk_row if snapshot_usable else None
    if display_risk_row is not None and display_risk_row["equity"] is not None:
        balance = BalanceSnapshotResponse(
            snapshotId=f"risk:{binding.account_id}:{display_risk_row['as_of']}",
            accountId=binding.account_id,
            currency=display_risk_row["currency"],
            equity=Decimal(str(display_risk_row["equity"])),
            availableBalance=optional_decimal(display_risk_row["free_margin"]),
            source="account_risk",
            dataQualityState=display_risk_row["data_quality_state"],
            asOf=display_risk_row["as_of"],
        )
    else:
        balance = (
            get_latest_balance(binding.account_id)
            if balance_row is not None and snapshot_usable
            else None
        )
    history_source = (
        risk_history_rows
        if snapshot_usable and risk_history_rows
        else (
            [
                row
                for row in history_rows
                if str(row["currency"]).upper() == account.base_currency.upper()
            ]
            if snapshot_usable
            else []
        )
    )
    equity_history = [
        StrategyEquityHistoryPointResponse(
            asOf=row["as_of"],
            equity=Decimal(str(row["equity"])),
            currency=row["currency"],
            assetScope=row["asset_scope"] if "asset_scope" in row.keys() else "coin",
            totalAssets=optional_decimal(row["total_assets"])
            if "total_assets" in row.keys()
            else None,
        )
        for row in history_source
    ]
    from app.account_performance import enrich_performance

    enrich_performance(binding.account_id, equity_history)
    daily_points = [
        StrategyEquityHistoryPointResponse(
            asOf=row["as_of"],
            equity=Decimal(str(row["equity"])),
            currency=row["currency"],
            assetScope=row["asset_scope"],
        )
        for row in daily_rows
    ]
    daily_pnl_points: list[StrategyDailyPnlPointResponse] = []
    if len(daily_points) > 1:
        from app.account_performance import daily_pnl as daily_pnl_series

        with connection() as db:
            series = daily_pnl_series(
                db,
                binding.account_id,
                daily_points,
                daily_points[-1].asset_scope,
                "equity",
            )
        for index, (point, (amount, rate, quality)) in enumerate(
            zip(daily_points, series, strict=True)
        ):
            daily_pnl_points.append(
                StrategyDailyPnlPointResponse(
                    date=str(point.as_of)[:10],
                    currency=point.currency or "",
                    pnl=amount,
                    returnRate=rate,
                    equityOpen=daily_points[index - 1].equity if index else None,
                    equityClose=point.equity,
                    quality=quality,
                )
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
    if binding.capability == "read_only" and venue_snapshot:
        positions = [PositionResponse.model_validate(row) for row in venue_snapshot["positions"]]
    account_scope = binding.capability == "read_only"
    orders = list_orders(
        None if account_scope else strategy_instance_id, account_id=binding.account_id
    )
    fills = list_fills(
        None if account_scope else strategy_instance_id, account_id=binding.account_id
    )
    fills_total = len(fills)
    fills = fills[:200]
    orders_total = len(orders)
    orders = orders[:200]
    from app.strategy_financial_readmodel import get_strategy_financials

    finance = get_strategy_financials(
        strategy_instance_id, account_id=binding.account_id, account_scope=account_scope
    )
    if not account_scope:
        positions = [PositionResponse.model_validate(row) for row in finance["positions"]]
    pnl = None
    if all(finance.get(key) is not None for key in ("realizedPnl", "tradingPnl", "fees")):
        pnl = PnlResponse(
            accountId=binding.account_id,
            instrumentId="account_total" if account_scope else "strategy_total",
            realizedPnl=finance["realizedPnl"],
            tradingPnl=finance["tradingPnl"],
            fees=finance["fees"],
        )
    risk_payload = json.loads(display_risk_row["payload_json"]) if display_risk_row else {}
    if account_scope:
        positions, exposure = monitor_position_valued(positions)
    else:
        exposure = finance.get("exposure") or {}
    position_value = optional_decimal(exposure.get("positionValue"))
    equity_for_leverage = optional_decimal(balance.equity) if balance is not None else None
    leverage = (
        position_value / equity_for_leverage
        if position_value is not None and equity_for_leverage
        else None
    )
    account_risk = (
        AccountRiskSnapshotResponse(
            accountId=display_risk_row["account_id"],
            currency=display_risk_row["currency"],
            equity=optional_decimal(display_risk_row["equity"]),
            margin=optional_decimal(display_risk_row["margin"]),
            freeMargin=optional_decimal(display_risk_row["free_margin"]),
            marginLevel=optional_decimal(display_risk_row["margin_level"]),
            dataQualityState=display_risk_row["data_quality_state"],
            asOf=display_risk_row["as_of"],
            assetScope=display_risk_row["asset_scope"],
            totalAssets=optional_decimal(display_risk_row["total_assets"]),
            assetBreakdown=risk_payload.get("assetBreakdown", []),
            assetOverviewAsOf=risk_payload.get("assetOverviewAsOf"),
            assetOverviewQuality=risk_payload.get("assetOverviewQuality", "unavailable"),
            walletBalance=risk_payload.get("walletBalance"),
            marginBalance=risk_payload.get("marginBalance"),
            maintenanceMargin=risk_payload.get("maintenanceMargin"),
            unrealizedPnl=risk_payload.get("unrealizedPnl"),
        )
        if display_risk_row is not None
        else None
    )
    sync_status = sync_status or "waiting_initial_sync"
    sync_error = (
        str(sync_row["error_code"]) if sync_row is not None and sync_row["error_code"] else None
    )
    quality = (
        ("stale" if is_stale else balance.data_quality_state)
        if balance is not None
        else sync_status
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
        equityHistory=equity_history,
        dailyPnl=daily_pnl_points,
        accountRisk=account_risk,
        positions=positions,
        positionValue=position_value,
        positionValueNet=optional_decimal(exposure.get("positionValueNet")),
        positionValueCurrency=exposure.get("positionValueCurrency"),
        leverage=leverage,
        venueLeverage=optional_decimal(risk_payload.get("leverage")),
        orders=orders,
        fills=fills,
        pnl=pnl,
        syncStatus=sync_status,
        syncErrorCode=sync_error,
        snapshotScope="account" if account_scope else "strategy",
        isStale=is_stale,
        lastSuccessfulSyncAt=sync_row["last_success_at"] if sync_row else None,
        historyStart=venue_snapshot.get("historyStart"),
        historyEnd=venue_snapshot.get("historyEnd"),
        coinBalances=venue_snapshot.get("balances", []),
        economicEventsQuality=venue_snapshot.get("economicEventsQuality", "unavailable"),
        economicEvents=venue_snapshot.get("economicEvents", [])
        if account_scope
        else finance["economicEvents"],
        finance=StrategyPnlResponse.model_validate(finance),
        ordersTotal=orders_total,
        fillsTotal=fills_total,
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
        row = db.execute(
            """
            SELECT id, account_id, currency, equity, available_balance, source,
                   data_quality_state, as_of
            FROM balance_snapshots
            WHERE account_id = ?
              AND upper(currency) = upper(?)
            ORDER BY as_of DESC, id ASC
            LIMIT 1
            """,
            (account_id, account.base_currency),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Balance snapshot not found")
    return BalanceSnapshotResponse(
        snapshotId=row["id"],
        accountId=row["account_id"],
        currency=row["currency"],
        equity=Decimal(str(row["equity"])),
        availableBalance=optional_decimal(row["available_balance"]),
        source=row["source"],
        dataQualityState=row["data_quality_state"],
        asOf=row["as_of"],
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


def list_orders(
    strategy_instance_id: str | None = None,
    *,
    account_id: str | None = None,
    limit: int | None = None,
) -> list[OrderDetailResponse]:
    from app.order_record_readmodel import order_record_links
    from app.venue_identity_repository import VenueIdentityConflict, load_order_identities

    filters: list[str] = []
    params: list[object] = []
    if strategy_instance_id is not None:
        filters.append("tc.strategy_instance_id = ?")
        params.append(strategy_instance_id)
    if account_id is not None:
        filters.append("o.account_id = ?")
        params.append(account_id)
    where = " WHERE " + " AND ".join(filters) if filters else ""
    with connection() as db:
        rows = db.execute(
            "SELECT o.*,tc.id AS known_command_id FROM orders o "
            "LEFT JOIN trade_commands tc ON tc.id=o.command_id"
            + where
            + " ORDER BY o.created_at DESC, o.id DESC",
            params,
        ).fetchall()
        try:
            identities = load_order_identities(db)
            links = order_record_links(
                db, identities=identities, accounts={row["account_id"] for row in rows}
            )
            if any(identities.canonical[row["id"]] is None for row in rows):
                raise VenueIdentityConflict("Order has multiple command owners")
            rows = [row for row in rows if identities.canonical[row["id"]] == row["id"]]
        except VenueIdentityConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return [order_from_row(row, links.get(row["id"])) for row in rows[:limit]]


def get_order(order_id: str) -> OrderDetailResponse:
    from app.order_record_readmodel import order_record_links

    with connection() as db:
        row = db.execute(
            """
            SELECT o.*,tc.id AS known_command_id FROM orders o
            LEFT JOIN trade_commands tc ON tc.id=o.command_id
            WHERE o.id = ?
            """,
            (order_id,),
        ).fetchone()
        links = order_record_links(db, accounts={row["account_id"]} if row else set())
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order_from_row(row, links.get(order_id))


def order_from_row(row, record_link=None) -> OrderDetailResponse:
    venue = (
        json.loads(row["venue_payload_json"] or "{}") if "venue_payload_json" in row.keys() else {}
    )
    return OrderDetailResponse(
        **(record_link or {}),
        timeQuality=(
            "platform_submission"
            if "known_command_id" in row.keys() and row["known_command_id"]
            else "source_clock_unverified"
            if "mt5" in row["account_id"].lower()
            else "venue_time"
        ),
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
        filledQuantity=venue.get("filledQuantity"),
        averageFillPrice=venue.get("averageFillPrice"),
        reduceOnly=venue.get("reduceOnly"),
        timeInForce=venue.get("timeInForce"),
        rejectReason=venue.get("rejectReason"),
        cancelReason=venue.get("cancelReason"),
    )


def list_fills(
    strategy_instance_id: str | None = None,
    *,
    account_id: str | None = None,
    limit: int | None = None,
) -> list[FillResponse]:
    from collections import defaultdict

    from app.order_record_readmodel import (
        fill_clock_metadata,
        mt5_entry_action,
        order_record_links,
    )
    from app.strategy_financial_readmodel import select_management_executions
    from app.venue_identity_repository import (
        VenueIdentityConflict,
        load_order_identities,
        scoped_identity,
    )
    from app.venue_reconciliation_repository import effective_venue_event

    with connection() as db:
        identities = load_order_identities(db)
        orders = {
            row["id"]: dict(row)
            for row in db.execute("SELECT * FROM orders")
            if identities.canonical[row["id"]] == row["id"]
            and (account_id is None or row["account_id"] == account_id)
            and (
                strategy_instance_id is None
                or identities.rows[row["id"]]["strategy_instance_id"] == strategy_instance_id
            )
        }
        if not orders:
            return []
        accounts = sorted({row["account_id"] for row in orders.values()})
        placeholders = ",".join("?" for _ in accounts)
        rows = db.execute(
            "SELECT f.*,f.id AS fill_id,o.quantity AS requested_quantity "
            "FROM fills f JOIN orders o ON o.id=f.order_id "
            f"WHERE f.account_id IN ({placeholders})",
            accounts,
        ).fetchall()
        raw: dict[str, list[dict[str, object]]] = defaultdict(list)
        try:
            for event in db.execute(
                "SELECT * FROM venue_account_events WHERE event_type='trade_fill' "
                f"AND account_id IN ({placeholders})",
                accounts,
            ):
                payload = effective_venue_event(
                    db, event["account_id"], "trade_fill", json.loads(event["payload_json"])
                )
                owner = identities.resolve(event["account_id"], payload)
                if owner is not None and owner in orders:
                    raw[owner].append(
                        {
                            **payload,
                            "source": event["source"],
                            "externalFillId": event["external_id"],
                        }
                    )
            selected, _issues = select_management_executions(orders, rows, raw, identities)
            links = order_record_links(db, identities=identities, accounts=set(accounts))
            clocks = fill_clock_metadata(selected, rows, identities)
        except VenueIdentityConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    result = []
    for row, clock in zip(selected, clocks, strict=True):
        native = row.get("native") or {}
        order = orders[row["order_id"]]
        external_id = native.get("externalFillId") or row.get("external_fill_id")
        source = native.get("source") or row.get("source")
        record_link = dict(links.get(order["id"], {}))
        if (
            source == "mt5_live"
            and not identities.rows[order["id"]]["strategy_instance_id"]
            and mt5_entry_action(native)
        ):
            record_link["action"] = mt5_entry_action(native)
        result.append(
            FillResponse(
                **clock,
                fillId=(
                    scoped_identity("fill", order["account_id"], str(source), str(external_id))
                    if native
                    else row["fill_id"]
                ),
                orderId=order["id"],
                accountId=order["account_id"],
                instrumentId=order["instrument_id"],
                symbol=order["symbol"],
                side=row["side"],
                quantity=row["quantity"],
                price=row["price"],
                occurredAt=row["occurred_at"],
                fee=native.get("fee"),
                currency=native.get("currency"),
                realizedPnl=native.get("realizedPnl"),
                swap=native.get("swap"),
                origin="venue_execution" if native else row.get("origin", "legacy"),
                source=source,
                externalFillId=external_id,
                externalOrderId=order["external_order_id"],
                **record_link,
            )
        )
    result.sort(
        key=lambda row: (
            row.order_confirmed_at or row.occurred_at
            if row.time_quality in {"source_clock_conflict", "runtime_confirmation"}
            else row.occurred_at,
            row.fill_id,
        ), reverse=True,
    )
    return result[:limit] if limit is not None else result


def get_strategy_pnl(strategy_instance_id: str) -> StrategyPnlResponse:
    from app.strategy_financial_readmodel import get_strategy_financials

    get_strategy_instance(strategy_instance_id)
    return StrategyPnlResponse.model_validate(get_strategy_financials(strategy_instance_id))


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
