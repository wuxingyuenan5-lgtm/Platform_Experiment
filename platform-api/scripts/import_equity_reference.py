"""Import the supplied HS300 raw export without importing hindsight percentiles.

Usage: python scripts/import_equity_reference.py PATH_TO_RAW_JSON
The source file is preserved. Re-importing identical data is idempotent.
"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.research_equity_metrics import number
from app.research_equity_sources import archive, publish_artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    items = json.loads(raw, parse_float=str)
    rows = []
    seen = set()
    for item in items:
        day = date.fromisoformat(item["d"]).isoformat()
        if day in seen:
            raise ValueError(f"Duplicate observation: {day}")
        seen.add(day)
        rows.append(
            {
                "date": day,
                **{k: number(item.get(k)) for k in ("close", "pe", "pb", "ps", "pcf", "erp")},
            }
        )
    if not rows:
        raise ValueError("Empty export")
    stamp = datetime.now(UTC).isoformat()
    digest = archive("hs300-reference", raw, stamp)
    publish_artifact(
        "reference-hs300",
        {
            "source": "附件沪深300历史 · Choice导出",
            "sourceFile": str(args.source.resolve()),
            "rawSha256": digest,
            "importedAt": stamp,
            "rows": sorted(rows, key=lambda p: p["date"]),
            "method": ("附件原值；历史分位重算，不使用原表全样本分位；财务历史版本未作时点验证"),
        },
    )
    print(
        f"Imported {len(rows)} observations; original preserved; "
        f"SHA256 {hashlib.sha256(raw).hexdigest()}"
    )


if __name__ == "__main__":
    main()
