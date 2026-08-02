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
        if index == 2:
            application_path = WEB / "internal" / "vite-config" / "src" / "config" / "application.ts"
            application_text = application_path.read_text(encoding="utf-8")
            old_application = """    const { VITE_PUBLIC_PATH, VITE_BUILD_COMPRESS, VITE_ENABLE_ANALYZE } = loadEnv(
      mode,
      root,
    );
"""
            new_application = """    const { VITE_PUBLIC_PATH, VITE_BUILD_COMPRESS, VITE_ENABLE_ANALYZE } = loadEnv(mode, root);
"""
            if application_text.count(old_application) != 1:
                raise RuntimeError("expected Phase 3 application loadEnv formatting target")
            application_path.write_text(
                application_text.replace(old_application, new_application, 1),
                encoding="utf-8",
            )

            package_path = WEB / "internal" / "vite-config" / "src" / "config" / "package.ts"
            package_text = package_path.read_text(encoding="utf-8")
            old_package = """import { defineConfig, mergeConfig, type UserConfig } from 'vite';
import { commonConfig } from './common';
"""
            new_package = """import { defineConfig, mergeConfig, type UserConfig } from 'vite';

import { commonConfig } from './common';
"""
            if package_text.count(old_package) != 1:
                raise RuntimeError("expected Phase 2 package import-order lint target")
            package_path.write_text(
                package_text.replace(old_package, new_package, 1),
                encoding="utf-8",
            )

            modify_vars_path = WEB / "internal" / "vite-config" / "src" / "utils" / "modifyVars.ts"
            modify_vars_text = modify_vars_path.read_text(encoding="utf-8")
            old_modify_vars = """  return source.replace(/@import(?:\\s+\\(reference\\))?\\s+['\"]([^'\"]+)['\"];?/g, (_match, importPath) => {
    if (importPath.startsWith('~')) {
      return '';
    }
    return inlineLessReferences(resolveLessImport(currentDir, importPath), seen);
  });
"""
            new_modify_vars = """  return source.replace(
    /@import(?:\\s+\\(reference\\))?\\s+['\"]([^'\"]+)['\"];?/g,
    (_match, importPath) => {
      if (importPath.startsWith('~')) {
        return '';
      }
      return inlineLessReferences(resolveLessImport(currentDir, importPath), seen);
    },
  );
"""
            if modify_vars_text.count(old_modify_vars) != 1:
                raise RuntimeError("expected Phase 2 modifyVars Prettier lint target")
            modify_vars_path.write_text(
                modify_vars_text.replace(old_modify_vars, new_modify_vars, 1),
                encoding="utf-8",
            )
        if index == 6:
            state_path = ROOT / "docs" / "codex" / "current-state.md"
            state_text = state_path.read_text(encoding="utf-8")
            old_phase2 = "Phase 2 Draft PR #141 remains Open, Draft and Unmerged; no Phase 3 code is added to it."
            new_phase2 = "GitHub PR #141 remains Open, Draft and Unmerged as the accepted Phase 2 review; no Phase 3 code is added to it."
            old_authority = "GitHub PR #148 owns the active Phase 3 HEAD, CI and review evidence."
            new_authority = "GitHub PR #148 owns the active branch, Draft PR, HEAD, CI and review state."
            if state_text.count(old_phase2) != 1 or state_text.count(old_authority) != 1:
                raise RuntimeError("expected Phase 2 and Phase 3 GitHub authority sentences")
            state_text = state_text.replace(old_phase2, new_phase2, 1)
            state_text = state_text.replace(old_authority, new_authority, 1)
            state_path.write_text(state_text, encoding="utf-8")
        if changes_dependencies:
'''
push_anchor = '''    git("push", "origin", f"HEAD:{BRANCH}")
'''
push_replacement = '''    snapshot_root = EVIDENCE / "commit-snapshots"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    reconstruction = {
        "schema_version": 1,
        "base_head": EXPECTED_HEAD,
        "validated_final_head": final_head,
        "commits": [],
    }
    for commit_index, commit_record in enumerate(real_commits, start=1):
        commit_sha = commit_record["sha"]
        parent_sha = git("rev-parse", f"{commit_sha}^", capture=True).stdout.strip()
        changed = git(
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            "-M",
            parent_sha,
            commit_sha,
            capture=True,
        ).stdout
        commit_dir = snapshot_root / f"{commit_index:02d}"
        files_dir = commit_dir / "files"
        entries = []
        for raw_line in changed.splitlines():
            if not raw_line.strip():
                continue
            parts = raw_line.split("\\t")
            status_code = parts[0]
            if status_code.startswith("R") or status_code.startswith("C"):
                old_path = parts[1]
                path = parts[2]
                entries.append({"action": "delete", "path": old_path, "status": status_code})
            else:
                path = parts[1]
            if status_code == "D":
                entries.append({"action": "delete", "path": path, "status": status_code})
                continue
            tree_line = git("ls-tree", commit_sha, "--", path, capture=True).stdout.strip()
            if not tree_line:
                raise RuntimeError(f"missing tree entry for {commit_sha}:{path}")
            metadata, listed_path = tree_line.split("\\t", 1)
            mode, object_type, object_sha = metadata.split()
            if listed_path != path:
                raise RuntimeError(f"unexpected tree path {listed_path} for {path}")
            file_target = files_dir / path
            file_target.parent.mkdir(parents=True, exist_ok=True)
            blob = subprocess.run(
                ["git", "show", f"{commit_sha}:{path}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
            file_target.write_bytes(blob)
            entries.append(
                {
                    "action": "upsert",
                    "path": path,
                    "status": status_code,
                    "mode": mode,
                    "type": object_type,
                    "source_blob_sha": object_sha,
                    "artifact_file": str(file_target.relative_to(EVIDENCE)),
                }
            )
        commit_manifest = {
            "index": commit_index,
            "source_sha": commit_sha,
            "source_parent_sha": parent_sha,
            "message": commit_record["message"],
            "entries": entries,
        }
        (commit_dir / "manifest.json").write_text(
            json.dumps(commit_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        reconstruction["commits"].append(commit_manifest)
    (EVIDENCE / "reconstruction.json").write_text(
        json.dumps(reconstruction, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
'''
if source.count(intermediate_gate) != 1:
    raise RuntimeError("expected exactly one intermediate boundary-gate block")
if source.count(apply_anchor) != 1:
    raise RuntimeError("expected exactly one patch application anchor")
if source.count(push_anchor) != 1:
    raise RuntimeError("expected exactly one materializer push anchor")
source = (
    source.replace(intermediate_gate, "", 1)
    .replace(apply_anchor, apply_replacement, 1)
    .replace(push_anchor, push_replacement, 1)
)
namespace = {"__file__": str(implementation), "__name__": "__main__"}
evidence = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "phase3-materialize-evidence"
try:
    exec(compile(source, str(implementation), "exec"), namespace)
except Exception:
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "failure-traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
    raise
