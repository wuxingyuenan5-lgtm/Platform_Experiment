#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL_ROOT = ROOT / "scripts" / "phase3-materialize"
PATCH_ROOT = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "patches"
WEB = ROOT / "platform-web"
EVIDENCE = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "phase3-materialize-evidence"
BRANCH = "refactor/platform-0-9-3-codebase-and-build-simplification"
BASE_SHA = "cd825fe6bd9ecdf42082069b2785844eda2efac8"
EXPECTED_HEAD = os.environ.get("PHASE3_EXPECTED_HEAD", os.environ.get("GITHUB_SHA", "")).strip()

COMMITS = [
    ("001.patch", "refactor(platform-0.9.3): remove unused test server workspace", True),
    ("002.patch", "refactor(platform-0.9.3): remove unused demo mock and template assets", True),
    ("003.patch", "refactor(platform-0.9.3): bound route and view discovery", False),
    ("004.patch", "ci(platform-0.9.3): enforce Phase 3 codebase boundaries", False),
    ("005.patch", "chore(platform-0.9.3): simplify frontend build inputs", False),
    ("006.patch", "docs(platform-0.9.3): record Phase 3 bounded cleanup state", False),
]


def load_patches() -> dict[str, bytes]:
    parts = sorted(TOOL_ROOT.glob("payload.part*"))
    if not parts:
        raise FileNotFoundError("phase3 materializer payload parts")
    raw = b"".join(path.read_bytes() for path in parts)
    payloads: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.startswith("patches/"):
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            payloads[Path(member.name).name] = extracted.read()
    missing = [name for name, _, _ in COMMITS if name not in payloads]
    if missing:
        raise FileNotFoundError(f"missing materializer patches: {missing}")
    return payloads


def run(*args: str, cwd: Path = ROOT, capture: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command = list(args)
    print("+", " ".join(command), flush=True)
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
        env=merged_env,
    )


