from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any

import httpx

_ALLOWED_STATUSES = {"ready", "partial", "stale", "no_data", "error"}
_HARD_FAILURE_STATUSES = {"error"}


@dataclass(slots=True)
class AcceptanceReport:
    checks: list[dict[str, Any]] = field(default_factory=list)
    hard_failures: int = 0

    def add(self, name: str, passed: bool, detail: str, *, hard: bool = True) -> None:
        self.checks.append({"name": name, "passed": passed, "detail": detail, "hard": hard})
        if hard and not passed:
            self.hard_failures += 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe the running Platform research API and record live upstream metadata. "
            "This script does not call providers directly and does not replace human value checks."
        )
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--stock-code", default="600519")
    parser.add_argument("--threshold-yuan", type=int, default=10_000_000_000)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--session-token", default="")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", default="")
    return parser.parse_args()


def request_headers(args: argparse.Namespace) -> tuple[dict[str, str], dict[str, str]]:
    headers: dict[str, str] = {}
    cookies: dict[str, str] = {}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"
    if args.session_token:
        cookies["vg_session"] = args.session_token
    return headers, cookies


def get_json(client: httpx.Client, path: str) -> dict[str, Any]:
    response = client.get(path)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} did not return a JSON object")
    return payload


def validate_meta(report: AcceptanceReport, label: str, module: Any) -> None:
    if not isinstance(module, dict):
        report.add(label, False, "module is not an object")
        return
    meta = module.get("meta")
    if not isinstance(meta, dict):
        report.add(label, False, "meta is missing")
        return
    status = str(meta.get("status") or "")
    source = str(meta.get("source") or "").strip()
    fetched_at = str(meta.get("fetchedAt") or "").strip()
    passed = status in _ALLOWED_STATUSES and bool(source) and bool(fetched_at)
    report.add(
        label,
        passed,
        f"status={status or 'missing'}, source={source or 'missing'}, fetchedAt={fetched_at or 'missing'}",
    )
    report.add(
        f"{label}.upstream_available",
        status not in _HARD_FAILURE_STATUSES,
        f"status={status or 'missing'}; no_data/partial/stale require human review",
        hard=False,
    )


def validate_dashboard(report: AcceptanceReport, payload: dict[str, Any]) -> None:
    for key in ("marketDetail", "breadth", "shenwan", "emotion"):
        validate_meta(report, f"dashboard.{key}", payload.get(key))

    market_data = (payload.get("marketDetail") or {}).get("data")
    report.add(
        "dashboard.marketDetail.rows",
        isinstance(market_data, list) and len(market_data) > 0,
        f"rows={len(market_data) if isinstance(market_data, list) else 'invalid'}",
        hard=False,
    )

    shenwan_data = (payload.get("shenwan") or {}).get("data")
    unmatched: list[Any] = []
    if isinstance(shenwan_data, dict):
        raw_unmatched = shenwan_data.get("unmatchedSecurityCodes")
        if isinstance(raw_unmatched, list):
            unmatched = raw_unmatched
    report.add(
        "dashboard.shenwan.unmatched",
        len(unmatched) == 0,
        f"unmatchedSecurityCodes={len(unmatched)}; review every non-zero result",
        hard=False,
    )


def validate_snapshot(report: AcceptanceReport, payload: dict[str, Any]) -> None:
    code = str(payload.get("securityCode") or "")
    modules = payload.get("modules")
    report.add("snapshot.securityCode", len(code) == 6 and code.isdigit(), f"securityCode={code}")
    report.add(
        "snapshot.modules",
        isinstance(modules, dict) and len(modules) > 0,
        f"modules={len(modules) if isinstance(modules, dict) else 'invalid'}",
        hard=False,
    )
    if isinstance(modules, dict):
        for key, module in modules.items():
            validate_meta(report, f"snapshot.{key}", module)


def validate_macro(report: AcceptanceReport, payload: dict[str, Any]) -> None:
    validate_meta(report, "macro.events", payload.get("events"))
    events = (payload.get("events") or {}).get("data")
    report.add(
        "macro.events.rows",
        isinstance(events, list) and len(events) > 0,
        f"events={len(events) if isinstance(events, list) else 'invalid'}",
        hard=False,
    )


def main() -> int:
    args = parse_args()
    headers, cookies = request_headers(args)
    base_url = args.base_url.rstrip("/")
    report = AcceptanceReport()

    try:
        with httpx.Client(
            base_url=base_url,
            headers=headers,
            cookies=cookies,
            timeout=args.timeout,
            follow_redirects=True,
        ) as client:
            health = get_json(client, "/health")
            report.add("platform.health", health.get("status") == "ok", json.dumps(health, ensure_ascii=False))

            dashboard = get_json(
                client,
                f"/api/v1/research/a-share/dashboard?thresholdYuan={args.threshold_yuan}",
            )
            validate_dashboard(report, dashboard)

            snapshot = get_json(
                client,
                f"/api/v1/research/a-share/stocks/{args.stock_code}/snapshot",
            )
            validate_snapshot(report, snapshot)

            macro = get_json(client, "/api/v1/research/macro/expectations")
            validate_macro(report, macro)
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        report.add("probe.execution", False, str(exc))

    result = {
        "baseUrl": base_url,
        "stockCode": args.stock_code,
        "thresholdYuan": args.threshold_yuan,
        "hardFailures": report.hard_failures,
        "checks": report.checks,
        "humanReviewRequired": [
            "指数价格、涨跌幅和成交额与可信行情终端交叉核对",
            "20日波动率抽样复算",
            "申万未匹配证券逐项核查",
            "涨停、炸板、连板梯队与当日市场核对",
            "研报、公告和新闻原文链接可访问性",
            "交易时段与非交易时段各执行一次",
        ],
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as output:
            output.write(rendered)
            output.write("\n")
    return 1 if report.hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
