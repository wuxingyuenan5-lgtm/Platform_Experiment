"""Index locally archived SSE/SZSE published shares for the theme ETF catalogue."""

import json
from datetime import date

from app.research_equity_metrics import number
from app.research_etf_native import ROOT, SSE, SZSE
from app.research_local_data import hedge_board_data_root, write_local_json
from app.research_theme_etfs import reference_funds


def main():
    root = hedge_board_data_root()
    archive = root / ROOT / "backfill"
    funds = {code: {} for code in reference_funds()}
    sources = []
    for exchange, url in (("sse", SSE), ("szse", SZSE)):
        for path in sorted(archive.glob(f"*/{exchange}/*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("sourceUrl", "").split("?")[0] != url:
                continue
            days = (
                {path.stem: doc["shares"]}
                if exchange == "sse" and "shares" in doc
                else doc.get("days", {})
            )
            for day, shares in days.items():
                date.fromisoformat(day)
                for code in funds.keys() & shares.keys():
                    value = number(shares[code])
                    if value is None or value < 0:
                        continue
                    prior = funds[code].get(day, str(value))
                    funds[code][day] = str(value) if number(prior) == value else None
            sources.append(path.relative_to(root).as_posix())
    if not sources or not any(funds.values()):
        raise ValueError("No matching local exchange share archives")
    write_local_json(
        ROOT + "theme-shares.json", {"funds": funds, "archives": sources, "sources": [SSE, SZSE]}
    )
    print(f"{len(sources)} local archives; {sum(len(v) for v in funds.values())} fund-days")


if __name__ == "__main__":
    main()
