"""Export the strategy-facing API without lifespan, database access or network I/O."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.application import app  # noqa: E402


def strategy_openapi() -> dict:
    schema = app.openapi()
    prefixes = (
        "/api/v1/trading/",
        "/api/v1/strategies/",
        "/api/v1/accounts",
        "/api/v1/instruments",
        "/api/v1/live-trading/",
        "/api/v1/security/",
        "/api/v1/system/runtime-readiness",
        "/api/v1/ops/reconciliation-summary",
    )
    schema["paths"] = {
        key: value for key, value in schema["paths"].items() if key.startswith(prefixes)
    }
    selected: dict = {}

    def visit(value):
        if isinstance(value, dict):
            ref = value.get("$ref", "")
            prefix = "#/components/schemas/"
            if ref.startswith(prefix):
                name = ref.removeprefix(prefix)
                if name not in selected:
                    selected[name] = schema["components"]["schemas"][name]
                    visit(selected[name])
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(schema["paths"])
    schema["components"]["schemas"] = selected
    return schema


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    schema = strategy_openapi()
    if "--check" in sys.argv:
        stored = (
            Path(__file__).resolve().parents[2] / "docs/contracts/platform-strategy.openapi.json"
        )
        if json.loads(stored.read_text(encoding="utf-8")) != schema:
            raise SystemExit("Strategy OpenAPI is stale; run pnpm generate:strategy-api")
    else:
        print(json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True))
