from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import httpx

from app.research_provider_errors import ResearchProviderError
from app.research_provider_macro_dashboard import MacroDashboardResponse

CRYPTO_DASHBOARD_URLS = (
    "https://raw.githubusercontent.com/wuxingyuenan5-lgtm/platform-data/"
    "main/public/v1/crypto/dashboard.json",
    "https://cdn.jsdelivr.net/gh/wuxingyuenan5-lgtm/platform-data@main/"
    "public/v1/crypto/dashboard.json",
)


class CryptoDashboardProvider:
    def __init__(self, *, timeout_seconds: float, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._last_known_good: MacroDashboardResponse | None = None

    async def get(self) -> MacroDashboardResponse:
        try:
            payload: Any = None
            last_error: Exception | None = None
            cache_key = int(datetime.now(UTC).timestamp() // 300)
            async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
                for url in CRYPTO_DASHBOARD_URLS:
                    try:
                        response = await client.get(
                            url,
                            params={"v": cache_key},
                            headers={"User-Agent": self._user_agent},
                        )
                        response.raise_for_status()
                        payload = response.json()
                        break
                    except Exception as exc:
                        last_error = exc
            if payload is None and last_error is not None:
                raise last_error
            if not isinstance(payload, dict):
                raise ResearchProviderError("crypto_dashboard_invalid_payload")
            document = cast(dict[str, Any], payload)
            if document.get("schemaVersion") != "1.0":
                raise ResearchProviderError("crypto_dashboard_schema_mismatch")
            contract = MacroDashboardResponse.model_validate(document)
            if not any(contract.groups.values()):
                raise ResearchProviderError("crypto_dashboard_without_series")
            self._last_known_good = contract.model_copy(deep=True)
            return contract
        except Exception as exc:
            if self._last_known_good is not None:
                return self._last_known_good.model_copy(deep=True)
            if isinstance(exc, ResearchProviderError):
                raise
            raise ResearchProviderError(
                f"crypto_dashboard_unavailable:{type(exc).__name__}"
            ) from exc
