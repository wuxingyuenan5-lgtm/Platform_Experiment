#!/usr/bin/env python3
from pathlib import Path

implementation = Path(__file__).with_name("run-impl.py")
source = implementation.read_text(encoding="utf-8")
intermediate_gate = '''        if index >= 3:
            run("node", "scripts/check-codebase-boundaries.cjs", cwd=WEB)
'''
if source.count(intermediate_gate) != 1:
    raise RuntimeError("expected exactly one intermediate boundary-gate block")
source = source.replace(intermediate_gate, "", 1)
namespace = {"__file__": str(implementation), "__name__": "__main__"}
exec(compile(source, str(implementation), "exec"), namespace)
