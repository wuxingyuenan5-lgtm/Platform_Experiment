from fastapi import FastAPI

from app.fake_gateway import FakeGateway
from app.models import ExecutionEvent, SubmitOrderCommand

app = FastAPI(title="Variable-Global Execution Runtime", version="0.1.0")
gateway = FakeGateway()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "execution-runtime",
        "gateway": "fake",
    }


@app.post("/commands/orders", response_model=list[ExecutionEvent], tags=["commands"])
def submit_order(command: SubmitOrderCommand) -> list[ExecutionEvent]:
    return gateway.submit_order(command)
