#!/usr/bin/env python3
"""One-shot extraction of Research macro probability history state."""

from __future__ import annotations

import ast
from pathlib import Path

SERVICE_PATH = Path("platform-api/app/research_service.py")
HISTORY_IMPORT = "from app.research_macro_history import MacroProbabilityHistoryStore\n"
IMPORT_MARKER = "from app.research_providers import FreeResearchProvider\n"


def main() -> None:
    service = SERVICE_PATH.read_text(encoding="utf-8")
    if (
        HISTORY_IMPORT in service
        and "class MacroProbabilityHistoryStore" not in service
        and "def _history_change(" not in service
    ):
        print("Research macro history extraction is already applied.")
        return

    tree = ast.parse(service)
    removable = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.ClassDef)
            and node.name == "MacroProbabilityHistoryStore"
        )
        or (
            isinstance(node, ast.FunctionDef)
            and node.name == "_history_change"
        )
    ]
    names = {
        node.name
        for node in removable
        if isinstance(node, (ast.ClassDef, ast.FunctionDef))
    }
    if names != {"MacroProbabilityHistoryStore", "_history_change"}:
        raise SystemExit(f"Macro history boundary mismatch: {sorted(names)}")

    lines = service.splitlines(keepends=True)
    for node in sorted(removable, key=lambda item: item.lineno, reverse=True):
        start = node.lineno - 1
        end = node.end_lineno
        while end < len(lines) and lines[end].strip() == "":
            end += 1
        lines[start:end] = []
    service = "".join(lines)

    if IMPORT_MARKER not in service:
        raise SystemExit("Research provider import boundary was not found")
    service = service.replace(IMPORT_MARKER, HISTORY_IMPORT + IMPORT_MARKER, 1)
    service = service.replace("import json\n", "", 1)
    service = service.replace("import os\n", "", 1)
    service = service.replace("from pathlib import Path\n", "", 1)
    service = service.replace("    MacroExpectationEvent,\n", "", 1)
    service = service.replace("    MacroProbabilityPoint,\n", "", 1)

    forbidden = (
        "RESEARCH_MACRO_HISTORY_PATH",
        "macro_probability_history.json",
        "json.loads",
        "json.dumps",
        "def _history_change(",
        "class MacroProbabilityHistoryStore",
    )
    if any(value in service for value in forbidden):
        raise SystemExit("Research Service retained macro history implementation details")
    required = (
        "_MACRO_HISTORY = MacroProbabilityHistoryStore()",
        "events = await _MACRO_HISTORY.update(events)",
        "_MACRO_CACHE = LastKnownGoodResearchCache",
        "_MACRO_LOCK = asyncio.Lock()",
        'copied.events.meta.status = "stale"',
    )
    if any(value not in service for value in required):
        raise SystemExit("Research Service state or LKG contract moved unexpectedly")

    SERVICE_PATH.write_text(service, encoding="utf-8")
    print("Research macro history extracted behind the stable service orchestration.")


if __name__ == "__main__":
    main()
