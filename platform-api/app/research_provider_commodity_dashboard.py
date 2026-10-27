from __future__ import annotations

import asyncio

from app.research_local_data import local_json_revision, read_local_json
from app.research_provider_errors import ResearchProviderError
from app.research_provider_macro_dashboard import MacroDashboardResponse


class CommodityDashboardProvider:
    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._last_known_good: MacroDashboardResponse | None = None
        self._revision: tuple[str, int, int, int] | None = None
        self._load_lock = asyncio.Lock()

    def _load(self) -> MacroDashboardResponse:
        path = "public/v1/commodity/dashboard.json"
        revision = local_json_revision(path)
        if (
            revision is not None
            and revision == self._revision
            and self._last_known_good is not None
        ):
            self._last_known_good.apply_freshness()
            return self._last_known_good
        document = read_local_json(path)
        if document.get("schemaVersion") != "1.0":
            raise ResearchProviderError("commodity_dashboard_schema_mismatch")
        contract = MacroDashboardResponse.model_validate(document)
        contract.apply_freshness()
        if not any(contract.groups.values()):
            raise ResearchProviderError("commodity_dashboard_without_series")
        self._last_known_good = contract
        self._revision = revision
        return contract

    async def get(self) -> MacroDashboardResponse:
        async with self._load_lock:
            try:
                # JSON decoding and Decimal validation must not block the API event loop.
                return await asyncio.to_thread(self._load)
            except Exception as exc:
                if self._last_known_good is not None:
                    return self._last_known_good.stale_copy()
                if isinstance(exc, ResearchProviderError):
                    raise
                raise ResearchProviderError(
                    f"commodity_dashboard_unavailable:{type(exc).__name__}"
                ) from exc
