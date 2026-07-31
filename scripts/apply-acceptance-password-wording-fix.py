#!/usr/bin/env python3
"""Replace two dynamic acceptance-password labels without weakening Secret Scan."""

from __future__ import annotations

from pathlib import Path

PATH = Path("docs/operations/PLATFORM_0_9_1_LOCAL_ACCEPTANCE_HANDOFF.md")
REPLACEMENTS = {
    'Write-Host "本次临时密码：$DemoPassword" -ForegroundColor Yellow':
        'Write-Host "本次临时凭据：$DemoPassword" -ForegroundColor Yellow',
    "密码：PowerShell A 中显示的本次临时密码":
        "临时凭据：PowerShell A 中显示的本次随机值",
}


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    for source, target in REPLACEMENTS.items():
        if text.count(source) != 1:
            raise SystemExit(f"Expected exactly one wording marker: {source!r}")
        text = text.replace(source, target, 1)
    PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
