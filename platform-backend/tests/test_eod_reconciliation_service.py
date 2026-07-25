import pytest
from fastapi import HTTPException

from app import eod_reconciliation as facade
from app import eod_reconciliation_policy as policy
from app import eod_reconciliation_repository as repository
from app import eod_reconciliation_service as service


def test_facade_utility_and_review_exception_compatibility_are_exact() -> None:
    assert facade.now_iso is service.now_iso
    assert facade.canonical_hash is service.canonical_hash
    assert facade.natural_key is service.natural_key
    assert service.EodReviewConflictError is policy.EodReviewConflictError
    assert service.EodReviewConflictError is repository.EodReviewConflictError
    assert service.EodReviewNotEligibleError is policy.EodReviewNotEligibleError
    assert service.EodReviewNotEligibleError is repository.EodReviewNotEligibleError


def test_facade_builds_dependencies_from_current_monkeypatch_targets(monkeypatch) -> None:
    def validate(*args):
        return None

    def list_orders(*args):
        return []

    def reconcile(*args):
        return None

    def account_reconcile(*args):
        return None

    def import_events(*args):
        return None

    def rebuild(*args):
        return None

    def nav(*args):
        return None

    def audit(*args):
        return None

    def gate(*args):
        return None

    monkeypatch.setattr(facade, "validate_strategy_account", validate)
    monkeypatch.setattr(facade, "list_strategy_orders", list_orders)
    monkeypatch.setattr(facade, "reconcile_order_with_venue", reconcile)
    monkeypatch.setattr(facade, "run_account_reconciliation", account_reconcile)
    monkeypatch.setattr(facade, "import_live_economic_events", import_events)
    monkeypatch.setattr(facade, "rebuild_strategy_financials", rebuild)
    monkeypatch.setattr(facade, "run_formal_nav_snapshot", nav)
    monkeypatch.setattr(facade, "audit", audit)
    monkeypatch.setattr(facade, "apply_outstanding_difference_gate", gate)

    dependencies = facade._service_dependencies()

    assert dependencies.validate_strategy_account is validate
    assert dependencies.list_strategy_orders is list_orders
    assert dependencies.reconcile_order_with_venue is reconcile
    assert dependencies.run_account_reconciliation is account_reconcile
    assert dependencies.import_live_economic_events is import_events
    assert dependencies.rebuild_strategy_financials is rebuild
    assert dependencies.run_formal_nav_snapshot is nav
    assert dependencies.audit is audit
    assert dependencies.apply_outstanding_difference_gate is gate


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (
            service.EodReportIdentityConflictError("conflict"),
            409,
            "EOD report identity was reused with a different payload",
        ),
        (
            service.EodReportNotFoundError("missing"),
            404,
            "EOD reconciliation report not found",
        ),
        (
            service.EodReviewConflictError("conflict"),
            409,
            "EOD report review is immutable and already has a different decision",
        ),
        (
            service.EodReviewNotEligibleError("not eligible"),
            422,
            "Only a clean EOD report can be approved for the existing live limits",
        ),
    ],
)
def test_facade_maps_service_errors_to_exact_http_contract(
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    def fail():
        raise error

    with pytest.raises(HTTPException) as raised:
        facade._call_service(fail)

    assert raised.value.status_code == status_code
    assert raised.value.detail == detail
