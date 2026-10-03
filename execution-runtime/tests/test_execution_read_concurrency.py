from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import Mock

import pytest

from app.bybit_mt5_gateway import BybitMt5Gateway
from app.config import Settings


def gateway():
    return BybitMt5Gateway(Settings(), bybit=Mock(), mt5=Mock())


def test_same_read_coalesces_but_different_accounts_do_not_block():
    reader = gateway()
    start = Barrier(6, timeout=2)
    loader = Mock(return_value={"sourceAsOf": "original", "bid": "1.0000000001"})

    def read(_):
        start.wait()
        return reader._cached_execution_read(("quote", "a", "BTC", "spot"), 1, loader)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(read, range(6)))
    assert loader.call_count == 1
    assert all(item is results[0] for item in results)
    assert results[0]["sourceAsOf"] == "original"

    independent = Barrier(2, timeout=2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(reader._cached_execution_read, ("quote", account, "ETH"), 1,
                            lambda: independent.wait()) for account in ("a", "b")]
        assert sorted(job.result() for job in jobs) == [0, 1]


def test_failed_read_is_not_cached_and_expiry_reloads(monkeypatch):
    reader = gateway()
    loader = Mock(side_effect=[RuntimeError("unavailable"), "first", "second"])
    clock = [10.0]
    monkeypatch.setattr("app.bybit_mt5_gateway.monotonic", lambda: clock[0])
    key = ("quote", "a", "BTC", "spot")
    with pytest.raises(RuntimeError, match="unavailable"):
        reader._cached_execution_read(key, 1, loader)
    assert reader._cached_execution_read(key, 1, loader) == "first"
    clock[0] = 11.01
    assert reader._cached_execution_read(key, 1, loader) == "second"
    assert not reader._execution_reads


def test_leverage_change_cannot_repopulate_old_margin_cache():
    reader = gateway()
    entered, release = Event(), Event()
    key = ("margin", "a", "BTC", "buy", "1", "100")

    def old_margin():
        entered.set()
        assert release.wait(2)
        return "old"

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(reader._cached_execution_read, key, 15, old_margin)
        assert entered.wait(2)
        reader.set_bybit_leverage(account_id="a", symbol="BTC", leverage=10)
        assert reader._cached_execution_read(key, 15, lambda: "new") == "new"
        release.set()
        assert pending.result() == "old"
    assert reader._cached_execution_read(key, 15, lambda: pytest.fail("lost new cache")) == "new"
