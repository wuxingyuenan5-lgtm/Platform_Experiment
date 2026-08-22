from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.database import connection
from app.strategies.adapters.cross_spread import build_cross_spread_plan
from app.strategies.adapters.funding_carry import build_funding_carry_plan
from app.strategies.domain import ExecutionPlan, StrategyInstructionAction


class FundingCarryParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    perpetual_symbol: str = Field(alias="perpetualSymbol", min_length=1, max_length=64)
    perpetual_quantity: Decimal = Field(alias="perpetualQuantity", gt=0)
    spot_symbol: str = Field(alias="spotSymbol", min_length=1, max_length=64)
    spot_quantity: Decimal = Field(alias="spotQuantity", gt=0)


class CrossSpreadParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    action: Literal["OPEN_LONG", "OPEN_SHORT"]
    quantity_oz: Decimal = Field(alias="quantityOz", gt=0)


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def _one(rows, detail: str):
    if len(rows) != 1:
        raise _unprocessable(detail)
    return rows[0]


def _binding(rows, role: str):
    return _one(
        [row for row in rows if row["role"] == role],
        f"Strategy binding for {role} is unavailable or ambiguous",
    )


def _instrument(db, *, venue_id: str, instrument_type: str, external_symbol: str | None = None):
    sql = """
        SELECT i.id AS instrument_id, m.external_symbol, cs.min_order_quantity,
               cs.quantity_step, cs.contract_multiplier
        FROM instrument_mappings m
        JOIN instruments i ON i.id = m.instrument_id
        JOIN contract_specifications cs ON cs.instrument_id = i.id
        WHERE m.venue_id = ? AND m.status = 'active'
          AND i.instrument_type = ? AND cs.data_quality_state = 'complete'
    """
    values: list[str] = [venue_id, instrument_type]
    if external_symbol is not None:
        sql += " AND upper(m.external_symbol) = upper(?)"
        values.append(external_symbol)
    return _one(
        db.execute(sql, values).fetchall(),
        f"Authoritative {instrument_type} instrument mapping is unavailable or ambiguous",
    )


def _parse(model: type[BaseModel], parameters: dict[str, object]) -> BaseModel:
    try:
        return model.model_validate(parameters)
    except ValidationError as exc:
        raise _unprocessable("Invalid strategy instruction parameters") from exc


def normalize_parameters(
    strategy_instance_id: str, parameters: dict[str, object]
) -> dict[str, object]:
    """Canonicalise the strategy-owned request schema before idempotency checks."""
    with connection() as db:
        instance = db.execute(
            """
            SELECT sd.strategy_key FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ?
            """,
            (strategy_instance_id,),
        ).fetchone()
    if instance is None:
        raise _unprocessable("Strategy instance is not runnable")
    model = {
        "funding_arbitrage": FundingCarryParameters,
        "cross_venue_spread": CrossSpreadParameters,
    }.get(instance["strategy_key"])
    if model is None:
        raise _unprocessable("Strategy has no registered instruction adapter")
    return _parse(model, parameters).model_dump(by_alias=True, mode="json")


def build_plan(
    strategy_instance_id: str,
    action: StrategyInstructionAction,
    parameters: dict[str, object],
) -> ExecutionPlan:
    with connection() as db:
        instance = db.execute(
            """
            SELECT sd.strategy_key, si.trading_mode FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ? AND si.status = 'active' AND sd.status = 'active'
            """,
            (strategy_instance_id,),
        ).fetchone()
        if instance is None:
            raise _unprocessable("Strategy instance is not runnable")
        bindings = db.execute(
            """
            SELECT sab.account_id, sab.role, sab.capability, a.venue_id, a.status AS account_status,
                   v.status AS venue_status
            FROM strategy_account_bindings sab
            JOIN accounts a ON a.id = sab.account_id JOIN venues v ON v.id = a.venue_id
            WHERE sab.strategy_instance_id = ? AND sab.status = 'active'
            """,
            (strategy_instance_id,),
        ).fetchall()
        if not bindings or any(row["capability"] != "trade_and_read" for row in bindings):
            raise _unprocessable("Strategy account binding is read_only or unavailable")
        now = datetime.now(UTC)
        if instance["strategy_key"] == "funding_arbitrage":
            typed = _parse(FundingCarryParameters, parameters)
            account = _binding(
                bindings, "local_test" if instance["trading_mode"] == "simulation" else "primary"
            )
            if account["account_status"] != "active" or account["venue_status"] != "active":
                raise _unprocessable("Strategy account or venue is unavailable")
            perpetual = _instrument(
                db,
                venue_id=account["venue_id"],
                instrument_type="crypto_perp",
                external_symbol=typed.perpetual_symbol,
            )
            spot = _instrument(
                db,
                venue_id=account["venue_id"],
                instrument_type="crypto_spot",
                external_symbol=typed.spot_symbol,
            )
            return build_funding_carry_plan(
                action=action.value,
                parameters={
                    "perpetualSymbol": perpetual["external_symbol"],
                    "perpetualQuantity": typed.perpetual_quantity,
                    "spotSymbol": spot["external_symbol"],
                    "spotQuantity": typed.spot_quantity,
                    "accountId": account["account_id"],
                    "perpetualInstrumentId": perpetual["instrument_id"],
                    "spotInstrumentId": spot["instrument_id"],
                    "perpetualQuantityStep": perpetual["quantity_step"],
                    "spotQuantityStep": spot["quantity_step"],
                    "perpetualContractMultiplier": perpetual["contract_multiplier"],
                    "spotContractMultiplier": spot["contract_multiplier"],
                },
                created_at=now,
            )
        if instance["strategy_key"] == "cross_venue_spread":
            typed = _parse(CrossSpreadParameters, parameters)
            bybit_account, mt5_account = (
                _binding(bindings, "venue_a"),
                _binding(bindings, "mt5_leg"),
            )
            bybit = _instrument(
                db, venue_id=bybit_account["venue_id"], instrument_type="crypto_perp"
            )
            mt5 = _instrument(db, venue_id=mt5_account["venue_id"], instrument_type="mt5_cfd")
            return build_cross_spread_plan(
                action=action.value,
                parameters={
                    "action": typed.action,
                    "quantityOz": typed.quantity_oz,
                    "bybitAccountId": bybit_account["account_id"],
                    "mt5AccountId": mt5_account["account_id"],
                    "bybitInstrumentId": bybit["instrument_id"],
                    "bybitSymbol": bybit["external_symbol"],
                    "mt5InstrumentId": mt5["instrument_id"],
                    "mt5Symbol": mt5["external_symbol"],
                    "mt5ContractMultiplier": mt5["contract_multiplier"],
                    "bybitContractMultiplier": bybit["contract_multiplier"],
                    "bybitQuantityStep": bybit["quantity_step"],
                    "mt5QuantityStep": mt5["quantity_step"],
                },
                created_at=now,
            )
    raise _unprocessable("Strategy has no registered instruction adapter")
