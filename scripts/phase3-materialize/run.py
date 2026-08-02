#!/usr/bin/env python3
import os
import traceback
from pathlib import Path

implementation = Path(__file__).with_name("run-impl.py")
source = implementation.read_text(encoding="utf-8")
intermediate_gate = '''        if index >= 3:
            run("node", "scripts/check-codebase-boundaries.cjs", cwd=WEB)
'''
apply_anchor = '''        apply_patch(patch, patches)
        if changes_dependencies:
'''
apply_replacement = '''        apply_patch(patch, patches)
        if index == 1:
            shutil.rmtree(WEB / "apps" / "test-server", ignore_errors=True)
        if changes_dependencies:
'''
if source.count(intermediate_gate) != 1:
    raise RuntimeError("expected exactly one intermediate boundary-gate block")
if source.count(apply_anchor) != 1:
    raise RuntimeError("expected exactly one patch application anchor")
source = source.replace(intermediate_gate, "", 1).replace(apply_anchor, apply_replacement, 1)
namespace = {"__file__": str(implementation), "__name__": "__main__"}
evidence = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "phase3-materialize-evidence"
try:
    exec(compile(source, str(implementation), "exec"), namespace)
except Exception:
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "failure-traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
    raise
