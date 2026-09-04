from __future__ import annotations

from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError
from app.research_provider_macro_dashboard import MacroDashboardResponse


class CommodityDashboardProvider:
    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._last_known_good: MacroDashboardResponse | None = None

    async def get(self) -> MacroDashboardResponse:
        try:
            document = read_local_json("public/v1/commodity/dashboard.json")
            if document.get("schemaVersion") != "1.0":
                raise ResearchProviderError("commodity_dashboard_schema_mismatch")
            contract = MacroDashboardResponse.model_validate(document)
            if not any(contract.groups.values()):
                raise ResearchProviderError("commodity_dashboard_without_series")
            self._last_known_good = contract.model_copy(deep=True)
            return contract
        except Exception as exc:
            if self._last_known_good is not None:
                return self._last_known_good.model_copy(deep=True)
            if isinstance(exc, ResearchProviderError):
                raise
            raise ResearchProviderError(
                f"commodity_dashboard_unavailable:{type(exc).__name__}"
            ) from exc
