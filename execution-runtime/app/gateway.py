from typing import Protocol

from app.models import ExecutionEvent, SubmitOrderCommand


class ExecutionGateway(Protocol):
    name: str

    def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        """Submit one normalized platform order command to the configured venue."""
