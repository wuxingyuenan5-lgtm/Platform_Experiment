from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.auth import require_principal
from app.catalog import get_order, list_fills, list_orders
from app.controlled_strategy_write_guard import (
    reject_controlled_account_legacy_order,
    reject_controlled_strategy_write_bypass,
)
from app.cross_spread import (
    STRATEGY_INSTANCE_ID as CROSS_SPREAD_STRATEGY_INSTANCE_ID,
)
from app.cross_spread import (
    get_bybit_account_id,
    get_cross_spread_history,
    get_cross_spread_snapshot,
    get_mt5_account_id,
    prepare_cross_spread_market_command,
    submit_cross_spread_market_command,
)
from app.cross_spread_leverage import read_bybit_leverage, update_bybit_leverage
from app.execution_batches import (
    create_execution_batch,
    get_execution_batch,
    list_execution_batches,
)
from app.execution_schemas import FundingMarketCommandRequest
from app.funding import submit_funding_market_command
from app.schemas import (
    CreateExecutionBatchRequest,
    CreateOrderRequest,
    CreateTradeCommandRequest,
    CrossSpreadHistoryPointResponse,
    CrossSpreadMarketCommandRequest,
    CrossSpreadPreflightRequest,
    CrossSpreadSnapshotResponse,
    ExecutionBatchResponse,
    FillResponse,
    OrderDetailResponse,
    OrderResponse,
    TradeCommandResponse,
)
from app.strategies.capital_transfer import (
    CreateInternalCapitalTransferRequest,
    FundingTransferQuoteResponse,
    InternalCapitalTransferResponse,
    cancel_funding_transfer,
    create_funding_transfer,
    get_funding_transfer,
    get_funding_transfer_quote,
)
from app.strategies.funding_schemas import (
    FundingExecutionContextResponse,
    FundingPositionGroupResponse,
    FundingWorkspaceResponse,
)
from app.strategies.funding_workspace import (
    get_funding_execution_context,
    get_funding_instruction_workspace,
    get_funding_instruction_workspace_by_idempotency,
    list_funding_position_groups,
    submit_funding_instruction,
)
from app.strategy_financial_readmodel import get_cross_spread_position_overview
from app.trade_commands import create_trade_command, get_trade_command
from app.trading import reconcile_order, submit_order


class CrossSpreadLeverageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    leverage: Decimal = Field(ge=1, le=100)


class CrossSpreadLeverageResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    accountId: str
    symbol: str
    leverage: Decimal | None
    source: str


class CrossSpreadPreflightResponse(BaseModel):
    status: Literal["ready"]
    preparedAt: str


class FundingInstructionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    action: Literal["open", "close"]
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    perpetual_symbol: str = Field(alias="perpetualSymbol", min_length=1, max_length=64)
    spot_symbol: str = Field(alias="spotSymbol", min_length=1, max_length=64)
    quantity: Decimal = Field(gt=0, max_digits=28, decimal_places=18)
    expected_perpetual_quantity: Decimal | None = Field(
        default=None, alias="expectedPerpetualQuantity", gt=0, max_digits=28, decimal_places=18
    )
    execution_policy: Literal["market", "fok", "post_only_chase"] = Field(
        default="post_only_chase", alias="executionPolicy"
    )
    perpetual_limit_price: Decimal | None = Field(
        default=None, alias="perpetualLimitPrice", gt=0, max_digits=28, decimal_places=18
    )
    target_open_instruction_id: str | None = Field(default=None, alias="targetOpenInstructionId")


