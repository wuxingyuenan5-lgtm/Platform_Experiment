from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

venue_path = ROOT / "platform-backend/app/venue_reconciliation.py"
venue = venue_path.read_text(encoding="utf-8")
old = '''    with connection() as db:\n        local_fill = db.execute(\n            "SELECT COALESCE(SUM(CAST(quantity AS REAL)), 0) AS quantity FROM fills WHERE order_id = ?",\n            (order_id,),\n        ).fetchone()\n    local_quantity = Decimal(str(local_fill["quantity"]))\n'''
new = '''    with connection() as db:\n        local_fill_rows = db.execute(\n            "SELECT quantity FROM fills WHERE order_id = ?",\n            (order_id,),\n        ).fetchall()\n    local_quantity = sum(\n        (Decimal(row["quantity"]) for row in local_fill_rows),\n        Decimal("0"),\n    )\n'''
if venue.count(old) != 1:
    raise SystemExit("expected exactly one binary-float fill aggregation block")
venue_path.write_text(venue.replace(old, new), encoding="utf-8")

test_path = ROOT / "platform-backend/tests/test_venue_reconciliation_decimal.py"
test_path.write_text(
    '''from pathlib import Path\n\nimport httpx\nfrom fastapi.testclient import TestClient\n\nfrom app.config import get_settings\nfrom app.database import connection\nfrom app.main import app\nfrom app.venue_reconciliation import compare_order\n\nSTRATEGY_ID = "strategy_funding_arbitrage_instance_default"\nACCOUNT_ID = "account_sim_usdt"\nINSTRUMENT_ID = "instrument_btc_usdt"\n\n\ndef test_order_fill_quantity_comparison_preserves_exact_decimal_sum(\n    monkeypatch,\n    tmp_path: Path,\n) -> None:\n    get_settings().database_path = str(tmp_path / "venue-decimal-quantity.db")\n    monkeypatch.setattr(\n        "app.trade_command_execution.httpx.post",\n        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("timeout")),\n    )\n\n    with TestClient(app) as client:\n        created = client.post(\n            "/api/v1/trading/commands",\n            json={\n                "idempotencyKey": "venue-decimal-command-001",\n                "strategyInstanceId": STRATEGY_ID,\n                "accountId": ACCOUNT_ID,\n                "instrumentId": INSTRUMENT_ID,\n                "symbol": "BTCUSDT",\n                "side": "buy",\n                "orderType": "limit",\n                "quantity": "0.3",\n                "price": "100",\n            },\n        )\n        assert created.status_code == 200\n        order_id = created.json()["platformOrderId"]\n\n        with connection() as db:\n            db.executemany(\n                """\n                INSERT INTO fills (\n                    id, order_id, account_id, instrument_id, side, quantity, price, occurred_at\n                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n                """,\n                [\n                    (\n                        "decimal-fill-1",\n                        order_id,\n                        ACCOUNT_ID,\n                        INSTRUMENT_ID,\n                        "buy",\n                        "0.1",\n                        "100",\n                        "2026-07-24T00:00:00+00:00",\n                    ),\n                    (\n                        "decimal-fill-2",\n                        order_id,\n                        ACCOUNT_ID,\n                        INSTRUMENT_ID,\n                        "buy",\n                        "0.2000000000000000000000000001",\n                        "100",\n                        "2026-07-24T00:00:01+00:00",\n                    ),\n                ],\n            )\n\n        differences = compare_order(\n            order_id,\n            {"status": "result_unknown"},\n            {"status": "unknown"},\n            [\n                {"quantity": "0.1"},\n                {"quantity": "0.2000000000000000000000000001"},\n            ],\n        )\n\n    assert differences == []\n''',
    encoding="utf-8",
)

changelog_path = ROOT / "CHANGELOG.md"
changelog = changelog_path.read_text(encoding="utf-8")
marker = "## Unreleased\n\n"
entry = '''### Exact Decimal venue fill reconciliation — Issue #59 / PR #60\n\n- Replaced SQLite `REAL` aggregation of stored fill quantities with exact Python `Decimal` accumulation.\n- Added regression coverage for fractional and high-precision quantities that would otherwise create false reconciliation differences.\n- Preserved reconciliation APIs, difference identities, persistence, accounting formulas, Runtime contracts and both Live Write defaults.\n\n'''
if entry not in changelog:
    if marker not in changelog:
        raise SystemExit("Changelog Unreleased marker not found")
    changelog_path.write_text(changelog.replace(marker, marker + entry, 1), encoding="utf-8")

state_path = ROOT / "docs/codex/current-state.md"
state = state_path.read_text(encoding="utf-8")
old_active = "No engineering code workstream is active by default after PR #58 merges."
new_active = "Issue #59 / Draft PR #60 is the only active engineering workstream: exact Decimal venue fill reconciliation."
if old_active not in state:
    raise SystemExit("current-state active-work marker not found")
state_path.write_text(state.replace(old_active, new_active, 1), encoding="utf-8")

Path(__file__).unlink()
workflow = ROOT / ".github/workflows/issue-59-apply.yml"
if workflow.exists():
    workflow.unlink()
