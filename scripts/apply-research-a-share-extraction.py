#!/usr/bin/env python3
"""One-shot mechanical extraction of the A-share Research provider adapter."""

from __future__ import annotations

import ast
from pathlib import Path

PROVIDER_PATH = Path("platform-api/app/research_providers.py")
ADAPTER_IMPORT = "from app.research_provider_a_share import AShareResearchProvider\n"
ERROR_IMPORT = "from app.research_provider_errors import ResearchProviderError\n"

PUBLIC_DELEGATES = {
    "a_share_spot": (
        "    async def a_share_spot(self) -> list[AShareTurnoverStock]:\n"
        "        return await self._a_share.a_share_spot()\n"
    ),
    "market_activity": (
        "    async def market_activity(self) -> AShareBreadthSnapshot:\n"
        "        return await self._a_share.market_activity()\n"
    ),
    "index_snapshots": (
        "    async def index_snapshots(self) -> list[AShareIndexSnapshot]:\n"
        "        return await self._a_share.index_snapshots()\n"
    ),
    "shenwan_memberships": (
        "    async def shenwan_memberships(self) -> list[ShenwanMembership]:\n"
        "        return await self._a_share.shenwan_memberships()\n"
    ),
    "short_term_emotion": (
        "    async def short_term_emotion(self) -> ShortTermEmotionSnapshot:\n"
        "        return await self._a_share.short_term_emotion()\n"
    ),
}
PRIVATE_METHODS = {"_index_snapshot", "_intraday_signal", "_limit_pool"}


def _node_start(node: ast.AST) -> int:
    decorators = getattr(node, "decorator_list", [])
    return min([node.lineno, *(decorator.lineno for decorator in decorators)])


def main() -> None:
    text = PROVIDER_PATH.read_text(encoding="utf-8")
    if ADAPTER_IMPORT in text and "return await self._a_share.a_share_spot()" in text:
        print("A-share Research provider extraction is already applied.")
        return

    tree = ast.parse(text)
    provider_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FreeResearchProvider"
    )
    replacements: list[tuple[int, int, str]] = []
    found_public: set[str] = set()
    found_private: set[str] = set()
    for node in provider_class.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name in PUBLIC_DELEGATES:
            replacements.append((_node_start(node), node.end_lineno, PUBLIC_DELEGATES[node.name]))
            found_public.add(node.name)
        elif node.name in PRIVATE_METHODS:
            replacements.append((_node_start(node), node.end_lineno, ""))
            found_private.add(node.name)
    if found_public != set(PUBLIC_DELEGATES) or found_private != PRIVATE_METHODS:
        raise SystemExit(
            f"A-share method boundary mismatch: public={sorted(found_public)}, "
            f"private={sorted(found_private)}"
        )

    index_definition = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "INDEX_DEFINITIONS"
    )
    replacements.append((index_definition.lineno, index_definition.end_lineno, ""))

    lines = text.splitlines(keepends=True)
    for start, end, replacement in sorted(replacements, reverse=True):
        lines[start - 1 : end] = [replacement]
    text = "".join(lines)

    text = text.replace(
        "from app.a_share_research_policy import annualized_volatility_20\n",
        "",
        1,
    )
    if ERROR_IMPORT not in text:
        raise SystemExit("Research provider error import boundary was not found")
    text = text.replace(ERROR_IMPORT, ADAPTER_IMPORT + ERROR_IMPORT, 1)
    text = text.replace("    EmotionLadderRow,\n", "", 1)
    text = text.replace("    EmotionStockRow,\n", "", 1)
    text = text.replace(
        "from app.research_provider_normalization import as_date as _date\n",
        "",
        1,
    )
    text = text.replace(
        "from app.research_provider_normalization import closest_prior_close as _closest_prior\n",
        "",
        1,
    )
    text = text.replace(
        "from app.research_provider_normalization import trend_marker as _trend\n",
        "",
        1,
    )
    text = text.replace(
        "        self._timeout_seconds = timeout_seconds\n"
        "        self._macro = MacroResearchProvider(\n",
        "        self._timeout_seconds = timeout_seconds\n"
        "        self._a_share = AShareResearchProvider(\n"
        "            timeout_seconds=timeout_seconds,\n"
        "            user_agent=USER_AGENT,\n"
        "            akshare_loader=_akshare,\n"
        "        )\n"
        "        self._macro = MacroResearchProvider(\n",
        1,
    )

    forbidden = (
        "INDEX_DEFINITIONS",
        "stock_zh_a_spot_em",
        "stock_market_activity_legu",
        "stock_zh_index_daily_em",
        "stock_industry_clf_hist_sw",
        "getTopicZTPool",
        "async def _limit_pool",
        "def _intraday_signal",
    )
    if any(value in text for value in forbidden):
        raise SystemExit("A-share extraction left duplicate implementation details")
    if "self._a_share = AShareResearchProvider" not in text:
        raise SystemExit("A-share adapter was not wired into the stable facade")
    if "def _akshare()" not in text:
        raise SystemExit("Shared AkShare lazy loader was removed unexpectedly")

    PROVIDER_PATH.write_text(text, encoding="utf-8")
    print("A-share Research provider extracted behind the stable facade.")


if __name__ == "__main__":
    main()
