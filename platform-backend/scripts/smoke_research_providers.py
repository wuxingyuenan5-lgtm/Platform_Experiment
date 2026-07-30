from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from app.research_providers import FreeResearchProvider


def json_value(value: Any) -> Any:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return json_value(model_dump(by_alias=True, mode="json"))
    if is_dataclass(value):
        return json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_value(item) for item in value]
    if isinstance(value, (date, datetime, Decimal, Enum)):
        return str(value)
    return value


def sample_size(value: Any) -> int | None:
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return None


async def run_check(
    name: str,
    loader: Callable[[], Awaitable[Any]],
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        value = await asyncio.wait_for(loader(), timeout=timeout_seconds)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        size = sample_size(value)
        sample = value[:2] if isinstance(value, list) else value
        return {
            "name": name,
            "status": "passed",
            "elapsedMs": elapsed_ms,
            "sampleSize": size,
            "sample": json_value(sample),
        }
    except Exception as exc:  # noqa: BLE001 - smoke output must preserve provider failures
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return {
            "name": name,
            "status": "failed",
            "elapsedMs": elapsed_ms,
            "errorType": type(exc).__name__,
            "error": str(exc),
        }


async def main_async(timeout_seconds: float) -> list[dict[str, Any]]:
    provider = FreeResearchProvider(timeout_seconds=min(timeout_seconds, 30.0))
    checks: tuple[tuple[str, Callable[[], Awaitable[Any]]], ...] = (
        ("a_share_spot", provider.a_share_spot),
        ("market_activity", provider.market_activity),
        ("index_snapshots", provider.index_snapshots),
        ("shenwan_memberships", provider.shenwan_memberships),
        ("short_term_emotion", provider.short_term_emotion),
        ("stock_quote_600519", lambda: provider.stock_quote("600519")),
    )
    return [
        await run_check(name, loader, timeout_seconds=timeout_seconds)
        for name, loader in checks
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run optional live smoke checks against free research providers. "
            "External uptime is reported but is non-blocking unless --strict is supplied."
        )
    )
    parser.add_argument("--timeout", type=float, default=45.0, help="Per-check timeout in seconds")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code when any external provider check fails",
    )
    arguments = parser.parse_args()
    results = asyncio.run(main_async(max(5.0, arguments.timeout)))
    passed = sum(item["status"] == "passed" for item in results)
    summary = {
        "status": "passed" if passed == len(results) else "partial",
        "passed": passed,
        "failed": len(results) - passed,
        "checks": results,
        "executionAuthoritative": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if arguments.strict and passed != len(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
