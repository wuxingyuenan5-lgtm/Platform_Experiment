#!/usr/bin/env python3
from pathlib import Path

implementation = Path(__file__).with_name("run-impl.py")
source = implementation.read_text(encoding="utf-8")
intermediate_gate = '''        if index >= 3:
            run("node", "scripts/check-codebase-boundaries.cjs", cwd=WEB)
'''
old_commit = '''def commit(message: str) -> str:
    run("git", "diff", "--cached", "--check")
    git("commit", "-m", message)
    return git("rev-parse", "HEAD", capture=True).stdout.strip()
'''
new_commit = '''def commit(message: str) -> str:
    summary = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    print(summary.stdout, flush=True)
    check = subprocess.run(
        ["git", "diff", "--cached", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    print(check.stdout, end="", flush=True)
    print(check.stderr, end="", file=sys.stderr, flush=True)
    if check.returncode:
        raise subprocess.CalledProcessError(check.returncode, check.args, check.stdout, check.stderr)
    committed = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )
    print(committed.stdout, end="", flush=True)
    print(committed.stderr, end="", file=sys.stderr, flush=True)
    if committed.returncode:
        raise subprocess.CalledProcessError(committed.returncode, committed.args, committed.stdout, committed.stderr)
    return git("rev-parse", "HEAD", capture=True).stdout.strip()
'''
if source.count(intermediate_gate) != 1:
    raise RuntimeError("expected exactly one intermediate boundary-gate block")
if source.count(old_commit) != 1:
    raise RuntimeError("expected exactly one commit function")
source = source.replace(intermediate_gate, "", 1).replace(old_commit, new_commit, 1)
namespace = {"__file__": str(implementation), "__name__": "__main__"}
exec(compile(source, str(implementation), "exec"), namespace)
