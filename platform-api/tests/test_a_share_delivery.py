from __future__ import annotations

import asyncio
import json
import sqlite3
from decimal import Decimal
from datetime import UTC, datetime, timedelta

import pytest
from a_share_fixture import CODES, AShareFixtureProvider
from fastapi.testclient import TestClient

import app.research_a_share_refresh as refresh
import app.research_a_share_repository as repository
import app.research_service as service
from app.application import create_application
from app.config import get_settings
from app.database import connection, initialize_database
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from scripts.user_demo_seed import seed_demo_users


@pytest.fixture
def research_db(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "delivery.db"))
    monkeypatch.setattr(settings, "research_refresh_enabled", False)
    monkeypatch.setattr(settings, "live_trading_enabled", False)
    monkeypatch.setattr(settings, "runtime_base_url", "http://127.0.0.1:1")
    monkeypatch.setattr(settings, "cors_origins", "http://127.0.0.1:4437")
    initialize_database()
    with connection() as db:
        db.execute(
            "INSERT INTO research_a_share_pool_config VALUES(1,?,1,?)",
            (json.dumps(CODES), datetime.now(UTC).isoformat()),
        )
    provider = AShareFixtureProvider()
    monkeypatch.setattr(refresh, "_PROVIDER", provider)
    monkeypatch.setattr(refresh, "_REFRESH_LOCK", asyncio.Lock())
    monkeypatch.setattr(service, "_DASHBOARD_LOCK", asyncio.Lock())
    return provider


def test_cumulative_volatility_run_does_not_replace_a_share_refresh_status(research_db):
    repository.start_refresh("legacy-a-share", "2026-09-23")
    repository.finish_refresh("legacy-a-share", "ready")
    repository.start_refresh("volatility-latest", None)
    repository.finish_refresh("volatility-latest", "ready")
    with connection() as db:
        db.execute(
            "UPDATE research_a_share_refresh_runs SET started_at=? WHERE run_id=?",
            ("2026-09-23T15:00:00+00:00", "legacy-a-share"),
        )
        db.execute(
            "UPDATE research_a_share_refresh_runs SET started_at=? WHERE run_id=?",
            ("2026-09-23T16:00:00+00:00", "volatility-latest"),
        )

    status = repository.read_refresh_status()

    assert status is not None
    assert status["runId"] == "legacy-a-share"


def test_weak_legacy_research_schema_is_rebuilt_without_losing_records():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    migration20 = next(item for item in PLATFORM_MIGRATIONS if item.version == 20)
    for statement in migration20.statements:
        weakened = statement.replace(" CHECK(status IN ('running','ready','partial','error'))", "")
        weakened = weakened.replace(
            " CHECK(status IN ('ready','partial','stale','error','no_data'))", ""
        )
        weakened = weakened.replace(
            ",\n                FOREIGN KEY(refresh_run_id) "
            "REFERENCES research_a_share_refresh_runs(run_id)",
            "",
        )
        db.execute(weakened)
    now = datetime.now(UTC).isoformat()
    db.execute(
        "INSERT INTO research_a_share_refresh_runs "
        "VALUES('legacy','2026-09-04',?,?,'ready',NULL,NULL)",
        (now, now),
    )
    db.execute(
        "INSERT INTO research_a_share_dataset_snapshots "
        "VALUES('stock_pool',?,?, 'ready','legacy',?,NULL,NULL,'legacy')",
        (now, now, json.dumps({"stocks": [{"code": "600519"}]})),
    )
    db.execute(
        "INSERT INTO research_a_share_dataset_snapshots "
        "VALUES('orphaned_snapshot',?,?, 'ready','legacy','{}',NULL,NULL,'missing-run')",
        (now, now),
    )
    db.commit()
    # This fixture contains only the legacy research tables. Exercise their
    # rebuild, not later migrations that require the complete trading schema.
    migrations = tuple(item for item in PLATFORM_MIGRATIONS if 20 <= item.version <= 21)
    apply_migrations(db, migrations)
    apply_migrations(db, migrations)
    assert json.loads(
        db.execute("SELECT codes_json FROM research_a_share_pool_config").fetchone()[0]
    ) == ["600519"]
    assert db.execute("SELECT COUNT(*) FROM research_a_share_dataset_snapshots").fetchone()[0] == 2
    assert (
        db.execute(
            "SELECT refresh_run_id FROM research_a_share_dataset_snapshots "
            "WHERE dataset = 'orphaned_snapshot'"
        ).fetchone()[0]
        is None
    )
    assert db.execute("PRAGMA foreign_key_list(research_a_share_dataset_snapshots)").fetchall()
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE research_a_share_dataset_snapshots SET status='invalid'")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE research_a_share_dataset_snapshots SET refresh_run_id='missing'")


