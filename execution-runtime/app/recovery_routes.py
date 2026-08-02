from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.gateway import ExecutionGateway
from app.journal import JournalEventError
from app.runtime_contracts import RuntimeExecutionEventV1, version_execution_events
from app.runtime_recovery import (
    RecoveryCommandNotFoundError,
    RecoveryCommandNotReadyError,
    RecoveryEvidenceMismatchError,
    recover_command,
)


def create_recovery_router(*, gateway: ExecutionGateway) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/commands/{command_id}/recover",
        response_model=list[RuntimeExecutionEventV1],
        tags=["commands"],
    )
    def recover(command_id: str) -> list[RuntimeExecutionEventV1]:
        try:
            return version_execution_events(recover_command(command_id, gateway=gateway))
        except RecoveryCommandNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Runtime command not found") from exc
        except RecoveryCommandNotReadyError as exc:
            raise HTTPException(
                status_code=409, detail="Runtime command is not recoverable yet"
            ) from exc
        except (RecoveryEvidenceMismatchError, JournalEventError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return router
