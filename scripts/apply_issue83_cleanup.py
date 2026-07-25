#!/usr/bin/env python3
"""Apply the bounded version/dead-code cleanup for Issue #83."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.7.0"


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    if old not in content:
        raise RuntimeError(f"expected snippet missing from {path}: {old[:120]!r}")
    target.write_text(content.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    (ROOT / "VERSION").write_text(f"{VERSION}\n", encoding="utf-8")

    replace_once(
        "platform-backend/pyproject.toml",
        'version = "0.2.0"',
        f'version = "{VERSION}"',
    )
    replace_once(
        "platform-backend/app/application.py",
        'version="0.6.0"',
        f'version="{VERSION}"',
    )
    replace_once(
        "platform-backend/app/application.py",
        '"version": "0.6.0"',
        f'"version": "{VERSION}"',
    )
    replace_once(
        "execution-runtime/pyproject.toml",
        'version = "0.1.1"',
        f'version = "{VERSION}"',
    )
    replace_once(
        "execution-runtime/app/main.py",
        'version="0.5.0"',
        f'version="{VERSION}"',
    )
    replace_once(
        "admin-risk/.env",
        'VITE_GLOB_APP_VERSION = "1.0.0"',
        f'VITE_GLOB_APP_VERSION = "{VERSION}"',
    )

    replace_once(
        "admin-risk/src/api/platform/trading.ts",
        "  CreateOrderInput,\n",
        "",
    )
    replace_once(
        "admin-risk/src/api/platform/trading.ts",
        "  OrderResult,\n",
        "",
    )
    replace_once(
        "admin-risk/src/api/platform/trading.ts",
        "export async function createTradingOrder(input: CreateOrderInput): Promise<OrderResult> {\n"
        "  const response = await client.post<OrderResult>('/trading/orders', input);\n"
        "  return response.data;\n"
        "}\n\n",
        "",
    )

    replace_once(
        "admin-risk/src/api/platform/trading.types.ts",
        "export type TradingOrderStatus =\n"
        "  | 'processing'\n"
        "  | 'acknowledged'\n"
        "  | 'filled'\n"
        "  | 'rejected'\n"
        "  | 'result_unknown';\n\n",
        "",
    )
    replace_once(
        "admin-risk/src/api/platform/trading.types.ts",
        "export interface CreateOrderInput {\n"
        "  accountId: string;\n"
        "  instrumentId: string;\n"
        "  symbol: string;\n"
        "  side: TradingSide;\n"
        "  orderType: TradingOrderType;\n"
        "  quantity: string;\n"
        "  price?: string;\n"
        "}\n\n"
        "export interface OrderResult {\n"
        "  orderId: string;\n"
        "  commandId: string;\n"
        "  status: TradingOrderStatus;\n"
        "  externalOrderId?: string | null;\n"
        "}\n\n",
        "",
    )

    (ROOT / "admin-risk/src/hooks/trading/usePlatformTrading.ts").write_text(
        """import { ref } from 'vue';

import { getTradingSnapshot } from '/@/api/platform/trading';
import type { TradingSnapshot } from '/@/api/platform/trading.types';

function normalizeError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return 'Trading request failed';
}

export function usePlatformTrading() {
  const refreshing = ref(false);
  const errorMessage = ref<string | null>(null);
  const snapshot = ref<TradingSnapshot>({ position: null, pnl: null });

  async function refresh(accountId: string, instrumentId: string): Promise<void> {
    refreshing.value = true;
    errorMessage.value = null;
    try {
      snapshot.value = await getTradingSnapshot(accountId, instrumentId);
    } catch (error) {
      errorMessage.value = normalizeError(error);
      throw error;
    } finally {
      refreshing.value = false;
    }
  }

  return {
    errorMessage,
    refreshing,
    snapshot,
    refresh,
  };
}
""",
        encoding="utf-8",
    )

    (ROOT / "scripts/check-version-consistency.py").write_text(
        '''#!/usr/bin/env python3
"""Fail when maintained product version declarations drift from root VERSION."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def project_version(path: str) -> str:
    with (ROOT / path).open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def require_match(path: str, pattern: str) -> str:
    content = (ROOT / path).read_text(encoding="utf-8")
    match = re.search(pattern, content)
    if match is None:
        raise SystemExit(f"Version declaration missing: {path}")
    return match.group(1)