def git(*args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return run("git", *args, capture=capture)


def remote_head() -> str:
    result = git("ls-remote", "origin", f"refs/heads/{BRANCH}", capture=True)
    line = result.stdout.strip()
    return line.split()[0] if line else ""


def assert_remote_head(expected: str) -> None:
    actual = remote_head()
    if actual != expected:
        raise RuntimeError(f"remote branch advanced unexpectedly: expected {expected}, got {actual}")


def tracked_metrics() -> dict[str, object]:
    suffixes = {".ts", ".tsx", ".js", ".jsx", ".vue", ".cjs", ".mjs", ".css", ".scss", ".less"}
    roots = [WEB / "src", WEB / "internal", WEB / "packages", WEB / "apps", WEB / "mock"]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes:
                files.append(path)
    total_lines = 0
    total_bytes = 0
    for path in files:
        raw = path.read_bytes()
        total_bytes += len(raw)
        total_lines += len(raw.decode("utf-8", errors="replace").splitlines())

    def path_metrics(relative: str) -> dict[str, int]:
        root = WEB / relative
        selected = [path for path in root.rglob("*") if path.is_file()] if root.exists() else []
        return {
            "files": len(selected),
            "bytes": sum(path.stat().st_size for path in selected),
            "lines": sum(len(path.read_text(encoding="utf-8", errors="replace").splitlines()) for path in selected),
        }

    workspace = []
    for package_json in sorted(WEB.glob("apps/*/package.json")) + sorted(WEB.glob("internal/*/package.json")) + sorted(WEB.glob("packages/*/package.json")):
        payload = json.loads(package_json.read_text(encoding="utf-8"))
        workspace.append({"path": str(package_json.parent.relative_to(WEB)), "name": payload.get("name")})
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    lock_text = (WEB / "pnpm-lock.yaml").read_text(encoding="utf-8")
    importers = len(re.findall(r"^  [^\s][^:]*:\s*$", lock_text.split("packages:", 1)[0], flags=re.M))
    packages = len(re.findall(r"^  [^\s][^:]*:\s*$", lock_text.split("packages:", 1)[1].split("snapshots:", 1)[0], flags=re.M)) if "packages:" in lock_text else 0
    snapshots = len(re.findall(r"^  [^\s][^:]*:\s*$", lock_text.split("snapshots:", 1)[1], flags=re.M)) if "snapshots:" in lock_text else 0
    return {
        "controlled_source": {"files": len(files), "lines": total_lines, "bytes": total_bytes},
        "demo_views": path_metrics("src/views/demo"),
        "demo_api": path_metrics("src/api/demo"),
        "root_mock": path_metrics("mock"),
        "test_server": path_metrics("apps/test-server"),
        "template_request": path_metrics("src/views/hooks/request"),
        "workspace": {"count": len(workspace), "packages": workspace},
        "dependencies": {
            "direct": len(package.get("dependencies", {})),
            "dev": len(package.get("devDependencies", {})),
        },
        "lockfile": {"importers": importers, "packages": packages, "snapshots": snapshots},
    }


def build_metrics(label: str) -> dict[str, object]:
    log_path = EVIDENCE / f"build-{label}.log"
    dist = WEB / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(
            ["pnpm", "build"],
            cwd=WEB,
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
            env={**os.environ, "CI": "true", "HUSKY": "0"},
        )
    elapsed = time.monotonic() - started
    if proc.returncode:
        print(log_path.read_text(encoding="utf-8", errors="replace"), file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, ["pnpm", "build"])
    text = log_path.read_text(encoding="utf-8", errors="replace")
    output_files = [p for p in dist.rglob("*") if p.is_file()] if dist.exists() else []
    max_file = max(output_files, key=lambda p: p.stat().st_size, default=None)
    module_matches = re.findall(r"([\d,]+) modules transformed", text)
    warning_lines = [line for line in text.splitlines() if re.search(r"\bwarn(?:ing)?\b", line, re.I)]
    return {
        "elapsed_seconds": round(elapsed, 3),
        "modules_transformed": int(module_matches[-1].replace(",", "")) if module_matches else None,
        "output_files": len(output_files),
        "output_bytes": sum(p.stat().st_size for p in output_files),
        "largest_chunk": None if max_file is None else {
            "path": str(max_file.relative_to(dist)),
            "bytes": max_file.stat().st_size,
        },
        "warnings": len(warning_lines),
        "log": str(log_path),
    }


def frozen_install() -> None:
    run("pnpm", "install", "--frozen-lockfile", cwd=WEB, env={"CI": "true", "HUSKY": "0"})


def lockfile_only() -> None:
    run("pnpm", "install", "--lockfile-only", cwd=WEB, env={"CI": "true", "HUSKY": "0"})
    frozen_install()


def apply_patch(name: str, payloads: dict[str, bytes]) -> None:
    print("+ git apply --binary --index -", name, flush=True)
    subprocess.run(
        ["git", "apply", "--binary", "--index", "-"],
        cwd=ROOT,
        input=payloads[name],
        check=True,
    )


def commit(message: str) -> str:
    run("git", "diff", "--cached", "--check")
    git("commit", "-m", message)
    return git("rev-parse", "HEAD", capture=True).stdout.strip()


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if not EXPECTED_HEAD:
        raise RuntimeError("expected Phase 3 head is required")
    if os.environ.get("GITHUB_HEAD_REF") and os.environ.get("GITHUB_HEAD_REF") != BRANCH:
        raise RuntimeError(f"unexpected head branch: {os.environ.get('GITHUB_HEAD_REF')}")
    assert_remote_head(EXPECTED_HEAD)
    git("status", "--short")
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")

    tool_version = run("pnpm", "--version", capture=True).stdout.strip()
    if tool_version != "9.15.9":
        raise RuntimeError(f"expected pnpm 9.15.9, got {tool_version}")
    node_version = run("node", "--version", capture=True).stdout.strip()

    before = tracked_metrics()
    frozen_install()
    before_build = build_metrics("before")
    patches = load_patches()
    (EVIDENCE / "before.json").write_text(
        json.dumps({"pnpm": tool_version, "node": node_version, "repository": before, "build": before_build}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    real_commits: list[dict[str, str]] = []
    for index, (patch, message, changes_dependencies) in enumerate(COMMITS, start=1):
        if index == 4:
            git("checkout", BASE_SHA, "--", ".github/workflows/version-consistency.yml")
        if index == 6:
            git("checkout", BASE_SHA, "--", "docs/codex/current-state.md")
        apply_patch(patch, patches)
        if changes_dependencies:
            lockfile_only()
        if index == 6:
            bootstrap = ROOT / ".github" / "workflows" / "phase-3-tool-bootstrap.yml"
            if bootstrap.exists():
                bootstrap.unlink()
                git("add", str(bootstrap.relative_to(ROOT)))
            shutil.rmtree(TOOL_ROOT)
            git("add", "-A", "scripts/phase3-materialize")
        git("add", "-A")
        sha = commit(message)
        real_commits.append({"sha": sha, "message": message})
        if index >= 3:
            run("node", "scripts/check-codebase-boundaries.cjs", cwd=WEB)

    frozen_install()
    run("node", "scripts/check-codebase-boundaries.cjs", cwd=WEB)
    run("python", "scripts/check-documentation-consistency.py")
    run("python", "scripts/check-repository-structure.py")
    run("python", "scripts/check-codex-context.py")
    run("python", "scripts/check-active-naming-consistency.py")
    run("python", "scripts/check-version-consistency.py")
    run("python", "scripts/context-for.py", "--check-budgets", "--json")
    run("pnpm", "lint", cwd=WEB, env={"CI": "true", "HUSKY": "0"})
    run("pnpm", "type:check", cwd=WEB, env={"CI": "true", "HUSKY": "0"})
    after_build = build_metrics("after")
    run("pnpm", "test:user-system", cwd=WEB, env={"CI": "true", "HUSKY": "0"})
    run("pnpm", "test:hedge-board-layout", cwd=WEB, env={"CI": "true", "HUSKY": "0"})

    after = tracked_metrics()
    final_head = git("rev-parse", "HEAD", capture=True).stdout.strip()
    status = git("status", "--porcelain", capture=True).stdout
    if status:
        raise RuntimeError(f"materialized worktree is dirty:\n{status}")
    assert_remote_head(EXPECTED_HEAD)
    payload = {
        "schema_version": 1,
        "phase2_head": BASE_SHA,
        "materializer_trigger_head": EXPECTED_HEAD,
        "final_head": final_head,
        "pnpm": tool_version,
        "node": node_version,
        "commits": real_commits,
        "before": before,
        "after": after,
        "build_before": before_build,
        "build_after": after_build,
    }
    (EVIDENCE / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    git("push", "origin", f"HEAD:{BRANCH}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
