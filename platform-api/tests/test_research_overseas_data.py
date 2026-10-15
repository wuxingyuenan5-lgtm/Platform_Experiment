"""海外公开研究数据（CME FedWatch / FRED / Farside UK / Deribit）定向测试。

覆盖范围：
1. 网络层安全：默认校验 TLS、无 verify=False/硬编码代理/浏览器伪装。
2. 刷新调度：_overseas_refresh_due 的时间窗与 _already_refreshed_today 的幂等判断。
3. 失败保留：刷新失败不丢既有数据，且明确暴露 stale/error 而非伪造数据。
4. 持久化读取：write/read 往返、最新观测日、健康状态判定。
5. 路由边界：tenor 正则、days 上下界、权限依赖。

**全部测试 mock 外部网络**：conftest 的 isolated_test_network 会拦截任何非
loopback 连接；此外本文件显式 patch 掉 provider 的 HTTP 客户端，绝不真实访问
CME / FRED / farside / Deribit。
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime, timedelta

import pytest

import app.research_overseas_refresh as refresh
import app.research_overseas_repository as repository
import app.research_provider_overseas as provider
from app.config import get_settings
from app.database import connection, initialize_database


@pytest.fixture
def overseas_db(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """每个测试独立的 SQLite，且默认关闭后台调度。"""
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "overseas.db"))
    monkeypatch.setattr(settings, "research_refresh_enabled", False)
    # Each asyncio.run owns a new loop; production's shared write lock is loop-bound.
    monkeypatch.setattr(refresh, "RESEARCH_DB_WRITE_LOCK", asyncio.Lock())
    initialize_database()
    return tmp_path


@pytest.fixture
def seed_run():
    """历史表的 refresh_run_id 外键指向刷新运行表，写数据前必须先建运行记录。"""
    from app.research_a_share_repository import finish_refresh, start_refresh

    def _seed(run_id: str, status: str = "ready") -> str:
        start_refresh(run_id, None)
        finish_refresh(run_id, status)
        return run_id

    return _seed


# ---------------------------------------------------------------------------
# 1. 网络层安全
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_provider_never_disables_tls_verification_or_hardcodes_a_proxy() -> None:
    """数据源 provider 不得关闭 TLS 校验、硬编码本机代理或伪装浏览器指纹。"""
    source = inspect.getsource(provider)

    assert "verify=False" not in source.replace("不传 ``verify=False``", "")
    assert "7890" not in source
    assert "impersonate" not in source
    assert "curl_cffi" not in source
    # 必须使用项目已声明的安全客户端与系统信任库
    assert "truststore" in source
    assert "httpx" in source


@pytest.mark.unit
def test_provider_declares_its_http_client_as_a_direct_dependency() -> None:
    """provider 使用的 HTTP 客户端必须是项目声明的直接依赖。"""
    import pathlib

    pyproject = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
    declared = pyproject.read_text(encoding="utf-8")

    assert "httpx>=" in declared
    assert "truststore>=" in declared
    # 被替换掉的旧客户端不应再出现在 provider 里
    assert "curl_cffi" not in inspect.getsource(provider)


@pytest.mark.unit
def test_farside_reader_markdown_parser_keeps_signed_flows_and_total() -> None:
    markdown = """
    |  | IBIT | FBTC | Total |
    | --- | --- | --- | --- |
    | 17 Sep 2026 | 183.7 | (16.6) | 167.1 |
    | 18 Sep 2026 | 108.4 | 310.7 | 419.1 |
    """

    tickers, rows = provider._parse_farside_btc_markdown(markdown)

    assert tickers[-1] == "Total"
    assert rows == [
        ["17 Sep 2026", "183.7", "(16.6)", "167.1"],
        ["18 Sep 2026", "108.4", "310.7", "419.1"],
    ]


@pytest.mark.unit
def test_farside_all_data_reader_parser_handles_split_cells() -> None:
    """BTC all-data Reader 输出的逐单元格文本仍应还原为完整日行。"""
    markdown = """
Date
IBIT
FBTC
Total
11 Jan 2024
111.7

227.0

655.3
12 Jan 2024
-