def main() -> None:
    actual = {
        "platform-backend package": project_version("platform-backend/pyproject.toml"),
        "platform-backend API": require_match(
            "platform-backend/app/application.py",
            r'app = FastAPI\(title=settings\.app_name, version="([^"]+)"',
        ),
        "platform-backend info": require_match(
            "platform-backend/app/application.py",
            r'"version": "([^"]+)"',
        ),
        "execution-runtime package": project_version("execution-runtime/pyproject.toml"),
        "execution-runtime API": require_match(
            "execution-runtime/app/main.py",
            r'app = FastAPI\(title=settings\.app_name, version="([^"]+)"',
        ),
        "frontend display": require_match(
            "admin-risk/.env",
            r'VITE_GLOB_APP_VERSION\s*=\s*"([^"]+)"',
        ),
    }
    drift = {name: value for name, value in actual.items() if value != EXPECTED}
    if drift:
        details = ", ".join(f"{name}={value}" for name, value in sorted(drift.items()))
        raise SystemExit(f"Version drift from VERSION={EXPECTED}: {details}")
    print(f"Maintained platform version declarations are consistent: {EXPECTED}")


if __name__ == "__main__":
    main()
''',
        encoding="utf-8",
    )

    workflow = ROOT / ".github/workflows/platform-ci.yml"
    workflow_text = workflow.read_text(encoding="utf-8")
    workflow_text = workflow_text.replace(
        "      - 'execution-runtime/**'\n",
        "      - 'VERSION'\n      - 'execution-runtime/**'\n",
        2,
    )
    workflow_text = workflow_text.replace(
        "      - 'admin-risk/package.json'\n",
        "      - 'admin-risk/.env'\n      - 'admin-risk/package.json'\n",
        2,
    )
    marker = (
        "      - name: Check architecture ownership documentation consistency\n"
        "        run: python scripts/check-documentation-consistency.py\n"
    )
    if marker not in workflow_text:
        raise RuntimeError("Platform CI repository-safety marker missing")
    workflow_text = workflow_text.replace(
        marker,
        marker
        + "      - name: Check maintained version consistency\n"
        + "        run: python scripts/check-version-consistency.py\n",
        1,
    )
    workflow.write_text(workflow_text, encoding="utf-8")

    replace_once(
        "docs/engineering/GIT_WORKFLOW.md",
        "## 7. 版本标记\n\nTag 只用于经过验收、需要明确回滚或部署识别的稳定点，例如：",
        "## 7. 版本标记\n\n根目录 `VERSION` 是 maintained product version 的唯一声明源。Backend、Execution Runtime 与前端展示版本必须同步，CI 会阻止漂移。\n\nTag 只用于经过验收、需要明确回滚或部署识别的稳定点，例如：",
    )

    replace_once(
        "CHANGELOG.md",
        "## Unreleased\n",
        "## Unreleased\n\n### Platform 0.7.0 version consolidation and dead-code cleanup — Issue #83\n\n"
        "- Added root `VERSION` as the maintained platform release identifier and synchronized Backend, Execution Runtime and frontend display versions to `0.7.0`.\n"
        "- Added a blocking version-consistency check to Repository Safety.\n"
        "- Removed the unused frontend legacy single-order submission client, request/result types and submit-state hook path; maintained funding execution continues through ExecutionBatch.\n"
        "- Retained the Backend deprecated `POST /trading/orders` compatibility API because backend recovery/safety tests and possible external consumers still depend on it.\n\n",
    )


if __name__ == "__main__":
    main()