def create_trading_router(api_prefix: str) -> APIRouter:
    router = APIRouter()

    @router.get(
        f"{api_prefix}/trading/cross-spread/leverage",
        response_model=CrossSpreadLeverageResponse,
        tags=["trading"],
    )
    def cross_spread_leverage() -> dict:
        return read_bybit_leverage()

    @router.post(
        f"{api_prefix}/trading/cross-spread/leverage",
        response_model=CrossSpreadLeverageResponse,
        tags=["trading"],
    )
    def set_cross_spread_leverage(request: CrossSpreadLeverageRequest) -> dict:
        return update_bybit_leverage(request.leverage)

    @router.post(
        f"{api_prefix}/trading/orders",
        response_model=OrderResponse,
        tags=["trading"],
        deprecated=True,
        summary="Compatibility order endpoint; use TradeCommand or ExecutionBatch",
    )
    def create_order(request: CreateOrderRequest) -> OrderResponse:
        reject_controlled_account_legacy_order(request.account_id)
        return submit_order(request)

    @router.post(
        f"{api_prefix}/trading/orders/{{order_id}}/reconcile",
        response_model=OrderResponse,
        tags=["trading"],
        summary="Recover an uncertain order from Runtime Journal",
    )
    def reconcile_trading_order(order_id: str) -> OrderResponse:
        return reconcile_order(order_id)

    @router.post(
        f"{api_prefix}/trading/execution-batches",
        response_model=ExecutionBatchResponse,
        tags=["trading"],
    )
    def create_batch(request: CreateExecutionBatchRequest) -> ExecutionBatchResponse:
        reject_controlled_strategy_write_bypass(
            request.strategy_instance_id, strategy_key=request.strategy_key
        )
        return create_execution_batch(request)

    @router.get(
        f"{api_prefix}/trading/cross-spread/snapshot",
        response_model=CrossSpreadSnapshotResponse,
        tags=["trading"],
    )
    def cross_spread_snapshot() -> CrossSpreadSnapshotResponse:
        snapshot = get_cross_spread_snapshot()
        return snapshot.model_copy(
            update={
                "position_overview": get_cross_spread_position_overview(
                    snapshot,
                    strategy_instance_id=CROSS_SPREAD_STRATEGY_INSTANCE_ID,
                    bybit_account_id=get_bybit_account_id(),
                    mt5_account_id=get_mt5_account_id(),
                )
            }
        )

    @router.get(
        f"{api_prefix}/trading/cross-spread/history",
        response_model=list[CrossSpreadHistoryPointResponse],
        tags=["trading"],
    )
    def cross_spread_history(
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> list[CrossSpreadHistoryPointResponse]:
        return get_cross_spread_history(limit)

    @router.post(
        f"{api_prefix}/trading/cross-spread/preflight",
        response_model=CrossSpreadPreflightResponse,
        tags=["trading"],
    )
    def cross_spread_preflight(
        request: CrossSpreadPreflightRequest,
        http_request: Request,
    ) -> dict[str, object]:
        require_principal(http_request)
        return prepare_cross_spread_market_command(request)

    @router.get(
        f"{api_prefix}/trading/cross-spread/funding-transfer/quote",
        response_model=FundingTransferQuoteResponse,
        tags=["trading"],
    )
    def cross_spread_funding_transfer_quote(
        http_request: Request,
    ) -> FundingTransferQuoteResponse:
        require_principal(http_request)
        return get_funding_transfer_quote()

    @router.post(
        f"{api_prefix}/trading/cross-spread/funding-transfer",
        response_model=InternalCapitalTransferResponse,
        tags=["trading"],
    )
    def cross_spread_funding_transfer(
        request: CreateInternalCapitalTransferRequest,
        http_request: Request,
    ) -> InternalCapitalTransferResponse:
        return create_funding_transfer(
            request,
            requested_by=require_principal(http_request).user_id,
        )

    @router.get(
        f"{api_prefix}/trading/cross-spread/funding-transfers/{{transfer_id}}",
        response_model=InternalCapitalTransferResponse,
        tags=["trading"],
    )
    def cross_spread_funding_transfer_status(
        transfer_id: str,
        http_request: Request,
    ) -> InternalCapitalTransferResponse:
        require_principal(http_request)
        return get_funding_transfer(transfer_id)

    @router.post(
        f"{api_prefix}/trading/cross-spread/funding-transfers/{{transfer_id}}/cancel",
        response_model=InternalCapitalTransferResponse,
        tags=["trading"],
    )
    def cross_spread_funding_transfer_cancel(
        transfer_id: str,
        http_request: Request,
    ) -> InternalCapitalTransferResponse:
        principal = require_principal(http_request)
        return cancel_funding_transfer(transfer_id, requested_by=principal.user_id)

    @router.post(
        f"{api_prefix}/trading/cross-spread/market-command",
        response_model=ExecutionBatchResponse,
        tags=["trading"],
    )
    def cross_spread_market_command(
        request: CrossSpreadMarketCommandRequest,
    ) -> ExecutionBatchResponse:
        return submit_cross_spread_market_command(request)

    @router.post(
        f"{api_prefix}/trading/funding/market-command",
        response_model=ExecutionBatchResponse,
        tags=["trading"],
    )
    def funding_market_command(
        request: FundingMarketCommandRequest,
        http_request: Request,
    ) -> ExecutionBatchResponse:
        principal = require_principal(http_request)
        return submit_funding_market_command(request, requested_by=principal.user_id)

    @router.get(
        f"{api_prefix}/trading/funding/execution-context",
        response_model=FundingExecutionContextResponse,
        tags=["trading"],
    )
    def funding_execution_context(
        http_request: Request,
        perpetual_symbol: str | None = Query(default=None, alias="perpetualSymbol"),
        spot_symbol: str | None = Query(default=None, alias="spotSymbol"),
        notional: Annotated[Decimal | None, Query(gt=0, allow_inf_nan=False)] = None,
        quantity: Annotated[Decimal | None, Query(gt=0, allow_inf_nan=False)] = None,
    ) -> dict[str, object]:
        require_principal(http_request)
        return get_funding_execution_context(
            perpetual_symbol=perpetual_symbol,
            spot_symbol=spot_symbol,
            notional=notional,
            quantity=quantity,
        )

    @router.get(
        f"{api_prefix}/trading/funding/positions",
        response_model=list[FundingPositionGroupResponse],
        tags=["trading"],
    )
    def funding_positions(
        http_request: Request,
        scope: str = Query(default="active"),
    ) -> list[dict[str, object]]:
        require_principal(http_request)
        return list_funding_position_groups(scope=scope)

    @router.get(
        f"{api_prefix}/trading/funding/instructions",
        response_model=FundingWorkspaceResponse,
        tags=["trading"],
    )
    def funding_instruction_by_idempotency(
        http_request: Request,
        idempotency_key: str = Query(alias="idempotencyKey"),
    ) -> dict[str, object]:
        require_principal(http_request)
        return get_funding_instruction_workspace_by_idempotency(idempotency_key)

    @router.post(
        f"{api_prefix}/trading/funding/instructions",
        response_model=FundingWorkspaceResponse,
        tags=["trading"],
    )
    def funding_instruction_submit(
        payload: FundingInstructionRequest,
        http_request: Request,
    ) -> dict[str, object]:
        principal = require_principal(http_request)
        return submit_funding_instruction(
            action=payload.action,
            idempotency_key=payload.idempotency_key,
            perpetual_symbol=payload.perpetual_symbol,
            spot_symbol=payload.spot_symbol,
            quantity=payload.quantity,
            requested_by=principal.user_id,
            target_open_instruction_id=payload.target_open_instruction_id,
            execution_policy=payload.execution_policy,
            perpetual_limit_price=payload.perpetual_limit_price,
            expected_perpetual_quantity=payload.expected_perpetual_quantity,
        )

    @router.get(
        f"{api_prefix}/trading/funding/instructions/{{instruction_id}}",
        response_model=FundingWorkspaceResponse,
        tags=["trading"],
    )
    def funding_instruction_workspace(
        instruction_id: str,
        http_request: Request,
    ) -> dict[str, object]:
        require_principal(http_request)
        return get_funding_instruction_workspace(instruction_id)

    @router.post(
        f"{api_prefix}/trading/commands",
        response_model=TradeCommandResponse,
        tags=["trading"],
    )
    def create_command(request: CreateTradeCommandRequest) -> TradeCommandResponse:
        reject_controlled_strategy_write_bypass(request.strategy_instance_id)
        return create_trade_command(request)

    @router.get(
        f"{api_prefix}/trading/commands/{{trade_command_id}}",
        response_model=TradeCommandResponse,
        tags=["trading"],
    )
    def trade_command(trade_command_id: str) -> TradeCommandResponse:
        return get_trade_command(trade_command_id)

    @router.get(
        f"{api_prefix}/trading/orders",
        response_model=list[OrderDetailResponse],
        tags=["trading"],
    )
    def orders(
        strategy_instance_id: str | None = Query(
            default=None,
            alias="strategyInstanceId",
        ),
    ) -> list[OrderDetailResponse]:
        return list_orders(strategy_instance_id)

    @router.get(
        f"{api_prefix}/trading/orders/{{order_id}}",
        response_model=OrderDetailResponse,
        tags=["trading"],
    )
    def order(order_id: str) -> OrderDetailResponse:
        return get_order(order_id)

    @router.get(
        f"{api_prefix}/trading/fills",
        response_model=list[FillResponse],
        tags=["trading"],
    )
    def fills(
        strategy_instance_id: str | None = Query(
            default=None,
            alias="strategyInstanceId",
        ),
    ) -> list[FillResponse]:
        return list_fills(strategy_instance_id)

    @router.get(
        f"{api_prefix}/trading/execution-batches",
        response_model=list[ExecutionBatchResponse],
        tags=["trading"],
    )
    def execution_batches(
        strategy_instance_id: str | None = Query(
            default=None,
            alias="strategyInstanceId",
        ),
    ) -> list[ExecutionBatchResponse]:
        return list_execution_batches(strategy_instance_id)

    @router.get(
        f"{api_prefix}/trading/execution-batches/{{batch_id}}",
        response_model=ExecutionBatchResponse,
        tags=["trading"],
    )
    def get_batch(batch_id: str) -> ExecutionBatchResponse:
        return get_execution_batch(batch_id)

    return router
