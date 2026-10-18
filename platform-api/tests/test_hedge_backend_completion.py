from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import research_market_detail_refresh as refresh
from app import research_overseas_refresh as overseas
from app import research_provider_commodity_dashboard as commodity
from app import research_provider_crypto_dashboard as crypto
from app import research_provider_macro_dashboard as macro
from app.auth import Principal, require_principal
from app.config import get_settings
from app.database import initialize_database
from app.research_a_share_repository import read_dataset_metadata
from app.research_market_layout_repository import read_layout, replace_layout
from app.research_provider_errors import ResearchProviderError
from app.research_provider_market_detail import (
    MarketDetailProvider,
    MarketDetailResponse,
    _change_from_period_start,
    _market_row,
)
from app.research_watchlist_repository import ResearchWatchlistConcurrentUpdateError
from app.research_watchlist_routes import router
from app.research_watchlist_schemas import ReplaceMarketLayoutRequest
from app.user_service import create_initial_ceo

pytestmark = pytest.mark.integration


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path / "hedge.db"))
    monkeypatch.setattr(get_settings(), "research_refresh_enabled", False)
    monkeypatch.setattr(refresh, "RESEARCH_DB_WRITE_LOCK", asyncio.Lock())
    monkeypatch.setattr(refresh, "_LOCK", asyncio.Lock())
    monkeypatch.setattr(refresh, "MARKET_SYMBOLS", {"us": {"us-spy": "SPY"}})
    initialize_database()


def snapshot():
    today = datetime.now(UTC).date()
    row = _market_row("us-spy", [(today.isoformat(), Decimal("123.456789"))])
    row.symbol = "SPY"
    return MarketDetailResponse(
        market_id="us",
        status="ready",
        as_of=today.isoformat(),
        retrieved_at=datetime.now(UTC),
        rows=[row],
    )


def test_market_refresh_persists_restart_read_and_failure_retains_date(db, monkeypatch):
    source = snapshot()

    async def fetch(_market):
        return source.model_copy(deep=True)

    monkeypatch.setattr(refresh._PROVIDER, "_get_live_market_detail", fetch)
    assert asyncio.run(refresh.refresh_market_details()) == {"us": "ready"}
    assert asyncio.run(refresh.refresh_market_details()) == {"us": "up_to_date"}
    provider = MarketDetailProvider(timeout_seconds=1, user_agent="test")
    result = asyncio.run(provider.get("us"))
    assert result.rows[0].close == Decimal("123.456789")
    assert result.rows[0].change_ytd is None

    async def fail(_market):
        raise ResearchProviderError("upstream_failed")

    monkeypatch.setattr(refresh._PROVIDER, "_get_live_market_detail", fail)
    assert asyncio.run(refresh.refresh_market_details(force=True)) == {"us": "stale"}
    result = asyncio.run(provider.get("us"))
    assert result.status == result.rows[0].status == "stale"
    assert result.retrieved_at == source.retrieved_at
    assert result.as_of == source.as_of
    assert result.rows[0].close == source.rows[0].close
    assert read_dataset_metadata("market_detail_us")["status"] == "stale"


def test_market_read_no_network_when_missing(db, monkeypatch):
    async def unexpected(_market):
        pytest.fail("GET must not call upstream")

    provider = MarketDetailProvider(timeout_seconds=1, user_agent="test")
    monkeypatch.setattr(provider, "_get_live_market_detail", unexpected)
    result = asyncio.run(provider.get("global"))
    assert result.status == "no_data" and result.rows == []


def test_partial_refresh_keeps_missing_symbol_stale(db, monkeypatch):
    first = snapshot()
    first.rows.append(first.rows[0].model_copy(update={"id": "us-qqq", "symbol": "QQQ"}))

    async def fetch(_market):
        return first

    monkeypatch.setattr(refresh._PROVIDER, "_get_live_market_detail", fetch)
    asyncio.run(refresh.refresh_market_details(force=True))

    async def partial(_market):
        return snapshot().model_copy(update={"status": "partial"})

    monkeypatch.setattr(refresh._PROVIDER, "_get_live_market_detail", partial)
    asyncio.run(refresh.refresh_market_details(force=True))
    result = asyncio.run(MarketDetailProvider(timeout_seconds=1, user_agent="test").get("us"))
    assert [(row.id, row.status) for row in result.rows] == [
        ("us-spy", "ready"),
        ("us-qqq", "stale"),
    ]


@pytest.mark.parametrize(
    "module,provider_class",
    [
        (macro, macro.MacroDashboardProvider),
        (commodity, commodity.CommodityDashboardProvider),
        (crypto, crypto.CryptoDashboardProvider),
    ],
)
def test_artifact_failure_marks_cached_values_stale(monkeypatch, module, provider_class):
    payload = {
        "schemaVersion": "1.0",
        "status": "ready",
        "asOf": "2026-10-01",
        "groups": {
            "test": [
                {
                    "seriesId": "test",
                    "label": "Test",
                    "status": "ready",
                    "unit": "percent",
                    "frequency": "monthly",
                    "observationDate": datetime.now(UTC).date().isoformat(),
                    "timezone": "UTC",
                    "source": "test",
                    "latestValue": "1.2345",
                    "methodologyVersion": "v1",
                }
            ]
        },
    }
    monkeypatch.setattr(module, "read_local_json", lambda _: payload)
    provider = provider_class(timeout_seconds=1, user_agent="test")
    original = asyncio.run(provider.get())

    def fail(_):
        raise ResearchProviderError("missing")

    monkeypatch.setattr(module, "read_local_json", fail)
    retained = asyncio.run(provider.get())
    assert retained.status == "stale"
    assert retained.groups["test"][0].is_stale
    assert retained.groups["test"][0].latest_value == Decimal("1.2345")
    assert original.status == "ready" and not original.groups["test"][0].is_stale


