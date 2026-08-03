"""Validate lightweight Codex collaboration context.

This check intentionally stays small. It verifies stable local facts that cause
expensive re-orientation when they drift: version, ports, package manager and
the current Codex context entrypoint.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.9.1"
EXPECTED_MAIN_BASELINE = "a4e22021c71cf5cd703cb0bc35676ff5adbfec36"
EXPECTED_FRONTEND_PORT = "4373"
EXPECTED_BACKEND_PORT = "8000"
EXPECTED_RUNTIME_PORT = "8100"
EXPECTED_PNPM = "pnpm@9.15.9"


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def pyproject_version(relative_path: str) -> str:
    with (ROOT / relative_path).open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def main() -> None:
    context_path = ROOT / "docs/codex/CURRENT_CONTEXT.md"
    require(context_path.exists(), "Missing docs/codex/CURRENT_CONTEXT.md")

    context = context_path.read_text(encoding="utf-8")
    context_map = read_text("docs/codex/context-map.md")
    lightweight_plan = read_text("docs/architecture/LIGHTWEIGHT_OPTIMIZATION_PLAN.md")
    readme = read_text("README.md")
    root_agents = read_text("AGENTS.md")
    package_json = json.loads(read_text("admin-risk/package.json"))
    vite_config = read_text("admin-risk/vite.config.ts")
    frontend_env = read_text("admin-risk/.env.development")
    dev_script = read_text("scripts/dev-platform.ps1")
    ui_guidelines = read_text("admin-risk/docs/design/platform-ui-guidelines.md")

    version_files = {
        "VERSION": read_text("VERSION").strip(),
        "platform-backend": pyproject_version("platform-backend/pyproject.toml"),
        "execution-runtime": pyproject_version("execution-runtime/pyproject.toml"),
    }
    for name, version in version_files.items():
        require(version == EXPECTED_VERSION, f"{name} version drifted: {version}")

    require(
        f'VITE_GLOB_APP_VERSION = "{EXPECTED_VERSION}"' in frontend_env,
        "Frontend display version drifted in admin-risk/.env.development",
    )
    require(
        package_json.get("packageManager") == EXPECTED_PNPM,
        "admin-risk/package.json packageManager drifted",
    )
    require(
        f"port: {EXPECTED_FRONTEND_PORT}" in vite_config,
        "Frontend Vite port drifted",
    )

    for text_name, text in {
        "CURRENT_CONTEXT.md": context,
        "README.md": readme,
        "AGENTS.md": root_agents,
    }.items():
        require(EXPECTED_VERSION in text, f"{text_name} is missing product version")
        require(EXPECTED_FRONTEND_PORT in text, f"{text_name} is missing frontend port")

    require(EXPECTED_MAIN_BASELINE in root_agents, "AGENTS.md main baseline drifted")
    require(EXPECTED_MAIN_BASELINE in context, "CURRENT_CONTEXT.md main baseline drifted")
    require("docs/codex/CURRENT_CONTEXT.md" in readme, "README.md does not link current context")
    require("docs/codex/CURRENT_CONTEXT.md" in context_map, "context-map does not prefer CURRENT_CONTEXT.md")

    for port, label in {
        EXPECTED_FRONTEND_PORT: "frontend",
        EXPECTED_BACKEND_PORT: "backend",
        EXPECTED_RUNTIME_PORT: "runtime",
    }.items():
        require(port in context, f"CURRENT_CONTEXT.md is missing {label} port")
        require(port in readme, f"README.md is missing {label} port")
        require(port in dev_script, f"dev-platform.ps1 is missing {label} port")

    banned_default_context = [
        "admin-risk/CHANGELOG.md",
        "admin-risk/project_structure.txt",
    ]
    for banned in banned_default_context:
        require(
            banned not in context,
            f"CURRENT_CONTEXT.md should not promote noisy context: {banned}",
        )

    require(
        "admin-risk/docs/design/platform-ui-guidelines.md" in context,
        "CURRENT_CONTEXT.md should point UI standards to platform-ui-guidelines.md",
    )
    require(
        "Hedge board research subnav uses same black" not in context
        and "market-detail widgets must not repeat" not in context,
        "CURRENT_CONTEXT.md should not own detailed UI standards",
    )
    require(
        "对冲基金研究子导航标准字号为 `14px`" in ui_guidelines,
        "platform-ui-guidelines.md is missing hedge board subnav typography standard",
    )
    require(
        "内部 `TerminalDetailPanel` 不再重复显示“市场明细”" in ui_guidelines,
        "platform-ui-guidelines.md is missing market detail duplicate-title standard",
    )
    require(
        "Georgia, Times New Roman, Noto Serif SC, serif" in ui_guidelines
        and "`18px`" in ui_guidelines
        and "`30px`" in ui_guidelines,
        "platform-ui-guidelines.md is missing login title typography standard",
    )
    require(
        re.search(r"npx\.cmd pnpm@9\.15\.9 type:check", context) is not None,
        "CURRENT_CONTEXT.md should list the Windows-safe frontend type check",
    )
    require(
        "Light UI tweak" in context
        and "Do not run the full frontend guard set for every small UI tweak" in context,
        "CURRENT_CONTEXT.md is missing lightweight UI execution tiers",
    )
    require(
        "小 UI 微调默认不更新 md、不新增守卫、不跑全量前端检查" in lightweight_plan,
        "LIGHTWEIGHT_OPTIMIZATION_PLAN.md is missing lightweight UI token discipline",
    )
    require(
        "Browser ambient state is evidence only" in context_map,
        "context-map.md is missing browser ambient-state discipline",
    )

    print("Codex context checks passed.")


if __name__ == "__main__":
    main()
