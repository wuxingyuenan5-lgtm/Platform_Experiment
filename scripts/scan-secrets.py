from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW_MARKER = "secret-scan: allow"
ALLOWED_ENV_NAMES = {".env.example", ".env.live.example"}
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".zip",
    ".pdf",
    ".db",
}

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_classic_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("github_fine_grained_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("openai_secret_key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    (
        "literal_secret_assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?secret|private[_-]?key|client[_-]?secret|password)\b"
            r"\s*[:=]\s*[\"'](?!\.\.\.|<|\$\{|secret://)([^\"']{12,})[\"']"
        ),
    ),
)


def tracked_files() -> list[Path]:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            stderr=subprocess.DEVNULL,
        )
        return [ROOT / item.decode("utf-8") for item in output.split(b"\0") if item]
    except (OSError, subprocess.CalledProcessError):
        return [path for path in ROOT.rglob("*") if path.is_file()]


def forbidden_env_file(path: Path) -> bool:
    name = path.name.lower()
    return (name == ".env" or name.startswith(".env.")) and name not in ALLOWED_ENV_NAMES


def scan_file(path: Path) -> list[str]:
    relative = path.relative_to(ROOT)
    if forbidden_env_file(path):
        return [f"{relative}: tracked environment file is forbidden"]
    if path.suffix.lower() in SKIP_SUFFIXES:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(f"{relative}:{line_number}: {name}")
    return findings


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if path.exists():
            findings.extend(scan_file(path))
    if findings:
        print("Secret scan failed. Remove or rotate the credential; do not merely rename it.")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Secret scan passed: no tracked high-risk credential material detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
