from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = ROOT / "scripts/collect-legacy-production-evidence.sh"


@pytest.mark.architecture
def test_legacy_evidence_collector_is_valid_read_only_shell() -> None:
    result = subprocess.run(
        ["bash", "-n", str(COLLECTOR)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.architecture
def test_legacy_evidence_collector_never_reads_secret_values_or_business_rows() -> None:
    source = COLLECTOR.read_text(encoding="utf-8")

    assert "set -euo pipefail" in source
    assert "umask 077" in source
    assert source.index("umask 077") < source.index('mkdir -p "$OUTPUT_DIR"')
    assert 'chmod 700 "$OUTPUT_DIR"' in source
    assert 'chmod 600 "$OUTPUT_DIR"/*' in source
    assert "systemctl is-active" in source
    assert "systemctl is-enabled" in source
    assert "ss -lntH" in source
    assert ":(80|443|3306|4373|8000|8080|8082|8100)" in source
    assert "git -C \"$REPO_ROOT\" status --short --branch" in source
    assert "stat --printf=" in source
    assert "sha256sum \"$file\"" in source
    assert "awk -F=" in source
    assert "information_schema.TABLES" in source
    assert "information_schema.COLUMNS" in source
    assert "information_schema.STATISTICS" in source
    assert "! -name 'MANIFEST.sha256'" in source

    for forbidden in (
        "set -x",
        "printenv",
        "systemctl show-environment",
        "EnvironmentFile=-",
        "cat /etc/variable-global",
        "source /etc/variable-global",
        ". /etc/variable-global",
        "ps -e",
        "ps aux",
        "nginx -T",
        "journalctl",
        "mysqldump",
        "SELECT *",
        "FROM risk_control.users",
        "FROM risk_control.accounts",
        "FROM risk_control.assets",
        "password_hash",
        "api_key_encrypted",
        "api_secret_encrypted",
        "git -C \"$REPO_ROOT\" remote get-url",
        "sudo ",
        "curl ",
        "wget ",
    ):
        assert forbidden not in source
