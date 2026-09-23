"""海外研究数据（FedWatch / ETF Flow / Deribit IV）的 SQLite 读写。

复用 `research_a_share_history` 通用历史累积表（表名源自 A 股首建，但结构为
`dataset + observed_at + entity_code` 的通用时序容器），用 dataset 名区分数据域：
- macro_fedwatch：entity_code = FOMC 会议日期
- crypto_etf_flow：entity_code = ETF 代码（IBIT/FBTC/...）
- crypto_eth_etf_flow：entity_code = ETH ETF 代码（ETHA/ETHB/...）
- crypto_iv_term：entity_code = 期限（1M/3M/6M/1Y）
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.database import connection
from app.research_a_share_repository import write_history_points


def _read_shared_daily_prices(asset: str, dates: list[str]) -> dict[str, float]:
    """Read daily reference closes from the strategy-owned Bybit projection.

    ETF flow rows remain the source-of-record for flow values.  This helper only
    joins an optional price overlay from the shared strategy archive so the ETF
    chart can render price on its own right-hand axis without duplicating raw
    candles in the hedge-board database.
    """
    # The current strategy archive owns BTC/XAUT candles.  Never map the XAUT
    # series onto ETH ETF rows: an unavailable ETH price must stay unavailable.
    if not dates or asset != "btc":
        return {}
    result: dict[str, float] = {}
    with connection() as db:
        rows = db.execute(
            "SELECT payload_json FROM research_a_share_history "
            "WHERE dataset=? AND entity_code=? AND observed_at>=? "
            "AND observed_at<=? ORDER BY observed_at ASC",
            (
                "cumulative_volatility",
                "btc:americas:1h",
                dates[0],
                dates[-1] + "T23:59:59.999Z",
            ),
        ).fetchall()
    date_set = set(dates)
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
            date = str(payload.get("sessionDate") or "")
            close = float(payload["price"])
        except (KeyError, TypeError, ValueError, OverflowError, json.JSONDecodeError):
            continue
        if close > 0 and date in date_set:
            result[date] = close
    return result


def write_overseas_series(
    run_id: str,
    dataset: str,
    observed_at: str,
    series: dict[str, Any],
    *,
    source: str,
) -> None:
    """把一次抓取的完整序列写入历史表。

    series 形如 {entity_code: payload}，同一 observed_at 一次性落库。

    写入前先 DELETE 该 (dataset, observed_at) 的旧行，避免上一次抓取留下的、
    本次已不存在的实体残留；历史维度由不同 observed_at 累积，不受影响。

    **失败保留**：DELETE 与随后的 INSERT 在同一个连接事务里完成
    （``write_history_points`` 接受外部 ``db``），任一语句抛错都会整体回滚，
    因此本次写入失败时该 observed_at 的既有行保持原样，不会被清空。
    调用方（刷新 worker）捕获异常后即返回 error/stale，旧数据继续可用。
    """
    points = [(observed_at, code, payload) for code, payload in series.items()]
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "DELETE FROM research_a_share_history WHERE dataset=? AND observed_at=?",
            (dataset, observed_at),
        )
        write_history_points(run_id, dataset, points, source=source, db=db)


def write_overseas_points(
    run_id: str,
    dataset: str,
    points: list[tuple[str, str, dict[str, Any]]],
    *,
    source: str,
) -> None:
    """把跨多个 observed_at 的点批量写入历史表（供 ETF 多日资金流使用）。

    points 形如 [(observed_at, entity_code, payload), ...]。
    """
    write_history_points(run_id, dataset, points, source=source)


def write_iv_snapshot(
    run_id: str,
    observed_at: str,
    snapshot: dict[str, Any],
    *,
    source: str,
) -> None:
    """把 1M/3M/6M/1Y 当日快照写入历史表（每个时段一行）。

    dataset = crypto_iv_snapshot，entity_code = tenor 名称。
    同一 observed_at 写入前先清旧，避免上一次抓取留下的时段残留。

    **失败保留**：清理与写入在同一事务内，失败整体回滚，既有行不被清空。
    """
    dataset = "crypto_iv_snapshot"
    points = [
        (observed_at, p["tenor"], {
            "iv": p["iv"],
            "expiry": p["expiry"],
            "daysToExpiry": p["daysToExpiry"],
            "strike": p["strike"],
        })
        for p in snapshot.get("tenors", [])
    ]
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "DELETE FROM research_a_share_history WHERE dataset=? AND observed_at=?",
            (dataset, observed_at),
        )
        # meta 行（指数价 + DVOL）
        db.execute(
            "INSERT INTO research_a_share_history "
            "(dataset,observed_at,entity_code,payload_json,source,fetched_at,refresh_run_id)"
            " VALUES (?,?,?,?,?,?,?) ON CONFLICT(dataset,observed_at,entity_code)"
            " DO UPDATE SET payload_json=excluded.payload_json,source=excluded.source,"
            " fetched_at=excluded.fetched_at,refresh_run_id=excluded.refresh_run_id",
            (
                dataset, observed_at, "__meta__",
                json.dumps({"index": snapshot.get("index"), "dvol": snapshot.get("dvol"),
                            "observedAt": snapshot.get("observedAt")},
                           ensure_ascii=False),
                source, _now(), run_id,
            ),
        )
        if points:
            write_history_points(run_id, dataset, points, source=source, db=db)


def read_iv_snapshot_latest() -> dict[str, Any]:
    """读最新一次 BTC IV 快照（4 时段当前 + 指数价 + DVOL）。"""
    dataset = "crypto_iv_snapshot"
    series = read_latest_series(dataset)
    meta = series.pop("__meta__", {})
    tenors = []
    for tenor, payload in sorted(series.items(), key=lambda kv: _MAJOR_TENOR_INDEX.get(kv[0], 999)):
        tenors.append({
            "tenor": tenor,
            "iv": payload.get("iv"),
            "expiry": payload.get("expiry"),
            "daysToExpiry": payload.get("daysToExpiry"),
            "strike": payload.get("strike"),
        })
    return {
        "index": meta.get("index"),
        "dvol": meta.get("dvol"),
        "observedAt": meta.get("observedAt"),
        "tenors": tenors,
    }


def read_iv_snapshot_history(tenor: str, days: int = 365) -> list[dict[str, Any]]:
    """读单一时段的累积历史快照（升序）。"""
    dataset = "crypto_iv_snapshot"
    with connection() as db:
        rows = db.execute(
            "SELECT observed_at, payload_json FROM research_a_share_history "
            "WHERE dataset=? AND entity_code=? ORDER BY observed_at DESC LIMIT ?",
            (dataset, tenor, days),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for r in reversed(rows):
        item: dict[str, Any] = {"observedAt": r["observed_at"]}
        if r["payload_json"]:
            item["iv"] = json.loads(r["payload_json"]).get("iv")
        result.append(item)
    return result


# 新增模块依赖（避免循环 import）
def _now():
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()


_MAJOR_TENOR_INDEX = {"1M": 0, "3M": 1, "6M": 2, "1Y": 3}


def read_latest_series(dataset: str) -> dict[str, Any]:
    """读该 dataset 最新一次抓取的全部行，返回 {entity_code: payload}。"""
    with connection() as db:
        row = db.execute(
            "SELECT observed_at FROM research_a_share_history WHERE dataset=? "
            "ORDER BY observed_at DESC LIMIT 1",
            (dataset,),
        ).fetchone()
        if row is None:
            return {}
        rows = db.execute(
            "SELECT entity_code, payload_json FROM research_a_share_history "
            "WHERE dataset=? AND observed_at=?",
            (dataset, row["observed_at"]),
        ).fetchall()
    return {
        r["entity_code"]: json.loads(r["payload_json"]) if r["payload_json"] else {}
        for r in rows
    }


def read_latest_observed_at(dataset: str) -> str | None:
    """返回该 dataset 最新一次抓取的 observed_at（用于幂等判断）。"""
    with connection() as db:
        row = db.execute(
            "SELECT observed_at FROM research_a_share_history WHERE dataset=? "
            "ORDER BY observed_at DESC LIMIT 1",
            (dataset,),
        ).fetchone()
    return row["observed_at"] if row else None


def read_latest_fetched_at(dataset: str) -> str | None:
    """返回该 dataset 最新一次落库的 fetched_at（UTC ISO 串）。"""
    with connection() as db:
        row = db.execute(
            "SELECT fetched_at FROM research_a_share_history WHERE dataset=? "
            "ORDER BY fetched_at DESC LIMIT 1",
            (dataset,),
        ).fetchone()
    return row["fetched_at"] if row else None


def read_dataset_health(dataset: str) -> dict[str, Any]:
    """返回该 dataset 的失败语义元数据，供只读路由标注 stale/error。

    设计意图：刷新失败时**不清空**既有数据，路由继续返回最后一次有效值，
    同时通过本函数暴露「上一次抓取失败了」这一事实，避免把陈旧数据当成
    当前数据静默展示。返回字段：

    - ``observedAt``：最后一次成功落库的观测日；无数据时为 None。
    - ``fetchedAt``：最后一次成功落库的平台抓取时间；无数据时为 None。
    - ``hasData``：是否已有可用历史（决定路由返回 ready 还是 no_data）。
    - ``lastRunStatus``：最近一次刷新运行的状态（ready/error/partial/running），
      无运行记录时为 None。
    - ``lastError``：最近一次失败的错误码与消息；最近一次成功时为 None。
    - ``status``：综合状态，取值 ``no_data`` / ``ready`` / ``stale``。

    判定规则：无任何历史 -> ``no_data``；最近一次运行为失败且历史早于该次
    运行 -> ``stale``（数据仍返回，但明确标记陈旧）；否则 ``ready``。
    """
    with connection() as db:
        latest = db.execute(
            "SELECT observed_at, fetched_at FROM research_a_share_history "
            "WHERE dataset=? ORDER BY observed_at DESC, fetched_at DESC LIMIT 1",
            (dataset,),
        ).fetchone()
        run = db.execute(
            "SELECT status, error_code, message, started_at, finished_at "
            "FROM research_a_share_refresh_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()

    observed_at = latest["observed_at"] if latest else None
    fetched_at = latest["fetched_at"] if latest else None
    has_data = observed_at is not None

    last_run_status = run["status"] if run else None
    last_error: dict[str, Any] | None = None
    if run is not None and run["status"] == "error":
        last_error = {
            "code": run["error_code"],
            "message": run["message"],
            "startedAt": run["started_at"],
            "finishedAt": run["finished_at"],
        }

    if not has_data:
        status = "no_data"
    elif last_error is not None:
        status = "stale"
    else:
        status = "ready"

    return {
        "observedAt": observed_at,
        "fetchedAt": fetched_at,
        "hasData": has_data,
        "lastRunStatus": last_run_status,
        "lastError": last_error,
        "status": status,
    }


def read_series_history(
    dataset: str,
    entity_code: str,
    limit: int = 90,
) -> list[dict[str, Any]]:
    """读单个实体的历史序列，返回 [{observed_at, ...payload}]（升序）。"""
    with connection() as db:
        rows = db.execute(
            "SELECT observed_at, payload_json FROM research_a_share_history "
            "WHERE dataset=? AND entity_code=? ORDER BY observed_at DESC LIMIT ?",
            (dataset, entity_code, limit),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for r in reversed(rows):
        item: dict[str, Any] = {"observedAt": r["observed_at"]}
        if r["payload_json"]:
            item.update(json.loads(r["payload_json"]))
        result.append(item)
    return result


def read_etf_flow(days: int = 3650, asset: str = "btc") -> dict[str, Any]:
    """读 BTC/ETH ETF 资金流矩阵的历史窗口。

    返回 {"observedAt", "tickers", "days": [{date, flows, totalFlow, cumulativeFlow}]}（升序）。
    表头列序存于 __meta__ 实体（取最新一次），行内 flow 缺省视为 0。
    """
    asset_key = asset.lower().strip()
    if asset_key not in {"btc", "eth"}:
        raise ValueError(f"unsupported_etf_asset:{asset}")
    # BTC's original dataset name is part of the public read contract.
    dataset = "crypto_etf_flow" if asset_key == "btc" else "crypto_eth_etf_flow"
    with connection() as db:
        date_rows = db.execute(
            "SELECT DISTINCT observed_at FROM research_a_share_history "
            "WHERE dataset=? AND entity_code!='__meta__' "
            "ORDER BY observed_at DESC LIMIT ?",
            (dataset, days),
        ).fetchall()
        dates = [r["observed_at"] for r in date_rows]
        if not dates:
            return {"observedAt": None, "tickers": [], "days": []}

        meta = db.execute(
            "SELECT payload_json FROM research_a_share_history "
            "WHERE dataset=? AND entity_code='__meta__' ORDER BY observed_at DESC LIMIT 1",
            (dataset,),
        ).fetchone()
        tickers: list[str] = []
        if meta and meta["payload_json"]:
            meta_payload = json.loads(meta["payload_json"])
            tickers = meta_payload.get("tickers", [])
        else:
            meta_payload = {}

        placeholders = ",".join("?" for _ in dates)
        rows = db.execute(
            f"SELECT observed_at, entity_code, payload_json FROM research_a_share_history "
            f"WHERE dataset=? AND observed_at IN ({placeholders})",
            (dataset, *dates),
        ).fetchall()

    by_date: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r["entity_code"] == "__meta__":
            continue
        cell = by_date.setdefault(r["observed_at"], {})
        if r["payload_json"]:
            cell[r["entity_code"]] = json.loads(r["payload_json"] or "{}")
    ordered_dates = sorted(dates)
    prices = _read_shared_daily_prices(asset_key, ordered_dates)
    days_out: list[dict[str, Any]] = []
    cumulative = Decimal("0")
    for d in ordered_dates:
        flows = by_date.get(d, {})
        coin_flows = {
            ticker: (
                payload.get("coinFlow")
                if payload.get("coinFlow") is not None
                else payload.get("flow")
            )
            for ticker, payload in flows.items()
            if isinstance(payload, dict)
        }
        values = [
            float(value)
            for ticker, value in coin_flows.items()
            if ticker != "Total" and value is not None
        ]
        total_payload = flows.get("Total") or {}
        total_flow = (
            total_payload.get("coinFlow")
            if total_payload.get("coinFlow") is not None
            else total_payload.get("flow")
        )
        if total_flow is None and values:
            total_flow = sum(values)
        total_flow = float(total_flow) if total_flow is not None else None
        try:
            if total_flow is not None:
                cumulative += Decimal(str(total_flow))
        except (InvalidOperation, ValueError):
            pass
        price = next(
            (payload.get("price") for payload in flows.values() if isinstance(payload, dict) and payload.get("price")),
            prices.get(d),
        )
        days_out.append(
            {
                "date": d,
                "flows": coin_flows,
                "totalFlow": total_flow,
                "cumulativeFlow": float(cumulative) if total_flow is not None else None,
                "price": price,
            }
        )
    has_coin_values = any(
        isinstance(payload, dict) and payload.get("coinFlow") is not None
        for day in by_date.values()
        for payload in day.values()
    )
    return {
        "observedAt": max(dates),
        "tickers": tickers,
        "flowUnit": meta_payload.get("coinUnit") or (asset_key.upper() if has_coin_values else "US$m"),
        "priceSource": meta_payload.get("priceSource"),
        "days": days_out,
    }
