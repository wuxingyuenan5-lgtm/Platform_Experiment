import copy
from decimal import Decimal

import pytest

from app.research_ai_financials import build_company, duration_values, trailing
from app.research_ai_sources import financial_checks, operating_kpis, reported_cds


def fact(start, end, value, filed="2026-10-01"):
    return {"start": start, "end": end, "val": value, "filed": filed, "form": "10-Q", "accn": "a"}


def facts(rows, tag="Revenues"):
    return {"us-gaap": {tag: {"units": {"USD": rows}}}}


def test_quarter_ytd_difference_q4_and_negative_cash_flow():
    rows = [
        fact("2025-01-01", "2025-03-31", 100),
        fact("2025-01-01", "2025-06-30", 180),
        fact("2025-01-01", "2025-09-30", 170),
        fact("2025-01-01", "2025-12-31", 240),
    ]
    q, a = duration_values(facts(rows), ["Revenues"], "2026-11-02")
    assert [p["value"] for p in q.values()] == [80, -10, 70, 100]
    assert q["2025-09-30"]["start"] == "2025-07-01"
    assert q["2025-12-31"]["source"]["baseEnd"] == "2025-09-30"
    assert a[("2025-01-01", "2025-12-31")]["value"] == 240


def test_direct_quarter_wins_latest_amendment_and_future_filing_excluded():
    rows = [
        fact("2025-01-01", "2025-03-31", 100),
        fact("2025-01-01", "2025-06-30", 180),
        fact("2025-04-01", "2025-06-30", 81),
        fact("2025-04-01", "2025-06-30", 82, "2026-10-02"),
        fact("2025-04-01", "2025-06-30", 999, "2026-12-01"),
    ]
    q, _ = duration_values(facts(rows), ["Revenues"], "2026-11-02")
    assert q["2025-06-30"]["value"] == 82
    assert q["2025-06-30"]["source"]["basis"] == "reported"


def test_ttm_requires_contiguous_periods_and_complete_metric():
    periods = [
        ("2025-01-01", "2025-03-31"),
        ("2025-04-01", "2025-06-30"),
        ("2025-07-01", "2025-09-30"),
        ("2025-10-01", "2025-12-31"),
    ]
    rows = [
        {
            "start": a,
            "end": b,
            "values": {
                "revenue": Decimal(100),
                "cfo": Decimal(20),
                "capex": None if i == 0 else Decimal(30),
            },
        }
        for i, (a, b) in enumerate(periods)
    ]
    result = trailing(rows, 3)
    assert result["values"]["revenue"] == 400
    assert result["values"]["capex"] is None and result["values"]["fcf"] is None
    rows[2]["start"] = "2025-07-02"
    assert trailing(rows, 3) is None


def test_company_rejects_identity_and_contract_revenue_subset():
    f = facts([fact("2025-01-01", "2025-03-31", 100)])
    f["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"] = {
        "units": {"USD": [fact("2025-01-01", "2025-03-31", 80)]}
    }
    doc = {"cik": "123", "entityName": "CONSTELLATION ENERGY", "facts": f}
    c = build_company(doc, ("CEG", 123, "Constellation", "Power", "CONSTELLATION"), "2026-11-02")
    assert c["latest"]["values"]["revenue"] == 100
    with pytest.raises(ValueError):
        build_company(doc, ("BAD", 124, "x", "x", "x"))


def table(label="Annual Recurring Revenue", value="5.84B"):
    return (
        "<p>USD in millions</p><table><thead><tr><th>Fiscal Quarter</th><th>Q2 2027</th></tr>"
        "<tr><th>Period Ending</th><th>Jul 31, 2026</th></tr></thead><tbody>"
        f"<tr><td>{label}</td><td>{value}</td></tr></tbody></table>"
    )


def test_kpis_preserve_arr_vs_growth_units_and_display_precision():
    rows = operating_kpis(table() + table("Azure Revenue Growth", "48.0%"), "https://source")
    assert rows[0]["kind"] == "ARR" and rows[0]["latest"]["value"] == Decimal("5840000000")
    assert rows[1]["unit"] == "percent" and rows[1]["latest"]["value"] == 48
    assert operating_kpis(table(value="—"), "x") == []


def test_customer_arr_threshold_is_a_count_and_cloud_profit_is_currency():
    rows = operating_kpis(
        table("Customers with Annualized Revenue Run-Rate (ARR) > 100K", "4,720")
        + table("AWS Operating Income", "17.77B")
        + table("Total Customers (>1M Product Revenue)", "828"),
        "x",
    )
    assert rows[0]["unit"] == "count" and rows[0]["kind"] != "ARR"
    assert rows[1]["unit"] == "USD"
    assert rows[2]["unit"] == "count"


