from decimal import Decimal

from fastapi import APIRouter, Request

from app.account_read_service import get_pnl as read_pnl
from app.account_read_service import get_position as read_position
from app.auth import require_principal
from app.catalog import (
    get_account,
    get_instrument,
    get_latest_balance,
    get_strategy_account_snapshot,
    get_strategy_instance,
    get_strategy_pnl,
    list_accounts,
    list_instruments,
    list_nav_snapshots,
    list_positions,
    list_strategy_account_bindings,
    list_strategy_definitions,
    list_strategy_instances,
    run_nav_snapshot,
)
from app.schemas import (
    AccountResponse,
    BalanceSnapshotResponse,
    CreateStrategyRunRequest,
    InstrumentResponse,
    PnlResponse,
    PositionResponse,
    StrategyAccountBindingResponse,
    StrategyAccountSnapshotResponse,
    StrategyDefinitionResponse,
    StrategyInstanceResponse,
    StrategyNavSnapshotResponse,
    StrategyPnlResponse,
    StrategyRunResponse,
    StrategyV1ReadinessResponse,
)
from app.strategies.instruction_service import (
    CreateStrategyInstructionRequest,
    create_instruction,
    get_instruction,
    list_instructions,
)
from app.strategy_runs import create_strategy_run, list_strategy_runs
from app.v1_readiness import get_strategy_v1_readiness


