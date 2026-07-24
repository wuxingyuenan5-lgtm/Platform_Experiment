"""Assign every runtime test to one executable test layer."""

from __future__ import annotations

from pathlib import Path

import pytest

LIVE_SAFETY_PATTERNS = (
    "atomic_command_claim",
    "bybit_live",
    "connectivity",
    "live",
    "mt5_live",
    "redaction",
    "secret",
)
UNIT_PATTERNS = (
    "cross_spread_market",
    "gateway_factory",
)
INTEGRATION_PATTERNS = (
    "bridge",
    "gateway",
    "journal",
    "query",
    "readiness",
    "venue",
)
PRIMARY_MARKERS = ("unit", "integration", "live_safety")


def classify_test_file(path: Path) -> str:
    """Return the single primary layer for a runtime test module."""

    name = path.stem.lower()
    if any(pattern in name for pattern in LIVE_SAFETY_PATTERNS):
        return "live_safety"
    if any(pattern in name for pattern in UNIT_PATTERNS):
        return "unit"
    if any(pattern in name for pattern in INTEGRATION_PATTERNS):
        return "integration"
    return "unit"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply exactly one primary marker to every collected runtime test."""

    for item in items:
        marker = classify_test_file(Path(str(item.path)))
        item.add_marker(getattr(pytest.mark, marker))
        primary_markers = {
            name for name in PRIMARY_MARKERS if item.get_closest_marker(name) is not None
        }
        if primary_markers != {marker}:
            raise pytest.UsageError(
                f"{item.nodeid} must have exactly one primary test marker; "
                f"found {sorted(primary_markers)}"
            )
