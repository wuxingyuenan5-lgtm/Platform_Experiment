from __future__ import annotations

import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF_PATH = Path("scripts/scan-secrets.py")
ALLOW_MARKER = "secret-scan: allow"
ALLOWED_ENV_NAMES = {".env.example", ".env.live.example"}
# These tracked frontend manifests were reviewed: they contain only VITE_* public
# build/runtime values. Vite exposes such values to the browser, so no credential
# is permitted there; known-token and entropy checks still scan their contents.
ALLOWED_PUBLIC_ENV_PATHS = {
    Path("platform-web/.env"),
    Path("platform-web/.env.analyze"),
    Path("platform-web/.env.development"),
    Path("platform-web/.env.docker"),
    Path("platform-web/.env.platform.example"),
    Path("platform-web/.env.production"),
    Path("platform-web/.env.test"),
}
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
PLACEHOLDER_TERMS = {
    "example",
    "placeholder",
    "dummy",
    "sample",
    "changeme",
    "replace-me",
    "replace_me",
    "replace_with",
    "test-token",
    "test-secret",
    "your-password",
    "your_password",
    "替换",
    "自行设置",
    "随机",
}

KNOWN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_classic_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("github_fine_grained_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("openai_secret_key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
)
LITERAL_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?secret|private[_-]?key|client[_-]?secret|password)\b"
    r"\s*[:=]\s*[\"']([^\"']{20,})[\"']"
)
DOCUMENT_PASSWORD_ASSIGNMENT = re.compile(
    r"密码\s*[：:]\s*[`*_\"']*([A-Za-z0-9!@#$%^&./+_-]{6,})"
)
SQL_IDENTIFIED_BY = re.compile(r"(?i)\bIDENTIFIED\s+BY\s+['\"]([^'\"]{6,})['\"]")
WEAK_HASH_LITERAL = re.compile(
    r"(?i)\b(?:MD5|SHA1)\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
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
    relative = path.relative_to(ROOT)
    if relative in ALLOWED_PUBLIC_ENV_PATHS:
        return False
    name = path.name.lower()
    return (name == ".env" or name.startswith(".env.")) and name not in ALLOWED_ENV_NAMES


def shannon_entropy(value: str) -> float:
    counts = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return value.startswith("secret://") or any(term in lowered for term in PLACEHOLDER_TERMS)


def is_runtime_password_reference(line: str, value: str) -> bool:
    if "本次临时密码" not in line:
        return False
    return value.startswith("$") or "PowerShell" in line


def looks_like_high_entropy_secret(value: str) -> bool:
    if is_placeholder(value):
        return False
    character_classes = sum(
        (
            any(char.islower() for char in value),
            any(char.isupper() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
    )
    return len(value) >= 24 and character_classes >= 3 and shannon_entropy(value) >= 3.5


def documentation_findings(line: str) -> list[str]:
    findings: list[str] = []
    password = DOCUMENT_PASSWORD_ASSIGNMENT.search(line)
    if password:
        value = password.group(1)
        if not is_placeholder(value) and not is_runtime_password_reference(line, value):
            findings.append("plaintext_document_password")
    sql_password = SQL_IDENTIFIED_BY.search(line)
    if sql_password and not is_placeholder(sql_password.group(1)):
        findings.append("fixed_sql_password")
    weak_hash = WEAK_HASH_LITERAL.search(line)
    if weak_hash and not is_placeholder(weak_hash.group(1)):
        findings.append("weak_password_hash_literal")
    return findings


def validate_detection_patterns() -> None:
    assert documentation_findings("密码：`example-secret-value`") == []
    assert documentation_findings("IDENTIFIED BY '替换为随机密码'") == []
    assert documentation_findings("本次临时密码：$DemoPassword") == []
    assert documentation_findings("密码：PowerShell A 中显示的本次临时密码") == []
    assert documentation_findings("密码：`12345678`") == ["plaintext_document_password"]
    assert documentation_findings("IDENTIFIED BY 'FixedPassword123!'") == [
        "fixed_sql_password"
    ]
    assert documentation_findings("SELECT MD5('123456')") == [
        "weak_password_hash_literal"
    ]


def scan_file(path: Path) -> list[str]:
    relative = path.relative_to(ROOT)
    # The scanner contains its own detection regexes and test fixtures as source
    # text. Skipping only this implementation file avoids deterministic self-
    # matches while every other tracked file remains inside the scan boundary.
    if relative == SELF_PATH:
        return []
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
        for name, pattern in KNOWN_PATTERNS:
            if pattern.search(line):
                findings.append(f"{relative}:{line_number}: {name}")
        assignment = LITERAL_ASSIGNMENT.search(line)
        if assignment and looks_like_high_entropy_secret(assignment.group(1)):
            findings.append(f"{relative}:{line_number}: high_entropy_secret_assignment")
        if path.suffix.lower() == ".md":
            for finding in documentation_findings(line):
                findings.append(f"{relative}:{line_number}: {finding}")
    return findings


def main() -> int:
    validate_detection_patterns()
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
