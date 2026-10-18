from __future__ import annotations

import asyncio

from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError
from app.research_provider_macro_dashboard import MacroDashboardResponse


class CryptoDashboardProvider:
    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._last_known_good: MacroDashboardResponse | None = None

    async def get(self) -> MacroDashboardResponse:
        try:
            document = await asyncio.to_thread(read_local_json, "public/v1/crypto/dashboard.json")
            if document.get("schemaVersion") != "1.0":
                raise ResearchProviderError("crypto_dashboard_schema_mismatch")
            contract = MacroDashboardResponse.model_validate(document)
            contract.apply_freshness()
            if not any(contract.groups.values()):
                raise ResearchProviderError("crypto_dashboard_without_series")
            # The route only serializes this contract; stale_copy owns mutation isolation.
            self._last_known_good = contract
            return contract
        except Exception as exc:
            if self._last_known_good is not None:
                return self._last_known_good.stale_copy()
            if isinstance(exc, ResearchProviderError):
                raise
            raise ResearchProviderError(
                f"crypto_dashboard_unavailable:{type(exc).__name__}"
            ) from exc
