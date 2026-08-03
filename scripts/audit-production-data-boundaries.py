#!/usr/bin/env python3
"""Audit production product paths for test data and unqualified simulated values."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config" / "production-data-boundary-policy.json"


class AuditError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise AuditError(f"missing policy: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError("production boundary policy must be a JSON object")
    return value


def _require_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise AuditError(f"{field} must be a list of non-empty strings")
    return value


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AuditError(f"production source is not UTF-8: {_relative(path)}") from exc


def _validate_markers(path: str, markers: list[str], *, label: str) -> None:
    target = ROOT / path
    if not target.is_file():
        raise AuditError(f"{label} path does not exist: {path}")
    content = _read(target)
    missing = [marker for marker in markers if marker not in content]
    if missing:
        raise AuditError(f"{label} {path} is missing markers: {missing}")


def audit(policy_path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    policy = _load_json(policy_path)
    if policy.get("schema_version") != 1:
        raise AuditError("production boundary policy schema_version must be 1")

    roots = _require_string_list(policy.get("scan_roots"), "scan_roots")
    extensions = set(_require_string_list(policy.get("extensions"), "extensions"))
    excluded = set(_require_string_list(policy.get("excluded_paths"), "excluded_paths"))

    raw_patterns = policy.get("forbidden_patterns")
    if not isinstance(raw_patterns, list) or not raw_patterns:
        raise AuditError("forbidden_patterns must be a non-empty list")
    patterns: list[tuple[str, re.Pattern[str], str]] = []
    for item in raw_patterns:
        if not isinstance(item, dict):
            raise AuditError("forbidden pattern entries must be objects")
        code = item.get("code")
        pattern = item.get("pattern")
        message = item.get("message")
        if not all(isinstance(value, str) and value for value in (code, pattern, message)):
            raise AuditError("forbidden patterns require code, pattern and message")
        try:
            compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        except re.error as exc:
            raise AuditError(f"invalid forbidden regex {code}: {exc}") from exc
        patterns.append((code, compiled, message))

    scanned_files: list[str] = []
    findings: list[dict[str, Any]] = []
    for root_name in roots:
        root = ROOT / root_name
        if not root.is_dir():
            raise AuditError(f"scan root does not exist: {root_name}")
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in extensions:
                continue
            relative = _relative(path)
            if relative in excluded:
                continue
            content = _read(path)
            scanned_files.append(relative)
            for code, pattern, message in patterns:
                for match in pattern.finditer(content):
                    line = content.count("\n", 0, match.start()) + 1
                    findings.append(
                        {
                            "code": code,
                            "path": relative,
                            "line": line,
                            "message": message,
                            "match": match.group(0)[:160],
                        }
                    )

    quarantines = policy.get("quarantines")
    if not isinstance(quarantines, list):
        raise AuditError("quarantines must be a list")
    quarantine_results: list[dict[str, Any]] = []
    for item in quarantines:
        if not isinstance(item, dict):
            raise AuditError("quarantine entries must be objects")
        path = item.get("path")
        owner = item.get("owner")
        consumer_path = item.get("consumer_path")
        if not all(isinstance(value, str) and value for value in (path, owner, consumer_path)):
            raise AuditError("quarantine requires path, owner and consumer_path")
        required_markers = _require_string_list(item.get("required_markers"), f"{path}.required_markers")
        consumer_markers = _require_string_list(
            item.get("consumer_required_markers"),
            f"{path}.consumer_required_markers",
        )
        _validate_markers(path, required_markers, label="quarantine")
        _validate_markers(consumer_path, consumer_markers, label="quarantine consumer")
        quarantine_results.append(
            {
                "path": path,
                "owner": owner,
                "consumer_path": consumer_path,
                "status": "isolated",
            }
        )

    unavailable_views = policy.get("explicit_unavailable_views")
    if not isinstance(unavailable_views, list):
        raise AuditError("explicit_unavailable_views must be a list")
    unavailable_results: list[dict[str, str]] = []
    for item in unavailable_views:
        if not isinstance(item, dict):
            raise AuditError("explicit unavailable entries must be objects")
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise AuditError("explicit unavailable entry requires path")
        markers = _require_string_list(item.get("required_markers"), f"{path}.required_markers")
        _validate_markers(path, markers, label="explicit unavailable view")
        unavailable_results.append({"path": path, "status": "explicit_unavailable"})

    result = {
        "schema_version": 1,
        "status": "ok" if not findings else "failed",
        "scanned_files": len(scanned_files),
        "findings": findings,
        "quarantines": quarantine_results,
        "explicit_unavailable_views": unavailable_results,
    }
    if findings:
        details = ", ".join(
            f"{item['path']}:{item['line']}:{item['code']}" for item in findings[:20]
        )
        raise AuditError(f"production data boundary violations: {details}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.policy)
    except AuditError as exc:
        print(f"production-data-boundary audit failed: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(payload)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