def test_migration_failure_rolls_back_ddl_as_well_as_data():
    from app.schema_migrations import Migration

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    with pytest.raises(sqlite3.OperationalError):
        apply_migrations(
            db,
            (
                Migration(
                    version=1,
                    name="fail",
                    statements=("CREATE TABLE transient(id)", "INSERT INTO missing VALUES(1)"),
                ),
            ),
        )
    assert db.execute("SELECT name FROM sqlite_master WHERE name='transient'").fetchone() is None
    assert db.execute("SELECT * FROM schema_migrations").fetchall() == []


def test_production_collects_once_preserves_missing_values_and_correct_periods(research_db):
    research_db.mode = "missing_value"
    assert asyncio.run(refresh.refresh_a_share_research(force=True)) == "partial"
    assert research_db.calls["spots"] == research_db.calls["memberships"] == 1
    pool = repository.read_stock_pool()
    assert pool["meta"]["report_date"] == "2026-09-07"
    missing = next(row for row in pool["stocks"] if row["code"] == "300750")
    assert missing["change"] is None
    assert pool["summary"]["breadth"]["flat"] == 0
    # CN production no longer collects the separately scheduled HK member.
    assert pool["summary"]["breadth"]["missing"] == 2
    assert next(row for row in pool["stocks"] if row["code"] == "00700")["status"] == "no_data"
    expected = sorted(
        [row for row in pool["stocks"] if len(row["code"]) == 6],
        key=lambda row: row["change_5d"],
        reverse=True,
    )
    assert [row["code"] for row in pool["leaders"]["5d"]["up"]] == [row["code"] for row in expected]
    assert pool["leaders"]["today"]["up"] != pool["leaders"]["20d"]["up"]
    assert repository.read_hot_stock_history()["counts"] == [2]
    assert repository.read_dashboard().market_history[-1].market_breadth_pct is not None
    crowding = repository.read_dashboard().crowding
    assert crowding.meta.status == "ready"
    assert crowding.data["latest"]["targets"]["通信设备"]["amount100m"] == 1000
    assert crowding.data["latest"]["targets"]["通信设备"]["turnoverPct"] == 3.52
    assert crowding.data["innovationHistory"][-1]["turnoverPct"] == 2.5


def test_missing_sector_quote_does_not_publish_zero_or_claim_ready(research_db, monkeypatch):
    assert asyncio.run(refresh.refresh_a_share_research(force=True)) == "ready"
    previous = repository.read_dashboard().crowding.data["latest"]

    async def fail_sector_quotes():
        raise RuntimeError("sector feed unavailable")

    monkeypatch.setattr(research_db, "sector_crowding_snapshot", fail_sector_quotes)
    assert asyncio.run(refresh.refresh_a_share_research(force=True)) == "partial"
    current = repository.read_dashboard().crowding
    assert current.meta.status == "partial"
    assert current.data["latest"] == previous


def test_failed_modules_keep_stale_data_and_do_not_freeze_healthy_stocks(research_db):
    assert asyncio.run(refresh.refresh_a_share_research(force=True)) == "ready"
    previous = repository.read_dashboard()
    research_db.mode = "partial"
    assert asyncio.run(refresh.refresh_a_share_research(force=True)) == "partial"
    current = repository.read_dashboard()
    assert current.emotion.meta.status == "stale"
    assert current.emotion.meta.fetched_at == previous.emotion.meta.fetched_at
    assert current.emotion.data == previous.emotion.data
    stocks = {row["code"]: row for row in repository.read_stock_pool()["stocks"]}
    assert stocks["000858"]["status"] == "stale"
    assert stocks["600519"]["status"] == "ready"
    assert stocks["300750"]["change_20d"] is not None
    assert stocks["300750"]["history_source"] == "stored"
    assert stocks["300750"]["status"] == "partial"
    assert "000858" not in [
        row["code"] for row in repository.read_stock_pool()["leaders"]["today"]["up"]
    ]


def test_publication_is_atomic_and_failed_run_remains_observable(research_db, monkeypatch):
    asyncio.run(refresh.refresh_a_share_research(force=True))
    with connection() as db:
        before = [
            tuple(row)
            for row in db.execute(
                "SELECT * FROM research_a_share_dataset_snapshots ORDER BY dataset"
            )
        ]

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("injected disk failure")

    monkeypatch.setattr(repository, "write_history_points", fail)
    assert asyncio.run(refresh.refresh_a_share_research(force=True)) == "error"
    with connection() as db:
        after = [
            tuple(row)
            for row in db.execute(
                "SELECT * FROM research_a_share_dataset_snapshots ORDER BY dataset"
            )
        ]
    assert after == before
    assert repository.read_refresh_status()["status"] == "error"
    assert repository.read_dashboard().breadth.meta.status == "stale"
    assert repository.read_stock_pool()["meta"]["status"] == "stale"


