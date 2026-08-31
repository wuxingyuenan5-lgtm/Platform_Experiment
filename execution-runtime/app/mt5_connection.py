from __future__ import annotations

from typing import Any


def initialize_mt5(
    mt5: Any,
    *,
    terminal_path: str | None,
    **kwargs: object,
) -> bool:
    """Initialize the explicit Terminal using MetaTrader5's positional path contract."""
    if terminal_path:
        return bool(mt5.initialize(terminal_path, **kwargs))
    return bool(mt5.initialize(**kwargs))
