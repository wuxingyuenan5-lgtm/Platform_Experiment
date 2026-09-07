"""One-time, explicit historical backfill for A-share research snapshots.

The input directory is supplied by the operator and is read only once. The
result belongs to Platform SQLite and carries a historical-backfill source;
the running application never imports the reference project.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from app.database import connection
from app.research_a_share_repository import ensure_schema, write_dataset, write_stock_pool


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def integer(value: str | None) -> int | None:
    return int(float(value)) if value not in (None, "") else None


def number(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def crowding_history(
    sector_rows: list[dict[str, str]], market_rows: list[dict[str, str]]
) -> list[dict[str, object]]:
    """Build the four-sector crowding series used by the research report.

    This is a one-time import of historical observations.  The application
    serves the stored series and does not invoke the reference project.
    """
    targets = {
        "通信设备": "801102",
        "计算机设备": "801101",
        "元件": "801083",
        "半导体": "801081",
    }
    all_a_amount = {
        str(row.get("date") or "")[:10]: number(row.get("total_amount_100m"))
        for row in market_rows
    }
    by_date: dict[str, dict[str, object]] = {}
    by_code = {code: name for name, code in targets.items()}
    for raw in sector_rows:
        observed = str(raw.get("发布日期") or raw.get("日期") or "")[:10]
        code = str(raw.get("指数代码") or "").replace(".0", "")
        label = by_code.get(code)
        if not observed or label is None:
            continue
        amount = number(raw.get("成交额"))
        denominator = all_a_amount.get(observed)
        item = {
            "code": code,
            "amount100m": amount,
            "amountShareOfA": amount / denominator if amount is not None and denominator else None,
            "turnoverPct": number(raw.get("换手率")),
        }
        by_date.setdefault(observed, {"date": observed, "targets": {}})["targets"][label] = item
    history: list[dict[str, object]] = []
    for observed, item in sorted(by_date.items()):
        targets_data = item["targets"]
        values = list(targets_data.values())
        item["combined"] = {
            "amount100m": sum(value["amount100m"] for value in values if value["amount100m"] is not None)
            if len(values) == 4 and all(value["amount100m"] is not None for value in values)
            else None,
            "amountShareOfA": sum(value["amountShareOfA"] for value in values if value["amountShareOfA"] is not None)
            if len(values) == 4 and all(value["amountShareOfA"] is not None for value in values)
            else None,
        }
        history.append(item)
    return history


def innovation_history(
    rows: list[dict[str, str]], market_rows: list[dict[str, str]]
) -> list[dict[str, object]]:
    denominator = {str(row.get("date") or "")[:10]: number(row.get("total_amount_100m")) for row in market_rows}
    history: list[dict[str, object]] = []
    for raw in rows:
        observed = str(raw.get("日期") or "")[:10]
        # The source amount is yuan, while the market core denominator is 亿。
        amount_100m = (number(raw.get("成交额")) or 0) / 1e8
        total = denominator.get(observed)
        if observed:
            history.append({
                "date": observed,
                "amount100m": amount_100m,
                "amountShareOfA": amount_100m / total if total else None,
                "turnoverPct": number(raw.get("换手率")),
            })
    return history


def backfill(root: Path) -> tuple[int, int]:
    history_path = root / "market-monitor" / "data" / "history" / "market_core.csv"
    stock_path = root / "data" / "stock-pool" / "stocks.csv"
    market_rows = read_csv(history_path)
    hot_rows = read_csv(root / "market-monitor" / "data" / "history" / "hot_stocks.csv")
    sector_rows = read_csv(root / "market-monitor" / "data" / "history" / "sw_analysis_daily_second.csv")
    innovation_rows = read_csv(root / "market-monitor" / "data" / "history" / "innovation_drug_eastmoney.csv")
    stock_rows = read_csv(stock_path) if stock_path.exists() else []
    ensure_schema()
    run_id = f"historical-backfill-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute(
            "INSERT OR IGNORE INTO research_a_share_refresh_runs(run_id,target_trade_date,started_at,finished_at,status,message) VALUES (?,?,?,?,?,?)",
            (run_id, market_rows[-1].get("date") if market_rows else None, now, now, "ready", "explicit historical backfill"),
        )
        for row in market_rows:
            observed = str(row.get("date") or "")[:10]
            if not observed:
                continue
            payload = {
                "up": integer(row.get("advance")),
                "down": integer(row.get("decline")),
                "flat": integer(row.get("flat")),
                "limitUp": integer(row.get("limit_up")),
                "limitDown": integer(row.get("limit_down")),
                "totalAmountYuan": float(row["total_amount_100m"]) * 1e8 if row.get("total_amount_100m") else None,
                "marketBreadthPct": float(row["market_breadth"]) * 100 if row.get("market_breadth") else None,
            }
            db.execute(
                """INSERT INTO research_a_share_history
                (dataset,observed_at,entity_code,payload_json,source,fetched_at,refresh_run_id)
                VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset,observed_at,entity_code) DO UPDATE SET
                payload_json=excluded.payload_json,source=excluded.source,fetched_at=excluded.fetched_at,
                refresh_run_id=excluded.refresh_run_id""",
                ("market", observed, "market", json.dumps(payload, ensure_ascii=False), "vibe-research-historical-backfill", now, run_id),
            )
        for dataset, rows, date_key, code_key in (
            ("hot_stocks", hot_rows, "date", "stock_code"),
            ("shenwan_history", sector_rows, "发布日期", "指数代码"),
        ):
            for row in rows:
                observed = str(row.get(date_key) or "")[:10]
                code = str(row.get(code_key) or "")
                if not observed or not code:
                    continue
                db.execute(
                    """INSERT INTO research_a_share_history
                    (dataset,observed_at,entity_code,payload_json,source,fetched_at,refresh_run_id)
                    VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset,observed_at,entity_code) DO UPDATE SET
                    payload_json=excluded.payload_json,source=excluded.source,fetched_at=excluded.fetched_at,
                    refresh_run_id=excluded.refresh_run_id""",
                    (dataset, observed, code, json.dumps(row, ensure_ascii=False), "vibe-research-historical-backfill", now, run_id),
                )
    if stock_rows:
        payload = {
            "meta": {"generated_at": now, "source": "vibe-research-historical-backfill"},
            "summary": {"tracked_count": len(stock_rows), "breadth": {"up": 0, "down": 0, "flat": 0}},
            "stocks": stock_rows,
            "indices": [],
            "heatmap": stock_rows,
            "leaders": {"today": {"up": [], "down": []}, "5d": {"up": [], "down": []}, "20d": {"up": [], "down": []}},
            "definitions": {"focus_codes": [], "research_baskets": []},
        }
        write_stock_pool(run_id, payload)
    crowding = crowding_history(sector_rows, market_rows)
    if crowding:
        innovation = innovation_history(innovation_rows, market_rows)
        write_dataset(
            "crowding",
            {"history": crowding, "latest": crowding[-1], "innovationHistory": innovation},
            source="Platform 历史行业成交额母表导入",
            run_id=run_id,
        )
    return len(market_rows), len(stock_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vibe-root", type=Path, required=True)
    args = parser.parse_args()
    history_count, stock_count = backfill(args.vibe_root)
    print(f"backfilled market_history={history_count} stock_pool={stock_count}")


if __name__ == "__main__":
    main()
