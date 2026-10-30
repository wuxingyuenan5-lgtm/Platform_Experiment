"""Persisted, read-only data checks. Never refresh sources or alter business facts."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import math
import sqlite3
import time
import zlib
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends

from app import monitor_health, runtime_transport
from app.auth import require_permission
from app.config import get_settings
from app.data_audit_calendar import calendar_snapshot, refresh_calendar
from app.database_connection import connection, database_path, read_only_connection
from app.production_monitoring import SCHEMA_SQL as ALERT_SCHEMA


def encode_report(report):
    data = json.dumps(report, ensure_ascii=False).encode("utf-8")
    return "zlib:" + base64.b64encode(zlib.compress(data, level=6)).decode("ascii")


def decode_report(value):
    if value.startswith("zlib:"):
        value = zlib.decompress(base64.b64decode(value[5:])).decode("utf-8")
    return json.loads(value)


INTERVAL = 300
LOG = logging.getLogger(__name__)
# Explicit inventory: new tables are visible as unclassified, never silently covered.
EVENT_TABLES = set(
    """execution_batches legal_entities funds portfolios books
strategy_definitions strategy_versions strategy_instances venues accounts credential_references
strategy_account_bindings instruments instrument_mappings contract_specifications trade_commands
external_order_references pnl_attribution_items strategy_nav_snapshots strategy_runs risk_decisions
audit_events orders execution_batch_legs fills positions economic_events market_spread_snapshots
pnl_results schema_migrations cross_spread_exit_plans users user_sessions password_reset_tickets
member_fund_holdings fund_nav_snapshots user_research_watchlists user_research_market_layouts
trading_kill_switches
kill_switch_commands execution_risk_policies execution_risk_policy_commands execution_batch_risk
execution_risk_actions venue_reconciliation_runs reconciliation_differences live_trading_sessions
live_trading_session_claims financial_facts formal_positions formal_pnl_results
formal_strategy_nav_snapshots execution_resource_claims execution_balance_reservations
internal_capital_transfers funding_spot_release_commands funding_perpetual_attempts
funding_exit_plans
order_execution_intents account_sync_status account_risk_snapshots research_a_share_refresh_runs
research_a_share_dataset_snapshots research_a_share_history research_a_share_pool_config
research_a_share_market_archive research_a_share_price_history research_a_share_archive_conflicts
account_venue_snapshots venue_account_events balance_snapshots operational_alerts
operational_alert_scan_runs controlled_operation_runs production_backup_records
production_restore_drills account_capital_movements account_capital_coverage account_capital_sync
account_valuation_rates runtime_order_terminals cross_spread_open_triggers account_read_jobs
research_strategy_parts research_strategy_capture research_strategy_experiments
research_strategy_drafts strategy_management_projection research_strategy_projection
research_strategy_projection_cursor research_strategy_candle_cursor research_strategy_price_capture
funding_basis_projection_cursor data_audit_runs data_audit_calendar
 data_audit_history_changes data_audit_history_cursor data_audit_history_findings""".split()
)
SNAPSHOTS = {
    "stock_pool",
    "market_detail",
    "breadth",
    "shenwan",
    "emotion",
    "stocks",
    "crowding",
    "memberships",
}
# Hours are fetch deadlines, not source publication dates (ETF may close on holidays).
HISTORY = {
    "market": 96,
    "hot_stock": 96,
    "index": 96,
    "stock": 96,
    "market_price": 96,
    "crypto_etf_flow": 36,
    "crypto_eth_etf_flow": 36,
    "macro_fedwatch": 2,
    "crypto_iv_snapshot": 36,
    "crypto_iv_term": 36,
    "cumulative_volatility": 2,
}
LEGACY = {"hot_stocks", "shenwan_history"}
ARCHIVAL_HISTORY = {"stock_choice_qfq", "stock_tencent_qfq_native", "stock_tencent_day_native"}


def iso_now():
    return datetime.now(UTC).isoformat()


def age_seconds(value, now):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return (now - parsed).total_seconds()
    except (TypeError, ValueError):
        return None


class AuditCheck(TypedDict):
    key: str
    name: str
    group: str
    status: str
    message: str
    evidence: dict[str, Any]


def check(key, name, group, status="healthy", message="检查通过", **evidence) -> AuditCheck:
    return {
        "key": key,
        "name": name,
        "group": group,
        "status": status,
        "message": message,
        "evidence": evidence,
    }


def freshness(key, name, group, timestamp, hours, now, **evidence):
    age = age_seconds(timestamp, now)
    status = "error" if age is None or age < -300 or age > hours * 3600 else "healthy"
    message = (
        "缺少有效时间戳"
        if age is None
        else "时间戳超前"
        if age < -300
        else "更新已超时"
        if status == "error"
        else "更新在时限内"
    )
    return check(
        key,
        name,
        group,
        status,
        message,
        lastSuccessAt=timestamp,
        deadlineHours=hours,
        ageSeconds=age,
        **evidence,
    )


def valid_number(value, *, positive=False, maximum=None):
    try:
        number = float(value)
        return (
            math.isfinite(number)
            and (number > 0 if positive else number >= 0)
            and (maximum is None or number <= maximum)
        )
    except (ValueError, TypeError):
        return False


def history_row_valid(dataset, entity, payload):
    if entity.startswith("__"):
        return True  # Explicit empty-day / metadata records are not measurements.
    if dataset == "market":
        return valid_number(payload.get("totalAmountYuan"), positive=True) and all(
            valid_number(payload.get(field)) for field in ["up", "down", "flat"]
        )
    if dataset == "macro_fedwatch":
        values = list((payload.get("probabilities") or {}).values())
        return (
            bool(values)
            and all(valid_number(v, maximum=100) for v in values)
            and abs(sum(float(v) for v in values) - 100) <= 0.2
        )
    if dataset == "hot_stock":
        return (
            valid_number(payload.get("turnoverYuan"), positive=True)
            and float(payload["turnoverYuan"]) > 1e10
        )
    if dataset in {"stock", "index"}:
        return valid_number(payload.get("close"), positive=True)
    return True


def crowding_checks(payload, market_dates):
    result = []
    for field, title in [("history", "四行业拥挤度"), ("innovationHistory", "创新药")]:
        rows = payload.get(field) or []
        bad, dates = [], set()
        for row in rows:
            day = row.get("date")
            dates.add(day)
            values = list((row.get("targets") or {}).values()) if field == "history" else [row]
            codes = {v.get("code") for v in values}
            invalid = field == "history" and codes != {"801102", "801101", "801083", "801081"}
            invalid |= any(
                not valid_number(v.get("amount100m"), positive=True)
                or not valid_number(v.get("amountShareOfA"), maximum=1)
                or not valid_number(v.get("turnoverPct"))
                for v in values
            )
            if invalid:
                bad.append(day)
        missing = sorted(market_dates - dates)
        result.append(
            check(
                "crowding." + field,
                title,
                "A股研究",
                "error" if bad or missing or not rows else "healthy",
                f"无效指标 {len(bad)} 日；跨表缺日 {len(missing)} 日",
                invalidDates=bad[:30],
                missingDates=missing[:30],
                checkedDays=len(rows),
                rule="成交额>0，占比0–1，换手率非负且不得缺失；四行业代码齐全",
            )
        )
    return result


def a_share_archive_check(db: sqlite3.Connection, *, since=None) -> AuditCheck:
    """Validate the owned archive without applying snapshot freshness rules."""
    recent = " WHERE trade_date>=?" if since else ""
    args = (since,) if since else ()
    market_rows = db.execute(
        """SELECT universe_key,COUNT(*) AS rows,MIN(trade_date) AS earliest,
        MAX(trade_date) AS latest,
        SUM(CASE WHEN quality_status NOT IN ('ready','stale') THEN 1 ELSE 0 END) AS invalid
        FROM research_a_share_market_archive"""
        + recent
        + " GROUP BY universe_key",
        args,
    ).fetchall()
    price_rows = db.execute(
        """SELECT instrument_code,COUNT(*) AS rows,MIN(trade_date) AS earliest,
        MAX(trade_date) AS latest,
        SUM(CASE WHEN close IS NULL OR CAST(close AS REAL) <= 0 THEN 1 ELSE 0 END) AS missing,
        SUM(CASE WHEN quality_status NOT IN ('ready','stale') THEN 1 ELSE 0 END) AS invalid
        FROM research_a_share_price_history"""
        + recent
        + " GROUP BY instrument_code",
        args,
    ).fetchall()
    conflict_count = db.execute(
        "SELECT COUNT(*) AS n FROM research_a_share_archive_conflicts "
        "WHERE reason != 'premature_close_corrected'" + (" AND observed_at>=?" if since else ""),
        args,
    ).fetchone()["n"]
    corrected_count = db.execute(
        "SELECT COUNT(*) AS n FROM research_a_share_archive_conflicts "
        "WHERE reason = 'premature_close_corrected'" + (" AND observed_at>=?" if since else ""),
        args,
    ).fetchone()["n"]
    markets = {row["universe_key"]: dict(row) for row in market_rows}
    prices = {row["instrument_code"]: dict(row) for row in price_rows}
    required_markets = {"all_a", "sh_sz_a"}
    required_prices = {"000300.SH", "801102.SWI", "BK0448", "BK1106"}
    missing_markets = sorted(required_markets - set(markets))
    missing_prices = sorted(required_prices - set(prices))
    invalid_rows = sum(int(row["invalid"] or 0) for row in market_rows) + sum(
        int(row["invalid"] or 0) for row in price_rows
    )
    missing_closes = sum(int(row["missing"] or 0) for row in price_rows)
    status = (
        "error"
        if invalid_rows or missing_closes
        else "warning"
        if missing_markets or missing_prices or conflict_count
        else "healthy"
    )
    message = (
        "归档包含无效质量状态或价格"
        if status == "error"
        else "归档品种不完整或存在待核对冲突"
        if status == "warning"
        else "A股来源归档完整且无待核对冲突"
    )
    return check(
        "a_share.archive",
        "A股来源归档",
        "A股研究",
        status,
        message,
        markets=markets,
        prices=prices,
        missingMarkets=missing_markets,
        missingPrices=missing_prices,
        invalidRows=invalid_rows,
        missingCloses=missing_closes,
        conflicts=conflict_count,
        correctedConflicts=corrected_count,
        scope="recent_window" if since else "all_stored_archive",
        windowStart=since,
        rule="历史归档按独立品种保留来源、NULL与冲突，不套用短周期快照时效",
    )


def history_inventory(db):
    """Seek dataset boundaries; never count the full intraday archive online."""
    result = {}
    previous = None
    while True:
        row = db.execute(
            "SELECT dataset FROM research_a_share_history "
            + ("WHERE dataset>? " if previous is not None else "")
            + "ORDER BY dataset LIMIT 1",
            (previous,) if previous is not None else (),
        ).fetchone()
        if row is None:
            return result
        name = row[0]
        first = db.execute(
            "SELECT observed_at FROM research_a_share_history WHERE dataset=? "
            "ORDER BY observed_at LIMIT 1",
            (name,),
        ).fetchone()
        last = db.execute(
            "SELECT observed_at,fetched_at FROM research_a_share_history WHERE dataset=? "
            "ORDER BY observed_at DESC,fetched_at DESC LIMIT 1",
            (name,),
        ).fetchone()
        result[name] = dict(dataset=name, start=first[0], end=last[0], fetched=last[1])
        previous = name


def inspect_database(now):
    checks = []
    with read_only_connection() as db:
        # Bound database work; a timeout is unverified, not success. No long writer lock.
        deadline = time.monotonic() + 2
        db.execute("PRAGMA busy_timeout=250")
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
        tables = [
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        unknown = sorted(set(tables) - EVENT_TABLES)
        checks.append(
            check(
                "database.inventory",
                "全库表登记",
                "平台数据库",
                "warning" if unknown else "healthy",
                "有未登记的数据表" if unknown else "所有现有数据表已登记",
                tableCount=len(tables),
                tables=tables,
                unclassified=unknown,
                scope="全表结构/外键；事件驱动表不设置每日新增要求",
            )
        )
        window_start = (now - timedelta(days=90)).date().isoformat()
        checks.append(a_share_archive_check(db, since=window_start))
        snapshots = {
            r["dataset"]: dict(r)
            for r in db.execute("SELECT * FROM research_a_share_dataset_snapshots")
        }
        local = now.astimezone(ZoneInfo("Asia/Shanghai"))
        latest_run = db.execute(
            "SELECT started_at,status FROM research_a_share_refresh_runs "
            "WHERE run_id LIKE 'a-share-%' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        calendar = calendar_snapshot(db, local.date().isoformat())
        is_trading_day = (
            local.date().isoformat() in calendar["days"] if calendar is not None else None
        )
        due = is_trading_day is True and local.hour >= 16
        attempted_today = bool(
            latest_run
            and datetime.fromisoformat(latest_run["started_at"])
            .astimezone(ZoneInfo("Asia/Shanghai"))
            .date()
            == local.date()
        )
        checks.append(
            check(
                "worker.a_share",
                "A股日度生产执行",
                "后台任务",
                "error"
                if due and (not attempted_today or latest_run["status"] == "error")
                else "warning"
                if (due and latest_run["status"] != "ready")
                or (local.hour >= 16 and is_trading_day is None)
                else "healthy",
                "交易日今日后台未留下执行记录"
                if due and not attempted_today
                else "今日后台执行失败"
                if due and latest_run["status"] == "error"
                else "今日后台尚未取得完整收盘数据"
                if due and latest_run["status"] != "ready"
                else "已过检查时点，但交易日历不可用，无法判断是否应执行"
                if local.hour >= 16 and is_trading_day is None
                else "今日为非交易日，无需日度行情生产"
                if is_trading_day is False
                else "未到时限或已有执行记录",
                lastAttempt=latest_run["started_at"] if latest_run else None,
                lastStatus=latest_run["status"] if latest_run else None,
                tradingDay=is_trading_day,
                rule="仅按平台缓存的独立交易日历判断；交易日16点后应有执行记录",
            )
        )
        for name in sorted(SNAPSHOTS | set(snapshots)):
            # Market snapshots have their own freshness and partial-data rules below.
            if name.startswith("market_detail_"):
                continue
            row = snapshots.get(name)
            if not row:
                checks.append(check("snapshot." + name, name, "A股研究", "error", "应有快照未落库"))
                continue
            item = freshness(
                "snapshot." + name,
                name,
                "A股研究",
                row["fetched_at"],
                96,
                now,
                sourceDate=row["observed_at"],
                sourceStatus=row["status"],
            )
            if row["status"] != "ready":
                evidence = item["evidence"]
                evidence.pop("lastSuccessAt", None)
                evidence["lastAttemptAt"] = row["fetched_at"]
                item.update(
                    status="error",
                    message="最近生产尝试的结果不完整：" + row["status"],
                    evidence=evidence,
                )
            checks.append(item)
        for market_id in ("us", "global", "gold", "crypto"):
            name = "market_detail_" + market_id
            row = snapshots.get(name)
            if not row:
                checks.append(
                    check("snapshot." + name, name, "市场明细", "error", "市场快照未落库")
                )
                continue
            try:
                payload = json.loads(row["payload_json"] or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("invalid snapshot")
            except ValueError:
                checks.append(check("snapshot." + name, name, "市场明细", "error", "快照格式无效"))
                continue
            item = freshness(
                "snapshot." + name,
                name,
                "市场明细",
                payload.get("retrievedAt"),
                1,
                now,
                sourceDate=payload.get("asOf"),
                sourceStatus=payload.get("status"),
            )
            if payload.get("status") != "ready":
                item.update(
                    status="warning"
                    if payload.get("status") == "partial" and item["status"] == "healthy"
                    else "error",
                    message="市场数据不完整：" + str(payload.get("status")),
                )
            checks.append(item)
        groups = history_inventory(db)
        for name in sorted(set(HISTORY) | set(groups)):
            row = groups.get(name)
            if name in LEGACY:
                checks.append(
                    check("history." + name, name, "历史归档", "info", "旧版归档，不再要求日更")
                )
            elif name in ARCHIVAL_HISTORY:
                checks.append(
                    check(
                        "history." + name,
                        name,
                        "历史归档",
                        "info",
                        "按原始来源与复权版本归档，不设日更要求",
                        **(row or {}),
                    )
                )
            elif name not in HISTORY:
                checks.append(
                    check(
                        "history." + name,
                        name,
                        "研究数据",
                        "warning",
                        "新数据集尚未定义更新时限",
                        **(row or {}),
                    )
                )
            elif not row:
                checks.append(check("history." + name, name, "研究数据", "error", "应有历史未落库"))
            else:
                checks.append(
                    freshness(
                        "history." + name,
                        name,
                        "研究数据",
                        row["fetched"],
                        HISTORY[name],
                        now,
                        historyStart=row["start"],
                        sourceDate=row["end"],
                        rows=row.get("rows"),
                    )
                )
        # A cross-table check is useful but cannot replace an independent exchange calendar.
        for dataset in ["market", "macro_fedwatch", "hot_stock", "stock", "index"]:
            samples = db.execute(
                "SELECT observed_at,entity_code,payload_json "
                "FROM research_a_share_history WHERE dataset=? "
                "ORDER BY observed_at DESC LIMIT 1000",
                (dataset,),
            ).fetchall()
            invalid = []
            for sample in samples:
                try:
                    valid = history_row_valid(
                        dataset, sample["entity_code"], json.loads(sample["payload_json"])
                    )
                except (ValueError, TypeError, AttributeError):
                    valid = False
                if not valid:
                    invalid.append({"date": sample["observed_at"], "entity": sample["entity_code"]})
            checks.append(
                check(
                    "fields." + dataset,
                    dataset + " 必需指标与范围",
                    "数据有效性",
                    "error" if invalid else "healthy" if samples else "warning",
                    f"检查最近 {len(samples)} 条；无效 {len(invalid)} 条",
                    samples=invalid[:20],
                    limit=1000,
                )
            )
        dates = {
            r[0][:10]
            for r in db.execute(
                "SELECT DISTINCT observed_at FROM research_a_share_history "
                "WHERE dataset='market' AND observed_at>=?",
                (window_start,),
            )
        }
        # Global MAX would hide gold stopping while BTC continues to update.
        for asset in ["btc", "gold"]:
            for interval in ["15m", "1h", "4h"]:
                latest = db.execute(
                    "SELECT observed_at FROM research_a_share_history "
                    "WHERE dataset='cumulative_volatility' "
                    "AND json_extract(payload_json,'$.asset')=? "
                    "AND json_extract(payload_json,'$.interval')=? "
                    "ORDER BY observed_at DESC LIMIT 1",
                    (asset, interval),
                ).fetchone()
                latest = latest[0] if latest is not None else None
                checks.append(
                    freshness(
                        "volatility." + asset + "." + interval,
                        asset.upper() + " 累计波动 · " + interval,
                        "研究数据",
                        latest,
                        {"15m": 2, "1h": 3, "4h": 8}[interval],
                        now,
                    )
                )
        if "crowding" in snapshots:
            checks.extend(
                crowding_checks(json.loads(snapshots["crowding"]["payload_json"] or "{}"), dates)
            )
        checks.append(
            check(
                "calendar.coverage",
                "独立交易日历",
                "完整性边界",
                "healthy" if calendar else "warning",
                "平台独立缓存的新浪交易日历"
                if calendar
                else "日历缺失或覆盖过期，整日完整性未验证",
                source=calendar["source"] if calendar else None,
            )
        )
        if calendar:
            checks.append(
                freshness(
                    "calendar.refresh",
                    "交易日历刷新",
                    "后台任务",
                    calendar["fetchedAt"],
                    8 * 24,
                    now,
                )
            )
            cutoff = local.date() if local.hour >= 16 else local.date() - timedelta(days=1)
            for dataset in ["market", "hot_stock"]:
                actual = {
                    r[0][:10]
                    for r in db.execute(
                        "SELECT DISTINCT observed_at FROM research_a_share_history "
                        "WHERE dataset=? AND observed_at>=?",
                        (dataset, window_start),
                    )
                }
                expected = {
                    d
                    for d in calendar["days"]
                    if max(
                        window_start,
                        (groups.get(dataset) or {}).get("start", cutoff.isoformat())[:10],
                    )
                    <= d
                    <= cutoff.isoformat()
                }
                missing_days = sorted(expected - actual)
                checks.append(
                    check(
                        "calendar.gaps." + dataset,
                        dataset + " 交易日连续性",
                        "A股研究",
                        "error" if missing_days else "healthy",
                        f"缺失 {len(missing_days)} 个交易日",
                        missingDates=missing_days[:50],
                        checkedDays=len(expected),
                        scope="recent_90_days",
                        windowStart=window_start,
                        source=calendar["source"],
                    )
                )
        for row in db.execute(
            "SELECT account_id,status,last_success_at,error_code FROM account_sync_status"
        ):
            item = freshness(
                "account." + row["account_id"],
                "账户同步 · " + row["account_id"],
                "账户与会计",
                row["last_success_at"],
                0.25,
                now,
            )
            if row["error_code"]:
                item.update(
                    status="error",
                    message="账户同步失败",
                    evidence={**item["evidence"], "errorCode": row["error_code"]},
                )
            checks.append(item)
        for row in db.execute(
            "SELECT strategy_instance_id,account_id,kind,updated_at,error_code,requested_at "
            "FROM strategy_management_projection"
        ):
            if row["kind"] == "detail" and (age_seconds(row["requested_at"], now) or 0) > 900:
                checks.append(
                    check(
                        "projection." + ".".join(row[:3]),
                        "按需策略详情",
                        "策略与会计",
                        "info",
                        "无近期查看请求，不要求持续刷新",
                    )
                )
                continue
            item = freshness(
                "projection." + ".".join(row[:3]),
                "策略投影 · " + row["kind"],
                "策略与会计",
                row["updated_at"],
                0.25,
                now,
            )
            if row["error_code"]:
                item.update(status="error", message="策略投影失败")
            checks.append(item)
    from app.strategy_research_database import read_only_connection as research_read

    with research_read() as research_db:
        parts = [
            dict(r) for r in research_db.execute("SELECT path,last_at FROM research_strategy_parts")
        ]
    # File checks outside SQLite read transaction. Do not hash terabytes every five minutes.
    from app.strategy_research_repository import root_path

    root = root_path()
    missing = [p["path"] for p in parts if not (root / p["path"]).is_file()]
    checks.append(
        check(
            "archive.manifest",
            "策略 Parquet 归档清单",
            "策略行情",
            "error" if missing else "healthy" if parts else "warning",
            f"{len(parts)} 个登记分片，{len(missing)} 个文件缺失",
            missing=missing[:20],
            scope="文件存在性；内容校验和不在轻量巡检内",
        )
    )
    return checks


def inspect_artifacts(now):
    from app.research_local_data import read_local_json

    results = []
    for name in ["macro", "crypto", "commodity"]:
        key = "artifact." + name
        try:
            document = read_local_json(f"public/v1/{name}/dashboard.json")
            series = [s for group in document.get("groups", {}).values() for s in group]
            results.append(
                check(
                    key,
                    name + " 本地研究库",
                    "研究文件库",
                    "healthy" if series else "warning",
                    f"登记 {len(series)} 条序列",
                )
            )
            active_contracts = {
                r.get("seriesId") for r in document.get("groups", {}).get("shfeGoldCurve", [])
            }
            historical_contracts = {
                r.get("seriesId")
                for r in document.get("groups", {}).get("shfeGoldCurveHistory", [])
            }
            archived_contracts = (
                historical_contracts - active_contracts if active_contracts else set()
            )
            for series_row in series:
                series_id = series_row.get("seriesId", "unknown")
                status = series_row.get("status")
                if status in {"permission_required", "reference", "external_link"}:
                    results.append(
                        check(
                            key + "." + series_id,
                            series_row.get("label", series_id),
                            "研究文件库",
                            "info",
                            "外部参考入口，不是平台持久数据",
                        )
                    )
                    continue
                if series_id in archived_contracts:
                    results.append(
                        check(
                            key + "." + series_id,
                            series_row.get("label", series_id),
                            "研究文件库",
                            "info",
                            "不在来源当前合约清单；保留历史，不要求日更",
                            sourceDate=series_row.get("observationDate"),
                            reason="archived_contract",
                        )
                    )
                    continue
                if "source_discontinued" in series_row.get("qualityFlags", []):
                    results.append(
                        check(
                            key + "." + series_id,
                            series_row.get("label", series_id),
                            "研究文件库",
                            "warning",
                            "来源已停止维护；保留历史数据，不能视为当前持仓",
                            sourceDate=series_row.get("observationDate"),
                            reason="source_discontinued",
                        )
                    )
                    continue
                item = freshness(
                    key + "." + series_id,
                    series_row.get("label", series_id),
                    "研究文件库",
                    series_row.get("retrievedAt"),
                    {
                        "daily_business_day": 72,
                        "weekly": 240,
                        "monthly": 1080,
                        "quarterly": 2880,
                    }.get(str(series_row.get("frequency", "")).lower(), 48),
                    now,
                    frequency=series_row.get("frequency"),
                    sourceDate=series_row.get("observationDate"),
                )
                if str(series_row.get("frequency", "")).lower() == "daily_business_day":
                    previous_weekday = now.date() - timedelta(days=1)
                    while previous_weekday.weekday() >= 5:
                        previous_weekday -= timedelta(days=1)
                    observed = str(series_row.get("observationDate") or "")[:10]
                    if (
                        observed
                        and observed < previous_weekday.isoformat()
                        and item["status"] == "healthy"
                    ):
                        item.update(status="warning", message="来源观测日期落后于最近工作日")
                if (series_row.get("isStale") or status not in {"ready", "available"}) and item[
                    "status"
                ] != "error":
                    item.update(status="warning", message="来源未就绪或声明数据陈旧")
                if "upstream_empty_table" in series_row.get("qualityFlags", []):
                    item.update(
                        status="error",
                        message="来源当日报表为空；保留上次有效观测",
                        reason="upstream_empty_table",
                    )
                results.append(item)
        except Exception as exc:
            results.append(
                check(
                    key,
                    name + " 本地研究库",
                    "研究文件库",
                    "error",
                    "研究文件不可读取",
                    errorType=type(exc).__name__,
                )
            )
    try:
        doc = read_local_json("public/v1/macro/expectations.json")
        item = freshness(
            "artifact.expectations", "宏观事件概率", "研究文件库", doc.get("updatedAt"), 1, now
        )
        if doc.get("status") != "ready" or not doc.get("events"):
            item.update(status="error", message="概率数据未就绪或为空")
        results.append(item)
    except Exception as exc:
        results.append(
            check(
                "artifact.expectations",
                "宏观事件概率",
                "研究文件库",
                "error",
                "数据不可读取",
                errorType=type(exc).__name__,
            )
        )
    return results


def source_check(source, value, now):
    key = "source." + source
    status = value.get("status")
    timestamp = value.get("lastReceivedAt")
    if status == "deferred" and value.get("reason") == "research_yielded_to_account_operations":
        result = freshness(
            key,
            source,
            "策略行情",
            value.get("lastReadAt"),
            0.25,
            now,
            sourceStatus=status,
            reason=value.get("reason"),
        )
        if result["status"] == "healthy":
            result.update(status="info", message="账户操作优先，研究采集短暂让路")
        return result
    if (
        source in {"mt5", "mt5:XAUUSD"}
        and status == "received"
        and value.get("lastRangeTickCount", 0) > 0
    ):
        timestamp = value.get("lastReadAt")
    if (
        source in {"mt5", "mt5:XAUUSD"}
        and status == "empty_range"
        and value.get("marketStatus") == "closed"
    ):
        result = freshness(
            key,
            source,
            "策略行情",
            value.get("lastReadAt"),
            0.25,
            now,
            sourceStatus=status,
            marketStatus="closed",
        )
        if result["status"] == "healthy":
            result.update(status="info", message="MT5 交易时段已关闭，本次扫描无新报价")
        return result
    if source in {"history:mt5", "mt5:recovery"} and status == "range_scanned":
        return check(
            key,
            source,
            "策略行情",
            "info",
            "历史窗口已扫描完成",
            sourceStatus=status,
            through=value.get("target"),
        )
    if status == "up_to_date" and value.get("lastCheckedAtMs") is not None:
        if int(value.get("through", -1)) >= int(value.get("expectedClosedThroughMs", 0)):
            timestamp = datetime.fromtimestamp(
                int(value["lastCheckedAtMs"]) / 1000, UTC
            ).isoformat()
    if timestamp is None and value.get("lastReceivedAtMs") is not None:
        try:
            timestamp = datetime.fromtimestamp(
                float(value["lastReceivedAtMs"]) / 1000, UTC
            ).isoformat()
        except (ValueError, TypeError, OverflowError, OSError):
            timestamp = None
    if status in {"gap", "error", "disconnected"}:
        return check(
            key,
            source,
            "策略行情",
            "error",
            "数据源报告中断或缺口",
            reason=value.get("reason"),
            observedAt=value.get("at") or timestamp,
            sourceStatus=status,
        )
    if status in {"received", "receiving", "up_to_date", "interval_measured"}:
        return freshness(
            key,
            source,
            "策略行情",
            timestamp,
            0.25,
            now,
            sourceStatus=status,
            sourceDate=value.get("through"),
        )
    return check(
        key,
        source,
        "策略行情",
        "warning",
        "当前状态不足以证明数据持续更新",
        sourceStatus=status,
        observedAt=timestamp,
        reason=value.get("reason"),
    )


def inspect_runtime(now):
    result = []
    for path, key, name in [
        ("/status", "runtime.journal", "Runtime 执行日志"),
        ("/v1/market-data/status", "runtime.capture", "Runtime 行情采集与持久化"),
    ]:
        try:
            response = runtime_transport.get(get_settings().runtime_base_url + path, timeout=5)
            response.raise_for_status()
            data = response.json()
            if key.endswith("journal"):
                result.append(
                    check(
                        key,
                        name,
                        "执行数据库",
                        "healthy"
                        if data.get("status") == "available" and data.get("journal")
                        else "error",
                        "通过 Runtime 所有者接口检查日志可读性；不以无交易判断断更",
                    )
                )
            else:
                if data.get("status") == "disabled":
                    result.append(check(key, name, "策略行情", "info", "采集已配置为停用"))
                    continue
                result.append(
                    freshness(
                        key,
                        name,
                        "策略行情",
                        data.get("lastDurableAt"),
                        0.25,
                        now,
                        dropped=data.get("dropped"),
                        sourceStatus=data.get("status"),
                    )
                )
                used = int(data.get("bytes", 0))
                budget = int(data.get("budgetBytes", 0))
                if budget > 0:
                    ratio = used / budget
                    result.append(
                        check(
                            "runtime.capacity",
                            "原始行情 spool 容量",
                            "策略行情",
                            "error" if used >= budget else "warning" if ratio >= 0.8 else "healthy",
                            (
                                "采集空间已达到预算"
                                if used >= budget
                                else "采集空间接近预算"
                                if ratio >= 0.8
                                else "采集空间在预算内"
                            ),
                            usedBytes=used,
                            budgetBytes=budget,
                            remainingBytes=max(0, budget - used),
                        )
                    )
                sources = data.get("sources", {})
                for source, value in sources.items():
                    # ``bybit`` is an aggregate subscription lifecycle state;
                    # freshness is reported by its concrete spot/linear/rates
                    # child streams below.
                    bybit_children = [name for name in sources if name.startswith("bybit:")]
                    if source == "bybit" and bybit_children:
                        result.append(
                            check(
                                "source.bybit",
                                "bybit",
                                "策略行情",
                                "healthy",
                                "Bybit 聚合订阅状态由子流接收时间检查",
                                childStreams=bybit_children,
                            )
                        )
                        continue
                    result.append(source_check(source, value, now))
                if "dropped" in data and "recoveryGaps" in data:
                    result.append(
                        check(
                            "runtime.loss",
                            "采集丢弃 / 恢复缺口",
                            "策略行情",
                            "error"
                            if data.get("dropped") or data.get("recoveryGaps")
                            else "healthy",
                            "采集器记录丢失数据"
                            if data.get("dropped") or data.get("recoveryGaps")
                            else "采集器未记录丢弃或恢复缺口",
                            dropped=data.get("dropped"),
                            gaps=data.get("recoveryGaps", [])[:10],
                        )
                    )
        except Exception as exc:
            result.append(
                check(
                    key,
                    name,
                    "执行数据库",
                    "error",
                    "所有者接口不可读取",
                    errorType=type(exc).__name__,
                )
            )
    try:
        response = runtime_transport.get(
            get_settings().runtime_base_url + "/gateway/capabilities", timeout=5
        )
        response.raise_for_status()
        payload = response.json()
        adapters = payload.get("adapters") if isinstance(payload, dict) else None
        if not isinstance(adapters, list):
            raise ValueError("Runtime capabilities are malformed")
        for adapter in adapters:
            if not isinstance(adapter, dict):
                continue
            account_statuses = adapter.get("accountStatuses")
            if isinstance(account_statuses, list) and account_statuses:
                for account in account_statuses:
                    if not isinstance(account, dict) or not account.get("accountId"):
                        continue
                    operational = bool(account.get("operational"))
                    result.append(
                        check(
                            "runtime.adapter.account." + str(account["accountId"]),
                            "Runtime 账户适配器 · " + str(account["accountId"]),
                            "账户与会计",
                            "healthy" if operational else "error",
                            "账户专属 Runtime 条件满足"
                            if operational
                            else "账户专属 Runtime 条件不满足",
                            adapter=adapter.get("adapter"),
                            configured=account.get("configured"),
                            missingRequirements=account.get("missingRequirements", []),
                        )
                    )
            else:
                operational = bool(adapter.get("operational"))
                result.append(
                    check(
                        "runtime.adapter." + str(adapter.get("adapter", "unknown")),
                        "Runtime 适配器 · " + str(adapter.get("adapter", "unknown")),
                        "账户与会计",
                        "healthy" if operational else "error",
                        "适配器共享条件满足" if operational else "适配器共享条件不满足",
                        accountIds=adapter.get("accountIds", []),
                        missingRequirements=adapter.get("missingRequirements", []),
                    )
                )
    except Exception as exc:
        result.append(
            check(
                "runtime.capabilities",
                "Runtime 账户适配器状态",
                "账户与会计",
                "error",
                "Runtime 适配器状态不可读取",
                errorType=type(exc).__name__,
            )
        )
    for name, label, seconds in [
        ("account_sync", "账户后台任务", 180),
        ("account_history", "账户历史回补任务", 600),
        ("management_projection", "策略损益投影任务", 120),
        ("funding_runner", "Funding 指令推进任务", 60),
        ("funding_exit", "Funding 价差自动平仓任务", 60),
    ]:
        state = monitor_health.snapshot(name, enabled=True, deadline=seconds)
        result.append(
            check(
                "worker." + name,
                label,
                "后台任务",
                "healthy"
                if state["status"] == "healthy"
                else "warning"
                if state["status"] == "starting"
                else "error",
                state["status"],
                **{k: v for k, v in state.items() if k not in {"error", "status"}},
            )
        )
    return result


def persist_report(checks, now):
    # Daily structural results remain visible between light scans with their own timestamp.
    for item in checks:
        item["checkedAt"] = now.isoformat()
    with read_only_connection() as db:
        previous = db.execute(
            "SELECT report_json FROM data_audit_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if previous:
        current = {item["key"] for item in checks}
        for item in decode_report(previous[0])["checks"]:
            if (
                item["key"] in {"database.integrity", "database.foreign_keys"}
                and item["key"] not in current
            ):
                checks.append(item)
            elif item["key"] not in current and item["status"] in {"error", "warning"}:
                checks.append(
                    {
                        **item,
                        "status": "warning",
                        "message": "本轮未取得复核证据，不能确认此前问题已恢复",
                    }
                )
    report = dict(
        checkedAt=now.isoformat(),
        intervalSeconds=INTERVAL,
        checks=checks,
        summary={
            s: sum(c["status"] == s for c in checks)
            for s in ["healthy", "warning", "error", "info"]
        },
    )
    with connection() as db:
        db.execute(
            "INSERT INTO data_audit_runs(checked_at,report_json) VALUES (?,?)",
            (report["checkedAt"], encode_report(report)),
        )
        # Retain 30 days of audit evidence; business facts are never changed.
        db.execute(
            "DELETE FROM data_audit_runs WHERE checked_at < ?",
            ((now - timedelta(days=30)).isoformat(),),
        )
        for item in checks:
            if item["checkedAt"] != now.isoformat():
                continue  # Retained evidence is not a new observation or a recovery.
            fingerprint = "data_audit:" + item["key"]
            if item["status"] in {"error", "warning"}:
                db.execute(
                    """INSERT INTO operational_alerts
                    (id,fingerprint,category,severity,status,subject_type,subject_id,owner,message,details_json,occurrence_count,first_seen_at,last_seen_at)
                    VALUES (?,?, 'data_audit',?,'open','dataset',?,'platform',?,?,1,?,?)
                    ON CONFLICT(fingerprint) DO UPDATE SET
                    severity=excluded.severity, message=excluded.message,
                    details_json=excluded.details_json,
                    status=CASE WHEN operational_alerts.status='closed' THEN 'open'
                        ELSE operational_alerts.status END,
                    occurrence_count=operational_alerts.occurrence_count+1,last_seen_at=excluded.last_seen_at,
                    closed_at=NULL,closed_by=NULL,resolution_reason=NULL""",
                    (
                        fingerprint,
                        fingerprint,
                        "critical" if item["status"] == "error" else "warning",
                        item["key"],
                        item["name"] + "：" + item["message"],
                        json.dumps(item["evidence"], ensure_ascii=False),
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
            elif item["status"] == "healthy":
                db.execute(
                    "UPDATE operational_alerts SET status='closed',closed_at=?,"
                    "closed_by='data_audit',resolution_reason='检查已恢复' "
                    "WHERE fingerprint=? AND status!='closed'",
                    (now.isoformat(), fingerprint),
                )
    return report


def run_audit():
    now = datetime.now(UTC)
    try:
        checks = inspect_database(now)
        checks.append(check("database.scan", "数据库审计执行", "平台数据库"))
    except Exception as exc:
        LOG.exception("Data audit database scan did not complete")
        checks = [
            check(
                "database.scan",
                "数据库审计执行",
                "平台数据库",
                "error",
                "审计未完成，不能确认数据正常",
                errorType=type(exc).__name__,
            )
        ]
    checks.extend(inspect_runtime(now))
    checks.extend(inspect_artifacts(now))
    from app.data_audit_history import inspect_changes, inspect_stock_returns, read_full_report

    changes = inspect_changes(now)
    checks.append(
        check(
            "history.incremental",
            "历史新增与修订检查",
            "数据有效性",
            changes["status"],
            "增量检查完成" if changes["status"] == "healthy" else "增量检查有异常、积压或未完成",
            **{k: v for k, v in changes.items() if k != "status"},
        )
    )
    returns = inspect_stock_returns()
    checks.append(
        check(
            "calculations.stock_returns",
            "股票池5日/20日收益复算",
            "计算一致性",
            returns["status"],
            "已复算本轮可用收益" if returns["status"] == "healthy" else "收益复算异常或未完成",
            **{k: v for k, v in returns.items() if k != "status"},
        )
    )
    try:
        full = read_full_report()
    except (OSError, ValueError):
        full = None
    if full and Path(full.get("source", "")).resolve() != database_path().resolve():
        full = None
    baseline = full if full and full.get("complete") else (full or {}).get("lastComplete")
    if baseline and Path(baseline.get("source", "")).resolve() != database_path().resolve():
        baseline = None
    full_status = (full or {}).get("status", "warning")
    if full_status == "running":
        full_status = "warning"
    if baseline and baseline.get("status") == "error" and not (full or {}).get("complete"):
        full_status = "error"
    if baseline and (age_seconds(baseline.get("finishedAt"), now) or 0) > 8 * 86400:
        full_status = "warning" if full_status != "error" else "error"
    checks.append(
        check(
            "history.full",
            "历史全量副本核对",
            "历史核对",
            full_status,
            "副本核对完成" if full and full.get("complete") else "尚未完成本轮全量副本核对",
            report=full,
            observedAt=(baseline or {}).get("snapshotAt"),
            fetched=(full or {}).get("finishedAt"),
            independentSourceValuesVerified=False,
            originalDatabasePhysicalIntegrityVerified=False,
        )
    )
    for key, field in [("integrity", "integrity"), ("foreign_keys", "foreignKeyViolations")]:
        evidence = (baseline or {}).get(field)
        healthy = evidence == [["ok"]] if key == "integrity" else evidence == []
        structure_status = (
            "error"
            if evidence is not None and not healthy
            else "healthy"
            if healthy
            and baseline
            and (age_seconds(baseline.get("finishedAt"), now) or 0) <= 8 * 86400
            else "warning"
        )
        checks.append(
            check(
                "database." + key,
                "研究副本结构 · " + key,
                "平台数据库",
                structure_status,
                "副本结构检查通过" if healthy else "副本结构检查未通过或未完成",
                evidence=evidence,
                observedAt=(baseline or {}).get("snapshotAt"),
                fetched=(baseline or {}).get("finishedAt"),
                snapshotAt=(baseline or {}).get("snapshotAt"),
            )
        )
    return persist_report(checks, now)


def read_report():
    with read_only_connection() as db:
        row = db.execute(
            "SELECT report_json FROM data_audit_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        alerts = [
            dict(r)
            for r in db.execute(
                "SELECT id,message,severity,status,first_seen_at,last_seen_at,occurrence_count "
                "FROM operational_alerts WHERE category='data_audit' "
                "ORDER BY last_seen_at DESC LIMIT 100"
            )
        ]
    report: dict[str, Any] = (
        decode_report(row[0]) if row else dict(checkedAt=None, checks=[], summary={})
    )
    age = age_seconds(report["checkedAt"], datetime.now(UTC))
    report.update(monitorStale=age is None or age > INTERVAL * 3, alerts=alerts)
    return report


def ensure_alert_schema():
    with connection() as db:
        db.executescript(ALERT_SCHEMA)


@asynccontextmanager
async def lifespan(_):
    await asyncio.to_thread(ensure_alert_schema)

    async def monitor():
        while True:
            try:
                monitor_health.begin("data_audit")
                if get_settings().research_refresh_enabled:
                    try:
                        await asyncio.to_thread(refresh_calendar)
                    except Exception:
                        LOG.warning(
                            "Independent calendar refresh failed; audit reports coverage explicitly"
                        )
                await asyncio.to_thread(run_audit)
                from app.data_audit_history import launch_full_audit_if_due

                await asyncio.to_thread(launch_full_audit_if_due, datetime.now(UTC))
                monitor_health.finish("data_audit")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOG.exception("Data audit persistence failed")
                monitor_health.finish("data_audit", type(exc).__name__)
            await asyncio.sleep(INTERVAL)

    task = asyncio.create_task(monitor())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


router = APIRouter(
    prefix="/api/v1/risk/data-audit",
    tags=["data-audit"],
    dependencies=[Depends(require_permission("risk.read"))],
)


@router.get("")
def data_audit_report():
    return read_report()
