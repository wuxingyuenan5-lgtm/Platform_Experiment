"""Synthetic fixtures exercise algorithms; none represent captured market history."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.strategy_research_experiments import run_experiment, scan
from app.strategy_research_policy import matched_quantity, scenario, vwap
from app.strategy_research_schemas import Scenario
from app.strategy_research_series import Deriver, seconds_series, stable_hash

T = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)


def request(**overrides):
    body = dict(
        pairId="funding-btc",
        direction="buy_spread",
        quantity="2",
        entrySpread="3",
        exitSpread="1",
        openedAt=T,
        closedAt=T + timedelta(hours=1),
        tradingFees="1",
        additionalExecutionCost="0",
        costProfileId="test-explicit",
        fundingCoverage="scenario",
        swapCoverage="not_applicable",
    )
    body.update(overrides)
    return Scenario.model_validate(body)


def event(
    n,
    symbol="BTCUSDT",
    category="linear",
    bid="101",
    ask="102",
    at=None,
    kind="snapshot",
    quality=None,
):
    at = at or T + timedelta(milliseconds=n * 100)
    return {
        "schemaVersion": "market-events.v1",
        "eventId": f"session:{n}",
        "collectorSessionId": "session",
        "ingestSequence": str(n),
        "runtimeReceivedAt": at.isoformat(),
        "sourceEventTimeMs": str(int(at.timestamp() * 1000)),
        "runtimeMonotonicNs": str(int(at.timestamp() * 1000) * 1_000_000),
        "sourceClock": {
            "methodVersion": "bybit-clock-interval.v1",
            "eventId": "fixture-clock",
            "collectorSessionId": "session",
            "offsetLowerNs": "0",
            "offsetUpperNs": "0",
            "localReceivedNs": str(int(at.timestamp() * 1000) * 1_000_000),
            "localMonotonicNs": str(int(at.timestamp() * 1000) * 1_000_000),
            "maxAgeNs": "120000000000",
            "driftAllowanceNs": "100000000",
        },
        "ingestionMode": "realtime",
        "quoteScope": "public",
        "quality": quality or [],
        "kind": "bybit_message",
        "stream": f"bybit:{category}:orderbook.50.{symbol}",
        "payload": {
            "topic": f"orderbook.50.{symbol}",
            "type": kind,
            "data": {"s": symbol, "u": n, "a": [[ask, "100"]], "b": [[bid, "100"]]},
        },
    }


def spread_rows(prices):
    d = Deriver()
    rows = []
    for i, (a, b) in enumerate(prices):
        for category, bid in (("linear", a), ("spot", b)):
            e = event(
                i * 2 + 1 + (category == "spot"),
                category=category,
                bid=str(bid),
                ask=str(bid + 1),
                at=T + timedelta(milliseconds=i * 500 + (category == "spot")),
            )
            rows.extend(r for r in d.consume(e) if r["kind"] == "spread")
    return rows


def minute_quote(n, category, at):
    e = event(n, category=category, at=at)
    e["kind"] = "quote_sample"
    e["payload"] = {
        "symbol": "BTCUSDT",
        "category": category,
        "bid": "101" if category == "linear" else "100",
        "ask": "102" if category == "linear" else "101",
        "samplingIntervalMs": 60000,
    }
    return e


def test_minute_quotes_never_pair_previous_minute_or_fabricate_duration():
    from app.strategy_research_projection import second_statistics, spread_chart

    d = Deriver()
    rows = []
    for i, minute in enumerate((0, 2)):
        first = d.consume(minute_quote(i * 2 + 1, "linear", T + timedelta(minutes=minute)))
        assert not any(r["kind"] == "spread" for r in first)
        rows.extend(
            r
            for r in d.consume(
                minute_quote(i * 2 + 2, "spot", T + timedelta(minutes=minute, milliseconds=50))
            )
            if r["kind"] == "spread"
        )
    assert len(rows) == 2 and all(r["samplingIntervalMs"] == 60000 for r in rows)
    points = seconds_series(rows)
    assert len(points) == 2 and all(r["validDurationMs"] == 0 for r in points)
    stats = second_statistics(points, points)
    assert stats["sampleCount"] == 2 and stats["sampling"] == "observed_1m_points"
    assert stats["validDurationMs"] == "0"
    assert any(p["value"][1] is None for p in spread_chart(points)[0]["data"])
    with pytest.raises(ValueError, match="分钟采样"):
        run_experiment(rows, params())


def params(**overrides):
    p = {
        "pairId": "funding-btc",
        "direction": "buy_spread",
        "quantity": "1",
        "entryThreshold": "2",
        "exitTarget": "5",
        "riskPnl": "-10",
        "maxHoldingSeconds": 3,
        "maxQuoteAgeMs": 2000,
        "from": T.isoformat(),
        "to": (T + timedelta(seconds=10)).isoformat(),
        "cutoff": (T + timedelta(seconds=10)).isoformat(),
        "validationFrom": (T + timedelta(seconds=5)).isoformat(),
        "costProfile": request(quantity="1", tradingFees="0").model_dump(mode="json"),
        "latencyMs": [0, 100],
        "holdingSeconds": [1, 5],
        "mt5SlippagePerUnit": None,
    }
    p.update(overrides)
    return p


@pytest.mark.parametrize(
    "direction,entry,exit,expected",
    [("buy_spread", "3", "1", "-5"), ("sell_spread", "1", "3", "-5")],
)
def test_immediate_close_pays_spreads_once(direction, entry, exit, expected):
    result = scenario(request(direction=direction, entrySpread=entry, exitSpread=exit))
    assert result["netPnl"] == expected
    assert result["pricePnl"] == "-4"


def test_unknown_cost_is_not_zero():
    result = scenario(request(tradingFees=None))
    assert result["netPnl"] is None
    assert result["breakEvenExitSpread"] is None


@pytest.mark.parametrize("direction,expected", [("buy_spread", "-2.00"), ("sell_spread", "2.00")])
def test_funding_sign_and_actual_event_time(direction, expected):
    result = scenario(
        request(
            direction=direction,
            funding=[
                {
                    "at": T + timedelta(minutes=30),
                    "observedAt": T,
                    "rate": ".01",
                    "mark": "100",
                    "kind": "settled",
                    "markQuality": "exact",
                }
            ],
        )
    )
    assert result["fundingCash"] == expected


def test_funding_boundary_gives_range_and_missing_mark_is_unknown():
    e = {
        "at": T,
        "observedAt": T,
        "rate": ".01",
        "mark": "100",
        "kind": "settled",
        "markQuality": "exact",
    }
    result = scenario(request(funding=[e]))
    assert result["fundingCash"] is None
    assert result["netPnlRange"] == ["-7.00", "-5"]
    e["mark"] = None
    assert scenario(request(funding=[e]))["netPnlRange"] is None


def test_future_indication_and_duplicate_settlement():
    e = {
        "at": T + timedelta(minutes=20),
        "observedAt": T,
        "rate": ".01",
        "mark": "100",
        "kind": "settled",
    }
    assert scenario(request(funding=[e, e]))["fundingCash"] == "-2.00"
    e.update(kind="indicated", observedAt=T + timedelta(minutes=1))
    assert scenario(request(funding=[e]))["netPnl"] is None


def test_borrow_spot_first_period_rounds_up_even_early_repayment():
    borrow = {
        "product": "uta_flexible",
        "principal": "600",
        "hourlyRate": ".01",
        "observedAt": T,
        "effectiveFrom": T,
    }
    result = scenario(
        request(
            openedAt=T + timedelta(minutes=4, seconds=30),
            closedAt=T + timedelta(minutes=4, seconds=40),
            borrow=borrow,
        )
    )
    assert Decimal(result["borrowCash"]) == Decimal("-.1")


def test_quantity_matching_and_depth():
    result = matched_quantity(Decimal("1"), Decimal(".001"), Decimal(".1"), Decimal(".1"))
    # The confirmed sizing rule selects the nearest legal perpetual quantity.
    assert Decimal(result["matched"]) == Decimal("1.00")
    assert Decimal(result["residual"]) == Decimal("-0.001")
    assert vwap([["10", "1"], ["12", "1"]], Decimal("2")) == 11
    assert vwap([["10", "1"]], Decimal("2")) is None


def test_no_future_join_and_backfill_invalid():
    d = Deriver()
    assert not any(r["kind"] == "spread" for r in d.consume(event(1)))
    out = d.consume(event(2, category="spot", bid="99", ask="100"))
    spread = next(r for r in out if r["kind"] == "spread")
    assert spread["inputEventIds"] == ["session:1", "session:2"]
    assert spread["buySpread"] == "3" and spread["sellSpread"] == "1"
    e = event(3, bid="105", ask="106")
    e["ingestionMode"] = "backfill"
    assert "backfill_only" in d.consume(e)[-1]["quality"]


def test_book_snapshot_zero_delete_reconnect_and_no_plus_one_rule():
    d = Deriver()
    d.consume(event(1))
    e = event(20, kind="delta", bid="100", ask="103")
    e["payload"]["data"]["a"] = [["102", "0"], ["103", "10"]]
    q = d.consume(e)[0]
    assert q["ask"] == "103"
    d.consume({"kind": "quality", "stream": "bybit:linear", "payload": {}})
    assert d.consume(event(21, kind="delta"))[0]["quality"] == ["book_unsynced"]
    assert d.consume(event(30, bid="110", ask="111"))[0]["bid"] == "110"


def test_invalid_raw_does_not_reuse_previous_valid_quote():
    d = Deriver()
    d.consume(event(1))
    d.consume(event(2, category="spot"))
    result = d.consume(event(3, bid="NaN", ask="100"))
    assert "numeric_invalid" in result[0]["quality"]
    assert not any(r["kind"] == "spread" for r in d.consume(event(4, category="spot")))


def test_mt5_same_millisecond_records_and_overlap_multiset():
    d = Deriver()
    e = event(1)
    e.update(kind="mt5_batch", stream="mt5:XAUUSD", quoteScope="account:fixture")
    a = {"time_msc": "1", "bid": "99", "ask": "100", "flags": "6"}
    b = dict(a, bid="98")
    e["payload"] = {"symbol": "XAUUSD.S", "server": "fixture", "ticks": [a, b, a]}
    first = [r for r in d.consume(e) if r["kind"] == "quote"]
    assert len(first) == 3
    e["eventId"] = "session:2"
    assert not d.consume(e)
    e["payload"]["ticks"] = [a, b, a, a]
    assert len(d.consume(e)) == 1


def test_event_extrema_not_leg_extrema_and_no_fabricated_tail():
    rows = spread_rows([(101, 100), (106, 102)])
    seconds = seconds_series(rows)
    assert Decimal(seconds[0]["ohlc"]["buySpread"]["high"]) == Decimal("7")
    assert seconds[-1]["validDurationMs"] < 1000


def test_continuous_deviation_does_not_create_repeated_events():
    rows = spread_rows([(101, 100)] * 10)
    result = scan(rows, params(maxHoldingSeconds=1))
    assert len(result["events"]) == 1
    assert result["events"][0]["exitReason"] == "timeout"


def test_censored_unknown_and_risk_are_reported():
    rows = spread_rows([(101, 100)] * 2)
    assert scan(rows, params())["events"][0]["exitReason"] == "right_censored"
    rows[-1]["quality"] = ["source_gap"]
    assert scan(rows, params())["events"][0]["exitReason"] == "path_unknown"
    rows = spread_rows([(101, 100), (80, 100)])
    assert scan(rows, params())["events"][0]["exitReason"] == "risk"


def test_replay_is_deterministic_and_oos_not_training():
    rows = spread_rows([(101, 100)] * 10)
    result = run_experiment(rows, params())
    assert stable_hash(result) == stable_hash(run_experiment(rows, params()))
    assert result["summary"]["independentEvents"] == 1
    assert result["sampleOutOfTraining"]["independentEvents"] == 0
    assert result["events"][0]["replay"][0]["inputEventIds"]


def test_schema_rejects_float_nonfinite_and_naive():
    with pytest.raises(ValueError):
        request(quantity=0.1)
    with pytest.raises(ValueError):
        request(quantity="NaN")
    with pytest.raises(ValueError):
        request(openedAt=T.replace(tzinfo=None))


@pytest.fixture
def db_ready(tmp_path):
    from app.config import get_settings
    from app.database import initialize_database

    get_settings().strategy_research_path = str(tmp_path / "archive")
    get_settings().strategy_research_min_free_bytes = 0
    initialize_database()
    return tmp_path


def test_archive_replay_atomic_cursor_decimal_and_backup(db_ready):
    from app.strategy_research_repository import backup, checkpoint, parts, publish, read_rows

    batch = {
        "schemaVersion": "market-events.v1",
        "after": None,
        "nextCursor": "one:1",
        "events": [
            event(1, bid="100.123456789012345678", ask="101.123456789012345678"),
            event(2, category="spot"),
        ],
        "capture": {},
    }
    part = publish(batch)
    assert publish(batch) == part
    assert len(parts()) == 1 and checkpoint()["cursor"] == "one:1"
    raw = read_rows(layer="raw")
    assert raw[0]["payload"]["data"]["b"][0][0] == "100.123456789012345678"
    result = backup(db_ready / "backup")
    assert result["integrity"] == "ok"


def test_manifest_failure_leaves_recoverable_orphan(db_ready, monkeypatch):
    from app import strategy_research_repository as repo

    batch = {
        "schemaVersion": "market-events.v1",
        "after": None,
        "nextCursor": "one:1",
        "events": [event(1)],
        "capture": {},
    }
    original = repo.assert_sqlite_safe
    monkeypatch.setattr(
        repo, "assert_sqlite_safe", lambda db: (_ for _ in ()).throw(RuntimeError("crash"))
    )
    with pytest.raises(RuntimeError):
        repo.publish(batch)
    assert repo.checkpoint()["cursor"] is None
    monkeypatch.setattr(repo, "assert_sqlite_safe", original)
    repo.publish(batch)
    assert len(repo.parts()) == 1


def test_experiments_are_user_scoped_and_idempotent(db_ready):
    from app.strategy_research_repository import enqueue_experiment, get_experiment

    first = enqueue_experiment("a", params())
    assert enqueue_experiment("a", params())["run_id"] == first["run_id"]
    assert get_experiment(first["run_id"], "b") is None


def test_existing_migrations_untouched_and_repeat_preserves_rows(db_ready):
    from app.database import initialize_database
    from app.database_connection import connection

    with connection() as db:
        before = db.execute("select count(*) from instruments").fetchone()[0]
        checksums = list(db.execute("select version,checksum from schema_migrations"))
    initialize_database()
    with connection() as db:
        assert db.execute("select count(*) from instruments").fetchone()[0] == before
        assert [tuple(r) for r in db.execute("select version,checksum from schema_migrations")] == [
            tuple(r) for r in checksums
        ]


def test_cancel_and_artifact_backup_are_bounded_and_verified(db_ready):
    from app import strategy_research_repository as repo
    from app.database_connection import connection

    job = repo.enqueue_experiment("a", params())
    repo.next_experiment()
    result = run_experiment(spread_rows([(101, 100)] * 8), params())
    repo.finish_experiment(job["run_id"], result)
    with connection() as db:
        saved = db.execute("SELECT result_json FROM research_strategy_experiments").fetchone()[0]
    assert "artifact" in saved and "replay" not in saved
    assert repo.get_experiment(job["run_id"], "a")["result"] == result
    assert repo.backup(db_ready / "artifact-backup")["parts"] == 1
    artifact = next(repo.root_path().glob("experiment-*.parquet"))
    with artifact.open("ab") as file:
        file.write(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        repo.get_experiment(job["run_id"], "a")
    with pytest.raises(ValueError, match="cancelled"):
        run_experiment(spread_rows([(101, 100)]), params(_cancelled=lambda: True))


def test_cutoff_uses_instant_and_includes_partial_shard(db_ready):
    from app import strategy_research_repository as repo

    stamp = T.replace(microsecond=0)
    e = event(1, at=stamp)
    repo.publish(
        {
            "schemaVersion": "market-events.v1",
            "after": None,
            "nextCursor": "a:1",
            "events": [e],
            "capture": {},
        }
    )
    assert len(repo.read_rows(layer="raw", start=stamp.isoformat(timespec="microseconds"))) == 1
    assert (
        len(
            repo.enqueue_experiment("a", params(cutoff=stamp.isoformat(timespec="microseconds")))[
                "parts"
            ]
        )
        == 1
    )


def test_permission_mapping_never_grants_execution():
    from app.auth import permission_for_request

    assert permission_for_request("POST", "/api/v1/research/strategies/scenario") == "research.read"
    assert permission_for_request("POST", "/api/v1/research/strategies/drafts") == "research.write"
    assert (
        permission_for_request("POST", "/api/v1/trading/cross-spread/market-command")
        == "trading.write"
    )


def test_paired_rules_have_same_entries_and_gap_is_not_success():
    rows = spread_rows([(101, 100)] * 10)
    result = run_experiment(rows, params())
    assert {x["entryCohortCount"] for x in result["exitRuleComparison"]} == {1}
    assert len({x["events"][0]["id"] for x in result["exitRuleComparison"]}) == 1
    assert result["opportunityDurations"]["count"] == 1
    rows[2]["quality"] = ["source_gap"]
    result = run_experiment(rows, params())
    assert result["summary"]["outcomes"] == {"path_unknown": 1}


def test_spawned_experiment_worker_reads_only_frozen_isolated_storage(db_ready):
    from concurrent.futures import ProcessPoolExecutor

    from app import strategy_research_repository as repo
    from app.config import get_settings
    from app.strategy_research_ingest import compute_job, initialize_worker

    repo.publish(
        {
            "schemaVersion": "market-events.v1",
            "after": None,
            "nextCursor": "a:1",
            "events": [event(1), event(2, category="spot")],
            "capture": {},
        }
    )
    job = repo.enqueue_experiment("a", params())
    raw = repo.next_experiment()
    import multiprocessing

    ctx = multiprocessing.get_context("spawn")
    stop = ctx.Event()
    with ProcessPoolExecutor(
        max_workers=1, mp_context=ctx, initializer=initialize_worker, initargs=(stop,)
    ) as pool:
        result = pool.submit(
            compute_job, raw, (get_settings().database_path, str(repo.root_path()))
        ).result(timeout=30)
        stop.set()
        with pytest.raises(ValueError, match="cancelled"):
            pool.submit(
                compute_job, raw, (get_settings().database_path, str(repo.root_path()))
            ).result(timeout=30)
    repo.finish_experiment(job["run_id"], result)
    assert repo.get_experiment(job["run_id"], "a")["status"] == "completed"
    assert result["coverage"]["observations"] == 1
    assert result["summary"]["outcomes"] == {"right_censored": 1}


def test_runtime_restart_clears_all_causal_leg_state():
    d = Deriver()
    d.consume(event(1))
    d.consume(event(2, category="spot"))
    d.consume({"kind": "quality", "stream": "runtime", "payload": {}, "quality": ["capture_gap"]})
    assert not d.state["books"] and not d.state["quotes"]
    assert not any(row["kind"] == "spread" for row in d.consume(event(3)))


def test_settlement_view_cannot_mix_other_instrument_rates():
    timestamp = str(int(T.timestamp() * 1000))
    other = {
        "stream": "bybit:linear:XAUTUSDT",
        "payload": {"fundingRateTimestamp": timestamp, "fundingRate": ".1"},
    }
    result = run_experiment(spread_rows([(101, 100)] * 4), params(_settlements=[other]))
    assert result["settlementEvents"] == []


def test_restore_verifier_rejects_missing_experiment_artifact(db_ready):
    from app import strategy_research_repository as repo

    job = repo.enqueue_experiment("owner", params())
    repo.next_experiment()
    repo.finish_experiment(job["run_id"], {"summary": {}, "replay": ["fixture"]})
    destination = db_ready / "verified-artifact"
    repo.backup(destination)
    assert repo.verify_backup(destination)["parts"] == 1
    (destination / "manifest.json").write_text("[]")
    with pytest.raises(ValueError, match="catalog differs"):
        repo.verify_backup(destination)


def test_clock_interval_is_causal_bounded_and_retains_native_source():
    from app.strategy_research_series import source_age_bounds

    e = event(1)
    native = str(int(e["sourceEventTimeMs"]) - 3000)
    e["sourceEventTimeMs"] = native
    e["sourceClock"].update(offsetLowerNs="-3100000000", offsetUpperNs="-2900000000")
    bounds = source_age_bounds(e)
    assert bounds["lowerMs"] == "-200" and bounds["upperMs"] == "200"
    row = Deriver().consume(e)[0]
    assert row["sourceTimeMs"] == native and not row["quality"]
    e["sourceClock"]["collectorSessionId"] = "previous-session"
    assert source_age_bounds(e) is None
    e["sourceClock"]["collectorSessionId"] = "session"
    e["runtimeMonotonicNs"] = str(int(e["runtimeMonotonicNs"]) - 1)
    assert source_age_bounds(e) is None  # Future calibration cannot repair this event.
    e["runtimeMonotonicNs"] = str(int(e["runtimeMonotonicNs"]) + 121000000001)
    assert source_age_bounds(e) is None  # Expired evidence.
    del e["sourceClock"]
    assert "clock_unverified" in Deriver().consume(e)[0]["quality"]


def test_historical_prices_do_not_mutate_observed_quotes():
    d = Deriver(None)
    e = event(1)
    e.update(
        kind="price_history",
        stream="bybit:linear:BTCUSDT:trade",
        ingestionMode="backfill",
        payload={
            "intervalMs": "900000",
            "symbol": "BTCUSDT",
            "category": "linear",
            "priceType": "trade",
            "response": {"result": {"list": [["1000000", "1", "2", "1", "1.5"]]}},
        },
    )
    result = d.consume(e)
    assert result[0]["kind"] == "historical_candle"
    assert result[0]["closeTimeMs"] == "1900000"
    assert d.consume(e) == []
    assert not d.state["quotes"]


def test_bad_history_keeps_quality_without_blocking_raw_publication():
    d = Deriver()
    e = event(1)
    e.update(
        kind="price_history",
        stream="history",
        payload={
            "intervalMs": "60000",
            "symbol": "BTCUSDT",
            "category": "linear",
            "priceType": "trade",
            "response": {"result": {"list": [["bad"], ["1", "2", "1", "3", "-1"]]}},
        },
    )
    result = d.consume(e)
    assert len(result) == 2 and all("numeric_invalid" in r["quality"] for r in result)
    assert result[1]["close"] == "-1"
    assert not d.state["quotes"]


def test_mt5_native_offset_requires_live_same_session_evidence():
    raw = event(1, at=T)
    raw["kind"] = "mt5_batch"
    stamp = int(T.timestamp() * 1000)
    raw["payload"] = {
        "symbol": "XAUUSD.s",
        "server": "fixture",
        "account": "mt5-owner",
        "timeConversionVersion": "mt5-observed-utc-offset.v1",
        "nativeClockEvidence": {
            "methodVersion": "mt5-observed-utc-offset.v1",
            "account": "mt5-owner",
            "symbol": "XAUUSD.S",
            "samples": 3,
            "collectorSessionId": "session",
            "nativeUtcOffsetMs": 10800000,
            "measuredMonotonicNs": str(stamp * 1000000 - 1000000000),
            "maxAgeNs": "30000000000",
        },
        "ticks": [{"time_msc": str(stamp + 10800000), "bid": "100", "ask": "101"}],
    }
    quote = Deriver().consume(raw)[0]
    assert quote["sourceTimeMs"] == str(stamp)
    assert quote["nativeSourceTimeMs"] == str(stamp + 10800000)
    assert "clock_unverified" not in quote["quality"]
    raw["payload"]["nativeClockEvidence"]["collectorSessionId"] = "other-session"
    assert "clock_unverified" in Deriver().consume(raw)[0]["quality"]