(10.0)

5.0
"""
    tickers, rows = provider._parse_farside_all_data_markdown(
        markdown, ("IBIT", "FBTC", "Total")
    )
    assert tickers == ["IBIT", "FBTC", "Total"]
    assert rows == [
        ["11 Jan 2024", "111.7", "227.0", "655.3"],
        ["12 Jan 2024", "-", "(10.0)", "5.0"],
    ]


@pytest.mark.unit
def test_etf_fetch_falls_back_to_farside_reader_when_direct_page_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Response:
        def __init__(self, text: str, status_code: int = 200) -> None:
            self.text = text
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise provider.httpx.HTTPStatusError(
                    "blocked",
                    request=provider.httpx.Request("GET", "https://example.invalid"),
                    response=provider.httpx.Response(self.status_code),
                )

    calls: list[str] = []
    markdown = (
        "| 18 Sep 2026 | 108.4 | 310.7 | 9.7 | 1.9 | 0 | 0 | 0 | 2.3 | 0 | 0 | 0 | 0 | 433.0 |"
    )

    def fake_get(url: str, **_kwargs):
        calls.append(url)
        if url == provider._FARSIDE_BTC_URL:
            return _Response("blocked", 403)
        return _Response(markdown)

    monkeypatch.setattr(provider, "_get", fake_get)
    data = provider.fetch_etf_flow(1)

    assert calls == [provider._FARSIDE_BTC_URL, provider._FARSIDE_BTC_READER_URL]
    assert data["days"][-1]["flows"]["Total"] == 433.0


@pytest.mark.unit
def test_eth_etf_fetch_uses_eth_page_and_ticker_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Response:
        def __init__(self, text: str, status_code: int = 200) -> None:
            self.text = text
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise provider.httpx.HTTPStatusError(
                    "blocked",
                    request=provider.httpx.Request("GET", provider._FARSIDE_ETH_URL),
                    response=provider.httpx.Response(self.status_code),
                )

    calls: list[str] = []
    markdown = "| 18 Sep 2026 | 114.3 | 0 | 26.2 | 1.3 | 0 | 1.9 | 0 | 0 | 0 | 0 | 0 | 143.7 |"

    def fake_get(url: str, **_kwargs):
        calls.append(url)
        if url == provider._FARSIDE_ETH_URL:
            return _Response("blocked", 403)
        return _Response(markdown)

    monkeypatch.setattr(provider, "_get", fake_get)
    data = provider.fetch_etf_flow(1, "eth")

    assert calls == [provider._FARSIDE_ETH_URL, provider._FARSIDE_ETH_READER_URL]
    assert data["tickers"] == list(provider._FARSIDE_ETH_TICKERS)
    assert data["days"][-1]["flows"]["ETHA"] == 114.3
    assert data["days"][-1]["flows"]["Total"] == 143.7


@pytest.mark.unit
def test_get_builds_a_scoped_client_with_verification_and_no_env_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_get 必须构造带校验的独立 client，并关闭 trust_env 以免继承外部代理。"""
    captured: dict[str, object] = {}

    class _FakeResponse:
        text = "ok"
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self):  # noqa: ANN201 - 测试替身
            return {"ok": True}

    class _FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def get(self, url: str, **kwargs: object) -> _FakeResponse:
            captured["url"] = url
            captured["get_kwargs"] = kwargs
            return _FakeResponse()

    monkeypatch.setattr(provider.httpx, "Client", _FakeClient)
    monkeypatch.setattr(
        provider.truststore, "SSLContext", lambda *_: "system-trust-store"
    )

    result = provider._get("https://example.invalid/data", params={"a": 1})

    assert captured["verify"] == "system-trust-store"
    assert captured["trust_env"] is False
    assert "verify" not in captured.get("get_kwargs", {})
    assert result.text == "ok"
    assert result.json() == {"ok": True}


