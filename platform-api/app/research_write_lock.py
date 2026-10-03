"""Shared in-process lock for SQLite research writes.

Collectors may fetch concurrently, but publication, projections, and refresh
snapshots must never commit against the same SQLite file at the same time.
"""

from __future__ import annotations

import asyncio

RESEARCH_DB_WRITE_LOCK = asyncio.Lock()
