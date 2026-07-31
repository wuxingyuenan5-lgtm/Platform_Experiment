#!/usr/bin/env python3
"""Produce read-only evidence for the Platform Research modularization workstream."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PythonFileMetric:
    path: str
    lines: int
    app_imports: list[str]
    top_level_symbols: int
    largest_symbol: str | None
    largest_symbol_lines: int


@dataclass(frozen=True)
class FrontendFileMetric:
    path: str
    lines: int
    template_lines: int | None
    script_lines: int | None
    style_lines: int | None
    inline_define_components: list[str]


def _service_roots(root: Path) -> tuple[Path, Path]:
    web = root / "platform-web"
    api = root / "platform-api"
    if not web.exists():
        web = root / "admin-risk"
    if not api.exists():
        api = root / "platform-backend"
    if not web.exists() or not api.exists():
        raise SystemExit("platform-web/platform-api service roots were not found")
    return web, api


def _python_metric(path: Path, root: Path) -> PythonFileMetric:
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    imports: list[str] = []
    symbols: list[tuple[str, int]] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
            imports.append(node.module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end = getattr(node, "end_lineno", node.lineno)
            symbols.append((node.name, end - node.lineno + 1))
    largest = max(symbols, key=lambda item: item[1], default=(None, 0))
    return PythonFileMetric(
        path=path.relative_to(root).as_posix(),
        lines=len(text.splitlines()),
        app_imports=sorted(set(imports)),
        top_level_symbols=len(symbols),
        largest_symbol=largest[0],
        largest_symbol_lines=largest[1],
    )


def _block_lines(text: str, tag: str) -> int | None:
    match = re.search(rf"<{tag}(?:\s[^>]*)?>.*?</{tag}>", text, re.DOTALL)
    return len(match.group(0).splitlines()) if match else None


def _frontend_metric(path: Path, root: Path) -> FrontendFileMetric:
    text = path.read_text(encoding="utf-8-sig")
    names = re.findall(r"const\s+(\w+)\s*=\s*defineComponent\(", text)
    return FrontendFileMetric(
        path=path.relative_to(root).as_posix(),
        lines=len(text.splitlines()),
        template_lines=_block_lines(text, "template") if path.suffix == ".vue" else None,
        script_lines=_block_lines(text, "script") if path.suffix == ".vue" else None,
        style_lines=_block_lines(text, "style") if path.suffix == ".vue" else None,
        inline_define_components=names,
    )


def build_report(root: Path) -> dict[str, Any]:
    web, api = _service_roots(root)
    app = api / "app"
    backend_paths = sorted(app.glob("research*.py"))
    backend_paths.append(app / "a_share_research_policy.py")
    backend_paths = sorted({path for path in backend_paths if path.exists()})

    hedge = web / "src/views/hedgeBoard"
    frontend_paths = [
        hedge / "index.vue",
        hedge / "aShare/index.vue",
        hedge / "aShare/useAShareResearch.ts",
        web / "src/api/hedgeResearch.ts",
        *sorted((hedge / "aShare/components").glob("*.vue")),
    ]
    frontend_paths = [path for path in frontend_paths if path.exists()]

    provider_text = (app / "research_providers.py").read_text(encoding="utf-8-sig")
    provider_tree = ast.parse(provider_text)
    provider_class = next(
        node
        for node in provider_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FreeResearchProvider"
    )
    provider_methods = [
        node.name
        for node in provider_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    service_text = (app / "research_service.py").read_text(encoding="utf-8-sig")
    provider_calls = sorted(set(re.findall(r"_PROVIDER\.([A-Za-z_]\w*)", service_text)))
    routes_text = (app / "research_routes.py").read_text(encoding="utf-8-sig")
    routes = re.findall(r'@router\.get\("([^"]+)"', routes_text)

    return {
        "service_roots": {
            "web": web.relative_to(root).as_posix(),
            "api": api.relative_to(root).as_posix(),
        },
        "backend": {
            "files": [asdict(_python_metric(path, root)) for path in backend_paths],
            "provider_class_lines": getattr(provider_class, "end_lineno", provider_class.lineno)
            - provider_class.lineno
            + 1,
            "provider_methods": provider_methods,
            "service_provider_calls": provider_calls,
            "routes": routes,
        },
        "frontend": {
            "files": [asdict(_frontend_metric(path, root)) for path in frontend_paths],
        },
        "protected_contracts": {
            "research_statuses": ["loading", "ready", "partial", "no_data", "stale", "error"],
            "api_routes": routes,
            "last_known_good": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    backend = report["backend"]
    frontend = report["frontend"]
    lines = [
        "# Research modularization inventory",
        "",
        f"- Platform Web root: `{report['service_roots']['web']}`",
        f"- Platform API root: `{report['service_roots']['api']}`",
        f"- FreeResearchProvider class: {backend['provider_class_lines']} lines / {len(backend['provider_methods'])} methods",
        f"- Provider methods consumed by service: {len(backend['service_provider_calls'])}",
        f"- Research GET routes: {len(backend['routes'])}",
        "",
        "## Backend files",
        "",
        "| File | Lines | Largest top-level symbol | Symbol lines | Internal imports |",
        "|---|---:|---|---:|---|",
    ]
    for item in backend["files"]:
        imports = ", ".join(f"`{value}`" for value in item["app_imports"]) or "—"
        lines.append(
            f"| `{item['path']}` | {item['lines']} | `{item['largest_symbol'] or '—'}` | "
            f"{item['largest_symbol_lines']} | {imports} |"
        )
    lines.extend(
        [
            "",
            "## Frontend files",
            "",
            "| File | Lines | Template | Script | Style | Inline components |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for item in frontend["files"]:
        components = ", ".join(f"`{name}`" for name in item["inline_define_components"]) or "—"
        lines.append(
            f"| `{item['path']}` | {item['lines']} | {item['template_lines'] or '—'} | "
            f"{item['script_lines'] or '—'} | {item['style_lines'] or '—'} | {components} |"
        )
    lines.extend(
        [
            "",
            "## Stable contracts",
            "",
            *[f"- `GET {route}`" for route in backend["routes"]],
            "- Last Known Good fallback remains mandatory.",
            "- Status vocabulary remains `loading/ready/partial/no_data/stale/error`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.root.resolve())
    output = json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else render_markdown(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
