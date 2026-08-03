from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.gateway import ExecutionGateway
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.journal import (
    claim_command,
    get_events,
    mark_command_result_unknown,
    save_command_events,
)
from app.models import ExecutionEvent
from app.runtime_contracts import (
    RuntimeExecutionEventV1,
    RuntimeSubmitOrderCommandV1,
    version_execution_events,
)


def create_command_router(*, gateway: ExecutionGateway) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/commands/orders",
        response_model=list[RuntimeExecutionEventV1],
        tags=["commands"],
    )
    def submit_order(command: RuntimeSubmitOrderCommandV1) -> list[RuntimeExecutionEventV1]:
        if not claim_command(command):
            events = get_events(command.command_id)
            if not events:
                raise HTTPException(
                    status_code=409,
                    detail="Command is already processing and has no persisted events yet",
                )
            return version_execution_events(events)

        try:
            events = gateway.submit_order(command)
        except (GatewayConfigurationError, GatewayRequestRejectedError) as exc:
            events = [
                ExecutionEvent(
                    command_id=command.command_id,
                    platform_order_id=command.platform_order_id,
                    event_type="order_rejected",
                    reason=str(exc),
                )
            ]
        except GatewayResultUnknownError as exc:
            mark_command_result_unknown(command.command_id)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        save_command_events(command, events)
        return version_execution_events(events)

    @router.get(
        "/commands/{command_id}/events",
        response_model=list[RuntimeExecutionEventV1],
        tags=["commands"],
    )
    def command_events(command_id: str) -> list[RuntimeExecutionEventV1]:
        events = get_events(command_id)
        if not events:
            raise HTTPException(status_code=404, detail="Command events not found")
        return version_execution_events(events)

    return router
