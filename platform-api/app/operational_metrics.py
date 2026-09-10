"""Prometheus export of operational evidence; never financial truth or a scheduler."""

import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from prometheus_client.core import GaugeMetricFamily

from app.auth import require_principal
from app.config import get_settings
from app.metrics_repository import read_operational_metrics


def _age(timestamp: str | None, now: datetime) -> float:
    if timestamp is None:
        return float("nan")
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return float("nan")
    if parsed.tzinfo is None:
        return float("nan")
    return max(0, (now - parsed).total_seconds())


class OperationalCollector:
    def describe(self):
        # Prometheus must not invoke database collection during module import.
        return []

    def collect(self):
        available = GaugeMetricFamily(
            "vg_platform_metrics_snapshot_available", "Existing operational store can be read"
        )
        try:
            snapshot = read_operational_metrics()
        except (sqlite3.Error, OSError):
            available.add_metric([], 0)
            yield available
            return
        available.add_metric([], 1)
        yield available
        now = datetime.now(UTC)
        risk_available = GaugeMetricFamily(
            "vg_platform_metrics_risk_store_available", "Existing execution risk store can be read"
        )
        risk_available.add_metric([], int(snapshot["risks"] is not None))
        yield risk_available
        for source in ("instructions", "batches", "risks"):
            rows = snapshot[source]
            if rows is None:
                continue
            count = GaugeMetricFamily(
                f"vg_platform_pending_{source}",
                "Persisted pending work, not in-memory tasks",
                labels=["strategy", "state"],
            )
            age = GaugeMetricFamily(
                f"vg_platform_pending_{source}_oldest_seconds",
                "Age since work creation; risk evidence uses last recorded update",
                labels=["strategy", "state"],
            )
            grouped: dict[tuple[str, str], tuple[int, float]] = {}
            for strategy, state, total, created in rows:
                # No user-selected instance, account, order, or command IDs in labels.
                key = (
                    strategy if strategy in {"funding_arbitrage", "cross_spread"} else "other",
                    state
                    if state
                    in {
                        "accepted",
                        "executing",
                        "reconciling",
                        "result_unknown",
                        "manual_intervention",
                        "pending",
                        "dispatching",
                        "partially_filled",
                        "partially_executed",
                        "residual_exposure",
                        "submitting",
                        "first_leg_filled",
                        "hedging",
                        "disposition_in_progress",
                        "escalated",
                    }
                    else "other",
                )
                previous = grouped.get(key, (0, 0.0))
                grouped[key] = (previous[0] + total, max(previous[1], _age(created, now)))
            for key, (total, oldest) in grouped.items():
                count.add_metric(list(key), total)
                age.add_metric(list(key), oldest)
            yield count
            yield age
        accounts = GaugeMetricFamily(
            "vg_platform_account_sync", "Persisted account sync count", labels=["venue", "state"]
        )
        last_success = GaugeMetricFamily(
            "vg_platform_account_sync_oldest_success_seconds",
            "Oldest successful sync age",
            labels=["venue", "state"],
        )
        snapshot_age = GaugeMetricFamily(
            "vg_platform_account_snapshot_oldest_seconds",
            "Oldest source snapshot age",
            labels=["venue", "state"],
        )
        missing = GaugeMetricFamily(
            "vg_platform_account_evidence_missing",
            "Accounts without persisted time evidence",
            labels=["venue", "state", "evidence"],
        )
        for venue, state, total, success, observed, no_success, no_snapshot in (
            snapshot["accounts"] or []
        ):
            labels = [venue, state]
            accounts.add_metric(labels, total)
            last_success.add_metric(labels, _age(success, now))
            snapshot_age.add_metric(labels, _age(observed, now))
            missing.add_metric([*labels, "last_success"], no_success)
            missing.add_metric([*labels, "source_snapshot"], no_snapshot)
        yield accounts
        yield last_success
        yield snapshot_age
        yield missing


REGISTRY.register(OperationalCollector())
router = APIRouter(prefix=get_settings().api_prefix, tags=["production-operations"])


@router.get("/ops/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    require_principal(request)  # Middleware additionally requires audit:read.
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})
