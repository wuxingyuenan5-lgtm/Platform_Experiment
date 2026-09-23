"""One read-only local acceptance sample; scheduling belongs to Codex automation."""

import json
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform-api"))
from app.config import get_settings

OUTPUT = (
    ROOT
    / "platform-api/data/backups/20260909-normal-trading-enable/strategy-stability-72h-20260915.jsonl"
)


def collect() -> dict:
    now = datetime.now(UTC)
    result = {"observedAt": now.isoformat(), "http": {}}
    opener = build_opener(ProxyHandler({}))
    for name, url in (
        ("web", "http://127.0.0.1:4373/index.html"),
        ("api", "http://127.0.0.1:8000/health"),
        ("runtime", "http://127.0.0.1:8100/health"),
        ("monitors", "http://127.0.0.1:8000/health/monitors"),
        ("runtimeMetrics", "http://127.0.0.1:8100/metrics"),
    ):
        started = perf_counter()
        try:
            with opener.open(url, timeout=5) as response:
                content = response.read().decode("utf-8")
                value = {"status": response.status}
            if name == "monitors":
                value["data"] = json.loads(content)
            elif name == "runtimeMetrics":
                value["process"] = {
                    line.split()[0]: float(line.split()[1])
                    for line in content.splitlines()
                    if line.startswith(
                        (
                            "process_start_time_seconds ",
                            "process_resident_memory_bytes ",
                            "process_cpu_seconds_total ",
                        )
                    )
                }
        except (OSError, ValueError, TimeoutError) as exc:
            value = {"error": type(exc).__name__}
        value["elapsedMs"] = round((perf_counter() - started) * 1000, 1)
        result["http"][name] = value
    try:
        path = Path(get_settings().database_path).resolve()
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
        try:
            result["accountStates"] = dict(
                db.execute(
                    "SELECT status,count(*) FROM account_sync_status GROUP BY status"
                ).fetchall()
            )
            result["financialJobStates"] = [
                list(row)
                for row in db.execute(
                    "SELECT job,status,count(*) FROM account_read_jobs GROUP BY job,status"
                )
            ]
            result["snapshotAgesSeconds"] = [
                round((now - datetime.fromisoformat(row[0])).total_seconds(), 1)
                if row[0]
                else None
                for row in db.execute("SELECT last_success_at FROM account_sync_status")
            ]
            result["commandStates"] = dict(
                db.execute(
                    "SELECT status,count(*) FROM trade_commands GROUP BY status"
                ).fetchall()
            )
        finally:
            db.close()
    except (OSError, ValueError, sqlite3.Error) as exc:
        result["storeError"] = type(exc).__name__
    for key, path in (
        ("managedServices", ROOT / ".codex/dev-platform/platform-dev-state.json"),
        ("webRelease", ROOT / ".codex/releases/web/current.json"),
    ):
        try:
            result[key] = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            result[key] = {"error": type(exc).__name__}
    try:
        pids = ",".join(
            str(int(row["pid"]))
            for row in result["managedServices"].get("services", [])
        )
        if pids:
            command = (
                f"Get-Process -Id {pids} -ErrorAction SilentlyContinue | "
                "Select-Object Id,CPU,WorkingSet64,HandleCount,"
                "@{n='ThreadCount';e={$_.Threads.Count}},"
                "@{n='StartedAt';e={$_.StartTime.ToUniversalTime().ToString('o')}} | "
                "ConvertTo-Json -Compress"
            )
            process = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            result["processResources"] = json.loads(process.stdout)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        result["resourceError"] = type(exc).__name__
    return result


if __name__ == "__main__":
    sample = collect()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(json.dumps(sample, ensure_ascii=False))
