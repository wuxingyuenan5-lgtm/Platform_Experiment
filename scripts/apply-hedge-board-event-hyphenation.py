#!/usr/bin/env python3
"""Normalize the touched Hedge Board update event to Vue hyphenation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "platform-web/src/views/hedgeBoard/index.vue"
OLD = '@update:modelValue="selectBoardCategory"'
NEW = '@update:model-value="selectBoardCategory"'


def main() -> None:
    content = TARGET.read_text(encoding="utf-8")
    if NEW in content and OLD not in content:
        print("Hedge Board event hyphenation is already applied.")
        return
    if content.count(OLD) != 1:
        raise SystemExit("Expected exactly one touched update:modelValue event")
    TARGET.write_text(content.replace(OLD, NEW, 1), encoding="utf-8")
    print("Normalized Hedge Board update event hyphenation.")


if __name__ == "__main__":
    main()
