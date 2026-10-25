"""Read-only projection of browser-captured treasury data and its chart image."""

from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError

SOURCE_URL = "https://sosovalue.com/zh/assets/bitcoin-treasuries/weekly-net-inflow"


def get_history():
    """Chart data is independent of the legacy image publication."""
    try:
        history = read_local_json("public/v1/crypto/treasury-weekly-history.json")
        rows = history.get("rows")
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or not all(key in row for key in (
                "weekDate", "observedAt", "netFlowUsd", "netFlowDisplay",
                "netBtc", "netBtcDisplay", "btcPriceUsd", "btcPriceDisplay", "companies",
            ))
            or not isinstance(row["companies"], list)
            for row in rows
        ):
            raise ResearchProviderError("treasury_history_schema_invalid")
        rows = sorted(rows, key=lambda row: row["weekDate"])
        return {
            "status": "ready" if rows else "no_data",
            "sourceUrl": SOURCE_URL,
            "observedAt": max((row["observedAt"] for row in rows), default=None),
            "weeks": rows,
        }
    except ResearchProviderError:
        return {"status": "unavailable", "sourceUrl": SOURCE_URL, "observedAt": None, "weeks": []}


def get_snapshot():
    try:
        document = read_local_json("public/v1/crypto/treasury-weekly-snapshot.json")
    except ResearchProviderError:
        return {
            "status": "no_data",
            "observedAt": None,
            "sourceUrl": SOURCE_URL,
            "dataPath": None,
            "dataStatus": "no_data",
            "weeks": [],
        }
    result = {key: document.get(key) for key in ("status", "observedAt", "sourceUrl", "dataPath")}
    try:
        history = read_local_json("public/v1/crypto/treasury-weekly-history.json")
        rows = history.get("rows")
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or not all(
                key in row
                for key in (
                    "weekDate",
                    "observedAt",
                    "netFlowDisplay",
                    "netBtcDisplay",
                    "btcPriceDisplay",
                    "companies",
                )
            )
            or not isinstance(row["companies"], list)
            for row in rows
        ):
            raise ResearchProviderError("treasury_history_schema_invalid")
        result.update(weeks=rows, dataStatus="ready")
    except ResearchProviderError:
        result.update(weeks=[], dataStatus="unavailable" if document.get("dataPath") else "no_data")
    return result
