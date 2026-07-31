#!/usr/bin/env python3
"""One-shot extraction of DataCenter-derived stock Research methods."""

from __future__ import annotations

import ast
from pathlib import Path

PROVIDER_PATH = Path("platform-api/app/research_providers.py")
PYPROJECT_PATH = Path("platform-api/pyproject.toml")
ADAPTER_IMPORT = (
    "from app.research_provider_stock_datacenter import StockDataCenterResearchProvider\n"
)
IMPORT_MARKER = "from app.research_provider_normalization import percentage_change as _pct_change\n"
PYRIGHT_MARKER = '  "app/research_provider_normalization.py",\n'

DELEGATES = {
    "stock_margin": (
        "    async def stock_margin(self, code: str) -> list[dict[str, Any]]:\n"
        "        return await self._stock_data_center.stock_margin(code)\n"
    ),
    "stock_block_trades": (
        "    async def stock_block_trades(self, code: str) -> list[dict[str, Any]]:\n"
        "        return await self._stock_data_center.stock_block_trades(code)\n"
    ),
    "stock_holders": (
        "    async def stock_holders(self, code: str) -> list[dict[str, Any]]:\n"
        "        return await self._stock_data_center.stock_holders(code)\n"
    ),
    "stock_dividends": (
        "    async def stock_dividends(self, code: str) -> list[dict[str, Any]]:\n"
        "        return await self._stock_data_center.stock_dividends(code)\n"
    ),
    "stock_dragon_tiger": (
        "    async def stock_dragon_tiger(self, code: str) -> dict[str, Any]:\n"
        "        return await self._stock_data_center.stock_dragon_tiger(code)\n"
    ),
    "stock_lockup": (
        "    async def stock_lockup(self, code: str) -> dict[str, Any]:\n"
        "        return await self._stock_data_center.stock_lockup(code)\n"
    ),
}


def main() -> None:
    provider = PROVIDER_PATH.read_text(encoding="utf-8")
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    if (
        ADAPTER_IMPORT in provider
        and "return await self._stock_data_center.stock_margin(code)" in provider
        and '  "app/research_provider_stock_datacenter.py",' in pyproject
    ):
        print("Stock DataCenter extraction is already applied.")
        return

    tree = ast.parse(provider)
    provider_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FreeResearchProvider"
    )
    methods = {
        node.name: node
        for node in provider_class.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name in DELEGATES
    }
    if set(methods) != set(DELEGATES):
        raise SystemExit(f"Stock DataCenter method boundary mismatch: {sorted(methods)}")

    lines = provider.splitlines(keepends=True)
    for name, node in sorted(methods.items(), key=lambda item: item[1].lineno, reverse=True):
        lines[node.lineno - 1 : node.end_lineno] = [DELEGATES[name]]
    provider = "".join(lines)

    if IMPORT_MARKER not in provider:
        raise SystemExit("Research normalization import boundary was not found")
    provider = provider.replace(
        IMPORT_MARKER,
        IMPORT_MARKER + ADAPTER_IMPORT,
        1,
    )
    provider = provider.replace("from collections.abc import Iterable\n", "", 1)
    provider = provider.replace(
        "from datetime import UTC, date, datetime, timedelta\n",
        "from datetime import UTC, datetime\n",
        1,
    )
    provider = provider.replace(IMPORT_MARKER, "", 1)
    provider = provider.replace(
        "        self._data_center = EastmoneyDataCenterClient(\n"
        "            timeout_seconds=timeout_seconds,\n"
        "            user_agent=USER_AGENT,\n"
        "        )\n",
        "        self._data_center = EastmoneyDataCenterClient(\n"
        "            timeout_seconds=timeout_seconds,\n"
        "            user_agent=USER_AGENT,\n"
        "        )\n"
        "        self._stock_data_center = StockDataCenterResearchProvider(\n"
        "            data_center=self._data_center,\n"
        "        )\n",
        1,
    )

    if PYRIGHT_MARKER not in pyproject:
        raise SystemExit("Pyright Research provider boundary was not found")
    pyproject = pyproject.replace(
        PYRIGHT_MARKER,
        PYRIGHT_MARKER + '  "app/research_provider_stock_datacenter.py",\n',
        1,
    )

    forbidden = (
        "RPTA_WEB_RZRQ_GGMX",
        "RPT_DATA_BLOCKTRADE",
        "RPT_HOLDERNUMLATEST",
        "RPT_SHAREBONUS_DET",
        "RPT_DAILYBILLBOARD_DETAILSNEW",
        "RPT_LIFT_STAGE",
    )
    if any(value in provider for value in forbidden):
        raise SystemExit("Facade retained DataCenter-derived stock implementation details")
    if "async def datacenter_rows" not in provider:
        raise SystemExit("Facade compatibility DataCenter method was removed")
    if "async def stock_fund_flow" not in provider or "async def stock_investor_qa" not in provider:
        raise SystemExit("Independent HTTP stock methods moved unexpectedly")

    PROVIDER_PATH.write_text(provider, encoding="utf-8")
    PYPROJECT_PATH.write_text(pyproject, encoding="utf-8")
    print("DataCenter-derived stock methods extracted behind the stable facade.")


if __name__ == "__main__":
    main()
