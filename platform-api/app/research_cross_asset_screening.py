"""Read-only reference archive for the multi-timeframe cross-asset screener.

The supplied archive is historical research data, never a live market feed.
Browser imports remain private to the current user and do not mutate this archive.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

ARCHIVE = Path(__file__).with_name("research_templates") / "cross_asset_screening"
SOURCE_REVISION = "3399f41cd961b37023997cf180e8a2d2ccfec806"
WORKBOOK_SNAPSHOT = (
    Path(__file__).resolve().parents[2] / ".codex/research-data/cross-asset-workbooks.json"
)
logger = logging.getLogger(__name__)


def read_screening_with_workbooks() -> dict:
    archive = read_screening_archive()
    try:
        with WORKBOOK_SNAPSHOT.open(encoding="utf-8") as source:
            snapshot = json.load(source)
        if (
            not isinstance(snapshot, dict)
            or snapshot.get("version") != 1
            or not isinstance(snapshot.get("date"), str)
            or not isinstance(snapshot.get("pools"), dict)
            or set(snapshot["pools"]) != {"core", "tools"}
            or any(
                not isinstance(pool, dict)
                or not isinstance(pool.get("file"), str)
                or not isinstance(pool.get("sheet"), str)
                or not isinstance(pool.get("rows"), list)
                for pool in snapshot["pools"].values()
            )
        ):
            raise ValueError("invalid workbook snapshot")
    except FileNotFoundError:
        return archive
    except (OSError, ValueError):
        logger.exception("Unable to read cross-asset workbook snapshot")
        return {**archive, "workbookSnapshotUnavailable": True}
    return {**archive, "workbookSnapshot": snapshot}


@lru_cache(maxsize=1)
def read_screening_archive() -> dict:
    def read(name: str):
        return json.loads((ARCHIVE / name).read_text(encoding="utf-8"))

    assets = read("assets.json")
    snapshot = read("sampleSnapshot.json")
    cap_date = "2026-10-26"
    rows = {
        asset["symbol"]: {
            "symbol": asset["symbol"], "value": asset["cap"], "currency": "USD",
            "date": cap_date, "observedAt": cap_date, "source": "分享包标的研究快照",
            "field": "market_cap",
        }
        for asset in assets if asset["kind"] == "stock" and asset.get("cap")
    }
    return {
        "snapshot": snapshot, "assets": assets, "calendar": read("sampleCalendar.json"),
        "caps": {
            "date": cap_date, "dates": [cap_date], "rows": rows, "total": len(rows),
            "method": "分享包标的研究快照 · 非实时市值", "checkedAt": None,
        },
        "legacyResearch": read("legacyResearch.json"), "sourceRevision": SOURCE_REVISION,
        "sourceDate": "2026-10-27", "source": "澜序多周期趋势监测 · 分享包原生行情归档",
        "mode": "historical-archive", "isStale": True,
    }
