#!/usr/bin/env python3
"""Formal Phase history audit entrypoint with generic transport classification."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_CORE_PATH = Path(__file__).with_name("audit_phase_history_core.py")
_SPEC = importlib.util.spec_from_file_location("audit_phase_history_core", _CORE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_CORE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _CORE
_SPEC.loader.exec_module(_CORE)
_ORIGINAL_CLASSIFY = _CORE.classify

def classify(message: str, entries: list[dict[str, str]]) -> str:
    subject = message.splitlines()[0].strip().lower()
    if not entries and "trigger" in subject and "bootstrap" in subject:
        return "transport"
    return _ORIGINAL_CLASSIFY(message, entries)

_CORE.classify = classify
AuditError = _CORE.AuditError
audit = _CORE.audit
main = _CORE.main

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"Phase history audit failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
