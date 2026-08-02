#!/usr/bin/env python3
import json
import os
import subprocess
import traceback
from pathlib import Path

implementation = Path(__file__).with_name("run-impl.py")
source = implementation.read_text(encoding="utf-8")
intermediate_gate = '''        if index >= 3:
            run("node", "scripts/check-codebase-boundaries.cjs", cwd=WEB)
'''
final_gate = '''    run("node", "scripts/check-codebase-boundaries.cjs", cwd=WEB)
'''
replacement_gate = '''    boundary = subprocess.run(
        ["node", "scripts/check-codebase-boundaries.cjs"],
        cwd=WEB,
        text=True,
        capture_output=True,
    )
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "boundary-diagnostic.json").write_text(
        json.dumps(
            {
                "stdout": boundary.stdout,
                "stderr": boundary.stderr,
                "returncode": boundary.returncode,
                "head": git("rev-parse", "HEAD", capture=True).stdout.strip(),
                "status": git("status", "--porcelain", capture=True).stdout,
                "tracked_materializer": git("ls-files", "scripts/phase3-materialize", capture=True).stdout,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(boundary.stdout, end="", flush=True)
    print(boundary.stderr, end="", file=sys.stderr, flush=True)
    if boundary.returncode:
        raise subprocess.CalledProcessError(
            boundary.returncode,
            boundary.args,
            boundary.stdout,
            boundary.stderr,
        )
'''
if source.count(intermediate_gate) != 1:
    raise RuntimeError("expected exactly one intermediate boundary-gate block")
source = source.replace(intermediate_gate, "", 1)
if source.count(final_gate) != 1:
    raise RuntimeError("expected exactly one final boundary-gate call")
source = source.replace(final_gate, replacement_gate, 1)
namespace = {"__file__": str(implementation), "__name__": "__main__"}
evidence = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "phase3-materialize-evidence"
try:
    exec(compile(source, str(implementation), "exec"), namespace)
except Exception:
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "failure-traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
    raise
