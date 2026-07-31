#!/usr/bin/env python3
"""One-shot extraction of independent HTTP-backed stock Research methods."""

from __future__ import annotations

import ast
from pathlib import Path

PROVIDER_PATH = Path("platform-api/app/research_providers.py")
PYPROJECT_PATH = Path("platform-api/pyproject.toml")
ADAPTER_IMPORT = "from app.research_provider_stock_http import StockHttpResearchProvider\n"
IMPORT_MARKER = (
    "from app.research_provider_stock_datacenter import StockDataCenterResearchProvider\n"
)
PYRIGHT_MARKER = '  "app/research_provider_stock_datacenter.py",\n'

DELEGATES = {
    "stock_quote": (
        "    async def stock_quote(self, code: str) -> dict[str, Any]:\n"
        "        return await self._stock_http.stock_quote(code)\n"
    ),
    "stock_reports": (
        "    async def stock_reports(\n"
        "        self, code: str, limit: int = 30\n"
        "    ) -> list[dict[str, Any]]:\n"
        "        return await self._stock_http.stock_reports(code, limit=limit)\n"
    ),
    "stock_announcements": (
        "    async def stock_announcements(\n"
        "        self, code: str, limit: int = 20\n"
        "    ) -> list[dict[str, Any]]:\n"
        "        return await self._stock_http.stock_announcements(code, limit=limit)\n"
    ),
    "stock_fund_flow": (
        "    async def stock_fund_flow(self, code: str) -> dict[str, Any]:\n"
        "        return await self._stock_http.stock_fund_flow(code)\n"
    ),
    "stock_investor_qa": (
        "    async def stock_investor_qa(\n"
        "        self, code: str, limit: int = 30\n"
        "    ) -> list[dict[str, Any]]:\n"
        "        return await self._stock_http.stock_investor_qa(code, limit=limit)\n"
    ),
}


def main() -> None:
    provider = PROVIDER_PATH.read_text(encoding="utf-8")
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    if (
        ADAPTER_IMPORT in provider
        and "return await self._stock_http.stock_quote(code)" in provider
        and '  "app/research_provider_stock_http.py",' in pyproject
    ):
        print("Independent stock HTTP extraction is already applied.")
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
        raise SystemExit(f"Stock HTTP method boundary mismatch: {sorted(methods)}")

    lines = provider.splitlines(keepends=True)
    for name, node in sorted(methods.items(), key=lambda item: item[1].lineno, reverse=True):
        lines[node.lineno - 1 : node.end_lineno] = [DELEGATES[name]]
    provider = "".join(lines)

    if IMPORT_MARKER not in provider:
        raise SystemExit("Stock DataCenter provider import boundary was not found")
    provider = provider.replace(IMPORT_MARKER, IMPORT_MARKER + ADAPTER_IMPORT, 1)
    provider = provider.replace("from datetime import UTC, datetime\n", "", 1)
    provider = provider.replace("import httpx\n", "", 1)
    provider = provider.replace(
        "from app.research_provider_normalization import as_decimal as _decimal\n",
        "",
        1,
    )
    provider = provider.replace(
        "from typing import Any\n\n\nfrom app.research_data_schemas import",
        "from typing import Any\n\nfrom app.research_data_schemas import",
        1,
    )
    provider = provider.replace(
        'TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="\n',
        "",
        1,
    )
    provider = provider.replace(
        "        self._stock_akshare = StockAkshareResearchProvider(\n"
        "            akshare_loader=_akshare,\n"
        "        )\n",
        "        self._stock_akshare = StockAkshareResearchProvider(\n"
        "            akshare_loader=_akshare,\n"
        "        )\n"
        "        self._stock_http = StockHttpResearchProvider(\n"
        "            timeout_seconds=timeout_seconds,\n"
        "            user_agent=USER_AGENT,\n"
        "        )\n",
        1,
    )

    if PYRIGHT_MARKER not in pyproject:
        raise SystemExit("Pyright Stock DataCenter provider boundary was not found")
    pyproject = pyproject.replace(
        PYRIGHT_MARKER,
        PYRIGHT_MARKER + '  "app/research_provider_stock_http.py",\n',
        1,
    )

    forbidden = (
        "qt.gtimg.cn",
        "reportapi.eastmoney.com",
        "np-anotice-stock.eastmoney.com",
        "push2his.eastmoney.com",
        "irm.cninfo.com.cn",
        "httpx.AsyncClient",
    )
    if any(value in provider for value in forbidden):
        raise SystemExit("Facade retained independent stock HTTP implementation details")
    required_compatibility = (
        "a_share_spot",
        "stock_financials",
        "datacenter_rows",
        "stock_margin",
        "macro_expectation_events",
    )
    if any(f"async def {name}" not in provider for name in required_compatibility):
        raise SystemExit("Stable facade methods moved unexpectedly")
    if "self._stock_http = StockHttpResearchProvider" not in provider:
        raise SystemExit("Stock HTTP adapter was not wired into the stable facade")

    PROVIDER_PATH.write_text(provider, encoding="utf-8")
    PYPROJECT_PATH.write_text(pyproject, encoding="utf-8")
    print("Independent stock HTTP methods extracted behind the stable facade.")


if __name__ == "__main__":
    main()
