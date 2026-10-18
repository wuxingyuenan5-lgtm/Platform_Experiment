import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from app.research_equity_metrics import (
    cn_structure,
    credit_impulse,
    distribution,
    hk_composite,
    month_shift,
    monthly_yoy,
    percentile,
    rolling_rank,
    theme_observations,
    trend,
)
from app.research_equity_sources import collect_one, parse_multpl, publish_artifact, read_artifact


def test_missing_negative_book_and_pe_are_not_zero_or_cheap():
    result = distribution(
        [
            {"pb": "0.8", "peTtm": "10"},
            {"pb": "-1", "peTtm": "-3"},
            {"pb": None},
            {"pb": "2", "peTtm": "30"},
        ]
    )
    assert result["belowBookPct"] == 50
    assert result["pbCount"] == 2
    assert result["nonpositivePbCount"] == 1
    assert result["medianPe"] == 20
    assert distribution([{}])["belowBookPct"] is None


def test_percentiles_have_minimum_and_neutral_ties():
    assert percentile([1] * 59, 1) is None
    assert percentile([1] * 60, 1) == 50
    rows = [{"date": "2020-01-01", "pe": 1000}, {"date": "2026-01-01", "pe": 10}]
    assert rolling_rank(rows, "pe", 1) == {
        "value": Decimal(50),
        "count": 1,
        "start": "2026-01-01",
        "end": "2026-01-01",
    }


def test_mixed_date_and_hk_stocks_do_not_pollute_cn_distribution():
    rows = [
        {"securityCode": "000001", "observedAt": "2026-10-15T07:01:00Z", "pb": "0.8"},
        {"securityCode": "000002", "observedAt": "2026-10-14T07:00:00Z", "pb": "0.1"},
        {
            "securityCode": "00700",
            "observedAt": "2026-10-15T08:00:00Z",
            "currency": "HKD",
            "pb": "0.1",
        },
    ]
    result, aligned = cn_structure(rows, [])
    assert len(aligned) == 1 and result["market"]["count"] == 1
    assert result["closed"] is True
    rows[0]["observedAt"] = "2026-10-15T06:59:00Z"
    assert cn_structure(rows, [])[0]["closed"] is False


def test_monthly_yoy_requires_exact_prior_month_not_previous_record():
    assert monthly_yoy({"2025-01": Decimal(100), "2026-02": Decimal(150)}) == {}
    assert monthly_yoy({"2025-02": Decimal(100), "2026-02": Decimal(150)})["2026-02"] == 50


def test_credit_pulse_uses_nominal_rolling_gdp_and_no_partial_year_flow():
    tsf = {month_shift("2021-01", i): Decimal(10) for i in range(48)}
    gdp = {f"{y}-{m:02d}": Decimal(m * 100) for y in range(2020, 2025) for m in (3, 6, 9, 12)}
    values = credit_impulse(tsf, gdp)
    assert values and set(values.values()) == {0}
    del tsf["2024-11"]
    assert "2024-12" not in credit_impulse(tsf, gdp)


def test_hk_missing_component_never_reweights_remaining_three():
    base = {month_shift("2020-01", i): Decimal(i) for i in range(60)}
    assert hk_composite({"m2": base, "ppi": base, "retail": base}, "2025-02-01")["value"] is None
    result = hk_composite(dict.fromkeys(["m2", "ppi", "retail", "credit"], base), "2025-02-01")
    assert result["value"] is not None
    assert sum(result["history"][-1]["contributions"].values()) == result["value"]
    assert all(r["weight"] == 25 for r in result["components"])


def test_theme_cross_membership_is_explicit_and_old_quotes_excluded():
    result = theme_observations(
        "us",
        {"MSFT": {"name": "Microsoft", "date": "2026-10-14", "status": "ready", "returnPct": 3}},
        "2026-10-15",
    )
    assert all(t["covered"] == 0 for t in result["items"])
    msft = [r for t in result["items"] for r in t["members"] if r["code"] == "MSFT"]
    assert all(r["themeCount"] == 2 for r in msft)


def test_trend_minimum_and_null_values():
    assert trend([{"date": "2026-01-01", "value": 10}])["above200"] is None
    assert trend([{"date": "2026-01-01", "value": None}])["count"] == 0


def test_multpl_estimates_are_retained_and_marked():
    rows = parse_multpl(
        '<table id="datatable"><tr><td>Oct 14, 2026</td><td><abbr>†</abbr>26.34</td></tr></table>'
    )
    assert rows == [{"date": "2026-10-14", "pe": Decimal("26.34"), "estimated": True}]


