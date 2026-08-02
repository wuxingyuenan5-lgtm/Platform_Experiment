#!/usr/bin/env python3
"""Formal stacked Platform Phase history audit entrypoint."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_CORE_PATH = Path(__file__).with_name("audit_phase_history_core.py")
_SCRIPTS_DIR = str(_CORE_PATH.parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
_SPEC = importlib.util.spec_from_file_location("audit_phase_history_core", _CORE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_CORE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _CORE
_SPEC.loader.exec_module(_CORE)

AuditError = _CORE.AuditError
CATEGORIES = _CORE.CATEGORIES
audit = _CORE.audit
classify = _CORE.classify
metadata_from_event = _CORE.metadata_from_event
parse_stacked_metadata = _CORE.parse_stacked_metadata
main = _CORE.main

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"Phase history audit failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
