from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.financial_facts import ensure_schema as ensure_financial_schema
from app.main import app
from app.venue_reconciliation import ensure_schema as ensure_reconciliation_schema

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


def report_payload(key: str = "eod-20260723-account-sim") -> dict[str, str]:
    return {
        "idempotencyKey": key,
        "businessDate": "2026-07-23",
        "timezone": "Asia/Shanghai",
        "valuationTime": "2026-07-23T23:59:00+08:00",
        "strategyInstanceId": STRATEGY_ID,
        "accountId": ACCOUNT_ID,
        "actor": "eod-runner",
        "owner": "operations-owner",
        "dueAt": "2026-07-24T23:59:00+08:00",
    }


def seed_complete_formal_pnl() -> None:
    ensure_financial_schema()
    with connection() as db:
        db.execute(
            """
            INSERT INTO formal_pnl_results (
                strategy_instance_id, account_id, instrument_id, currency,
                trading_pnl, funding_pnl, swap_pnl, fee_pnl, fx_pnl,
                total_pnl, fact_count, data_quality_state, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                STRATEGY_ID,
                ACCOUNT_ID,
                INSTRUMENT_ID,
                "USDT",
                "10",
                "2",
                "0",
                "-1",
                "0",
                "11",
                3,
                "complete",
                "2026-07-23T15:59:00+00:00",
            ),
        )


def test_clean_eod_report_is_idempotent_and_reviewable(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "clean-eod.db")
    with TestClient(app) as client:
        ensure_reconciliation_schema()
        seed_complete_formal_pnl()

        monkeypatch.setattr(
            "app.eod_reconciliation.list_strategy_orders",
            lambda *args, **kwargs: ["order-live-001"],
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.reconcile_order_with_venue",
            lambda order_id: SimpleNamespace(difference_ids=[]),
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.run_account_reconciliation",
            lambda request: SimpleNamespace(run_id="account-run-clean"),
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.import_live_economic_events",
            lambda request: SimpleNamespace(
                import_id="economic-import-clean",
                skipped_external_ids=[],
            ),
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.rebuild_strategy_financials",
            lambda strategy_instance_id: None,
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.run_formal_nav_snapshot",
            lambda strategy_instance_id, valuation_time: SimpleNamespace(
                snapshot_id="nav-clean",
                missing_account_ids=[],
            ),
        )

        first = client.post("/api/v1/ops/eod-reconciliation/reports", json=report_payload())
        replay = client.post("/api/v1/ops/eod-reconciliation/reports", json=report_payload())

        assert first.status_code == 200
        assert replay.status_code == 200
        assert replay.json() == first.json()
        report = first.json()
        assert report["status"] == "complete"
        assert report["scaleGateStatus"] == "eligible_for_review"
        assert report["orderReconciliationCount"] == 1
        assert report["formalPnlCount"] == 1
        assert report["formalPnlIncompleteCount"] == 0
        assert report["openDifferenceCount"] == 0
        assert report["skippedExternalIds"] == []
        assert report["missingAccountIds"] == []
        assert report["errors"] == []

        rerun = client.post(
            "/api/v1/ops/eod-reconciliation/reports",
            json={**report_payload("different-key"), "actor": "different-actor"},
        )
        assert rerun.status_code == 200
        assert rerun.json()["attempt"] == 2

        approved = client.post(
            f"/api/v1/ops/eod-reconciliation/reports/{report['reportId']}/review",
            json={
                "decision": "approved_same_limits",
                "reviewer": "risk-reviewer",
                "reason": "clean report; existing minimum live limits only",
            },
        )
        assert approved.status_code == 200
        assert approved.json()["scaleGateStatus"] == "approved_same_limits"

        immutable_conflict = client.post(
            f"/api/v1/ops/eod-reconciliation/reports/{report['reportId']}/review",
            json={
                "decision": "rejected",
                "reviewer": "other-reviewer",
                "reason": "must not overwrite the first review",
            },
        )
        assert immutable_conflict.status_code == 409

        listed = client.get(
            "/api/v1/ops/eod-reconciliation/reports",
            params={
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "businessDate": "2026-07-23",
            },
        )
        assert listed.status_code == 200
        assert len(listed.json()) == 1


def test_differences_skips_and_missing_accounts_block_approval(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "blocked-eod.db")
    with TestClient(app) as client:
        ensure_reconciliation_schema()
        seed_complete_formal_pnl()

        def account_run(_request):
            with connection() as db:
                db.execute(
                    """
                    INSERT INTO venue_reconciliation_runs (
                        id, idempotency_key, payload_hash, strategy_instance_id,
                        account_id, run_type, source, status, order_count,
                        fill_count, position_count, balance_count, fact_count,
                        difference_count, started_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "account-run-blocked",
                        "account-run-blocked",
                        "hash",
                        STRATEGY_ID,
                        ACCOUNT_ID,
                        "account_snapshot",
                        "live",
                        "completed_with_differences",
                        0,
                        0,
                        1,
                        1,
                        2,
                        1,
                        "2026-07-23T15:59:00+00:00",
                        "2026-07-23T16:00:00+00:00",
                    ),
                )
                db.execute(
                    """
                    INSERT INTO reconciliation_differences (
                        id, run_id, difference_key, difference_type, entity_type,
                        local_reference, external_reference, local_value_json,
                        external_value_json, status, resolution_actor,
                        resolution_reason, resolved_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "difference-open-001",
                        "account-run-blocked",
                        "position:btc:quantity_mismatch",
                        "quantity_mismatch",
                        "position",
                        "local-position",
                        "external-position",
                        '{"netQuantity":"1"}',
                        '{"netQuantity":"2"}',
                        "open",
                        None,
                        None,
                        None,
                        "2026-07-23T16:00:00+00:00",
                    ),
                )
            return SimpleNamespace(run_id="account-run-blocked")

        monkeypatch.setattr(
            "app.eod_reconciliation.list_strategy_orders",
            lambda *args, **kwargs: [],
        )
        monkeypatch.setattr("app.eod_reconciliation.run_account_reconciliation", account_run)
        monkeypatch.setattr(
            "app.eod_reconciliation.import_live_economic_events",
            lambda request: SimpleNamespace(
                import_id="economic-import-blocked",
                skipped_external_ids=["unmapped-swap-001"],
            ),
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.rebuild_strategy_financials",
            lambda strategy_instance_id: None,
        )
        monkeypatch.setattr(
            "app.eod_reconciliation.run_formal_nav_snapshot",
            lambda strategy_instance_id, valuation_time: SimpleNamespace(
                snapshot_id="nav-partial",
                missing_account_ids=["account_missing_live"],
            ),
        )

        response = client.post(
            "/api/v1/ops/eod-reconciliation/reports",
            json=report_payload("eod-blocked-001"),
        )
        assert response.status_code == 200
        report = response.json()
        assert report["status"] == "completed_with_differences"
        assert report["scaleGateStatus"] == "blocked"
        assert report["openDifferenceCount"] == 1
        assert report["skippedExternalIds"] == ["unmapped-swap-001"]
        assert report["missingAccountIds"] == ["account_missing_live"]

        forbidden_approval = client.post(
            f"/api/v1/ops/eod-reconciliation/reports/{report['reportId']}/review",
            json={
                "decision": "approved_same_limits",
                "reviewer": "risk-reviewer",
                "reason": "must not approve unresolved differences",
            },
        )
        assert forbidden_approval.status_code == 422

        remediation = client.post(
            f"/api/v1/ops/eod-reconciliation/reports/{report['reportId']}/review",
            json={
                "decision": "needs_remediation",
                "reviewer": "risk-reviewer",
                "reason": "resolve position mismatch and instrument mapping",
            },
        )
        assert remediation.status_code == 200
        assert remediation.json()["scaleGateStatus"] == "needs_remediation"


def test_external_failures_produce_failed_report_not_false_complete(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "failed-eod.db")
    with TestClient(app) as client:
        ensure_reconciliation_schema()
        ensure_financial_schema()

        monkeypatch.setattr(
            "app.eod_reconciliation.list_strategy_orders",
            lambda *args, **kwargs: [],
        )

        def fail(*args, **kwargs):
            raise RuntimeError("external venue unavailable")

        monkeypatch.setattr("app.eod_reconciliation.run_account_reconciliation", fail)
        monkeypatch.setattr("app.eod_reconciliation.import_live_economic_events", fail)
        monkeypatch.setattr("app.eod_reconciliation.rebuild_strategy_financials", fail)
        monkeypatch.setattr("app.eod_reconciliation.run_formal_nav_snapshot", fail)

        response = client.post(
            "/api/v1/ops/eod-reconciliation/reports",
            json=report_payload("eod-failed-001"),
        )
        assert response.status_code == 200
        report = response.json()
        assert report["status"] == "failed"
        assert report["scaleGateStatus"] == "blocked"
        assert len(report["errors"]) == 4
        assert report["navSnapshotId"] is None
        assert report["accountReconciliationRunId"] is None
        assert report["economicEventImportId"] is None
