from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OLD_A = "refactor/platform-0-9-3-repository-and-context-optimization"
OLD_B = "refactor/platform-0-9-3-codebase-and-build-simplification"
PATTERN = "refactor/platform-0-9-3-*"
PREFIX = "refactor/platform-0-9-3-"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def replace_or_assert(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new)
    if new not in text:
        raise RuntimeError(f"missing expected replacement for {label}")
    return text
