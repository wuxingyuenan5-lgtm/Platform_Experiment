from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time as wall_time
from decimal import Decimal
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.research_providers import FreeResearchProvider

MARKET_TIMEZONE = ZoneInfo("Asia/Shanghai")
EASTMONEY_QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"


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


def market_session(observed_at: datetime) -> str:
    if observed_at.weekday() >= 5:
        return "non_trading"
    current = observed_at.time()
    morning = wall_time(9, 30) <= current <= wall_time(11, 30)
    afternoon = wall_time(13, 0) <= current <= wall_time(15, 0)
    return "trading" if morning or afternoon else "non_trading"


def eastmoney_scaled(value: Any) -> Decimal | None:
    if value in (None, "", "-"):
        return None
    try:
        return Decimal(str(value)) / Decimal("100")
    except Exception:  # noqa: BLE001 - acceptance evidence preserves malformed upstream values
        return None


async def eastmoney_quote_600519(timeout_seconds: float) -> dict[str, Any]:
    params = {
        "secid": "1.600519",
        "fields": "f43,f57,f58,f60,f170",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 Chrome/150.0 Safari/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        response = await client.get(EASTMONEY_QUOTE_URL, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise RuntimeError("eastmoney_quote_payload_missing")
    price = eastmoney_scaled(data.get("f43"))
    previous_close = eastmoney_scaled(data.get("f60"))
    change_pct = eastmoney_scaled(data.get("f170"))
    if price is None:
        raise RuntimeError("eastmoney_quote_price_missing")
    return {
        "name": str(data.get("f58") or ""),
        "code": str(data.get("f57") or ""),
        "price": price,
        "lastClose": previous_close,
        "changePct": change_pct,
        "source": "Eastmoney single-security quote",
    }


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
    except Exception as exc:  # noqa: BLE001 - smoke evidence must preserve provider failures
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        return {
            "name": name,
            "status": "failed",
            "elapsedMs": elapsed_ms,
            "errorType": type(exc).__name__,
            "error": str(exc),
        }


def quote_cross_check(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {str(item.get("name")): item for item in results}
    tencent = by_name.get("stock_quote_600519")
    eastmoney = by_name.get("eastmoney_quote_600519")
    if not tencent or not eastmoney:
        return {
            "name": "quote_cross_source_600519",
            "status": "failed",
            "error": "quote_check_result_missing",
        }
    if tencent.get("status") != "passed" or eastmoney.get("status") != "passed":
        return {
            "name": "quote_cross_source_600519",
            "status": "failed",
            "error": "one_or_more_quote_sources_unavailable",
        }
    tencent_sample = tencent.get("sample")
    eastmoney_sample = eastmoney.get("sample")
    try:
        tencent_price = Decimal(str(tencent_sample["price"]))
        eastmoney_price = Decimal(str(eastmoney_sample["price"]))
    except (KeyError, TypeError, ArithmeticError) as exc:
        return {
            "name": "quote_cross_source_600519",
            "status": "failed",
            "error": f"quote_price_parse_failed:{type(exc).__name__}",
        }
    difference = abs(tencent_price - eastmoney_price)
    tolerance = max(Decimal("1.00"), tencent_price * Decimal("0.0015"))
    return {
        "name": "quote_cross_source_600519",
        "status": "passed" if difference <= tolerance else "failed",
        "sample": {
            "tencentPrice": tencent_price,
            "eastmoneyPrice": eastmoney_price,
            "absoluteDifference": difference,
            "tolerance": tolerance.quantize(Decimal("0.01")),
        },
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
        ("eastmoney_quote_600519", lambda: eastmoney_quote_600519(timeout_seconds)),
    )
    results = [
        await run_check(name, loader, timeout_seconds=timeout_seconds)
        for name, loader in checks
    ]
    results.append(quote_cross_check(results))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run optional live checks against free research providers. "
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
    observed_at = datetime.now(MARKET_TIMEZONE)
    results = asyncio.run(main_async(max(5.0, arguments.timeout)))
    passed = sum(item["status"] == "passed" for item in results)
    summary = {
        "status": "passed" if passed == len(results) else "partial",
        "observedAt": observed_at.isoformat(),
        "marketTimezone": str(MARKET_TIMEZONE),
        "marketSession": market_session(observed_at),
        "passed": passed,
        "failed": len(results) - passed,
        "checks": results,
        "executionAuthoritative": False,
        "humanReviewRequired": True,
    }
    print(json.dumps(json_value(summary), ensure_ascii=False, indent=2))
    return 1 if arguments.strict and passed != len(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
