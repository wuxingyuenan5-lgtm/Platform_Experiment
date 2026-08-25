from decimal import Decimal

from fastapi import APIRouter, Query, Request

from app.auth import require_principal
from app.catalog import get_order, list_fills, list_orders
from app.cross_spread import (
    get_cross_spread_history,
    get_cross_spread_snapshot,
    submit_cross_spread_market_command,
)
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
    create_funding_transfer,
    get_funding_transfer,
    get_funding_transfer_quote,
)
from app.strategies.funding_workspace import (
    get_funding_execution_context,
    get_funding_instruction_workspace,
    list_funding_position_groups,
    submit_funding_instruction,
)
from app.trade_commands import create_trade_command, get_trade_command
from app.trading import reconcile_order, submit_order


def create_trading_router(api_prefix: str) -> APIRouter:
    router = APIRouter()

    @router.post(
        f"{api_prefix}/trading/orders",
        response_model=OrderResponse,
        tags=["trading"],
        deprecated=True,
        summary="Compatibility order endpoint; use TradeCommand or ExecutionBatch",
    )
    def create_order(request: CreateOrderRequest) -> OrderResponse:
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
        return create_execution_batch(request)

    @router.get(
        f"{api_prefix}/trading/cross-spread/snapshot",
        response_model=CrossSpreadSnapshotResponse,
        tags=["trading"],
    )
    def cross_spread_snapshot() -> CrossSpreadSnapshotResponse:
        return get_cross_spread_snapshot()

    @router.get(
        f"{api_prefix}/trading/cross-spread/history",
        response_model=list[CrossSpreadHistoryPointResponse],
        tags=["trading"],
    )
    def cross_spread_history(
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> list[CrossSpreadHistoryPointResponse]:
        return get_cross_spread_history(limit)

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

    @router.get(f"{api_prefix}/trading/funding/execution-context", tags=["trading"])
    def funding_execution_context(
        http_request: Request,
        perpetual_symbol: str | None = Query(default=None, alias="perpetualSymbol"),
        spot_symbol: str | None = Query(default=None, alias="spotSymbol"),
        notional: str | None = Query(default=None),
    ) -> dict[str, object]:
        require_principal(http_request)
        return get_funding_execution_context(
            perpetual_symbol=perpetual_symbol,
            spot_symbol=spot_symbol,
            notional=Decimal(notional) if notional not in (None, "") else None,
        )

    @router.get(f"{api_prefix}/trading/funding/positions", tags=["trading"])
    def funding_positions(http_request: Request) -> list[dict[str, object]]:
        require_principal(http_request)
        return list_funding_position_groups()

    @router.post(f"{api_prefix}/trading/funding/instructions", tags=["trading"])
    def funding_instruction_submit(
        payload: dict[str, object],
        http_request: Request,
    ) -> dict[str, object]:
        principal = require_principal(http_request)
        return submit_funding_instruction(
            action=str(payload["action"]),
            idempotency_key=str(payload["idempotencyKey"]),
            perpetual_symbol=str(payload["perpetualSymbol"]),
            spot_symbol=str(payload["spotSymbol"]),
            quantity=Decimal(str(payload["quantity"])),
            requested_by=principal.user_id,
        )

    @router.get(
        f"{api_prefix}/trading/funding/instructions/{{instruction_id}}",
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
    def orders() -> list[OrderDetailResponse]:
        return list_orders()

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
    def fills() -> list[FillResponse]:
        return list_fills()

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