@pytest.mark.unit
def test_get_retries_configured_proxy_when_direct_upstream_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    class _FakeResponse:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code
            self.text = "ok"

        def raise_for_status(self) -> None:
            return None

        def json(self):  # noqa: ANN201 - 测试替身
            return {"ok": True}

    class _FakeClient:
        def __init__(self, **kwargs: object) -> None:
            calls.append(bool(kwargs["trust_env"]))
            self.status_code = 403 if not kwargs["trust_env"] else 200

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def get(self, url: str, **kwargs: object) -> _FakeResponse:
            return _FakeResponse(self.status_code)

    monkeypatch.setattr(provider.httpx, "Client", _FakeClient)
    monkeypatch.setattr(provider.truststore, "SSLContext", lambda *_: "system-trust-store")

    result = provider._get("https://example.invalid/data")

    assert calls == [False, True]
    assert result.text == "ok"


# ---------------------------------------------------------------------------
# 2. 刷新调度
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("hour", "expected"),
    [(5, False), (6, True), (12, True), (23, True)],
)
def test_refresh_is_due_only_at_or_after_0600_china_time(
    hour: int, expected: bool
) -> None:
    """美股收盘后 06:00（Asia/Shanghai）起才允许自动刷新。"""
    local = datetime(2026, 9, 11, hour, 0, tzinfo=refresh._CHINA)
    assert refresh._overseas_refresh_due(local.astimezone(UTC)) is expected


@pytest.mark.unit
def test_already_refreshed_today_is_idempotent_within_the_china_day(
    overseas_db, seed_run, monkeypatch: pytest.MonkeyPatch
) -> None:
    """同一中国日内只刷一次；跨日或时间戳损坏时必须重新允许刷新。"""
    seed_run("run-1")
    repository.write_overseas_points(
        "run-1",
        "macro_fedwatch",
        [("2026-09-11", "__meta__", {"effr": 4.33})],
        source="fixture",
    )
    # 把 fetched_at 固定为当天中国时间 08:00
    now_local = datetime.now(refresh._CHINA).replace(hour=8, minute=0, second=0, microsecond=0)
    with connection() as db:
        db.execute(
            "UPDATE research_a_share_history SET fetched_at=? WHERE dataset='macro_fedwatch'",
            (now_local.astimezone(UTC).isoformat(),),
        )

    assert refresh._already_refreshed_today("macro_fedwatch") is True

    # 昨天抓的 -> 需要重新刷新
    with connection() as db:
        db.execute(
            "UPDATE research_a_share_history SET fetched_at=? WHERE dataset='macro_fedwatch'",
            ((now_local - timedelta(days=1)).astimezone(UTC).isoformat(),),
        )
    assert refresh._already_refreshed_today("macro_fedwatch") is False


@pytest.mark.unit
def test_fedwatch_refresh_gate_is_hourly_not_daily(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 9, 20, 5, 0, tzinfo=UTC)
    fetched = {"value": "2026-09-20T04:10:00+00:00"}
    monkeypatch.setattr(refresh, "read_latest_fetched_at", lambda _dataset: fetched["value"])

    assert refresh._already_refreshed_within(
        "macro_fedwatch", timedelta(hours=1), now=now
    ) is True

    fetched["value"] = "2026-09-20T03:59:00+00:00"
    assert refresh._already_refreshed_within(
        "macro_fedwatch", timedelta(hours=1), now=now
    ) is False


@pytest.mark.unit
def test_fedwatch_collect_persists_an_hourly_utc_bucket(
    overseas_db, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        refresh,
        "fetch_fedwatch",
        lambda: {
            "effr": 4.33,
            "currentTarget": "4.25%-4.50%",
            "observedAt": "2026-09-20",
            "zqPricing": [],
            "meetings": [{"date": "2026-10-28", "probabilities": {}, "contract": "ZQZ6"}],
        },
    )

    def capture(_run_id, _dataset, observed_at, series, **_kwargs):
        captured["observed_at"] = observed_at
        captured["series"] = series

    monkeypatch.setattr(refresh, "write_overseas_series", capture)

    assert asyncio.run(refresh._collect_fedwatch(force=True))[0] == "ready"
    observed_at = str(captured["observed_at"])
    assert observed_at.endswith(":00+00:00")
    assert captured["series"]["__meta__"]["observedAt"] == observed_at


