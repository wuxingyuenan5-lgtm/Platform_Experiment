#!/usr/bin/env python3
"""One-shot mechanical extraction of the Eastmoney DataCenter client."""

from __future__ import annotations

import ast
from pathlib import Path

PROVIDER_PATH = Path("platform-api/app/research_providers.py")
PYPROJECT_PATH = Path("platform-api/pyproject.toml")
DATACENTER_IMPORT = (
    "from app.research_provider_datacenter import EastmoneyDataCenterClient\n"
)
IMPORT_MARKER = "from app.research_provider_a_share import AShareResearchProvider\n"
PYRIGHT_MARKER = '  "app/research_provider_a_share.py",\n'


def main() -> None:
    provider = PROVIDER_PATH.read_text(encoding="utf-8")
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    already_applied = (
        DATACENTER_IMPORT in provider
        and "return await self._data_center.rows(" in provider
        and '  "app/research_provider_datacenter.py",' in pyproject
    )
    if already_applied:
        print("Eastmoney DataCenter extraction is already applied.")
        return

    tree = ast.parse(provider)
    provider_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FreeResearchProvider"
    )
    method = next(
        node
        for node in provider_class.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "datacenter_rows"
    )
    delegate = (
        "    async def datacenter_rows(\n"
        "        self,\n"
        "        *,\n"
        "        report_name: str,\n"
        "        filter_value: str,\n"
        "        page_size: int = 30,\n"
        "        sort_columns: str = \"\",\n"
        "        sort_types: str = \"-1\",\n"
        "    ) -> list[dict[str, Any]]:\n"
        "        return await self._data_center.rows(\n"
        "            report_name=report_name,\n"
        "            filter_value=filter_value,\n"
        "            page_size=page_size,\n"
        "            sort_columns=sort_columns,\n"
        "            sort_types=sort_types,\n"
        "        )\n"
    )
    lines = provider.splitlines(keepends=True)
    lines[method.lineno - 1 : method.end_lineno] = [delegate]
    provider = "".join(lines)

    if IMPORT_MARKER not in provider:
        raise SystemExit("A-share provider import boundary was not found")
    provider = provider.replace(
        IMPORT_MARKER,
        IMPORT_MARKER + DATACENTER_IMPORT,
        1,
    )
    provider = provider.replace(
        'EASTMONEY_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"\n',
        "",
        1,
    )
    provider = provider.replace(
        "        self._a_share = AShareResearchProvider(\n"
        "            timeout_seconds=timeout_seconds,\n"
        "            user_agent=USER_AGENT,\n"
        "            akshare_loader=_akshare,\n"
        "        )\n",
        "        self._a_share = AShareResearchProvider(\n"
        "            timeout_seconds=timeout_seconds,\n"
        "            user_agent=USER_AGENT,\n"
        "            akshare_loader=_akshare,\n"
        "        )\n"
        "        self._data_center = EastmoneyDataCenterClient(\n"
        "            timeout_seconds=timeout_seconds,\n"
        "            user_agent=USER_AGENT,\n"
        "        )\n",
        1,
    )

    if PYRIGHT_MARKER not in pyproject:
        raise SystemExit("Pyright Research provider boundary was not found")
    pyproject = pyproject.replace(
        PYRIGHT_MARKER,
        PYRIGHT_MARKER + '  "app/research_provider_datacenter.py",\n',
        1,
    )

    if "EASTMONEY_DATACENTER_URL" in provider:
        raise SystemExit("Facade retained the DataCenter URL constant")
    if "self._data_center = EastmoneyDataCenterClient" not in provider:
        raise SystemExit("DataCenter client was not wired into the stable facade")
    if "async def stock_margin" not in provider or "async def stock_lockup" not in provider:
        raise SystemExit("DataCenter-derived stock methods moved unexpectedly")

    PROVIDER_PATH.write_text(provider, encoding="utf-8")
    PYPROJECT_PATH.write_text(pyproject, encoding="utf-8")
    print("Eastmoney DataCenter client extracted behind the stable facade.")


if __name__ == "__main__":
    main()
