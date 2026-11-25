from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import strategy_financial_readmodel
from app.config import get_settings
from app.database import connection, initialize_database
from tests.test_strategy_financial_readmodel import ACCOUNT, FUNDING, NOW, fill, order

OTHER_ACCOUNT = "account_crypto_test"


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    get_settings().database_path = str(tmp_path / "currency-scoped-rates.db")
    initialize_database()


@pytest.fixture
def candidate():
    return strategy_financial_readmodel


def capture_rate_reads(monkeypatch, module):
    reads: list[str] = []
    original = module.connection

    @contextmanager
    def traced_connection():
        with original() as db:
            db.set_trace_callback(
                lambda sql: reads.append(sql)
                if sql.lstrip().upper().startswith("SELECT")
                and "account_valuation_rates" in sql
                else None
            )
            yield db

    monkeypatch.setattr(module, "connection", traced_connection)
    return reads


def insert_rates(rows):
    with connection() as db:
        db.executemany(
            "INSERT INTO account_valuation_rates(account_id,currency,as_of,usd_rate) "
            "VALUES (?,?,?,?)",
            rows,
        )


def test_only_requested_account_and_currency_rates_are_loaded(monkeypatch, candidate):
    order("scoped", FUNDING, "buy", "1", "2000")
    fill("scoped-fill", "scoped", "1", "2000", "1", "USD")
    insert_rates(
        [
            (ACCOUNT, "USD", NOW, "1"),
            (ACCOUNT, "USDT", NOW, "0.5"),
            (ACCOUNT, "BTC", NOW, "60000"),
            (OTHER_ACCOUNT, "USD", NOW, "1"),
        ]
    )

    reads = capture_rate_reads(monkeypatch, candidate)
    result = candidate.get_strategy_financials(FUNDING)

    assert Decimal(result["fees"]) == Decimal("2")
    rate_sql = "\n".join(reads)
    assert "BTC" not in rate_sql
    assert OTHER_ACCOUNT not in rate_sql
    assert any("usd_rate" in sql.lower() and ACCOUNT in sql for sql in reads)


def test_same_currency_does_not_query_rates(monkeypatch, candidate):
    order("same-only", FUNDING, "buy", "1", "2000")
    fill("same-only-fill", "same-only", "1", "2000", "0.20", "USDT")
    insert_rates([(ACCOUNT, "BTC", NOW, "60000"), (OTHER_ACCOUNT, "USD", NOW, "1")])

    reads = capture_rate_reads(monkeypatch, candidate)
    result = candidate.get_strategy_financials(FUNDING)

    assert result["fees"] == "0.20"
    assert reads == []


def test_mixed_case_currency_variants_preserve_uppercase_matching(monkeypatch, candidate):
    order("mixed-case", FUNDING, "buy", "1", "2000")
    fill("mixed-case-fill", "mixed-case", "1", "2000", "1", "uSd")
    insert_rates([(ACCOUNT, "usd", NOW, "1"), (ACCOUNT, "UsDt", NOW, "0.5")])

    capture_rate_reads(monkeypatch, candidate)
    result = candidate.get_strategy_financials(FUNDING)

    assert Decimal(result["fees"]) == Decimal("2")


@pytest.mark.parametrize("offset", [-301, -300, 300, 301])
def test_three_hundred_second_boundary_is_unchanged(candidate, offset):
    order(f"boundary-{offset}", FUNDING, "buy", "1", "2000")
    fill(f"boundary-fill-{offset}", f"boundary-{offset}", "1", "2000", "1", "USD")
    observed = (datetime.fromisoformat(NOW) + timedelta(seconds=offset)).isoformat()
    insert_rates([(ACCOUNT, "USD", observed, "1"), (ACCOUNT, "USDT", observed, "0.5")])

    result = candidate.get_strategy_financials(FUNDING)
    if abs(offset) <= 300:
        assert Decimal(result["fees"]) == Decimal("2")
        assert "historical_fx_unavailable" not in result["issues"]
    else:
        assert result["fees"] is None
        assert "historical_fx_unavailable" in result["issues"]


def test_negative_rate_is_rejected(candidate):
    order("negative-rate", FUNDING, "buy", "1", "2000")
    fill("negative-rate-fill", "negative-rate", "1", "2000", "1", "USD")
    insert_rates([(ACCOUNT, "USD", NOW, "-1"), (ACCOUNT, "USDT", NOW, "0.5")])

    result = candidate.get_strategy_financials(FUNDING)
    assert result["fees"] is None
    assert "historical_fx_unavailable" in result["issues"]


def test_missing_base_rate_is_rejected(candidate):
    order("missing-base", FUNDING, "buy", "1", "2000")
    fill("missing-base-fill", "missing-base", "1", "2000", "1", "USD")
    insert_rates([(ACCOUNT, "USD", NOW, "1")])

    result = candidate.get_strategy_financials(FUNDING)
    assert result["fees"] is None
    assert "historical_fx_unavailable" in result["issues"]
