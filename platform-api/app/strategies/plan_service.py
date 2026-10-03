from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from sqlite3 import Connection
from typing import Literal

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app import runtime_transport
from app.config import get_settings
from app.database import connection
from app.strategies.adapters.cross_spread import build_cross_spread_plan
from app.strategies.adapters.funding_carry import (
    SPOT_BASE_FEE_RATE,
    build_funding_carry_plan,
    funding_open_quantities,
    funding_spot_quantity_for_perpetual,
)
from app.strategies.domain import ExecutionPlan, StrategyInstructionAction
from app.strategy_financial_readmodel import canonical_fills


class FundingCarryParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, allow_inf_nan=False)
    perpetual_symbol: str = Field(alias="perpetualSymbol", min_length=1, max_length=64)
    perpetual_quantity: Decimal = Field(alias="perpetualQuantity", gt=0)
    spot_symbol: str = Field(alias="spotSymbol", min_length=1, max_length=64)
    spot_quantity: Decimal = Field(alias="spotQuantity", gt=0)
    spot_base_fee_rate: Decimal | None = Field(default=None, alias="spotBaseFeeRate", ge=0, lt=1)
    execution_policy: Literal["market", "fok", "post_only_chase"] = Field(
        default="post_only_chase", alias="executionPolicy"
    )
    perpetual_limit_price: Decimal | None = Field(default=None, alias="perpetualLimitPrice", gt=0)
    target_open_instruction_id: str | None = Field(
        default=None, alias="targetOpenInstructionId", min_length=1, max_length=128
    )

    @model_validator(mode="after")
    def validate_execution_price(self):
        if (self.execution_policy == "fok") != (self.perpetual_limit_price is not None):
            raise ValueError("Only FOK execution requires a perpetual limit price")
        return self