@pytest.mark.unit
def test_corrupt_fetched_at_does_not_block_future_refreshes(overseas_db, seed_run) -> None:
    """fetched_at 无法解析时按「未刷过」处理，避免永久卡住调度。"""
    seed_run("run-bad", status="error")
    repository.write_overseas_points(
        "run-bad",
        "crypto_etf_flow",
        [("2026-09-11", "__meta__", {"tickers": []})],
        source="fixture",
    )
    with connection() as db:
        db.execute(
            "UPDATE research_a_share_history SET fetched_at='not-a-timestamp' "
            "WHERE dataset='crypto_etf_flow'"
        )

    assert refresh._already_refreshed_today("crypto_etf_flow") is False


@pytest.mark.unit
def test_refresh_keeps_fedwatch_hourly_cadence_before_0600(
    overseas_db, monkeypatch
) -> None:
    """早于 06:00 仍允许 FedWatch 更新，日度源继续走 China 日门控。"""
    monkeypatch.setattr(refresh, "_overseas_refresh_due", lambda: False)

    called = {"n": 0}

    async def _fedwatch(_force: bool):
        called["n"] += 1
        return "up_to_date", ""

    monkeypatch.setattr(refresh, "_collect_fedwatch", _fedwatch)
    assert asyncio.run(refresh.refresh_overseas()) == "up_to_date"
    assert called["n"] == 1


# ---------------------------------------------------------------------------
# 3. 失败保留语义
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_failed_refresh_retains_last_valid_rows(overseas_db, seed_run, monkeypatch) -> None:
    """抓取失败时既有历史必须原样保留，且运行状态记录为 error。"""
    seed_run("run-ok")
    repository.write_overseas_series(
        "run-ok",
        "macro_fedwatch",
        "2026-09-10",
        {"__meta__": {"effr": 4.33}, "2026-09-17": {"probabilities": {"4.00-4.25": 92.0}}},
        source="fixture",
    )

    def _boom():
        raise provider.ResearchProviderError("cme_settlements_empty")

    monkeypatch.setattr(refresh, "fetch_fedwatch", _boom)

    with pytest.raises(provider.ResearchProviderError):
        asyncio.run(refresh._collect_fedwatch(force=True))

    # 旧数据仍在，未被清空
    series = repository.read_latest_series("macro_fedwatch")
    assert series["__meta__"]["effr"] == 4.33
    assert series["2026-09-17"]["probabilities"] == {"4.00-4.25": 92.0}
    # 且明确暴露失败
    health = repository.read_dataset_health("macro_fedwatch")
    assert health["hasData"] is True
    assert health["status"] == "stale"
    assert health["lastRunStatus"] == "error"
    assert health["lastError"]["code"] == "ResearchProviderError"


@pytest.mark.unit
def test_write_failure_rolls_back_the_cleanup_so_data_survives(
    overseas_db, seed_run, monkeypatch
) -> None:
    """写库中途失败时必须整体回滚：DELETE 不能先于 INSERT 独立提交。"""
    seed_run("run-keep")
    repository.write_overseas_series(
        "run-keep",
        "crypto_iv_snapshot",
        "2026-09-10",
        {"1M": {"iv": 36.7}},
        source="fixture",
    )

    def _fail(*_args, **_kwargs):
        raise RuntimeError("insert exploded")

    monkeypatch.setattr(repository, "write_history_points", _fail)

    with pytest.raises(RuntimeError):
        seed_run("run-fail")
        repository.write_overseas_series(
            "run-fail",
            "crypto_iv_snapshot",
            "2026-09-10",
            {"1M": {"iv": 99.9}},
            source="fixture",
        )

    # 回滚后仍是旧值，没有被清空成空
    assert repository.read_iv_snapshot_history("1M")[-1]["iv"] == 36.7


@pytest.mark.unit
def test_dataset_health_reports_no_data_without_fabricating_a_value(overseas_db) -> None:
    """无数据时返回 no_data，绝不伪造数值。"""
    health = repository.read_dataset_health("macro_fedwatch")

    assert health["hasData"] is False
    assert health["status"] == "no_data"
    assert health["observedAt"] is None
    assert health["fetchedAt"] is None


