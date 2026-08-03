import pytest
from fastapi import HTTPException

from app import venue_reconciliation
from app import venue_reconciliation_runtime_client as runtime_client
from app import venue_reconciliation_service as service
from app.venue_reconciliation_schemas import ResolveDifferenceRequest, VenueReconciliationRunRequest


def raise_error(error: Exception):
    def operation(*args, **kwargs):
        raise error

    return operation


def test_service_uses_explicit_domain_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        service.repository,
        "load_strategy_instance_id_for_command",
        lambda command_id: None,
    )
    with pytest.raises(service.MissingAuthoritativeStrategyError) as strategy_error:
        service.strategy_for_order({"command_id": "command-1"})
    assert str(strategy_error.value) == (
        "Order has no authoritative StrategyInstance and cannot enter formal reconciliation"
    )

    monkeypatch.setattr(
        service.repository,
        "has_active_strategy_account",
        lambda strategy_instance_id, account_id: False,
    )
    with pytest.raises(service.StrategyAccountNotBoundError) as binding_error:
        service.validate_strategy_account("strategy-1", "account-1")
    assert str(binding_error.value) == "Account is not actively bound to strategy"


def test_facade_preserves_runtime_error_mapping(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "runtime_get",
        raise_error(runtime_client.RuntimeQueryError("Execution Runtime query failed")),
    )

    with pytest.raises(HTTPException) as exc_info:
        venue_reconciliation.runtime_get("/venue/positions")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Execution Runtime query failed"
    assert isinstance(exc_info.value.__cause__, runtime_client.RuntimeQueryError)


@pytest.mark.parametrize(
    ("operation_name", "error", "args", "status_code", "detail"),
    [
        (
            "strategy_for_order",
            service.MissingAuthoritativeStrategyError("missing"),
            ({"command_id": "command-1"},),
            422,
            "Order has no authoritative StrategyInstance and cannot enter formal reconciliation",
        ),
        (
            "run_account_reconciliation",
            service.ReconciliationIdempotencyConflictError("conflict"),
            (
                VenueReconciliationRunRequest(
                    idempotencyKey="key-1",
                    strategyInstanceId="strategy-1",
                    accountId="account-1",
                    actor="tester",
                ),
            ),
            409,
            "Reconciliation idempotency key was reused with a different payload",
        ),
        (
            "validate_strategy_account",
            service.StrategyAccountNotBoundError("forbidden"),
            ("strategy-1", "account-1"),
            403,
            "Account is not actively bound to strategy",
        ),
        (
            "get_run",
            service.ReconciliationRunNotFoundError("missing"),
            ("run-1",),
            404,
            "Reconciliation run not found",
        ),
        (
            "resolve_difference",
            service.ReconciliationDifferenceNotFoundError("missing"),
            (
                "difference-1",
                ResolveDifferenceRequest(
                    status="resolved",
                    actor="tester",
                    reason="resolved in test",
                ),
            ),
            404,
            "Reconciliation difference not found",
        ),
    ],
)
def test_facade_preserves_domain_error_http_contract(
    monkeypatch,
    operation_name: str,
    error: Exception,
    args: tuple[object, ...],
    status_code: int,
    detail: str,
) -> None:
    monkeypatch.setattr(service, operation_name, raise_error(error))

    with pytest.raises(HTTPException) as exc_info:
        getattr(venue_reconciliation, operation_name)(*args)

    assert exc_info.value.status_code == status_code
    assert exc_info.value.detail == detail
    assert exc_info.value.__cause__ is error


def test_facade_preserves_repository_and_service_compatibility_aliases() -> None:
    assert venue_reconciliation.SCHEMA_SQL is service.repository.SCHEMA_SQL
    assert venue_reconciliation.ensure_schema is service.repository.ensure_schema
    assert venue_reconciliation.audit is service.repository.audit
    assert venue_reconciliation.create_difference is service.repository.store_difference
    assert venue_reconciliation.run_from_row is service.repository.run_from_row
    assert venue_reconciliation.difference_from_row is service.repository.difference_from_row
    assert venue_reconciliation.now_iso is service.now_iso
    assert venue_reconciliation.canonical_hash is service.canonical_hash