class CrossSpreadGuard(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    target_spread: Decimal = Field(alias="targetSpread")
    max_adverse_spread: Decimal = Field(default=Decimal("0"), alias="maxAdverseSpread", ge=0)
    mt5_account_id: str = Field(alias="mt5AccountId", min_length=1)
    mt5_symbol: str = Field(alias="mt5Symbol", min_length=1)
    mt5_close: bool = Field(alias="mt5Close")
    mt5_min_quantity: Decimal = Field(alias="mt5MinQuantity", gt=0)
    mt5_quantity_step: Decimal = Field(alias="mt5QuantityStep", gt=0)
    mt5_contract_multiplier: Decimal = Field(alias="mt5ContractMultiplier", gt=0)


class CrossSpreadParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    action: Literal["OPEN_LONG", "CLOSE_LONG", "OPEN_SHORT", "CLOSE_SHORT"]
    quantity_oz: Decimal = Field(alias="quantityOz", gt=0)
    bybit_reduce_only: bool = Field(default=False, alias="bybitReduceOnly")
    mt5_reduce_only: bool = Field(default=False, alias="mt5ReduceOnly")
    mt5_position_id: str | None = Field(default=None, alias="mt5PositionId")
    execution_policy: Literal["market", "fok", "post_only_chase"] = Field(
        default="market",
        alias="executionPolicy",
    )
    bybit_limit_price: Decimal | None = Field(default=None, alias="bybitLimitPrice", gt=0)
    max_adverse_spread: Decimal = Field(default=Decimal("0"), alias="maxAdverseSpread", ge=0)
    cross_spread_guard: CrossSpreadGuard | None = Field(default=None, alias="crossSpreadGuard")


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
        SELECT i.id AS instrument_id, m.external_symbol, cs.price_tick,
               cs.min_order_quantity, cs.quantity_step, cs.contract_multiplier
        FROM instrument_mappings m
        JOIN instruments i ON i.id = m.instrument_id
        JOIN contract_specifications cs ON cs.instrument_id = i.id
        WHERE m.venue_id = ? AND m.status = 'active'
          AND i.instrument_type = ? AND cs.data_quality_state = 'complete'
          AND cs.effective_from = (
              SELECT MAX(current_cs.effective_from)
              FROM contract_specifications current_cs
              WHERE current_cs.instrument_id = i.id
                AND current_cs.data_quality_state = 'complete'
          )
    """
    values: list[str] = [venue_id, instrument_type]
    if external_symbol is not None:
        sql += " AND upper(m.external_symbol) = upper(?)"
        values.append(external_symbol)
    return _one(
        db.execute(sql, values).fetchall(),
        f"Authoritative {instrument_type} instrument mapping is unavailable or ambiguous",
    )


def _parse[ModelT: BaseModel](model: type[ModelT], parameters: dict[str, object]) -> ModelT:
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
    normalized = _parse(model, parameters).model_dump(by_alias=True, mode="json")
    if model is FundingCarryParameters:
        for key in ("targetOpenInstructionId", "perpetualLimitPrice"):
            if normalized.get(key) is None:
                normalized.pop(key, None)
        if normalized.get("executionPolicy") == "post_only_chase":
            normalized.pop("executionPolicy", None)
    return normalized


def funding_account_binding(db: Connection, strategy_instance_id: str):
    """Use the same authoritative account for funding quotes and execution plans."""
    rows = db.execute(
        """
        SELECT sab.account_id, a.venue_id, v.venue_code, a.environment,
               si.trading_mode
        FROM strategy_instances si
        JOIN strategy_account_bindings sab ON sab.strategy_instance_id=si.id
        JOIN accounts a ON a.id=sab.account_id
        JOIN venues v ON v.id=a.venue_id
        WHERE si.id=? AND si.status='active' AND sab.status='active'
          AND sab.role=CASE WHEN si.trading_mode='simulation' THEN 'local_test' ELSE 'primary' END
          AND sab.capability='trade_and_read' AND a.status='active' AND v.status='active'
        """,
        (strategy_instance_id,),
    ).fetchall()
    account = _one(rows, "Funding execution account is unavailable or ambiguous")
    expected_environment = "simulation" if account["trading_mode"] == "simulation" else "live"
    if account["environment"] != expected_environment:
        raise _unprocessable("Funding strategy and account environments do not match")
    return account


def _funding_live_specification(account_id: str, instrument, instrument_type: str) -> dict:
    category = "spot" if instrument_type == "crypto_spot" else "linear"
    symbol = str(instrument["external_symbol"]).upper()
    try:
        response = runtime_transport.get(
            f"{get_settings().runtime_base_url}/venue/instruments/{symbol}",
            params={
                "accountId": account_id,
                "instrumentType": instrument_type,
                "category": category,
            },
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(409, "交易所交易规则暂不可用，请刷新后重试") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("accountId") != account_id
        or payload.get("symbol") != symbol
        or payload.get("instrumentType") != instrument_type
        or payload.get("category") != category
        or payload.get("dataQualityState") != "complete"
        or str(payload.get("status", "")).lower() != "trading"
    ):
        raise HTTPException(409, "交易所交易规则未获确认，本次未下单")
    if not funding_market_access_ready(payload, instrument_type):
        market = "现货" if instrument_type == "crypto_spot" else "永续"
        raise HTTPException(409, f"{market}交易权限未获确认，本次未下单")
    resolved = dict(instrument)
    for target, source in (
        ("quantity_step", "quantityStep"),
        ("min_order_quantity", "minQuantity"),
        ("price_tick", "priceTick"),
        ("contract_multiplier", "contractMultiplier"),
    ):
        try:
            value = Decimal(str(payload[source]))
            if not value.is_finite() or value <= 0:
                raise ValueError("Invalid native specification")
        except (KeyError, ValueError, ArithmeticError) as exc:
            raise HTTPException(409, "交易所数量或价格规则无效，本次未下单") from exc
        resolved[target] = str(value)
    if Decimal(resolved["contract_multiplier"]) != 1:
        raise _unprocessable("当前资费组合要求现货和永续均按标的币数量交易")
    maximum = payload.get("maxMarketQuantity")
    if maximum is not None:
        resolved["max_market_quantity"] = str(maximum)
    return resolved


def funding_market_access_ready(payload: dict, instrument_type: str) -> bool:
    checks = payload.get("accessChecks")
    return isinstance(checks, dict) and (
        checks.get("readOnly") is False
        and checks.get("ipBound") is True
        and checks.get("orderPermission") is True
        and (instrument_type == "crypto_spot" or checks.get("positionPermission") is True)
    )


def validate_funding_plan_markets(plan: ExecutionPlan) -> None:
    """Recheck both markets before the first side effect, against the frozen plan."""
    for leg in plan.legs:
        instrument_type = "crypto_perp" if leg.role == "perpetual_leg" else "crypto_spot"
        spec = _funding_live_specification(
            leg.account_id,
            {"instrument_id": leg.instrument_id, "external_symbol": leg.external_symbol},
            instrument_type,
        )
        if any(
            Decimal(spec[field]) != expected
            for field, expected in (
                ("quantity_step", leg.quantity_step),
                ("price_tick", leg.price_tick),
                ("contract_multiplier", leg.contract_multiplier),
                ("min_order_quantity", leg.minimum_quantity),
            )
        ):
            raise HTTPException(409, "交易规则已变化，请重新确认指令；本次未下单")
        if spec.get("max_market_quantity") is not None:
            maximum = Decimal(spec["max_market_quantity"])
            if not maximum.is_finite() or maximum <= 0 or leg.maximum_quantity > maximum:
                raise HTTPException(409, "委托数量超过交易所单笔限制，本次未下单")


def validate_funding_close_capacity(
    db: Connection, strategy_instance_id: str, parameters: dict[str, object], plan: ExecutionPlan
) -> None:
    """Check group capacity inside the transaction that declares a close intent."""
    target_id = str(parameters.get("targetOpenInstructionId") or "")
    target = db.execute(
        "SELECT execution_batch_id,execution_plan_json FROM strategy_runs WHERE id=? "
        "AND strategy_instance_id=? AND action='open'",
        (target_id, strategy_instance_id),
    ).fetchone()
    if target is None or not target[0]:
        raise _unprocessable("Funding close target is unavailable")
    batch_id = target[0]
    original = ExecutionPlan.model_validate_json(target["execution_plan_json"])
    def identity(leg):
        return leg.role, leg.account_id, leg.instrument_id, leg.external_symbol

    if {identity(leg) for leg in plan.legs} != {identity(leg) for leg in original.legs}:
        raise HTTPException(409, "Funding close must preserve original accounts and instruments")
    rows = db.execute(
        "SELECT f.*, f.id AS fill_id, o.quantity AS requested_quantity, legs.role "
        "FROM fills f JOIN orders o ON o.id=f.order_id JOIN ("
        "SELECT order_id, role FROM execution_batch_legs WHERE batch_id=? "
        "UNION SELECT order_id,'perpetual_leg' FROM funding_perpetual_attempts WHERE batch_id=? "
        "UNION SELECT order_id,'spot_leg' FROM funding_spot_release_commands WHERE batch_id=?"
        ") legs ON legs.order_id=o.id ORDER BY f.occurred_at,f.id",
        (batch_id, batch_id, batch_id),
    ).fetchall()
    quantities = {"perpetual_leg": Decimal("0"), "spot_leg": Decimal("0")}
    for row in canonical_fills(rows):
        quantities[row["role"]] += Decimal(str(row["quantity"]))
    opened = min(quantities.values())
    # An unresolved close retains its entire intent. A failure with no order
    # identities has no external side effect and does not reserve inventory.
    close_rows = db.execute(
        "SELECT json_extract(requested_parameters_json,'$.perpetualQuantity') AS quantity "
        "FROM strategy_runs r WHERE r.strategy_instance_id=? AND r.action='close' "
        "AND json_extract(requested_parameters_json,'$.targetOpenInstructionId')=? "
        "AND (r.status NOT IN ('failed','rejected') OR EXISTS ("
        "SELECT 1 FROM funding_perpetual_attempts p WHERE p.batch_id=r.execution_batch_id "
        "AND p.order_id IS NOT NULL))",
        (strategy_instance_id, target_id),
    ).fetchall()
    reserved = sum((Decimal(str(row["quantity"])) for row in close_rows), Decimal("0"))
    if Decimal(str(parameters["perpetualQuantity"])) > opened - reserved:
        raise HTTPException(
            status_code=409, detail="Funding close quantity exceeds remaining hedged quantity"
        )


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
            SELECT sab.account_id, sab.role, sab.capability, a.venue_id,
                   a.environment AS account_environment, a.status AS account_status,
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
            account = funding_account_binding(db, strategy_instance_id)
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
            if account["environment"] == "live":
                perpetual = _funding_live_specification(
                    account["account_id"], perpetual, "crypto_perp"
                )
                spot = _funding_live_specification(account["account_id"], spot, "crypto_spot")
            if action is StrategyInstructionAction.OPEN:
                fee_rate = SPOT_BASE_FEE_RATE if account["environment"] == "live" else Decimal("0")
                if typed.spot_base_fee_rate is not None and typed.spot_base_fee_rate != fee_rate:
                    raise _unprocessable("现货手续费率与当前账户开仓规则不一致，请刷新预览")
                if account["environment"] == "live" or typed.spot_base_fee_rate is not None:
                    if any(
                        Decimal(str(spec["contract_multiplier"])) != 1 for spec in (perpetual, spot)
                    ):
                        raise _unprocessable(
                            "Funding fee-aware sizing requires unit coin multipliers"
                        )
                    expected_spot, _, _ = funding_spot_quantity_for_perpetual(
                        typed.perpetual_quantity,
                        fee_rate=fee_rate,
                        spot_step=Decimal(str(spot["quantity_step"])),
                        spot_minimum=Decimal(str(spot["min_order_quantity"])),
                    )
                    if typed.spot_quantity != expected_spot:
                        raise _unprocessable(
                            "现货数量须按永续目标数量和扣费后净额自动配平"
                        )
                    _, expected_perpetual, _ = funding_open_quantities(
                        typed.spot_quantity,
                        fee_rate=fee_rate,
                        perpetual_step=Decimal(str(perpetual["quantity_step"])),
                        perpetual_minimum=Decimal(str(perpetual["min_order_quantity"])),
                    )
                    if typed.perpetual_quantity != expected_perpetual or expected_perpetual <= 0:
                        raise _unprocessable(
                            "永续数量须按现货扣费后的净币数量选择最接近的可下单量"
                        )
            for quantity, specification in (
                (typed.perpetual_quantity, perpetual),
                (typed.spot_quantity, spot),
            ):
                step = Decimal(str(specification["quantity_step"]))
                if quantity % step != 0 or quantity < Decimal(
                    str(specification["min_order_quantity"])
                ):
                    raise _unprocessable("委托数量不符合交易所最小数量或数量步长")
            if (
                typed.perpetual_limit_price is not None
                and typed.perpetual_limit_price % Decimal(str(perpetual["price_tick"])) != 0
            ):
                raise _unprocessable("永续限价不符合交易所价格步长")
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
                    "perpetualPriceTick": perpetual["price_tick"],
                    "perpetualMinimumQuantity": perpetual["min_order_quantity"],
                    "spotQuantityStep": spot["quantity_step"],
                    "spotPriceTick": spot["price_tick"],
                    "spotMinimumQuantity": spot["min_order_quantity"],
                    "perpetualContractMultiplier": perpetual["contract_multiplier"],
                    "spotContractMultiplier": spot["contract_multiplier"],
                    "executionPolicy": typed.execution_policy,
                    "perpetualLimitPrice": typed.perpetual_limit_price,
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
                db,
                venue_id=bybit_account["venue_id"],
                instrument_type="crypto_perp",
                external_symbol="XAUTUSDT",
            )
            mt5 = _instrument(db, venue_id=mt5_account["venue_id"], instrument_type="mt5_cfd")
            guard = typed.cross_spread_guard
            if guard is not None and (
                guard.mt5_close != typed.action.startswith("CLOSE_")
                or guard.mt5_account_id != mt5_account["account_id"]
                or guard.mt5_symbol != mt5["external_symbol"]
                or guard.mt5_min_quantity != Decimal(str(mt5["min_order_quantity"]))
                or guard.mt5_quantity_step != Decimal(str(mt5["quantity_step"]))
                or guard.mt5_contract_multiplier != Decimal(str(mt5["contract_multiplier"]))
            ):
                raise _unprocessable("Cross-spread guard MT5 specification does not match binding")
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
                    "bybitPriceTick": bybit["price_tick"],
                    "mt5QuantityStep": mt5["quantity_step"],
                    "mt5PriceTick": mt5["price_tick"],
                    "bybitReduceOnly": typed.bybit_reduce_only,
                    "mt5ReduceOnly": typed.mt5_reduce_only,
                    "mt5PositionId": typed.mt5_position_id,
                    "executionPolicy": typed.execution_policy,
                    "bybitLimitPrice": typed.bybit_limit_price,
                    "crossSpreadGuard": (
                        typed.cross_spread_guard.model_dump(by_alias=True, mode="json")
                        if typed.cross_spread_guard is not None
                        else None
                    ),
                },
                created_at=now,
            )
    raise _unprocessable("Strategy has no registered instruction adapter")