@pytest.mark.unit
def test_dataset_health_is_ready_after_a_successful_collection(
    overseas_db, monkeypatch
) -> None:
    """成功刷新后健康状态为 ready，且不残留错误信息。"""
    monkeypatch.setattr(
        refresh,
        "fetch_fedwatch",
        lambda: {
            "effr": 4.33,
            "currentTarget": "4.00%-4.25%",
            "observedAt": "2026-09-10",
            "zqPricing": [],
            "meetings": [
                {
                    "date": "2026-09-17",
                    "contract": "ZQU6",
                    "probabilities": {"4.00-4.25": 92.0},
                }
            ],
        },
    )

    assert asyncio.run(refresh._collect_fedwatch(force=True))[0] == "ready"

    health = repository.read_dataset_health("macro_fedwatch")
    assert health["status"] == "ready"
    assert health["lastRunStatus"] == "ready"
    assert health["lastError"] is None


@pytest.mark.unit
def test_fed_futures_missing_settlement_remains_unavailable() -> None:
    rows = provider._build_zq_pricing_table({})
    assert len(rows) == 13
    assert all(row["settle"] is None for row in rows)


@pytest.mark.unit
def test_one_failed_source_does_not_block_the_others(overseas_db, monkeypatch) -> None:
    """单源失败隔离：其他源照常落库，整体结果报 error 但不丢成功源的数据。"""
    monkeypatch.setattr(refresh, "_overseas_refresh_due", lambda: True)
    monkeypatch.setattr(refresh, "_REFRESH_LOCK", asyncio.Lock())

    def _boom():
        raise provider.ResearchProviderError("farside_btc_empty")

    monkeypatch.setattr(refresh, "fetch_fedwatch", _boom)
    def _flow(_days=14, _asset="btc"):
        ticker = "IBIT" if _asset == "btc" else "ETHA"
        return {
            "tickers": [ticker],
            "days": [{"date": "2026-09-10", "flows": {ticker: 12.5}}],
        }

    monkeypatch.setattr(refresh, "fetch_etf_flow", _flow)
    monkeypatch.setattr(
        refresh,
        "fetch_deribit_iv",
        lambda: {"index": 60000.0, "term": []},
    )
    monkeypatch.setattr(
        refresh,
        "fetch_btc_iv_snapshot",
        lambda: {
            "index": 60000.0,
            "dvol": 41.2,
            "observedAt": "2026-09-10",
            "tenors": [
                {
                    "tenor": "1M",
                    "iv": 36.7,
                    "expiry": "2026-10-01",
                    "daysToExpiry": 21,
                    "strike": 60000,
                }
            ],
        },
    )

    assert asyncio.run(refresh.refresh_overseas(force=True)) == "error"

    # Ethereum ETF 源成功落库
    assert repository.read_etf_flow(14)["days"][0]["flows"]["IBIT"] == 12.5
    assert repository.read_etf_flow(14, "eth")["days"][0]["flows"]["ETHA"] == 12.5
    # IV 源成功落库
    assert repository.read_iv_snapshot_latest()["tenors"][0]["iv"] == 36.7


# ---------------------------------------------------------------------------
# 4. 持久化读取
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_latest_series_roundtrip_and_dedup(overseas_db, seed_run) -> None:
    """同一 observed_at 重写应覆盖而非累积；不同日期则累积。"""
    seed_run("r1")
    seed_run("r2")
    seed_run("r3")
    repository.write_overseas_series(
        "r1", "macro_fedwatch", "2026-09-10", {"__meta__": {"effr": 4.30}},
        source="fixture",
    )
    repository.write_overseas_series(
        "r2", "macro_fedwatch", "2026-09-10", {"__meta__": {"effr": 4.33}},
        source="fixture",
    )
    assert repository.read_latest_series("macro_fedwatch")["__meta__"]["effr"] == 4.33

    repository.write_overseas_series(
        "r3", "macro_fedwatch", "2026-09-11", {"__meta__": {"effr": 4.35}},
        source="fixture",
    )
    assert repository.read_latest_observed_at("macro_fedwatch") == "2026-09-11"
    assert repository.read_latest_fetched_at("macro_fedwatch") is not None


