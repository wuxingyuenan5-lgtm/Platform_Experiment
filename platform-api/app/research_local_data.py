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


def local_json_revision(relative_path: str) -> tuple[str, int, int, int] | None:
    """Identify atomic producer replacements without reading their full histories."""
    root = hedge_board_data_root().resolve()
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise ResearchProviderError("local_data_path_outside_root")
    try:
        stat = path.stat()
    except OSError:
        return None
    return str(path), stat.st_mtime_ns, stat.st_size, stat.st_ino


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


def write_local_json(relative_path: str, payload: dict[str, Any]) -> None:
    """Atomically publish a validated research artifact under the data root."""
    root = hedge_board_data_root().resolve()
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise ResearchProviderError("local_data_path_outside_root")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
