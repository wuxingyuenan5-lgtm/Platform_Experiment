#!/usr/bin/env python3
"""Generate deterministic static architecture evidence for the maintained Platform codebase."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ROOTS = (
    ROOT / "platform-api" / "app",
    ROOT / "execution-runtime" / "app",
    ROOT / "platform-web" / "src",
)
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".vue"}
IGNORED_PARTS = {"node_modules", "dist", "build", "coverage", ".venv", "__pycache__"}
COMPATIBILITY_PATTERN = re.compile(
    r"\b(legacy|deprecated|replica|compatibility|compat|alias|re[- ]?export)\b",
    re.IGNORECASE,
)
TYPE_DEBT_PATTERNS = {
    "ts_nocheck": re.compile(r"@ts-nocheck"),
    "ts_ignore": re.compile(r"@ts-ignore"),
    "eslint_disable": re.compile(r"eslint-disable"),
    "python_type_ignore": re.compile(r"#\s*type:\s*ignore"),
    "python_any": re.compile(r"\bAny\b"),
}
DIRECT_SQL_PATTERN = re.compile(
    r"\b(SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|CREATE\s+TABLE|ALTER\s+TABLE)\b",
    re.IGNORECASE,
)
EXTERNAL_CLIENT_PATTERN = re.compile(
    r"\b(httpx|requests|aiohttp|fetch\s*\(|axios|WebSocket|MT5|Bybit|Binance)\b",
    re.IGNORECASE,
)
GLOBAL_STATE_PATTERN = re.compile(r"^(?:[A-Z][A-Z0-9_]+|_[A-Za-z0-9_]+)\s*=", re.MULTILINE)
TS_IMPORT_PATTERN = re.compile(
    r"(?:import\s+(?:type\s+)?(?:[^;]*?\s+from\s+)?|export\s+[^;]*?\s+from\s+|import\s*\()"
    r"[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
VUE_SCRIPT_PATTERN = re.compile(r"<script[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)
ROUTE_CONTRACT_PATTERN = re.compile(r"\b(APIRouter|router\.(?:get|post|put|patch|delete)|RouteRecordRaw)\b")


@dataclass(frozen=True)
class FileMetric:
    path: str
    domain: str
    language: str
    lines: int
    bytes: int
    sha256: str
    symbol_count: int
    responsibility_markers: tuple[str, ...]
    imports: tuple[str, ...]
    import_fan_out: int
    import_fan_in: int
    cross_domain_imports: int
    direct_sql_matches: int
    external_client_matches: int
    global_state_matches: int
    type_debt: dict[str, int]
    compatibility_matches: tuple[str, ...]
    contract_markers: int


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def domain_for(path: Path) -> str:
    rel = relative(path)
    if rel.startswith("platform-api/app/"):
        return "platform-api"
    if rel.startswith("execution-runtime/app/"):
        return "execution-runtime"
    if rel.startswith("platform-web/src/"):
        parts = rel.split("/")
        if "views" in parts:
            index = parts.index("views")
            return f"platform-web:{parts[index + 1]}" if len(parts) > index + 1 else "platform-web"
        return "platform-web"
    return "other"


def iter_sources() -> Iterable[Path]:
    for root in PRODUCTION_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if (
                path.is_file()
                and path.suffix in SOURCE_SUFFIXES
                and not IGNORED_PARTS.intersection(path.parts)
            ):
                yield path


def python_imports_and_symbols(text: str) -> tuple[tuple[str, ...], int]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return (), 0
    imports: list[str] = []
    symbols = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols += 1
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return tuple(sorted({item for item in imports if item})), symbols


def ts_imports_and_symbols(text: str) -> tuple[tuple[str, ...], int]:
    script = "\n".join(VUE_SCRIPT_PATTERN.findall(text)) if "<script" in text else text
    imports = tuple(sorted(set(TS_IMPORT_PATTERN.findall(script))))
    symbols = sum(
        len(pattern.findall(script))
        for pattern in (
            re.compile(r"\bfunction\s+[A-Za-z_$][\w$]*"),
            re.compile(r"\bclass\s+[A-Za-z_$][\w$]*"),
            re.compile(r"\b(?:const|let)\s+[A-Za-z_$][\w$]*\s*=\s*(?:async\s*)?\("),
            re.compile(r"\bdefineComponent\s*\("),
        )
    )
    return imports, symbols


def responsibility_markers(text: str) -> tuple[str, ...]:
    markers: list[str] = []
    checks = {
        "http": r"\b(APIRouter|FastAPI|router\.|Request|Response)\b",
        "sql": DIRECT_SQL_PATTERN,
        "external-client": EXTERNAL_CLIENT_PATTERN,
        "policy": r"\b(policy|permission|risk|kill switch|reconciliation|accounting|pnl|nav)\b",
        "state": r"\b(store|ref\(|reactive\(|computed\(|global)\b",
        "view": r"<template|defineComponent|\.vue\b",
        "lifecycle": r"\b(lifespan|startup|shutdown|onMounted|onUnmounted)\b",
    }
    for name, pattern in checks.items():
        compiled = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, re.IGNORECASE)
        if compiled.search(text):
            markers.append(name)
    return tuple(markers)


def resolve_internal_import(path: Path, specifier: str, known: set[str]) -> str | None:
    if path.suffix == ".py":
        if specifier.startswith("app."):
            candidate = "platform-api/" + specifier.replace(".", "/") + ".py"
            if candidate in known:
                return candidate
            candidate = "execution-runtime/" + specifier.replace(".", "/") + ".py"
            return candidate if candidate in known else None
        return None
    if specifier.startswith("@/"):
        base = ROOT / "platform-web" / "src" / specifier[2:]
    elif specifier.startswith("."):
        base = path.parent / specifier
    else:
        return None
    candidates = [
        base,
        *[base.with_suffix(suffix) for suffix in SOURCE_SUFFIXES],
        *[(base / "index").with_suffix(suffix) for suffix in SOURCE_SUFFIXES],
    ]
    for candidate in candidates:
        try:
            rel = relative(candidate.resolve())
        except ValueError:
            continue
        if rel in known:
            return rel
    return None


def collect() -> dict[str, object]:
    paths = list(iter_sources())
    known = {relative(path) for path in paths}
    parsed: dict[str, tuple[Path, str, tuple[str, ...], int]] = {}
    internal_edges: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        imports, symbols = (
            python_imports_and_symbols(text)
            if path.suffix == ".py"
            else ts_imports_and_symbols(text)
        )
        rel = relative(path)
        parsed[rel] = (path, text, imports, symbols)
        for specifier in imports:
            resolved = resolve_internal_import(path, specifier, known)
            if resolved:
                internal_edges[rel].add(resolved)
    fan_in: Counter[str] = Counter(
        target for targets in internal_edges.values() for target in targets
    )
    metrics: list[FileMetric] = []
    for rel, (path, text, imports, symbols) in sorted(parsed.items()):
        source_domain = domain_for(path)
        cross_domain = sum(
            1
            for target in internal_edges[rel]
            if domain_for(ROOT / target) != source_domain
        )
        compatibility = tuple(
            sorted(
                {match.group(0) for match in COMPATIBILITY_PATTERN.finditer(text)},
                key=str.lower,
            )
        )
        type_debt = {
            name: len(pattern.findall(text))
            for name, pattern in TYPE_DEBT_PATTERNS.items()
        }
        metrics.append(
            FileMetric(
                path=rel,
                domain=source_domain,
                language=path.suffix.lstrip("."),
                lines=len(text.splitlines()),
                bytes=len(text.encode("utf-8")),
                sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                symbol_count=symbols,
                responsibility_markers=responsibility_markers(text),
                imports=imports,
                import_fan_out=len(internal_edges[rel]),
                import_fan_in=fan_in[rel],
                cross_domain_imports=cross_domain,
                direct_sql_matches=len(DIRECT_SQL_PATTERN.findall(text)),
                external_client_matches=len(EXTERNAL_CLIENT_PATTERN.findall(text)),
                global_state_matches=len(GLOBAL_STATE_PATTERN.findall(text)),
                type_debt=type_debt,
                compatibility_matches=compatibility,
                contract_markers=len(ROUTE_CONTRACT_PATTERN.findall(text)),
            )
        )
    cycles = find_cycles(internal_edges)
    return {
        "schema_version": 1,
        "root": ".",
        "production_file_count": len(metrics),
        "metrics": [asdict(item) for item in metrics],
        "internal_edges": {
            key: sorted(value)
            for key, value in sorted(internal_edges.items())
            if value
        },
        "cycles": cycles,
    }


def find_cycles(edges: dict[str, set[str]]) -> list[list[str]]:
    cycles: set[tuple[str, ...]] = set()
    visiting: list[str] = []
    active: set[str] = set()
    complete: set[str] = set()

    def visit(node: str) -> None:
        if node in complete:
            return
        if node in active:
            start = visiting.index(node)
            cycle = visiting[start:] + [node]
            rotations = [
                tuple(cycle[index:-1] + cycle[:index] + [cycle[index]])
                for index in range(len(cycle) - 1)
            ]
            cycles.add(min(rotations))
            return
        active.add(node)
        visiting.append(node)
        for target in sorted(edges.get(node, ())):
            visit(target)
        visiting.pop()
        active.remove(node)
        complete.add(node)

    for node in sorted(edges):
        visit(node)
    return [list(cycle) for cycle in sorted(cycles)]


def write_reports(output_dir: Path, result: dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics = result["metrics"]
    assert isinstance(metrics, list)
    hotspots = sorted(
        metrics,
        key=lambda item: (
            item["lines"]
            + 80 * item["cross_domain_imports"]
            + 20 * len(item["responsibility_markers"]),
            item["path"],
        ),
        reverse=True,
    )
    compatibility = [item for item in metrics if item["compatibility_matches"]]
    type_debt = [item for item in metrics if any(item["type_debt"].values())]
    contracts = [item for item in metrics if item["contract_markers"]]
    totals = {
        "production_files": len(metrics),
        "production_lines": sum(item["lines"] for item in metrics),
        "production_bytes": sum(item["bytes"] for item in metrics),
        "direct_sql_matches": sum(item["direct_sql_matches"] for item in metrics),
        "type_debt_matches": sum(
            sum(item["type_debt"].values()) for item in metrics
        ),
        "cross_domain_imports": sum(item["cross_domain_imports"] for item in metrics),
        "cycle_count": len(result["cycles"]),
    }
    reports = {
        "platform-0-9-3-phase-4-hotspots.json": {
            "schema_version": 1,
            "hotspots": hotspots,
        },
        "platform-0-9-3-phase-4-import-graph.json": {
            "schema_version": 1,
            "edges": result["internal_edges"],
            "cycles": result["cycles"],
        },
        "platform-0-9-3-phase-4-compatibility-inventory.json": {
            "schema_version": 1,
            "candidates": compatibility,
        },
        "platform-0-9-3-phase-4-type-debt.json": {
            "schema_version": 1,
            "files": type_debt,
        },
        "platform-0-9-3-phase-4-contract-inventory.json": {
            "schema_version": 1,
            "files": contracts,
        },
        "platform-0-9-3-phase-4-before-metrics.json": {
            "schema_version": 1,
            "totals": totals,
        },
    }
    for name, payload in reports.items():
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    write_reports(args.output_dir, collect())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
