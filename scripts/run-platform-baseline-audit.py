#!/usr/bin/env python3
"""Run the repository audit with strict text-file classification.

The original collector intentionally remains unchanged in this audit phase so
its first evidence run stays reproducible. This entrypoint corrects binary
asset classification without changing any product code. The two files will be
folded together when the audit tooling is finalized.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

COLLECTOR_PATH = Path(__file__).with_name("audit-platform-baseline.py")


def load_collector() -> ModuleType:
    spec = importlib.util.spec_from_file_location("platform_baseline_collector", COLLECTOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load collector: {COLLECTOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def strict_is_text(module: ModuleType, path: Path) -> bool:
    if path.name.startswith(".env"):
        return True
    suffix = path.suffix.lower()
    if suffix:
        return suffix in module.TEXT_SUFFIXES
    try:
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def main() -> int:
    collector = load_collector()
    collector.is_text = lambda path: strict_is_text(collector, path)
    return int(collector.main())


if __name__ == "__main__":
    raise SystemExit(main())