def test_partial_index_refresh_preserves_prior_series_and_marks_missing_counts(
    research_db, monkeypatch
):
    asyncio.run(refresh.refresh_a_share_research(force=True))
    original = research_db.index_snapshots

    async def benchmarks_only():
        return (await original())[:4]

    monkeypatch.setattr(research_db, "index_snapshots", benchmarks_only)
    research_db.mode = "partial"
    assert asyncio.run(refresh.refresh_a_share_research(force=True)) == "partial"
    dashboard = repository.read_dashboard()
    assert len(dashboard.market_detail.data) == 8
    assert dashboard.market_detail.meta.status == "partial"
    assert "机器人" in dashboard.market_detail.meta.message
    assert dashboard.breadth.data["limitUp"] is None
    assert dashboard.breadth.data["limitDown"] is None


def test_daily_import_metadata_has_timezone_and_unmatched_turnover_is_included(research_db):
    asyncio.run(refresh.refresh_a_share_research(force=True))
    run = repository.read_refresh_status()
    repository.write_dataset(
        "crowding",
        {"history": []},
        source="historical import",
        run_id=run["runId"],
        observed_at="2026-09-04",
    )
    dashboard = repository.read_dashboard()
    assert dashboard.crowding.meta.source_timestamp.isoformat() == "2026-09-04T15:00:00+08:00"
    assert dashboard.market_history[-1].total_amount_yuan == sum(
        row.turnover_yuan for row in asyncio.run(research_db.a_share_spot())
    )


def test_full_market_turnover_history_includes_backend_day_change_and_source(research_db):
    asyncio.run(refresh.refresh_a_share_research(force=True))
    repository.start_refresh("market-turnover-history-test", None)
    repository.finish_refresh("market-turnover-history-test", "ready")
    with connection() as db:
        db.execute("DELETE FROM research_a_share_history WHERE dataset='market'")
    repository.write_history_points(
        "market-turnover-history-test",
        "market",
        [
            ("2030-01-02", "market", {"totalAmountYuan": "10000000000"}),
            ("2030-01-03", "market", {"totalAmountYuan": "11000000000"}),
        ],
        source="测试全市场行情源",
    )

    rows = repository.read_dashboard().market_history

    assert rows[-2].observed_at.isoformat() == "2030-01-02"
    assert rows[-2].source == "测试全市场行情源"
    assert rows[-2].amount_change_pct is None
    assert rows[-1].observed_at.isoformat() == "2030-01-03"
    assert rows[-1].amount_change_pct == 10


def test_market_width_normalizes_both_archive_units_without_changing_raw_evidence(research_db):
    asyncio.run(refresh.refresh_a_share_research(force=True))
    cases = [
        ("2030-01-02", 2989, 2108, 113, "0.17284677261134002", "B_001004"),
        ("2030-01-03", 2713, 2166, 137, "10.90510366826156299840510367", "platform-daily-v1"),
        ("2030-01-04", 10, 10, 50, "0", "B_001004"),
        ("2030-01-05", 0, 0, 50, "0", "platform-daily-v1"),
    ]
    for day, up, down, flat, native, definition in cases:
        assert (
            repository.write_market_archive(
                dict(
                    universe_key="sh_sz_a",
                    trade_date=day,
                    up=up,
                    down=down,
                    flat=flat,
                    market_breadth_pct=native,
                    source_name="fixture",
                    definition_version=definition,
                    payload={"native_width": native},
                )
            )
            == "inserted"
        )
    repository.start_refresh("missing-counts", "2030-01-06")
    repository.finish_refresh("missing-counts", "ready")
    repository.write_history_points(
        "missing-counts",
        "market",
        [
            ("2030-01-06", "market", {"marketBreadthPct": 99}),
        ],
        source="fixture",
    )
    rows = {row.observed_at.isoformat(): row for row in repository.read_dashboard().market_history}
    for day, up, down, flat, native, definition in cases:
        expected = Decimal(100) * (up - down) / (up + down) if up + down else None
        assert rows[day].market_breadth_pct == expected
    assert rows["2030-01-06"].market_breadth_pct is None
    with connection() as db:
        stored = db.execute(
            "SELECT trade_date,market_breadth_pct,payload_json FROM research_a_share_market_archive WHERE trade_date >= '2030-01-02' ORDER BY trade_date"
        ).fetchall()
    assert [row["market_breadth_pct"] for row in stored] == [case[4] for case in cases]
    assert [json.loads(row["payload_json"]) for row in stored] == [
        {"native_width": case[4]} for case in cases
    ]


