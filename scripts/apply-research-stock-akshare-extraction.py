#!/usr/bin/env python3
"""One-shot extraction of AkShare-backed stock Research methods."""

from __future__ import annotations

import ast
from pathlib import Path

PROVIDER_PATH = Path("platform-api/app/research_providers.py")
PYPROJECT_PATH = Path("platform-api/pyproject.toml")
ADAPTER_IMPORT = "from app.research_provider_stock_akshare import StockAkshareResearchProvider\n"
IMPORT_MARKER = (
    "from app.research_provider_stock_datacenter import StockDataCenterResearchProvider\n"
)
PYRIGHT_MARKER = '  "app/research_provider_stock_datacenter.py",\n'

DELEGATES = {
    "stock_financials": (
        "    async def stock_financials(self, code: str) -> dict[str, Any]:\n"
        "        return await self._stock_akshare.stock_financials(code)\n"
    ),
    "stock_forecast": (
        "    async def stock_forecast(\n"
        "        self, code: str, price: Decimal | None\n"
        "    ) -> dict[str, Any]:\n"
        "        return await self._stock_akshare.stock_forecast(code, price)\n"
    ),
    "stock_valuation_percentile": (
        "    async def stock_valuation_percentile(self, code: str) -> dict[str, Any]:\n"
        "        return await self._stock_akshare.stock_valuation_percentile(code)\n"
    ),
    "stock_news": (
        "    async def stock_news(\n"
        "        self, code: str, limit: int = 20\n"
        "    ) -> list[dict[str, Any]]:\n"
        "        return await self._stock_akshare.stock_news(code, limit=limit)\n"
    ),
}


def main() -> None:
    provider = PROVIDER_PATH.read_text(encoding="utf-8")
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    if (
        ADAPTER_IMPORT in provider
        and "return await self._stock_akshare.stock_financials(code)" in provider
        and '  "app/research_provider_stock_akshare.py",' in pyproject
    ):
        print("AkShare stock extraction is already applied.")
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
        raise SystemExit(f"AkShare stock method boundary mismatch: {sorted(methods)}")

    lines = provider.splitlines(keepends=True)
    for name, node in sorted(methods.items(), key=lambda item: item[1].lineno, reverse=True):
        lines[node.lineno - 1 : node.end_lineno] = [DELEGATES[name]]
    provider = "".join(lines)

    if IMPORT_MARKER not in provider:
        raise SystemExit("Stock DataCenter provider import boundary was not found")
    provider = provider.replace(IMPORT_MARKER, ADAPTER_IMPORT + IMPORT_MARKER, 1)
    provider = provider.replace("import asyncio\n", "", 1)
    provider = provider.replace("import math\n", "", 1)
    provider = provider.replace(
        "from app.research_provider_normalization import as_non_negative_integer as _integer\n",
        "",
        1,
    )
    provider = provider.replace(
        "from app.research_provider_normalization import first_present as _pick\n",
        "",
        1,
    )
    provider = provider.replace(
        "from app.research_provider_normalization import frame_records as _records\n",
        "",
        1,
    )
    provider = provider.replace(
        "        self._stock_data_center = StockDataCenterResearchProvider(\n"
        "            data_center=self._data_center,\n"
        "        )\n",
        "        self._stock_akshare = StockAkshareResearchProvider(\n"
        "            akshare_loader=_akshare,\n"
        "        )\n"
        "        self._stock_data_center = StockDataCenterResearchProvider(\n"
        "            data_center=self._data_center,\n"
        "        )\n",
        1,
    )

    if PYRIGHT_MARKER not in pyproject:
        raise SystemExit("Pyright stock provider boundary was not found")
    pyproject = pyproject.replace(
        PYRIGHT_MARKER,
        '  "app/research_provider_stock_akshare.py",\n' + PYRIGHT_MARKER,
        1,
    )

    forbidden = (
        "stock_financial_abstract_ths",
        "stock_profit_forecast_ths",
        "stock_zh_valuation_baidu",
        "stock_news_em",
    )
    if any(value in provider for value in forbidden):
        raise SystemExit("Facade retained AkShare stock implementation details")
    required_http_methods = (
        "stock_quote",
        "stock_reports",
        "stock_announcements",
        "stock_fund_flow",
        "stock_investor_qa",
    )
    if any(f"async def {name}" not in provider for name in required_http_methods):
        raise SystemExit("Independent HTTP stock methods moved unexpectedly")
    if "def _akshare()" not in provider:
        raise SystemExit("Shared AkShare lazy loader was removed unexpectedly")
    if "self._stock_akshare = StockAkshareResearchProvider" not in provider:
        raise SystemExit("AkShare stock adapter was not wired into the stable facade")

    PROVIDER_PATH.write_text(provider, encoding="utf-8")
    PYPROJECT_PATH.write_text(pyproject, encoding="utf-8")
    print("AkShare stock methods extracted behind the stable facade.")


if __name__ == "__main__":
    main()
