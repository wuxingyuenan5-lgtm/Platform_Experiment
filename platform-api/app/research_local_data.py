from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast

from app.research_provider_errors import ResearchProviderError

DEFAULT_HEDGE_BOARD_DATA_ROOT = Path(r"D:\自营数据库\hedge-board")


def hedge_board_data_root() -> Path:
    configured = os.getenv("HEDGE_BOARD_DATA_ROOT", "").strip()
    return Path(configured) if configured else DEFAULT_HEDGE_BOARD_DATA_ROOT


def read_local_json(relative_path: str) -> dict[str, Any]:
    root = hedge_board_data_root().resolve()
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise ResearchProviderError("local_data_path_outside_root")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ResearchProviderError(f"local_data_not_found:{relative_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchProviderError(
            f"local_data_unavailable:{relative_path}:{type(exc).__name__}"
        ) from exc
    if not isinstance(payload, dict):
        raise ResearchProviderError(f"local_data_invalid_payload:{relative_path}")
    return cast(dict[str, Any], payload)