def test_pbc_months_units_and_blank_future_cells():
    import io

    import pandas as pd
    import pytest

    from app.research_equity_sources import parse_pbc_tsf

    def workbook(unit):
        buf = io.BytesIO()
        pd.DataFrame(
            [
                ["社会融资规模增量统计表", None],
                [unit, None],
                [2025.01, 100],
                [2025.1, -20],
                [2025.11, None],
            ]
        ).to_excel(buf, header=False, index=False)
        return buf.getvalue()

    assert parse_pbc_tsf(workbook("单位：亿元人民币")) == [
        {"date": "2025-01", "value": Decimal(100)},
        {"date": "2025-10", "value": Decimal(-20)},
    ]
    with pytest.raises(ValueError, match="schema"):
        parse_pbc_tsf(workbook("单位：万亿元人民币"))


def test_monthly_freshness_uses_period_end():
    from app.research_equity_observatory import source_state

    doc = {"status": "ready", "observationDate": "2026-06"}
    assert source_state(doc, "2026-10-16", True) == "ready"
    assert source_state(doc, "2026-10-20", True) == "stale"


def test_pbc_discovery_archives_documents_and_preserves_row_provenance(tmp_path, monkeypatch):
    import io

    import pandas as pd

    from app.research_equity_sources import PBC_URL

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    buf = io.BytesIO()
    pd.DataFrame(
        [["社会融资规模增量统计表", None], ["单位：亿元人民币", None], [2025.01, 100]]
    ).to_excel(buf, header=False, index=False)
    paths = []

    def respond(request):
        paths.append(request.url.path)
        content = {
            "/diaochatongjisi/116219/index.html": (
                f'<a href="/year">{datetime.now(UTC).year}年统计数据</a>'.encode()
            ),
            "/year": '<a href="/flow">社会融资规模</a>'.encode(),
            "/flow": b'<a href="/flow.xlsx">xls</a>',
            "/flow.xlsx": buf.getvalue(),
        }[request.url.path]
        return httpx.Response(200, content=content)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await collect_one(
                client,
                {"id": "cn_tsf_pbc", "name": "PBC", "url": PBC_URL, "kind": "pbc_tsf"},
                force=True,
            )

    result = asyncio.run(run())
    assert result["status"] == "ready" and len(paths) == 4
    assert len(result["rawDocuments"]) == 4
    assert result["rows"][0]["sourceUrl"] == "https://www.pbc.gov.cn/flow.xlsx"
    assert result["acquisitionMethod"] == "http"