@pytest.mark.unit
def test_etf_flow_read_returns_meta_tickers_and_ordered_days(overseas_db, seed_run) -> None:
    """ETF 读取要回读表头列序、按日期升序、缺省单元格保持缺失而非填 0。"""
    seed_run("r1")
    repository.write_overseas_points(
        "r1",
        "crypto_etf_flow",
        [
            ("2026-09-10", "__meta__", {"tickers": ["IBIT", "FBTC"], "unit": "US$m"}),
            ("2026-09-09", "IBIT", {"flow": -17.1}),
            ("2026-09-09", "FBTC", {"flow": None}),
            ("2026-09-10", "IBIT", {"flow": 12.5}),
            ("2026-09-10", "FBTC", {"flow": 3.2}),
        ],
        source="fixture",
    )

    data = repository.read_etf_flow(14)

    assert data["tickers"] == ["IBIT", "FBTC"]
    assert data["observedAt"] == "2026-09-10"
    assert [d["date"] for d in data["days"]] == ["2026-09-09", "2026-09-10"]
    # 未发布的一格保持 None，不被伪造成 0
    assert data["days"][0]["flows"]["FBTC"] is None
    assert data["days"][0]["flows"]["IBIT"] == -17.1
    # 图表所需的日总流量与累计值在后端生成，前端不重算
    assert data["days"][0]["totalFlow"] == -17.1
    assert data["days"][0]["cumulativeFlow"] == -17.1
    assert data["days"][1]["totalFlow"] == 15.7
    assert data["days"][1]["cumulativeFlow"] == -1.4
    assert data["days"][0]["price"] is None


@pytest.mark.unit
def test_iv_snapshot_latest_orders_tenors_and_keeps_meta(overseas_db, seed_run) -> None:
    """IV 快照按 1M/3M/6M/1Y 固定顺序返回，并带出指数价与 DVOL。"""
    seed_run("r1")
    repository.write_iv_snapshot(
        "r1",
        "2026-09-10",
        {
            "index": 60123.4,
            "dvol": 41.2,
            "observedAt": "2026-09-10",
            "tenors": [
                {
                    "tenor": "1Y",
                    "iv": 52.1,
                    "expiry": "2027-09-01",
                    "daysToExpiry": 356,
                    "strike": 60000,
                },
                {
                    "tenor": "1M",
                    "iv": 36.7,
                    "expiry": "2026-10-01",
                    "daysToExpiry": 21,
                    "strike": 60000,
                },
                {
                    "tenor": "3M",
                    "iv": 44.5,
                    "expiry": "2026-12-01",
                    "daysToExpiry": 82,
                    "strike": 60000,
                },
            ],
        },
        source="fixture",
    )

    snap = repository.read_iv_snapshot_latest()

    assert snap["index"] == 60123.4
    assert snap["dvol"] == 41.2
    assert [t["tenor"] for t in snap["tenors"]] == ["1M", "3M", "1Y"]


@pytest.mark.unit
def test_iv_history_is_ascending_and_bounded_by_days(overseas_db, seed_run) -> None:
    """历史读取按日期升序，并遵守 days 上限。"""
    for day, iv in [
        ("2026-09-08", 35.0),
        ("2026-09-09", 36.0),
        ("2026-09-10", 37.0),
    ]:
        seed_run(f"r-{day}")
        repository.write_iv_snapshot(
            f"r-{day}",
            day,
            {
                "index": 60000.0,
                "dvol": 41.0,
                "observedAt": day,
                "tenors": [
                    {
                        "tenor": "1M",
                        "iv": iv,
                        "expiry": "2026-10-01",
                        "daysToExpiry": 21,
                        "strike": 60000,
                    }
                ],
            },
            source="fixture",
        )

    history = repository.read_iv_snapshot_history("1M", 365)
    assert [p["observedAt"] for p in history] == ["2026-09-08", "2026-09-09", "2026-09-10"]
    assert [p["iv"] for p in history] == [35.0, 36.0, 37.0]

    assert len(repository.read_iv_snapshot_history("1M", 2)) == 2