def test_revision_replaces_daily_qualifiers_and_persists_a_zero_day(research_db, monkeypatch):
    asyncio.run(refresh.refresh_a_share_research(force=True))
    original = research_db.a_share_spot

    async def low_turnover():
        return [
            row.model_copy(update={"turnover_yuan": row.turnover_yuan / 10})
            for row in await original()
        ]

    monkeypatch.setattr(research_db, "a_share_spot", low_turnover)
    asyncio.run(refresh.refresh_a_share_research(force=True))
    history = repository.read_hot_stock_history()
    assert history["dates"] == ["2026-09-07"]
    assert history["counts"] == [0]
    assert history["rows"] == []


def test_single_flight_rejects_overlapping_refresh(research_db):
    research_db.delay = 0.01

    async def run():
        return await asyncio.gather(
            refresh.refresh_a_share_research(force=True),
            refresh.refresh_a_share_research(force=True),
        )

    assert sorted(asyncio.run(run())) == ["busy", "ready"]
    assert research_db.calls["spots"] == 1


def test_http_permissions_csrf_personal_scope_conflicts_and_reload(research_db):
    accounts = seed_demo_users(password="a-share isolated test password", prefix="delivery")
    users = {row.role: row for row in accounts}
    employees = [row for row in accounts if row.role == "employee"]
    app = create_application()

    def login(client, username):
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "http://127.0.0.1:4437"},
            json={"username": username, "password": "a-share isolated test password"},
        )
        assert response.status_code == 200, response.text
        return {"Origin": "http://127.0.0.1:4437", "X-CSRF-Token": response.json()["csrfToken"]}

    with TestClient(app) as ceo, TestClient(app) as first, TestClient(app) as second:
        admin_headers = login(ceo, users["ceo"].username)
        first_headers = login(first, employees[0].username)
        second_headers = login(second, employees[1].username)
        root = "/api/v1/research/a-share/stock-pool"
        assert (
            first.post(root + "/focus", json={"codes": ["00700"], "expectedVersion": 0}).status_code
            == 403
        )
        assert (
            first.post(
                root + "/add-batch", headers=first_headers, json={"codes": ["600000"]}
            ).status_code
            == 403
        )
        response = first.post(
            root + "/focus",
            headers=first_headers,
            json={"codes": ["00700", "600000"], "expectedVersion": 0},
        )
        assert response.status_code == 200, response.text
        assert second.get(root + "/focus").json()["data"]["codes"] == []
        assert (
            first.post(
                root + "/focus", headers=first_headers, json={"codes": [], "expectedVersion": 0}
            ).status_code
            == 409
        )
        assert (
            ceo.post(
                root + "/add-batch", headers=admin_headers, json={"codes": ["600000"]}
            ).status_code
            == 200
        )
        assert "600000" in [row["code"] for row in second.get(root).json()["data"]["stocks"]]
        assert (
            ceo.delete(
                root + "/remove", headers=admin_headers, params={"instrument_id": "600000"}
            ).status_code
            == 200
        )
        assert first.get(root + "/focus").json()["data"]["codes"] == ["00700", "600000"]
        assert first.get(root).json()["data"]["focusStocks"][-1]["code"] == "600000"
        assert (
            ceo.post(
                root + "/add-batch", headers=admin_headers, json={"codes": ["oops"]}
            ).status_code
            == 422
        )
        assert (
            first.post(
                root + "/focus", headers=first_headers, json={"codes": [], "expectedVersion": 1}
            ).status_code
            == 200
        )
        assert first.get(root + "/focus").json()["data"]["codes"] == []
        assert second.get(root + "/focus").headers["Cache-Control"] == "no-store"
        assert (
            second.post(
                root + "/focus",
                headers=second_headers,
                json={"codes": ["000858"], "expectedVersion": 0},
            ).status_code
            == 200
        )
        with TestClient(app) as member:
            member_headers = login(member, users["member"].username)
            assert member.get(root).status_code == 200
            assert member.get(root + "/focus").json()["data"]["codes"] == []
            assert (
                member.post(
                    root + "/focus",
                    headers=member_headers,
                    json={"codes": ["600519"], "expectedVersion": 0},
                ).status_code
                == 200
            )
            assert (
                member.post(
                    root + "/add-batch", headers=member_headers, json={"codes": ["600000"]}
                ).status_code
                == 403
            )


