"""Validate the lightweight Agent context entrypoints.

The check deliberately validates only repository facts and context-governance
rules. Product UI standards, task progress and live GitHub status belong to
their own owners and must not be duplicated here.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PORT = "4373"
BACKEND_PORT = "8000"
RUNTIME_PORT = "8100"
STALE_BRANCHES = (
    "feature/issue-117-platform-0-9-1",
    "feature/issue-117-platform-0.9.1",
)
CONTEXT_PACKS = (
    "hedge-style",
    "research-field",
    "identity-permission",
    "member-contract",
    "trading-display",
    "research-provider",
    "user-e2e",
)


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def pyproject_version(relative_path: str) -> str:
    with (ROOT / relative_path).open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def frontend_version(relative_path: str) -> str:
    content = read_text(relative_path)
    match = re.search(r'VITE_GLOB_APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
    require(match is not None, f"Missing frontend version in {relative_path}")
    return match.group(1)


def main() -> None:
    required = (
        "AGENTS.md",
        "README.md",
        "docs/codex/current-state.md",
        "docs/codex/context-map.md",
        "docs/architecture/OWNERSHIP.md",
        "docs/contracts/README.md",
        "scripts/context-for.py",
    )
    for relative_path in required:
        require((ROOT / relative_path).is_file(), f"Missing context entrypoint: {relative_path}")

    agents = read_text("AGENTS.md")
    readme = read_text("README.md")
    current_state = read_text("docs/codex/current-state.md")
    context_map = read_text("docs/codex/context-map.md")
    context_tool = read_text("scripts/context-for.py")
    dev_script = read_text("scripts/dev-platform.ps1")
    vite_config = read_text("platform-web/vite.config.ts")
    package_json = json.loads(read_text("platform-web/package.json"))

    expected_version = read_text("VERSION").strip()
    actual_versions = {
        "platform-api": pyproject_version("platform-api/pyproject.toml"),
        "execution-runtime": pyproject_version("execution-runtime/pyproject.toml"),
        "platform-web package": str(package_json.get("version", "")),
        "frontend development": frontend_version("platform-web/.env.development"),
        "frontend production": frontend_version("platform-web/.env.production"),
    }
    drift = {name: value for name, value in actual_versions.items() if value != expected_version}
    require(not drift, f"Version declarations drifted from VERSION={expected_version}: {drift}")
    require(
        f"Current target version: Platform `{expected_version}`" in current_state,
        "current-state.md does not match root VERSION",
    )

    package_manager = str(package_json.get("packageManager", ""))
    require(package_manager.startswith("pnpm@"), "Frontend packageManager is missing or invalid")
    require(package_manager in current_state, "current-state.md is missing the package-manager authority")

    require(f"port: {FRONTEND_PORT}" in vite_config, "Frontend Vite port drifted")
    for port, label in {
        FRONTEND_PORT: "Platform Web",
        BACKEND_PORT: "Platform API",
        RUNTIME_PORT: "Platform Execution Runtime",
    }.items():
        require(port in dev_script, f"dev-platform.ps1 is missing the {label} port")

    for path_name, text in {
        "AGENTS.md": agents,
        "README.md": readme,
        "context-map.md": context_map,
    }.items():
        require(
            "docs/codex/current-state.md" in text,
            f"{path_name} must link to the sole current-state authority",
        )
        for stale in STALE_BRANCHES:
            require(stale not in text, f"{path_name} contains stale branch authority: {stale}")

    require(
        "sole repository document for current version, branch, phase and known limits" in current_state,
        "current-state.md must declare its bounded authority",
    )
    require(
        "docs/architecture/OWNERSHIP.md" in current_state
        and "docs/contracts/README.md" in current_state,
        "current-state.md must link ownership and domain contracts",
    )
    require(
        "GitHub PR #141" in current_state
        and "active branch, Draft PR, HEAD, CI and review state" in current_state,
        "current-state.md must delegate volatile delivery state to GitHub PR #141",
    )

    require(
        "## Executable task packs" in context_map
        and "python scripts/context-for.py --list" in context_map,
        "context-map.md must expose the context-pack tool",
    )
    require(
        "## Bounded task packs" in context_map
        and "## Default exclusions" in context_map
        and "## Authority rules" in context_map,
        "context-map.md is missing bounded task-routing sections",
    )
    for pack in CONTEXT_PACKS:
        require(pack in context_map, f"context-map.md is missing tool key: {pack}")
        require(f'"{pack}"' in context_tool, f"context-for.py is missing task pack: {pack}")

    for required_pack in (
        "A-share/Shenwan/research field",
        "Identity/permission/session",
        "Member holdings/NAV",
        "Trading execution/risk",
        "Financial Fact/PnL/NAV/accounting",
        "Runtime adapter",
    ):
        require(required_pack in context_map, f"context-map.md is missing task pack: {required_pack}")

    for noisy in (
        "node_modules",
        "lock files",
        "tasks/",
        "projects/risk-control",
        "src/views/demo",
        "Plan",
        "Handoff",
        "Audit",
        "Superseded",
    ):
        require(noisy in context_map, f"context-map.md is missing default exclusion: {noisy}")

    for forbidden_context_path in ("PLAN.md", "HANDOFF.md", "AUDIT.md", "SUPERSEDED.md"):
        require(
            forbidden_context_path not in context_tool.upper(),
            f"context-for.py must not load historical material: {forbidden_context_path}",
        )

    require(
        "Browser ambient state is evidence only" in context_map,
        "context-map.md is missing browser evidence discipline",
    )
    require(
        "## Context budgets" in context_map
        and "python scripts/context-for.py --check-budgets --json" in context_map
        and "4,000 estimated tokens" in context_map,
        "context-map.md is missing executable budget governance",
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/context-for.py"), "--check-budgets", "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    print(f"Codex context checks passed for Platform {expected_version}.")


if __name__ == "__main__":
    main()