# ---------------------------------------------------------------------------
# 5. 路由边界与权限
# ---------------------------------------------------------------------------


def _research_app(monkeypatch: pytest.MonkeyPatch):
    """构造一个禁用调度、独立数据库的应用实例。"""
    from app.application import create_application

    settings = get_settings()
    monkeypatch.setattr(settings, "research_refresh_enabled", False)
    monkeypatch.setattr(settings, "live_trading_enabled", False)
    return create_application()


def _bearer_auth(monkeypatch: pytest.MonkeyPatch, token: str, roles: list[str]) -> dict[str, str]:
    """配置 api_key 认证模式下的一枚静态凭据，返回可直接使用的请求头。

    测试进程默认 ``auth_mode=development``，中间件会给任何请求派发一个 admin
    开发身份，匿名断言因此不成立。只有显式切到 ``api_key`` 模式，未带凭据
    的请求才会真的以 401 被拒。
    """
    import hashlib
    import json

    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(
        settings,
        "auth_credentials_json",
        json.dumps(
            [
                {
                    "credentialId": f"credential-{roles[0]}",
                    "userId": f"user-{roles[0]}",
                    "tokenSha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                    "roles": roles,
                    "status": "active",
                }
            ]
        ),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
def test_overseas_read_routes_require_authentication(tmp_path, monkeypatch) -> None:
    """海外只读端点必须拒绝未认证请求（401），并允许持 research.read 的身份读取。"""
    from fastapi.testclient import TestClient

    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "routes.db"))
    viewer_headers = _bearer_auth(monkeypatch, "viewer-token", ["viewer"])
    initialize_database()

    app = _research_app(monkeypatch)
    with TestClient(app) as client:
        paths = (
            "/api/v1/research/macro/fedwatch",
            "/api/v1/research/crypto/etf-flow",
            "/api/v1/research/crypto/iv-term",
            "/api/v1/research/crypto/iv-snapshot",
            "/api/v1/research/crypto/iv-history?tenor=1M",
            "/api/v1/research/crypto/iv-dvol",
        )
        for path in paths:
            anonymous = client.get(path)
            assert anonymous.status_code == 401, f"{path} -> {anonymous.status_code}"

        # viewer 持有 research.read：空库下应返回 200，并带上无数据/过期状态。
        allowed = client.get("/api/v1/research/macro/fedwatch", headers=viewer_headers)
        assert allowed.status_code == 200
        assert allowed.json()["data"]["status"] == "no_data"


@pytest.mark.integration
def test_overseas_refresh_requires_write_permission(tmp_path, monkeypatch) -> None:
    """手动刷新需要 research.write；匿名与只读身份都必须被拒绝，且不触发抓取。"""
    from fastapi.testclient import TestClient

    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "refresh.db"))
    viewer_headers = _bearer_auth(monkeypatch, "viewer-token", ["viewer"])
    initialize_database()

    called = {"n": 0}

    async def _spy(**_kwargs):
        called["n"] += 1
        return "ready"

    monkeypatch.setattr("app.research_routes.refresh_overseas", _spy)

    app = _research_app(monkeypatch)
    with TestClient(app) as client:
        anonymous = client.post("/api/v1/research/overseas/refresh")
        read_only = client.post("/api/v1/research/overseas/refresh", headers=viewer_headers)

    assert anonymous.status_code == 401
    assert read_only.status_code == 403
    assert read_only.json()["detail"]["code"] == "permission_denied"
    assert called["n"] == 0