def test_live_lkg_marks_stale_without_rewriting_fetch_time(research_db, monkeypatch):
    from app.research_cache import LastKnownGoodResearchCache
    from app.research_data_schemas import AShareLiveSectorFundFlowResponse

    clock = [datetime.now(UTC)]
    cache = LastKnownGoodResearchCache[AShareLiveSectorFundFlowResponse](
        ttl=timedelta(minutes=5), is_meaningful=lambda value: bool(value.rows), now=lambda: clock[0]
    )
    monkeypatch.setattr(service, "_LIVE_SECTOR_FLOW_CACHE", cache)
    monkeypatch.setattr(service, "_PROVIDER", research_db)
    good = asyncio.run(service.get_live_a_share_sector_fund_flow())
    clock[0] += timedelta(minutes=6)
    research_db.mode = "error"
    stale = asyncio.run(service.get_live_a_share_sector_fund_flow())
    assert stale.status == "stale" and stale.is_stale
    assert stale.fetched_at == good.fetched_at
    assert stale.rows == good.rows


def test_live_turnover_uses_hot_stock_history_as_authoritative_daily_count(
    research_db, monkeypatch
):
    from app.research_cache import LastKnownGoodResearchCache
    from app.research_data_schemas import AShareMarketTurnoverResponse

    class LaggingSnapshotProvider(AShareFixtureProvider):
        async def a_share_market_turnover(self):
            return []

    repository.start_refresh("lagging-stocks-test", "2026-09-29")
    repository.start_refresh("hot-stock-authoritative-test", "2026-09-29")
    repository.write_dataset(
        "stocks",
        [
            {
                "securityCode": "300308",
                "securityName": "中际旭创",
                "turnoverYuan": "13099145541.12",
                "returnPct": "10.38",
                "industry": "通信设备",
            },
            {
                "securityCode": "300502",
                "securityName": "新易盛",
                "turnoverYuan": "10061899943.16",
                "returnPct": "8.08",
                "industry": "通信设备",
            },
        ],
        source="lagging-stocks",
        run_id="lagging-stocks-test",
        observed_at="2026-09-29",
    )
    repository.write_history_points(
        "hot-stock-authoritative-test",
        "hot_stock",
        [
            (
                "2026-09-29",
                "300308",
                {
                    "securityCode": "300308",
                    "securityName": "中际旭创",
                    "turnoverYuan": "13099145541.12",
                    "returnPct": "10.38",
                    "industry": "通信设备",
                },
            ),
            (
                "2026-09-29",
                "600487",
                {
                    "securityCode": "600487",
                    "securityName": "亨通光电",
                    "turnoverYuan": "11344313714.0",
                    "returnPct": "9.28",
                    "industry": "通信设备",
                },
            ),
            (
                "2026-09-29",
                "300502",
                {
                    "securityCode": "300502",
                    "securityName": "新易盛",
                    "turnoverYuan": "10061899943.16",
                    "returnPct": "8.08",
                    "industry": "通信设备",
                },
            ),
        ],
        source="hot-stock-history",
    )
    cache = LastKnownGoodResearchCache[AShareMarketTurnoverResponse](
        ttl=timedelta(minutes=5), is_meaningful=lambda value: True
    )
    monkeypatch.setattr(service, "_LIVE_TURNOVER_CACHE", cache)
    monkeypatch.setattr(service, "_LIVE_TURNOVER_LOCK", asyncio.Lock())
    monkeypatch.setattr(service, "_PROVIDER", LaggingSnapshotProvider())

    result = asyncio.run(service.get_live_a_share_market_turnover())

    assert result.daily_observed_at == "2026-09-29"
    assert result.high_turnover_count == 3
    assert {row.security_code for row in result.high_turnover_rows} == {
        "300308",
        "600487",
        "300502",
    }


def test_hot_history_all_dates_keeps_ninety_day_totals(research_db):
    run_id = "history-all-test"
    repository.start_refresh(run_id, None)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    points = [
        (
            (start + timedelta(days=index)).date().isoformat(),
            "600519",
            {"securityCode": "600519", "industry": "食品饮料"},
        )
        for index in range(105)
    ]
    repository.write_history_points(run_id, "hot_stock", points, source="test")
    history = repository.read_hot_stock_history(days=None, matrix_days=None)
    assert len(history["dates"]) == 105
    assert history["counts"] == [1] * 105
    assert history["industries"][0]["counts"] == [1] * 105
    assert history["industries"][0]["historyTotal"] == 90
    assert len(repository.read_hot_stock_history()["dates"]) == 10
