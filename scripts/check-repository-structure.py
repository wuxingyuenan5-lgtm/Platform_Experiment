"""Fail CI when permanent repository and architecture boundaries regress."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_APP = ROOT / "platform-api" / "app"
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
VISUAL_WORKFLOW = "platform-visual-baseline.yml"

EXPECTED_SERVICES = {
    "platform-web": ROOT / "platform-web",
    "platform-api": ROOT / "platform-api",
    "execution-runtime": ROOT / "execution-runtime",
}
ALLOWED_TOP_LEVEL_DIRECTORIES = {
    "00-人工可读目录",
    "config",
    "deploy",
    "docs",
    "execution-runtime",
    "platform-api",
    "platform-web",
    "references",
    "scripts",
}
REQUIRED_ENTRYPOINTS = (
    "README.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/codex/current-state.md",
    "docs/codex/context-map.md",
    "docs/architecture/SYSTEM_MAP.md",
    "docs/architecture/OWNERSHIP.md",
    "docs/operations/RUNBOOK.md",
    "docs/database/README.md",
    "docs/engineering/GIT_WORKFLOW.md",
    "docs/contracts/README.md",
)
FORBIDDEN_BACKEND_IMPORTS = {"MetaTrader5", "binance", "ccxt", "ib_insync", "pybit"}
HISTORICAL_WORKFLOW_PATTERN = re.compile(
    r"(?:0[-.]9[-.]2|0[-.]9[-.]3|phase[-_ ]?[0-6])", re.IGNORECASE
)


def imported_top_levels(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return imports


def check_root_directories(errors: list[str]) -> None:
    for name, path in EXPECTED_SERVICES.items():
        if not path.is_dir():
            errors.append(f"{name}: maintained service directory is missing")
    for path in sorted(ROOT.iterdir()):
        if (
            path.is_dir()
            and not path.name.startswith(".")
            and path.name not in ALLOWED_TOP_LEVEL_DIRECTORIES
        ):
            errors.append(
                f"{path.name}: unregistered top-level directory; maintained services are "
                "platform-web, platform-api and execution-runtime"
            )


def check_backend_venue_boundary(errors: list[str]) -> None:
    for path in sorted(BACKEND_APP.rglob("*.py")):
        forbidden = imported_top_levels(path) & FORBIDDEN_BACKEND_IMPORTS
        if forbidden:
            errors.append(
                f"{path.relative_to(ROOT)}: Platform API imports venue SDK(s) "
                f"{sorted(forbidden)}; external effects belong in execution-runtime"
            )


def check_execution_risk_boundaries(errors: list[str]) -> None:
    paths = {
        "models": BACKEND_APP / "execution_risk_models.py",
        "policy": BACKEND_APP / "execution_risk_policy.py",
        "repository": BACKEND_APP / "execution_risk_repository.py",
        "router": BACKEND_APP / "execution_risk.py",
        "application": BACKEND_APP / "application.py",
    }
    missing = [path for path in paths.values() if not path.is_file()]
    for path in missing:
        errors.append(f"{path.relative_to(ROOT)}: execution-risk owner is missing")
    if missing:
        return

    source = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    if "app.database" in source["models"] or "fastapi" in source["models"]:
        errors.append("execution_risk_models.py must not access database or HTTP")
    if any(
        token in source["policy"] for token in ("app.database", "fastapi", "connection()")
    ):
        errors.append("execution_risk_policy.py must remain pure and deterministic")
    if any(
        token in source["repository"] for token in ("fastapi", "APIRouter", "HTTPException")
    ):
        errors.append("execution_risk_repository.py must not contain HTTP logic")
    for anchor in (
        "CREATE TABLE IF NOT EXISTS trading_kill_switches",
        "CREATE TABLE IF NOT EXISTS execution_risk_policies",
        "CREATE TABLE IF NOT EXISTS execution_batch_risk",
        "CREATE TABLE IF NOT EXISTS execution_risk_actions",
    ):
        if anchor not in source["repository"]:
            errors.append(f"execution_risk_repository.py missing persistence anchor: {anchor}")
    if "from app.trade_commands import" in source["router"]:
        errors.append("execution_risk.py must not import the concrete trade-command implementation")
    if "connection()" in source["router"] or "app.database" in source["router"]:
        errors.append("execution_risk.py must not access the database directly")
    if "configure_trade_command_port" not in source["router"]:
        errors.append("execution_risk.py is missing the local trade-command port")
    if "configure_trade_command_port(create_trade_command)" not in source["application"]:
        errors.append("application.py must wire the execution-risk trade-command port")


def check_documents(errors: list[str]) -> None:
    for relative in REQUIRED_ENTRYPOINTS:
        if not (ROOT / relative).is_file():
            errors.append(f"{relative}: required active entrypoint is missing")
    current = ROOT / "docs/codex/current-state.md"
    if current.is_file():
        source = current.read_text(encoding="utf-8")
        for anchor in (
            "Platform `0.10.0`",
            "Platform `0.10.1`",
            "refactor/platform-0-10-1-non-ui-convergence",
            "Live Write",
            "Frontend product restoration is explicitly deferred",
        ):
            if anchor not in source:
                errors.append(f"docs/codex/current-state.md missing current anchor: {anchor}")
    database = ROOT / "docs/database/README.md"
    if (
        database.is_file()
        and "app/execution_risk_repository.py"
        not in database.read_text(encoding="utf-8")
    ):
        errors.append("docs/database/README.md must register execution_risk_repository.py")


def check_deployment_contract(errors: list[str]) -> None:
    path = ROOT / "platform-web/.gitlab-ci.yml"
    if not path.is_file():
        errors.append("platform-web/.gitlab-ci.yml: deployment configuration is missing")
        return
    source = path.read_text(encoding="utf-8")
    for variable in ("PLATFORM_WEB_DEPLOY_DIR", "PLATFORM_WEB_PUBLIC_URL"):
        if variable not in source:
            errors.append(
                f"platform-web/.gitlab-ci.yml missing required neutral variable {variable}"
            )
    if "${PLATFORM_WEB_DEPLOY_DIR:?" not in source:
        errors.append(
            "platform-web/.gitlab-ci.yml must fail when PLATFORM_WEB_DEPLOY_DIR is absent"
        )


def check_workflows(errors: list[str]) -> None:
    if not WORKFLOW_ROOT.is_dir():
        errors.append(".github/workflows: workflow directory is missing")
        return
    for path in sorted(WORKFLOW_ROOT.glob("*.yml")):
        relative = path.relative_to(ROOT).as_posix()
        if HISTORICAL_WORKFLOW_PATTERN.search(path.name):
            errors.append(f"{relative}: historical phase workflow is forbidden")
        if path.name == VISUAL_WORKFLOW:
            continue
        if "refactor/platform-0-9-3-" in path.read_text(encoding="utf-8"):
            errors.append(f"{relative}: historical branch trigger is forbidden")
    for relative in (
        "scripts/audit-phase-history.py",
        "scripts/audit_phase_history_core.py",
        "scripts/stacked_phase_history_git.py",
        "scripts/stacked_phase_history_model.py",
        "scripts/stacked_phase_history_metadata.py",
        "platform-api/tests/test_architecture_phase_history_audit.py",
        "platform-api/tests/test_architecture_phase_history_governance_classification.py",
        "platform-api/tests/test_architecture_stacked_phase_workflows.py",
        "platform-api/tests/test_architecture_stacked_phase_governance.py",
    ):
        if (ROOT / relative).exists():
            errors.append(f"{relative}: historical phase governance is forbidden")


def main() -> int:
    errors: list[str] = []
    check_root_directories(errors)
    check_backend_venue_boundary(errors)
    check_execution_risk_boundaries(errors)
    check_documents(errors)
    check_deployment_contract(errors)
    check_workflows(errors)
    if errors:
        print("Repository structure and architecture checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Repository structure and architecture checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
