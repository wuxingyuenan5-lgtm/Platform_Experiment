from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread

import pytest

from app import financial_fact_repository as repository
from app import financial_facts, financial_projection_service as service
from app.database import connection, initialize_database
from app.financial_fact_schemas import CreateFinancialFactRequest

STRATEGY = "strategy_funding_arbitrage_instance_default"
ACCOUNT = "account_sim_usdt"
INSTRUMENT = "instrument_btc_usdt"


def record(key, amount, instrument=INSTRUMENT):
    return financial_facts.record_financial_fact(CreateFinancialFactRequest.model_validate({
        "idempotencyKey": key, "externalId": key, "factType": "funding",
        "source": "isolated-test", "strategyInstanceId": STRATEGY,
        "accountId": ACCOUNT, "instrumentId": instrument,
        "occurredAt": "2026-10-01T00:00:00+00:00", "amount": amount, "currency": "USDT",
    }))


@pytest.mark.parametrize("whole_strategy", [False, True])
def test_fact_append_cannot_overtake_inflight_projection(monkeypatch, whole_strategy):
    initialize_database()
    record("first", "5")
    read, release, writer_started, writer_done = Event(), Event(), Event(), Event()
    original = repository.list_projection_fact_rows

    def paused_read(*args, **kwargs):
        rows = original(*args, **kwargs)
        if current_thread().name.startswith("old-projection"):
            read.set()
            assert release.wait(5)
        return rows

    def append():
        writer_started.set()
        record("second", "7")
        writer_done.set()

    monkeypatch.setattr(repository, "list_projection_fact_rows", paused_read)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="old-projection") as old_pool:
        with ThreadPoolExecutor(max_workers=1) as writers:
            if whole_strategy:
                old = old_pool.submit(service.rebuild_strategy_financials, STRATEGY)
            else:
                old = old_pool.submit(
                    service.rebuild_account_instrument_projection, STRATEGY, ACCOUNT, INSTRUMENT,
                )
            try:
                assert read.wait(3)
                newer = writers.submit(append)
                assert writer_started.wait(3)
                assert not writer_done.wait(0.2), "Fact writer bypassed projection transaction"
            finally:
                release.set()
            old.result(timeout=5)
            newer.result(timeout=5)
    row = repository.list_formal_pnl(STRATEGY)[0]
    assert str(row.total_pnl) == "12"
    assert row.fact_count == 2
    assert row.data_quality_state == "complete"


@pytest.mark.parametrize("failure_at", ["first", "second", "audit"])
def test_failed_strategy_rebuild_preserves_all_prior_projections(monkeypatch, failure_at):
    initialize_database()
    record("first", "5")
    record("second", "7", "instrument_btc_usdt_perp")
    before = repository.list_formal_pnl(STRATEGY)
    original = service._rebuild_account_instrument_projection
    calls = 0

    def fail_pair(*args):
        nonlocal calls
        calls += 1
        if calls == {"first": 1, "second": 2}.get(failure_at):
            raise RuntimeError("injected projection failure")
        original(*args)

    def fail_audit(**kwargs):
        raise RuntimeError("injected projection failure")

    monkeypatch.setattr(service, "_rebuild_account_instrument_projection", fail_pair)
    if failure_at == "audit":
        monkeypatch.setattr(repository, "record_projection_rebuild_audit", fail_audit)
    with pytest.raises(RuntimeError, match="injected projection failure"):
        service.rebuild_strategy_financials(STRATEGY)
    assert repository.list_formal_pnl(STRATEGY) == before
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM financial_facts").fetchone()[0] == 2
        assert db.execute(
            "SELECT COUNT(*) FROM audit_events WHERE event_type=?",
            ("formal_financial_projection_rebuilt",),
        ).fetchone()[0] == 0
