from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "platform-backend"


def replace_function(source: str, name: str, replacement: str, next_name: str) -> str:
    start = source.index(f"def {name}")
    end = source.index(f"\ndef {next_name}", start)
    return source[:start] + replacement.rstrip() + "\n\n" + source[end + 1 :]


def update_main() -> None:
    (BACKEND / "app/main.py").write_text(
        dedent(
            '''\
            from app.application import app
            from app.auth import AuthenticationMiddleware
            from app.credential_security import router as credential_security_router
            from app.disaster_recovery import router as disaster_recovery_router
            from app.eod_reconciliation import router as eod_reconciliation_router
            from app.execution_risk import router as execution_risk_router
            from app.financial_facts import router as financial_facts_router
            from app.live_trading_sessions import router as live_trading_sessions_router
            from app.live_venue_accounting import router as live_venue_accounting_router
            from app.production_monitoring import router as production_monitoring_router
            from app.venue_reconciliation import router as venue_reconciliation_router

            app.include_router(financial_facts_router)
            app.include_router(execution_risk_router)
            app.include_router(venue_reconciliation_router)
            app.include_router(live_venue_accounting_router)
            app.include_router(eod_reconciliation_router)
            app.include_router(live_trading_sessions_router)
            app.include_router(credential_security_router)
            app.include_router(production_monitoring_router)
            app.include_router(disaster_recovery_router)

            # Authentication is added at the composition root so every legacy and modular
            # route passes through one default-deny production authorization boundary.
            app.add_middleware(AuthenticationMiddleware)

            __all__ = ["app"]
            '''
        ),
        encoding="utf-8",
    )


def update_auth() -> None:
    path = BACKEND / "app/auth.py"
    source = path.read_text(encoding="utf-8")
    replacement = dedent(
        '''\
        def permission_for_request(method: str, path: str) -> str:
            normalized_method = method.upper()
            if normalized_method in {"GET", "HEAD"}:
                audit_read_suffixes = (
                    "/security/credential-references",
                    "/security/credential-rotations",
                    "/ops/audit-events",
                    "/ops/production-status",
                    "/ops/alerts",
                    "/ops/backups",
                    "/ops/restore-drills",
                    "/ops/controlled-operations",
                )
                if any(path.endswith(suffix) for suffix in audit_read_suffixes):
                    return "audit:read"
                return "platform:read"

            if path.endswith("/live-trading/sessions") and normalized_method == "POST":
                return "live_session:request"
            if "/live-trading/sessions/" in path and path.endswith("/approve"):
                return "live_session:approve"
            if "/live-trading/sessions/" in path and path.endswith("/revoke"):
                return "live_session:revoke"

            if path.endswith("/trading/commands") or path.endswith("/trading/execution-batches"):
                return "trade:submit"
            if path.endswith("/trading/orders") and normalized_method == "POST":
                return "trade:submit"
            if path.endswith("/trading/cross-spread/market-command"):
                return "trade:submit"

            if "/risk/kill-switches/" in path or path.endswith("/execution-risk-policy"):
                return "risk:manage"
            if "/trading/execution-batches/" in path and path.endswith("/risk-actions"):
                return "risk:manage"

            if "/venue-reconciliation/differences/" in path and path.endswith("/resolve"):
                return "reconciliation:review"
            if "/eod-reconciliation/reports/" in path and path.endswith("/review"):
                return "eod:review"
            if "/ops/alerts/" in path and (
                path.endswith("/acknowledge") or path.endswith("/close")
            ):
                return "reconciliation:review"

            production_write_suffixes = (
                "/ops/alerts/scan",
                "/ops/backups",
                "/ops/restore-drills",
                "/ops/controlled-operations",
            )
            if normalized_method == "POST" and any(
                path.endswith(suffix) for suffix in production_write_suffixes
            ):
                return "operations:run"

            operations_paths = (
                "/financial-facts",
                "/financials/rebuild",
                "/ops/live-economic-events/import",
                "/ops/venue-reconciliation/runs",
                "/ops/eod-reconciliation/reports",
            )
            if any(fragment in path for fragment in operations_paths):
                return "operations:run"
            if "/strategies/instances/" in path and path.endswith("/runs"):
                return "strategy:run"
            return "admin:write"
        '''
    )
    source = replace_function(source, "permission_for_request(method: str, path: str) -> str:", replacement, "audit_auth_event(")
    path.write_text(source, encoding="utf-8")


def update_execution_risk() -> None:
    path = BACKEND / "app/execution_risk.py"
    source = path.read_text(encoding="utf-8")
    import_line = "from app.execution_exposure import calculate_residual_exposure\n"
    if import_line not in source:
        source = source.replace(
            "from app.database import connection\n",
            "from app.database import connection\n" + import_line,
            1,
        )
    start = source.index("def calculate_residual_exposure(batch_id: str) -> tuple[Decimal, str, str]:\n")
    end = source.index("\ndef execute_risk_action(", start)
    source = source[:start] + source[end + 1 :]
    path.write_text(source, encoding="utf-8")