def test_secondary_checks_units_and_material_difference():
    company = {"annual": [{"end": "2026-07-31", "values": {"capex": Decimal(5000000)}}]}
    html = table("Capital Expenditures", "-6").replace("Q2 2027", "FY 2026")
    result = financial_checks(company, html, "x", "cash")[0]
    assert result["secondary"] == 6000000 and result["differencePct"] == 20
    assert result["status"] == "difference"
    with pytest.raises(ValueError):
        financial_checks(company, html.replace("USD in millions", ""), "x", "cash")


def cds_document():
    return {
        "meta": {
            "ticker": "ORCL",
            "units": "basis points",
            "field_coverage": {"reported_bp": {"observations": 1, "as_of": "2026-10-30"}},
        },
        "rows": [
            {"date": "2026-10-29", "reported_bp": None, "model_upper_bp": 200, "reported_n": 0},
            {"date": "2026-10-30", "reported_bp": 293, "model_lower_bp": 100, "reported_n": 2},
        ],
    }


def test_cds_excludes_model_and_rejects_coverage_disagreement():
    doc = cds_document()
    result = reported_cds(doc, "ORCL")
    assert len(result["history"]) == 1 and result["latest"]["value"] == 293
    bad = copy.deepcopy(doc)
    bad["meta"]["field_coverage"]["reported_bp"]["observations"] = 2
    with pytest.raises(ValueError):
        reported_cds(bad, "ORCL")
    doc["rows"][-1]["reported_n"] = 0
    with pytest.raises(ValueError):
        reported_cds(doc, "ORCL")


def test_ai_routes_are_read_only_and_validate_ticker(monkeypatch, tmp_path):
    from app import research_ai
    from app.research_equity_sources import publish_artifact

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    publish_artifact("ai/summary", {"companies": [], "status": "ready"})
    monkeypatch.setattr(
        research_ai.httpx, "Client", lambda **kwargs: pytest.fail("GET must not fetch upstream")
    )
    assert research_ai.read_ai()["status"] == "ready"
    assert research_ai.read_ai("MSFT")["status"] == "no_data"
    with pytest.raises(ValueError):
        research_ai.read_ai("../../bad")


def test_endpoint_permission_and_local_contract(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.auth import Principal, require_principal
    from app.research_routes import router

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    url = "/api/v1/research/equity/ai"
    assert client.get(url).status_code == 401
    app.dependency_overrides[require_principal] = lambda: Principal("test", ("admin",), "session")
    assert client.get(url).status_code == 200
    assert client.get(url + "/MSFT").headers["cache-control"] == "no-store"
    assert client.get(url + "/INVALID").status_code == 422
    app.dependency_overrides[require_principal] = lambda: Principal("test", (), "session")
    assert client.get(url).status_code == 403


def test_failed_sources_preserve_history_and_do_not_zero_other_companies(monkeypatch, tmp_path):
    import httpx

    from app import research_ai as ai
    from app.research_equity_sources import publish_artifact

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    companies = ai.COMPANIES[:4]
    monkeypatch.setattr(ai, "COMPANIES", companies)
    for spec in companies:
        row = {
            "start": "2026-07-01",
            "end": "2026-09-30",
            "values": {"capex": "10", "cfo": "8", "revenue": "20"},
        }
        company = {
            "ticker": spec[0],
            "name": spec[2],
            "sector": spec[3],
            "status": "ready",
            "periodEnd": row["end"],
            "latest": row,
            "quarters": [row],
            "annual": [],
            "methodology": "sec-us-gaap-usd-latest-vintage-v2",
        }
        publish_artifact("ai/" + spec[0], company)
        publish_artifact("ai/cache/sec-" + spec[0], {"data": company})
    real_client = httpx.Client
    monkeypatch.setattr(
        ai.httpx,
        "Client",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(lambda request: httpx.Response(503))
        ),
    )
    assert ai.refresh(force=True) == "partial"
    result = ai.read_ai()
    assert len(result["companies"]) == 4
    assert all(c["status"] == "stale" for c in result["companies"])
    assert result["capexHistory"][-1]["capex"] == "40"
    assert result["capexHistory"][-1]["fcf"] == "-8"
    assert ai.read_ai("MSFT")["quarters"][0]["values"]["capex"] == "10"
