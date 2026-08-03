from fastapi import HTTPException

from app.database import connection
from app.schemas import StrategyV1ReadinessResponse


def get_strategy_v1_readiness(strategy_instance_id: str) -> StrategyV1ReadinessResponse:
    with connection() as db:
        strategy = db.execute(
            """
            SELECT sd.strategy_key, sd.v1_scope, si.status AS instance_status,
                   si.capital_base, si.data_quality_state
            FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ?
            """,
            (strategy_instance_id,),
        ).fetchone()
        if strategy is None:
            raise HTTPException(status_code=404, detail="Strategy instance not found")

        latest_run = db.execute(
            """
            SELECT status
            FROM strategy_runs
            WHERE strategy_instance_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (strategy_instance_id,),
        ).fetchone()
        manual_intervention_count = db.execute(
            """
            SELECT COUNT(*) AS value
            FROM execution_batches
            WHERE strategy_instance_id = ? AND requires_manual_intervention = 1
            """,
            (strategy_instance_id,),
        ).fetchone()["value"]
        result_unknown_order_count = db.execute(
            """
            SELECT COUNT(*) AS value
            FROM orders o
            JOIN execution_batch_legs ebl ON ebl.order_id = o.id
            JOIN execution_batches eb ON eb.id = ebl.batch_id
            WHERE eb.strategy_instance_id = ? AND o.status = 'result_unknown'
            """,
            (strategy_instance_id,),
        ).fetchone()["value"]

    blockers: list[str] = []
    warnings: list[str] = []
    if strategy["v1_scope"] != "closed_loop":
        blockers.append("Strategy is not in V1 closed-loop scope")
    if strategy["instance_status"] != "active":
        blockers.append("Strategy instance is not active")
    if strategy["capital_base"] is None:
        warnings.append("Strategy has no capital base; NAV snapshots will be unavailable")
    if strategy["data_quality_state"] != "complete":
        warnings.append("Strategy data quality is incomplete")
    if manual_intervention_count:
        warnings.append("Manual intervention batches exist")
    if result_unknown_order_count:
        warnings.append("Result-unknown orders exist and need reconciliation")

    return StrategyV1ReadinessResponse(
        strategyInstanceId=strategy_instance_id,
        strategyKey=strategy["strategy_key"],
        runnable=not blockers and result_unknown_order_count == 0,
        blockers=blockers,
        warnings=warnings,
        latestRunStatus=latest_run["status"] if latest_run is not None else None,
        manualInterventionCount=manual_intervention_count,
        resultUnknownOrderCount=result_unknown_order_count,
    )