def test_csi_history_preserves_precision_and_updates_incrementally(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    queries = []

    def respond(request):
        queries.append(dict(request.url.params))
        return httpx.Response(
            200,
            content=b'{"success":true,"data":[{"indexCode":"000300","tradeDate":"20250102","peg":12.12345678,"close":4000}]}',
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            spec = {
                "id": "test",
                "name": "CSI",
                "url": "https://example.org",
                "kind": "csi_history",
                "code": "000300",
            }
            await collect_one(client, spec, force=True)
            return await collect_one(client, spec, force=True)

    result = asyncio.run(run())
    assert result["status"] == "ready" and len(result["rows"]) == 1
    assert str(result["rows"][0]["pe"]) == "12.12345678"
    assert queries[-1]["startDate"] == "20241226"


def test_csi_history_keeps_separate_valuation_samples():
    from app.research_equity_observatory import valuations

    result = valuations(
        {
            "csi_history_000300": {"rows": [{"date": "2026-10-15", "pe": "12.87"}]},
            "csi_000300": {"rows": [{"date": "2026-10-15", "pe": "14.16"}]},
        },
        "cn",
        "2026-10-16",
    )
    rows = {r["id"]: r for r in result}
    assert rows["csi_history_000300"]["pe"] == "12.87"
    assert rows["csi_000300"]["pe"] == "14.16"
    assert rows["csi_history_000300"]["peRank"]["count"] == 1


def test_official_tsf_revision_wins_without_mutating_archived_history(monkeypatch):
    from app import research_equity_observatory as module

    received = {}

    def capture(tsf, gdp):
        received.update(tsf)
        return {}

    monkeypatch.setattr(module, "credit_impulse", capture)
    history = {"rows": [{"date": "2026-04", "value": "6245"}]}
    official = {
        "rows": [{"date": "2026-04", "value": "6238"}, {"date": "2026-09", "value": "35476"}]
    }
    module.build_hk("2026-10-16", {"cn_tsf": history, "cn_tsf_pbc": official})
    assert received == {"2026-04": Decimal(6238), "2026-09": Decimal(35476)}
    assert history["rows"][0]["value"] == "6245"


def test_failed_collection_retains_source_date_and_last_success(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    old = {
        "rows": [{"date": "2026-01", "value": "1"}],
        "observationDate": "2026-01",
        "fetchedAt": "2026-02-01T00:00:00+00:00",
        "status": "ready",
    }
    publish_artifact("sources/test", old)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(503))
        ) as client:
            return await collect_one(
                client, {"id": "test", "name": "test", "url": "https://example.org"}, force=True
            )

    result = asyncio.run(run())
    assert result["status"] == "stale"
    assert result["rows"] == old["rows"] and result["fetchedAt"] == old["fetchedAt"]
    assert read_artifact("sources/test")["observationDate"] == "2026-01"


def test_collection_idempotence_and_annual_hkma_rows_excluded(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    payload = {
        "header": {"success": True},
        "result": {
            "records": [
                {"end_of_month": "2025-00", "m2_total": 20},
                {"end_of_month": "2025-12", "m2_total": 20},
            ]
        },
    }

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ) as client:
            spec = {"id": "test", "name": "test", "url": "https://example.org", "kind": "hkma"}
            await collect_one(client, spec, force=True)
            return await collect_one(client, spec, force=True)

    result = asyncio.run(run())
    assert len(result["rows"]) == 1 and result["rows"][0]["date"] == "2025-12"
    assert len(list(tmp_path.rglob("*.bin"))) == 1


def test_reader_never_fetches_and_detects_producer_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    from app.research_equity_observatory import read_equity_observatory

    publish_artifact(
        "cn", {"market": "cn", "status": "ready", "generatedAt": datetime.now(UTC).isoformat()}
    )
    publish_artifact("health", {"markets": {"cn": {"status": "error"}}})
    assert read_equity_observatory("cn")["status"] == "stale"
    assert read_equity_observatory("us")["status"] == "no_data"


def test_source_regression_retains_last_success(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    old = {
        "rows": [{"date": "2026-06", "value": "2"}],
        "observationDate": "2026-06",
        "fetchedAt": "2026-07-01T00:00:00+00:00",
    }
    publish_artifact("sources/test", old)
    payload = {
        "header": {"success": True},
        "result": {"records": [{"end_of_month": "2026-05", "m2_total": 1}]},
    }

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ) as client:
            return await collect_one(
                client,
                {"id": "test", "name": "test", "url": "https://example.org", "kind": "hkma"},
                force=True,
            )

    result = asyncio.run(run())
    assert result["status"] == "stale"
    assert result["rows"] == old["rows"]
    assert result["fetchedAt"] == old["fetchedAt"]


def test_projection_failure_keeps_other_market_and_last_good(tmp_path, monkeypatch):
    from app import research_equity_observatory as module

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    old = {"market": "cn", "status": "ready", "date": "2026-01-01"}
    publish_artifact("cn", old)

    def broken(*args):
        raise ValueError("bad source")

    monkeypatch.setattr(module, "build_cn", broken)
    monkeypatch.setattr(module, "build_us", lambda *_: {"market": "us", "status": "ready"})
    result = module.produce_local({})
    assert result["cn"]["status"] == "error" and result["us"]["status"] == "ready"
    assert read_artifact("cn") == old


def test_missing_industry_amount_stays_null():
    rows = [{"securityCode": "000001", "observedAt": "2026-01-01T07:00:00Z"}]
    memberships = [{"securityCode": "000001", "swL1Code": "a", "swL1Name": "a"}]
    assert cn_structure(rows, memberships)[0]["industries"][0]["amountSharePct"] is None


def test_reader_handle_is_closed_before_atomic_publication(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from app import research_equity_sources as module

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    publish_artifact("test", {"value": Decimal("1.2300")})
    original = module.read_local_json
    opened, release = Event(), Event()

    def holding_reader(path):
        opened.set()
        assert release.wait(3)
        return original(path)

    monkeypatch.setattr(module, "read_local_json", holding_reader)
    with ThreadPoolExecutor(max_workers=2) as pool:
        read = pool.submit(read_artifact, "test")
        assert opened.wait(3)
        write = pool.submit(publish_artifact, "test", {"value": Decimal("2.3400")})
        try:
            assert not write.done()
        finally:
            release.set()
        assert read.result()["value"] == "1.2300"
        write.result()
    assert read_artifact("test")["value"] == "2.3400"


def test_persistent_publication_failure_is_not_silently_accepted(monkeypatch):
    import pytest

    from app import research_equity_sources as module

    calls = []

    def denied(*args):
        calls.append(1)
        raise PermissionError("access denied")

    monkeypatch.setattr(module, "write_local_json", denied)
    with pytest.raises(PermissionError):
        publish_artifact("test", {"value": 1})
    assert len(calls) == 1


def test_hk_composite_keeps_value_but_marks_failed_dependency_stale(monkeypatch):
    from app import research_equity_observatory as module

    monkeypatch.setattr(
        module,
        "hk_composite",
        lambda *_: {
            "status": "ready",
            "value": Decimal("1"),
            "components": [{"id": k} for k in ("m2", "ppi", "retail", "credit")],
        },
    )
    sources = {
        k: {"status": "ready", "observationDate": "2026-08"}
        for k in ("hk_m2", "cn_ppi", "cn_retail", "cn_tsf", "cn_gdp")
    }
    sources["cn_gdp"]["status"] = "stale"
    result = module.build_hk("2026-10-15", sources)
    assert result["value"] == 1 and result["status"] == "stale"
    assert result["components"][-1]["status"] == "stale"


def test_hkma_all_currency_table_year_carry_and_precision(monkeypatch):
    import pandas as pd

    from app.research_equity_sources import parse_hkma_money

    frame = pd.DataFrame([[None] * 15 for _ in range(23)])
    frame.iloc[3, 0] = "Table 2.3.3 : All currencies"
    frame.iloc[12, 11] = "M2"
    frame.iloc[21, 0] = 2026
    frame.iloc[21, 2] = "7月"
    frame.iloc[21, 11] = 21876782.192
    frame.iloc[22, 2] = "8月"
    frame.iloc[22, 11] = 22174394.152999997
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: frame)
    assert parse_hkma_money(b"xls") == [
        {"date": "2026-07", "value": Decimal("21876782.192")},
        {"date": "2026-08", "value": Decimal("22174394.153")},
    ]


def test_monthly_estimate_updates_do_not_inflate_sample_count(tmp_path, monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    publish_artifact(
        "sources/test",
        {
            "rows": [{"date": "2026-09-14", "pe": "20", "estimated": True}],
            "observationDate": "2026-09-14",
        },
    )
    body = '<table id="datatable"><tr><td>Sep 15, 2026</td><td>†21</td></tr></table>'

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body))
        ) as client:
            return await collect_one(
                client,
                {"id": "test", "name": "test", "url": "https://example.org", "kind": "multpl"},
                force=True,
            )

    result = asyncio.run(run())
    assert len(result["rows"]) == 1
    assert result["rows"][0]["date"] == "2026-09-15"
    assert result["rows"][0]["pe"] == 21


