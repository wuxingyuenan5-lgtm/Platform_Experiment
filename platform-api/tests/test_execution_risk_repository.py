from pathlib import Path

import pytest

from app import execution_risk_repository as repository
from app.config import get_settings
from app.database import initialize_database
from app.execution_risk_models import (
    ExecutionRiskPolicyUpdateRequest,
    KillSwitchUpdateRequest,
)

pytestmark = pytest.mark.integration

STRATEGY_INSTANCE_ID = "strategy_funding_arbitrage_instance_default"


def prepare_database(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "execution-risk-repository.db")
    initialize_database()
    repository.ensure_schema()


def test_repository_persists_kill_switch_and_policy_idempotently(
    tmp_path: Path,
) -> None:
    prepare_database(tmp_path)

    switch_request = KillSwitchUpdateRequest(
        idempotencyKey="repository-kill-switch-001",
        enabled=True,
        reason="repository test",
        actor="risk-test",
    )
    first_switch = repository.set_kill_switch("global", "*", switch_request)
    replayed_switch = repository.set_kill_switch("global", "*", switch_request)

    assert first_switch == replayed_switch
    assert repository.first_enabled_kill_switch(
        STRATEGY_INSTANCE_ID, []
    ) == ("global", "*", "repository test")

    policy_request = ExecutionRiskPolicyUpdateRequest(
        idempotencyKey="repository-risk-policy-001",
        maxLegDelaySeconds=12,
        maxResidualNotional="250.125",
        failureAction="auto_flatten",
        actor="risk-test",
    )
    first_policy = repository.set_execution_risk_policy(
        STRATEGY_INSTANCE_ID, policy_request
    )
    replayed_policy = repository.set_execution_risk_policy(
        STRATEGY_INSTANCE_ID, policy_request
    )

    assert first_policy == replayed_policy
    assert first_policy.max_residual_notional.as_tuple().exponent == -3
    assert repository.get_configured_policy(STRATEGY_INSTANCE_ID) == first_policy


def test_repository_rejects_idempotency_key_payload_reuse(tmp_path: Path) -> None:
    prepare_database(tmp_path)
    first = KillSwitchUpdateRequest(
        idempotencyKey="repository-conflict-001",
        enabled=True,
        reason="first",
        actor="risk-test",
    )
    repository.set_kill_switch("global", "*", first)

    with pytest.raises(
        repository.IdempotencyConflictError,
        match="different payload",
    ):
        repository.set_kill_switch(
            "global",
            "*",
            KillSwitchUpdateRequest(
                idempotencyKey="repository-conflict-001",
                enabled=False,
                reason="second",
                actor="risk-test",
            ),
        )