@pytest.mark.integration
def test_iv_history_validates_tenor_pattern_and_days_bounds(tmp_path, monkeypatch) -> None:
    """tenor 只接受 1M/3M/6M/1Y；days 限制在 1..730。

    认证中间件在路由层参数校验之前执行，因此未认证的越界请求先返回 401。
    越界约束本身由 422 负责：带合法身份请求越界参数即得到 FastAPI 的校验响应。
    """
    from fastapi.testclient import TestClient

    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "bounds.db"))
    viewer_headers = _bearer_auth(monkeypatch, "viewer-token", ["viewer"])
    initialize_database()

    app = _research_app(monkeypatch)
    with TestClient(app) as client:
        # 未认证：中间件先于参数校验，一律 401
        assert client.get("/api/v1/research/crypto/iv-history?tenor=9X").status_code == 401
        assert client.get("/api/v1/research/crypto/iv-history?tenor=1M&days=0").status_code == 401
        assert (
            client.get("/api/v1/research/crypto/iv-history?tenor=1M&days=9999").status_code == 401
        )

        # 已认证：越界参数被 FastAPI 校验拒绝
        assert (
            client.get(
                "/api/v1/research/crypto/iv-history?tenor=9X", headers=viewer_headers
            ).status_code
            == 422
        )
        assert (
            client.get(
                "/api/v1/research/crypto/iv-history?tenor=1M&days=0", headers=viewer_headers
            ).status_code
            == 422
        )
        assert (
            client.get(
                "/api/v1/research/crypto/iv-history?tenor=1M&days=9999", headers=viewer_headers
            ).status_code
            == 422
        )

        # 合法参数 + research.read：空库返回 200 与空历史
        ok = client.get(
            "/api/v1/research/crypto/iv-history?tenor=1M&days=365", headers=viewer_headers
        )
        assert ok.status_code == 200
        assert ok.json()["data"]["history"] == []


@pytest.mark.unit
def test_read_routes_expose_status_field_for_stale_reporting() -> None:
    """只读路由必须返回 status 字段，前端才能标注 stale/error。"""
    import app.research_routes as routes

    source = inspect.getsource(routes)
    # 每个海外读取端点都带上健康状态
    assert 'read_dataset_health' in source
    assert source.count('"status": health["status"]') >= 4
    assert source.count('"lastError": health["lastError"]') >= 4


@pytest.mark.parametrize("asset", ["btc", "eth"])
def test_etf_uses_shared_spot_exact_closed_days_and_ignores_legacy_contract(
    overseas_db, seed_run, asset
):
    import json

    seed_run("spot-test")
    dataset = "crypto_etf_flow" if asset == "btc" else "crypto_eth_etf_flow"
    repository.write_overseas_points(
        "spot-test",
        dataset,
        [
            ("2026-09-10", "__meta__", {"tickers": ["Total"], "coinUnit": asset.upper()}),
            ("2026-09-09", "Total", {"flow": 1, "coinFlow": 999, "price": 999}),
            ("2026-09-10", "Total", {"flow": 2, "coinFlow": 888, "price": 888}),
        ],
        source="fixture",
    )
    stamp = int(datetime(2026, 9, 10, tzinfo=UTC).timestamp() * 1000)
    with connection() as db:
        for kind, entity, at, close in [
            ("daily_candle", f"{asset.upper()}USDT:spot:trade", stamp, "100"),
            ("historical_candle", f"{asset.upper()}USDT:linear:trade", stamp + 86400000, "999"),
            # A nearly closed day must not substitute for a missing exact close.
            (
                "historical_candle",
                f"{asset.upper()}USDT:spot:trade",
                stamp + 86400000 - 60000,
                "200",
            ),
        ]:
            db.execute(
                "INSERT INTO research_strategy_projection VALUES(?,?,?,?)",
                (kind, entity, at, json.dumps({"close": close, "quality": []})),
            )
    result = repository.read_etf_flow(asset=asset)
    assert [d["price"] for d in result["days"]] == [100, None]
    assert result["flowUnit"] == "US$m"  # no mixed-unit conversion on incomplete coverage
    assert [d["totalFlow"] for d in result["days"]] == [1, 2]
    assert result["priceSource"] == "Bybit spot UTC daily close (USDT)"
    with connection() as db:
        db.execute(
            "INSERT INTO research_strategy_projection VALUES(?,?,?,?)",
            (
                "daily_candle",
                f"{asset.upper()}USDT:spot:trade",
                stamp + 86400000,
                json.dumps({"close": "200", "quality": []}),
            ),
        )
    result = repository.read_etf_flow(asset=asset)
    assert [d["price"] for d in result["days"]] == [100, 200]
    assert result["flowUnit"] == asset.upper()
    assert [d["totalFlow"] for d in result["days"]] == [10000, 10000]