def update_eod_reconciliation() -> None:
    path = BACKEND / "app/eod_reconciliation.py"
    source = path.read_text(encoding="utf-8")
    import_line = (
        "from app.eod_policy import apply_outstanding_difference_gate, "
        "list_strategy_orders_for_eod\n"
    )
    if import_line not in source:
        source = source.replace(
            "from app.database import connection\n",
            "from app.database import connection\n" + import_line,
            1,
        )
    list_start = source.index("def list_strategy_orders(\n")
    list_end = source.index("\ndef create_eod_report(", list_start)
    source = source[:list_start] + source[list_end + 1 :]
    source = source.replace(
        "for order_id in list_strategy_orders(\n",
        "for order_id in list_strategy_orders_for_eod(\n",
        1,
    )
    create_start = source.index("def create_eod_report(\n")
    create_end = source.index("\ndef formal_pnl_counts(", create_start)
    segment = source[create_start:create_end]
    old_return = "    return report_from_row(row)\n"
    if segment.count(old_return) != 1:
        raise RuntimeError("Unexpected create_eod_report return structure")
    replacement = dedent(
        '''\
            apply_outstanding_difference_gate(
                report_id,
                request.strategy_instance_id,
                request.account_id,
            )
            return get_eod_report(report_id)
        '''
    )
    segment = segment.replace(old_return, replacement, 1)
    source = source[:create_start] + segment + source[create_end:]
    path.write_text(source, encoding="utf-8")


def add_architecture_tests() -> None:
    (BACKEND / "tests/test_architecture_boundaries.py").write_text(
        dedent(
            '''\
            from __future__ import annotations

            import ast
            from pathlib import Path

            from app.auth import permission_for_request

            BACKEND_ROOT = Path(__file__).resolve().parents[1]


            def function_names(path: Path) -> list[str]:
                tree = ast.parse(path.read_text(encoding="utf-8"))
                return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]


            def test_composition_root_only_wires_application_components() -> None:
                source = (BACKEND_ROOT / "app/main.py").read_text(encoding="utf-8")
                forbidden_assignments = (
                    "execution_risk.calculate_residual_exposure =",
                    "eod_reconciliation.list_strategy_orders =",
                    "eod_reconciliation.create_eod_report =",
                    "auth.permission_for_request =",
                )
                assert all(marker not in source for marker in forbidden_assignments)


            def test_residual_exposure_has_one_authoritative_implementation() -> None:
                risk_functions = function_names(BACKEND_ROOT / "app/execution_risk.py")
                exposure_functions = function_names(BACKEND_ROOT / "app/execution_exposure.py")
                assert "calculate_residual_exposure" not in risk_functions
                assert exposure_functions.count("calculate_residual_exposure") == 1


            def test_eod_policy_is_an_explicit_dependency() -> None:
                source = (BACKEND_ROOT / "app/eod_reconciliation.py").read_text(encoding="utf-8")
                assert "from app.eod_policy import" in source
                assert "list_strategy_orders_for_eod(" in source
                assert "def list_strategy_orders(" not in source


            def test_production_operations_permissions_live_in_auth_policy() -> None:
                assert permission_for_request("GET", "/api/v1/ops/production-status") == "audit:read"
                assert permission_for_request("GET", "/api/v1/security/credential-rotations") == "audit:read"
                assert permission_for_request("POST", "/api/v1/ops/alerts/scan") == "operations:run"
                assert (
                    permission_for_request("POST", "/api/v1/ops/alerts/alert-1/acknowledge")
                    == "reconciliation:review"
                )
            '''
        ),
        encoding="utf-8",
    )


def update_ci_and_docs() -> None:
    ci_path = ROOT / ".github/workflows/platform-ci.yml"
    ci = ci_path.read_text(encoding="utf-8")
    entry = "            tests/test_architecture_boundaries.py \\\n"
    if entry not in ci:
        ci = ci.replace(
            "            tests/test_eod_policy.py \\\n",
            "            tests/test_eod_policy.py \\\n" + entry,
            1,
        )
    ci_path.write_text(ci, encoding="utf-8")

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    rule = "- `platform-backend/app/main.py` 仅负责 Router 与 Middleware 装配，不得通过运行时赋值修改领域模块。\n"
    if rule not in readme:
        readme = readme.replace(
            "- 未通过测试和 CI 的改动不得进入正式分支。\n",
            "- 未通过测试和 CI 的改动不得进入正式分支。\n" + rule,
            1,
        )
    readme_path.write_text(readme, encoding="utf-8")

    agents_path = ROOT / "AGENTS.md"
    agents = agents_path.read_text(encoding="utf-8")
    rule = "- Keep composition roots declarative: wire routers and middleware only; import domain policies explicitly and never monkey-patch modules.\n"
    if rule not in agents:
        agents = agents.replace(
            "- Prefer existing architecture patterns over introducing new frameworks.\n",
            "- Prefer existing architecture patterns over introducing new frameworks.\n" + rule,
            1,
        )
    agents_path.write_text(agents, encoding="utf-8")

    architecture_path = ROOT / "docs/architecture/README.md"
    architecture = architecture_path.read_text(encoding="utf-8")
    section = dedent(
        '''

        ## Composition Root 边界

        - `platform-backend/app/main.py` 只装配 Router 与 Middleware，不承载业务规则。
        - 风险敞口、EOD 策略和权限映射由各自模块显式导入，禁止运行时 monkey patch。
        - 同一业务事实只能有一个权威实现；残余敞口计算统一由 `execution_exposure.py` 提供。
        - `tests/test_architecture_boundaries.py` 对上述边界进行静态回归检查。
        '''
    )
    if "## Composition Root 边界" not in architecture:
        architecture = architecture.rstrip() + section + "\n"
    architecture_path.write_text(architecture, encoding="utf-8")


def main() -> None:
    update_main()
    update_auth()
    update_execution_risk()
    update_eod_reconciliation()
    add_architecture_tests()
    update_ci_and_docs()


if __name__ == "__main__":
    main()