def create_catalog_router(api_prefix: str) -> APIRouter:
    router = APIRouter()

    @router.get(
        f"{api_prefix}/strategies/definitions",
        response_model=list[StrategyDefinitionResponse],
        tags=["strategies"],
    )
    def strategies_definitions() -> list[StrategyDefinitionResponse]:
        return list_strategy_definitions()

    @router.get(
        f"{api_prefix}/strategies/instances",
        response_model=list[StrategyInstanceResponse],
        tags=["strategies"],
    )
    def strategies_instances() -> list[StrategyInstanceResponse]:
        return list_strategy_instances()

    @router.get(
        f"{api_prefix}/strategies/instances/{{strategy_instance_id}}",
        response_model=StrategyInstanceResponse,
        tags=["strategies"],
    )
    def strategy_instance(strategy_instance_id: str) -> StrategyInstanceResponse:
        return get_strategy_instance(strategy_instance_id)

    @router.get(
        f"{api_prefix}/strategies/instances/{{strategy_instance_id}}/accounts",
        response_model=list[StrategyAccountBindingResponse],
        tags=["strategies"],
    )
    def strategy_accounts(
        strategy_instance_id: str,
    ) -> list[StrategyAccountBindingResponse]:
        return list_strategy_account_bindings(strategy_instance_id)

    @router.get(
        f"{api_prefix}/strategies/instances/{{strategy_instance_id}}/account-snapshot",
        response_model=StrategyAccountSnapshotResponse,
        tags=["strategies"],
    )
    def strategy_account_snapshot(
        strategy_instance_id: str,
    ) -> StrategyAccountSnapshotResponse:
        return get_strategy_account_snapshot(strategy_instance_id)

    @router.post(
        f"{api_prefix}/strategies/instances/{{strategy_instance_id}}/runs",
        response_model=StrategyRunResponse,
        tags=["strategies"],
    )
    def create_run(
        strategy_instance_id: str,
        request: CreateStrategyRunRequest,
        http_request: Request,
    ) -> StrategyRunResponse:
        return create_strategy_run(
            strategy_instance_id,
            request,
            requested_by=require_principal(http_request).user_id,
        )

    @router.get(
        f"{api_prefix}/strategies/instances/{{strategy_instance_id}}/runs",
        response_model=list[StrategyRunResponse],
        tags=["strategies"],
    )
    def strategy_runs(strategy_instance_id: str) -> list[StrategyRunResponse]:
        return list_strategy_runs(strategy_instance_id)

    @router.post(
        f"{api_prefix}/strategies/{{strategy_instance_id}}/instructions", tags=["strategies"]
    )
    def create_strategy_instruction(
        strategy_instance_id: str,
        request: CreateStrategyInstructionRequest,
        http_request: Request,
    ) -> dict[str, object]:
        return create_instruction(
            strategy_instance_id, request, requested_by=require_principal(http_request).user_id
        )

    @router.get(
        f"{api_prefix}/strategies/{{strategy_instance_id}}/instructions", tags=["strategies"]
    )
    def strategy_instructions(strategy_instance_id: str) -> list[dict[str, object]]:
        return list_instructions(strategy_instance_id)

    @router.get(f"{api_prefix}/strategy-instructions/{{instruction_id}}", tags=["strategies"])
    def strategy_instruction(instruction_id: str) -> dict[str, object]:
        return get_instruction(instruction_id)

    @router.get(
        f"{api_prefix}/strategies/instances/{{strategy_instance_id}}/v1-readiness",
        response_model=StrategyV1ReadinessResponse,
        tags=["strategies"],
    )
    def strategy_v1_readiness(
        strategy_instance_id: str,
    ) -> StrategyV1ReadinessResponse:
        return get_strategy_v1_readiness(strategy_instance_id)

    @router.get(
        f"{api_prefix}/accounts",
        response_model=list[AccountResponse],
        tags=["accounts"],
    )
    def accounts() -> list[AccountResponse]:
        return list_accounts()

    @router.get(
        f"{api_prefix}/accounts/{{account_id}}",
        response_model=AccountResponse,
        tags=["accounts"],
    )
    def account(account_id: str) -> AccountResponse:
        return get_account(account_id)

    @router.get(
        f"{api_prefix}/accounts/{{account_id}}/balances/latest",
        response_model=BalanceSnapshotResponse,
        tags=["accounts"],
    )
    def latest_balance(account_id: str) -> BalanceSnapshotResponse:
        return get_latest_balance(account_id)

    @router.get(
        f"{api_prefix}/accounts/{{account_id}}/positions",
        response_model=list[PositionResponse],
        tags=["accounts"],
    )
    def account_positions(account_id: str) -> list[PositionResponse]:
        rows = list_positions(account_id)
        return [
            PositionResponse(
                accountId=row["account_id"],
                instrumentId=row["instrument_id"],
                netQuantity=Decimal(row["net_quantity"]),
                averagePrice=(Decimal(row["average_price"]) if row["average_price"] else None),
            )
            for row in rows
        ]

    @router.get(
        f"{api_prefix}/accounts/{{account_id}}/positions/{{instrument_id}}",
        response_model=PositionResponse,
        tags=["accounts"],
    )
    def get_position(account_id: str, instrument_id: str) -> PositionResponse:
        return read_position(account_id, instrument_id)

    @router.get(
        f"{api_prefix}/accounts/{{account_id}}/pnl/{{instrument_id}}",
        response_model=PnlResponse,
        tags=["pnl"],
    )
    def get_pnl(account_id: str, instrument_id: str) -> PnlResponse:
        return read_pnl(account_id, instrument_id)

    @router.get(
        f"{api_prefix}/instruments",
        response_model=list[InstrumentResponse],
        tags=["instruments"],
    )
    def instruments() -> list[InstrumentResponse]:
        return list_instruments()

    @router.get(
        f"{api_prefix}/instruments/{{instrument_id}}",
        response_model=InstrumentResponse,
        tags=["instruments"],
    )
    def instrument(instrument_id: str) -> InstrumentResponse:
        return get_instrument(instrument_id)

    @router.get(
        f"{api_prefix}/strategies/instances/{{strategy_instance_id}}/pnl",
        response_model=StrategyPnlResponse,
        tags=["pnl"],
    )
    def strategy_pnl(strategy_instance_id: str) -> StrategyPnlResponse:
        return get_strategy_pnl(strategy_instance_id)

    @router.get(
        f"{api_prefix}/strategies/instances/{{strategy_instance_id}}/nav-snapshots",
        response_model=list[StrategyNavSnapshotResponse],
        tags=["pnl"],
    )
    def strategy_nav_snapshots(
        strategy_instance_id: str,
    ) -> list[StrategyNavSnapshotResponse]:
        return list_nav_snapshots(strategy_instance_id)

    @router.post(
        f"{api_prefix}/strategies/instances/{{strategy_instance_id}}/nav-snapshots/run",
        response_model=StrategyNavSnapshotResponse,
        tags=["pnl"],
    )
    def run_strategy_nav_snapshot(
        strategy_instance_id: str,
    ) -> StrategyNavSnapshotResponse:
        return run_nav_snapshot(strategy_instance_id)

    return router
