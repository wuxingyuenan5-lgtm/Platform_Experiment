#!/usr/bin/env python3
"""Audit and resolve the Phase 5 product/data owner matrix."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "config" / "product-data-owner-matrix.json"
DEFAULT_OVERRIDES = ROOT / "config" / "product-data-owner-overrides.json"
FORMAL_MANIFEST = ROOT / "platform-web" / "scripts" / "formal-route-manifest.json"

REQUIRED_ENTRY_FIELDS = {
    "module",
    "routes",
    "route_names",
    "view_owner",
    "frontend_services",
    "api_endpoints",
    "application_services",
    "repository_or_provider",
    "real_data_source",
    "permissions",
    "roles",
    "refresh",
    "as_of",
    "timezone",
    "currency",
    "unit",
    "precision",
    "empty_state",
    "unavailable_state",
    "fallback",
    "writes",
    "live_write",
    "e2e",
    "provider_smoke",
    "closure_status",
    "gap_reason",
}
ALLOWED_CLOSURE = {"verified", "explicit_unavailable", "gap"}
ALLOWED_UNAVAILABLE = {
    "not_configured",
    "request_error",
    "provider_unavailable",
    "runtime_unavailable",
    "error",
    "unsupported",
}
ALLOWED_EMPTY = {"no_data", "empty_collection"}
EXTERNAL_PREFIXES = ("external:", "external/", "data-service:")
VIRTUAL_OWNERS = {"execution-runtime"}


class AuditError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuditError(f"missing required registry: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def _formal_view_routes(manifest: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    routes: dict[str, str] = {}
    names: dict[str, str] = {}
    for module in manifest.get("modules", []):
        for route in module.get("routes", []):
            view = route.get("view_import")
            if not view:
                continue
            full_path = route.get("full_path")
            name = route.get("name")
            if not isinstance(full_path, str) or not isinstance(name, str):
                raise AuditError("formal route manifest contains an invalid view route")
            if full_path in routes:
                raise AuditError(f"formal route manifest repeats path {full_path}")
            if name in names:
                raise AuditError(f"formal route manifest repeats name {name}")
            routes[full_path] = f"platform-web/src/views/{view}"
            names[name] = full_path
    return routes, names


def _apply_overrides(
    matrix: dict[str, Any], overrides: dict[str, Any]
) -> dict[str, Any]:
    if overrides.get("schema_version") != 1:
        raise AuditError("product data owner overrides schema_version must be 1")
    values = overrides.get("overrides")
    if not isinstance(values, dict):
        raise AuditError("product data owner overrides must contain an overrides object")

    resolved = copy.deepcopy(matrix)
    entries = resolved.get("entries")
    if not isinstance(entries, list):
        raise AuditError("product data owner matrix must contain entries")
    by_module = {
        entry.get("module"): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("module"), str)
    }
    unknown = sorted(set(values) - set(by_module))
    if unknown:
        raise AuditError(f"overrides reference unknown modules: {unknown}")
    for module, patch in values.items():
        if not isinstance(patch, dict) or not patch:
            raise AuditError(f"{module}: override must be a non-empty object")
        forbidden = {"module", "routes", "route_names", "view_owner"} & patch.keys()
        if forbidden:
            raise AuditError(f"{module}: overrides cannot change formal ownership fields {sorted(forbidden)}")
        by_module[module].update(copy.deepcopy(patch))
    resolved["resolved_with"] = str(DEFAULT_OVERRIDES.relative_to(ROOT))
    return resolved


def resolve_matrix(matrix_path: Path, overrides_path: Path) -> dict[str, Any]:
    matrix = _load_json(matrix_path)
    if matrix.get("schema_version") != 1:
        raise AuditError("product data owner matrix schema_version must be 1")
    return _apply_overrides(matrix, _load_json(overrides_path))


def _is_repository_path(value: str) -> bool:
    return not value.startswith(EXTERNAL_PREFIXES) and value not in VIRTUAL_OWNERS


def _require_path(value: str, *, field: str, module: str) -> None:
    if not _is_repository_path(value):
        return
    if not (ROOT / value).exists():
        raise AuditError(f"{module}: {field} path does not exist: {value}")


def audit(
    matrix_path: Path,
    *,
    require_closed: bool,
    overrides_path: Path = DEFAULT_OVERRIDES,
) -> dict[str, Any]:
    matrix = resolve_matrix(matrix_path, overrides_path)
    manifest = _load_json(FORMAL_MANIFEST)
    formal_routes, formal_names = _formal_view_routes(manifest)

    entries = matrix.get("entries")
    if not isinstance(entries, list) or not entries:
        raise AuditError("product data owner matrix must contain entries")

    mapped_routes: dict[str, str] = {}
    mapped_names: dict[str, str] = {}
    statuses: Counter[str] = Counter()
    modules: set[str] = set()
    unique_views: set[str] = set()

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise AuditError("each product data owner entry must be an object")
        missing = REQUIRED_ENTRY_FIELDS - raw_entry.keys()
        if missing:
            raise AuditError(f"entry is missing fields: {sorted(missing)}")
        module = raw_entry["module"]
        if not isinstance(module, str) or not module:
            raise AuditError("entry module must be a non-empty string")
        if module in modules:
            raise AuditError(f"duplicate product module: {module}")
        modules.add(module)

        routes = raw_entry["routes"]
        names = raw_entry["route_names"]
        if not isinstance(routes, list) or not routes:
            raise AuditError(f"{module}: routes must be a non-empty list")
        if not isinstance(names, list) or not names:
            raise AuditError(f"{module}: route_names must be a non-empty list")
        if len(routes) != len(names):
            raise AuditError(f"{module}: routes and route_names must have equal length")

        view_owner = raw_entry["view_owner"]
        if not isinstance(view_owner, str) or not view_owner:
            raise AuditError(f"{module}: view_owner must be a non-empty path")
        _require_path(view_owner, field="view_owner", module=module)
        unique_views.add(view_owner)

        for route, name in zip(routes, names, strict=True):
            if not isinstance(route, str) or not isinstance(name, str):
                raise AuditError(f"{module}: route values must be strings")
            if route in mapped_routes:
                raise AuditError(f"route {route} is mapped more than once")
            if name in mapped_names:
                raise AuditError(f"route name {name} is mapped more than once")
            mapped_routes[route] = view_owner
            mapped_names[name] = route

        for field in ("frontend_services", "application_services", "repository_or_provider"):
            values = raw_entry[field]
            if not isinstance(values, list):
                raise AuditError(f"{module}: {field} must be a list")
            for value in values:
                if not isinstance(value, str) or not value:
                    raise AuditError(f"{module}: {field} contains an invalid owner")
                _require_path(value, field=field, module=module)

        for field in ("api_endpoints", "permissions", "roles", "e2e", "provider_smoke"):
            values = raw_entry[field]
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value for value in values
            ):
                raise AuditError(f"{module}: {field} must contain strings")

        closure_status = raw_entry["closure_status"]
        if closure_status not in ALLOWED_CLOSURE:
            raise AuditError(f"{module}: invalid closure_status {closure_status!r}")
        statuses[closure_status] += 1
        gap_reason = raw_entry["gap_reason"]
        if closure_status == "gap" and (not isinstance(gap_reason, str) or not gap_reason):
            raise AuditError(f"{module}: gap entries require gap_reason")
        if closure_status != "gap" and gap_reason is not None:
            raise AuditError(f"{module}: closed entries must set gap_reason to null")
        if require_closed and closure_status == "gap":
            raise AuditError(f"{module}: unresolved product/data gap: {gap_reason}")

        if raw_entry["empty_state"] not in ALLOWED_EMPTY:
            raise AuditError(f"{module}: invalid empty_state {raw_entry['empty_state']!r}")
        if raw_entry["unavailable_state"] not in ALLOWED_UNAVAILABLE:
            raise AuditError(f"{module}: invalid unavailable_state {raw_entry['unavailable_state']!r}")
        if raw_entry["live_write"] is not False:
            raise AuditError(f"{module}: Phase 5 must not enable Live Write")
        if not isinstance(raw_entry["writes"], bool):
            raise AuditError(f"{module}: writes must be boolean")

        for field in (
            "real_data_source",
            "refresh",
            "as_of",
            "timezone",
            "currency",
            "unit",
            "precision",
            "fallback",
        ):
            if not isinstance(raw_entry[field], str) or not raw_entry[field]:
                raise AuditError(f"{module}: {field} must be a non-empty string")

        if closure_status == "verified" and raw_entry["real_data_source"].startswith("not-configured"):
            raise AuditError(f"{module}: verified entry cannot use not-configured source")
        if closure_status == "explicit_unavailable" and raw_entry["unavailable_state"] not in {
            "not_configured",
            "unsupported",
        }:
            raise AuditError(f"{module}: explicit_unavailable requires not_configured or unsupported")

    missing_routes = sorted(set(formal_routes) - set(mapped_routes))
    extra_routes = sorted(set(mapped_routes) - set(formal_routes))
    if missing_routes or extra_routes:
        raise AuditError(f"route coverage mismatch: missing={missing_routes}, extra={extra_routes}")
    missing_names = sorted(set(formal_names) - set(mapped_names))
    extra_names = sorted(set(mapped_names) - set(formal_names))
    if missing_names or extra_names:
        raise AuditError(f"route-name coverage mismatch: missing={missing_names}, extra={extra_names}")
    for route, expected_view in formal_routes.items():
        if mapped_routes[route] != expected_view:
            raise AuditError(f"{route}: matrix view {mapped_routes[route]} does not match {expected_view}")
    for name, expected_route in formal_names.items():
        if mapped_names[name] != expected_route:
            raise AuditError(f"{name}: matrix route {mapped_names[name]} does not match {expected_route}")

    debt = matrix.get("evidence_debt")
    if not isinstance(debt, dict):
        raise AuditError("matrix must contain evidence_debt")
    expected_heads = {
        "pr_149": "964f26031e708b3599852fb25b5b4dc5535333fa",
        "pr_150": "bbdff03948322e25b2d995946d6fa25e6ba21b0d",
    }
    pending = False
    for key, expected_head in expected_heads.items():
        item = debt.get(key)
        if not isinstance(item, dict):
            raise AuditError(f"evidence_debt.{key} is missing")
        if item.get("head") != expected_head:
            raise AuditError(f"evidence_debt.{key} head drifted")
        if item.get("status") not in {"pending", "resolved"}:
            raise AuditError(f"evidence_debt.{key} has invalid status")
        pending = pending or item["status"] == "pending"
    if debt.get("affects_phase5_engineering") is not False:
        raise AuditError("Phase 4 evidence debt must not block Phase 5 engineering")
    if pending and debt.get("blocks_final_rc") is not True:
        raise AuditError("pending Phase 4 evidence debt must block final RC")

    return {
        "schema_version": 1,
        "status": "ok",
        "formal_routes": len(formal_routes),
        "route_names": len(formal_names),
        "entries": len(entries),
        "unique_views": len(unique_views),
        "closure": dict(sorted(statuses.items())),
        "evidence_debt": {
            "pr_149": debt["pr_149"]["status"],
            "pr_150": debt["pr_150"]["status"],
            "blocks_final_rc": debt["blocks_final_rc"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--require-closed", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resolved-output", type=Path)
    args = parser.parse_args()
    try:
        result = audit(
            args.matrix,
            require_closed=args.require_closed,
            overrides_path=args.overrides,
        )
        resolved = resolve_matrix(args.matrix, args.overrides)
    except AuditError as exc:
        print(f"product-data-owner audit failed: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(payload)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    if args.resolved_output is not None:
        args.resolved_output.parent.mkdir(parents=True, exist_ok=True)
        args.resolved_output.write_text(
            json.dumps(resolved, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