def test_decoder_failure_keeps_last_success(tmp_path, monkeypatch):
    from app import research_equity_sources as module

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    old = {
        "rows": [{"date": "2026-01-01", "value": "100"}],
        "observationDate": "2026-01-01",
        "fetchedAt": "2026-01-02T00:00:00+00:00",
    }
    publish_artifact("sources/test", old)

    def broken(*args):
        raise RuntimeError("decoder library error")

    monkeypatch.setattr(module, "parse_sina_hk", broken)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text="bad data"))
        ) as client:
            return await collect_one(
                client,
                {"id": "test", "name": "test", "url": "https://example.org", "kind": "sina_hk"},
                force=True,
            )

    result = asyncio.run(run())
    assert result["status"] == "stale"
    assert result["rows"] == old["rows"] and result["fetchedAt"] == old["fetchedAt"]


def test_equity_route_authentication_and_market_validation(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.auth import Principal, require_principal
    from app.research_routes import router

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    url = "/api/v1/research/equity-observatory/cn"
    assert client.get(url).status_code == 401
    app.dependency_overrides[require_principal] = lambda: Principal("test", ("admin",), "session")
    response = client.get(url)
    assert response.status_code == 200 and response.json()["status"] == "no_data"
    assert response.headers["cache-control"] == "no-store"
    assert client.get(url.replace("/cn", "/invalid")).status_code == 422
    app.dependency_overrides[require_principal] = lambda: Principal("test", (), "session")
    assert client.get(url).status_code == 403