def test_short_history_does_not_invent_full_period_returns():
    points = [(date(2026, 7, 4), Decimal("10")), (date(2026, 7, 5), Decimal("12"))]
    assert _change_from_period_start(points, date(2026, 1, 1)) is None
    assert _change_from_period_start(points, date(2026, 7, 5)) == Decimal("20.0")


def test_iv_retry_is_not_skipped_when_only_term_succeeded(db, monkeypatch):
    monkeypatch.setattr(overseas, "RESEARCH_DB_WRITE_LOCK", asyncio.Lock())
    monkeypatch.setattr(overseas, "_already_refreshed_today", lambda ds: ds == "crypto_iv_term")
    monkeypatch.setattr(overseas, "fetch_deribit_iv", lambda: {"index": 1, "term": []})
    calls = []
    monkeypatch.setattr(
        overseas,
        "fetch_btc_iv_snapshot",
        lambda: (
            calls.append(True)
            or {"index": 1, "dvol": 2, "observedAt": datetime.now(UTC).isoformat(), "tenors": []}
        ),
    )
    assert asyncio.run(overseas._collect_deribit_iv(False))[0] == "ready"
    assert calls == [True]


def test_layout_persists_empty_reset_and_conflicts_without_market_values(db):
    user = create_initial_ceo(username="layout-owner", password="correct horse battery staple")
    assert read_layout(user.id, "us")["groups"] is None
    assert replace_layout(user.id, "us", [], 0)["rowVersion"] == 1
    assert read_layout(user.id, "us")["groups"] == []
    assert read_layout(user.id, "global")["groups"] is None
    assert read_layout("another-user", "us")["groups"] is None
    with pytest.raises(ResearchWatchlistConcurrentUpdateError):
        replace_layout(user.id, "us", None, 0)
    assert replace_layout(user.id, "us", None, 1)["rowVersion"] == 2
    assert read_layout(user.id, "us")["groups"] is None
    with pytest.raises(ValidationError):
        ReplaceMarketLayoutRequest.model_validate(
            {
                "expectedVersion": 0,
                "groups": [
                    {
                        "label": "test",
                        "rows": [{"id": "spy", "name": "SPY", "symbol": "SPY", "price": 99}],
                    }
                ],
            }
        )


def test_layout_routes_use_authenticated_owner_and_validate_market(db):
    user = create_initial_ceo(username="layout-api", password="correct horse battery staple")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_principal] = lambda: Principal(user.id, ("admin",), "session")
    client = TestClient(app)
    path = "/api/v1/me/research-market-layout/us"
    assert client.put(path, json={"groups": [], "expectedVersion": 0}).status_code == 200
    assert client.get(path).json()["groups"] == []
    assert client.put(path, json={"groups": [], "expectedVersion": 0}).status_code == 409
    assert client.get("/api/v1/me/research-market-layout/invalid").status_code == 422
    app.dependency_overrides[require_principal] = lambda: Principal("other", ("admin",), "session")
    assert client.get(path).json()["groups"] is None
    app.dependency_overrides[require_principal] = lambda: Principal("other", (), "session")
    assert client.get(path).status_code == 403


def test_partial_market_snapshot_has_one_source_specific_audit_check(db, monkeypatch):
    from app.data_audit import inspect_database

    source = snapshot()
    source.status = "partial"

    async def fetch(_market):
        return source.model_copy(deep=True)

    monkeypatch.setattr(refresh._PROVIDER, "_get_live_market_detail", fetch)
    asyncio.run(refresh.refresh_market_details(force=True))
    checks = [
        item
        for item in inspect_database(datetime.now(UTC))
        if item["key"] == "snapshot.market_detail_us"
    ]
    assert len(checks) == 1
    assert checks[0]["status"] == "warning"
    assert checks[0]["group"] == "市场明细"

def test_instrument_replacement_never_relabels_old_prices(db,monkeypatch):
    old=snapshot()
    old.rows[0].symbol='OLD'
    async def prior(_market):return old
    monkeypatch.setattr(refresh._PROVIDER,'_get_live_market_detail',prior)
    asyncio.run(refresh.refresh_market_details(force=True))
    async def missing(_market):return snapshot().model_copy(update={'rows':[],'status':'partial'})
    monkeypatch.setattr(refresh._PROVIDER,'_get_live_market_detail',missing)
    asyncio.run(refresh.refresh_market_details(force=True))
    result=asyncio.run(MarketDetailProvider(timeout_seconds=1,user_agent='test').get('us'))
    assert result.rows==[]
