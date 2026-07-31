#!/usr/bin/env python3
"""One-shot mechanical extraction of the macro Research provider adapter."""

from __future__ import annotations

import ast
from pathlib import Path

PROVIDER_PATH = Path("platform-api/app/research_providers.py")
ERROR_IMPORT = "from app.research_provider_errors import ResearchProviderError\n"
MACRO_IMPORT = "from app.research_provider_macro import MacroResearchProvider\n"
NORMALIZATION_MARKER = "from app.research_provider_normalization import as_date as _date\n"


def main() -> None:
    text = PROVIDER_PATH.read_text(encoding="utf-8")
    if MACRO_IMPORT in text and "return await self._macro.macro_expectation_events" in text:
        print("Macro Research provider extraction is already applied.")
        return

    tree = ast.parse(text)
    provider_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FreeResearchProvider"
    )
    macro_method = next(
        node
        for node in provider_class.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "macro_expectation_events"
    )
    lines = text.splitlines(keepends=True)
    delegate = (
        "    async def macro_expectation_events(\n"
        "        self, limit: int = 12\n"
        "    ) -> list[MacroExpectationEvent]:\n"
        "        return await self._macro.macro_expectation_events(limit=limit)\n"
    )
    text = "".join(lines[: macro_method.lineno - 1]) + delegate + "".join(lines[macro_method.end_lineno :])

    text = text.replace("import json\n", "", 1)
    if NORMALIZATION_MARKER not in text:
        raise SystemExit("normalization import boundary was not found")
    text = text.replace(
        NORMALIZATION_MARKER,
        ERROR_IMPORT + MACRO_IMPORT + NORMALIZATION_MARKER,
        1,
    )
    text = text.replace(
        'POLYMARKET_MARKETS_URL = "https://gamma-api.polymarket.com/markets"\n',
        "",
        1,
    )
    text = text.replace(
        "\n\nclass ResearchProviderError(RuntimeError):\n    pass\n",
        "",
        1,
    )
    text = text.replace(
        "    def __init__(self, *, timeout_seconds: float = 20.0) -> None:\n"
        "        self._timeout_seconds = timeout_seconds\n",
        "    def __init__(self, *, timeout_seconds: float = 20.0) -> None:\n"
        "        self._timeout_seconds = timeout_seconds\n"
        "        self._macro = MacroResearchProvider(\n"
        "            timeout_seconds=timeout_seconds,\n"
        "            user_agent=USER_AGENT,\n"
        "        )\n",
        1,
    )

    forbidden = (
        "POLYMARKET_MARKETS_URL",
        "class ResearchProviderError",
        "json.loads",
        "macro_expectation_events_empty",
    )
    if any(value in text for value in forbidden):
        raise SystemExit("macro extraction left duplicate implementation details")
    if "self._macro = MacroResearchProvider" not in text:
        raise SystemExit("macro adapter was not wired into the stable facade")
    PROVIDER_PATH.write_text(text, encoding="utf-8")
    print("Macro Research provider extracted behind the stable facade.")


if __name__ == "__main__":
    main()
