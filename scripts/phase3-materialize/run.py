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
push_replacement = '''    import base64
    import urllib.request

    token = os.environ.get("GH_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repository:
        raise RuntimeError("GH_TOKEN and GITHUB_REPOSITORY are required for detached Git object publication")

    api_root = f"https://api.github.com/repos/{repository}/git"

    def github_json(method, url, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "platform-phase3-materializer",
            },
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))

    remote_parent = EXPECTED_HEAD
    remote_base_tree = git(
        "rev-parse",
        f"{EXPECTED_HEAD}^{{tree}}",
        capture=True,
    ).stdout.strip()
    published_commits = []

    for commit_index, commit_record in enumerate(real_commits, start=1):
        local_sha = commit_record["sha"]
        local_parent = git("rev-parse", f"{local_sha}^", capture=True).stdout.strip()
        changed = git(
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            "-M",
            local_parent,
            local_sha,
            capture=True,
        ).stdout
        tree_entries = []

        for raw_line in changed.splitlines():
            if not raw_line.strip():
                continue
            parts = raw_line.split("\\t")
            status_code = parts[0]
            if status_code.startswith("R") or status_code.startswith("C"):
                old_path = parts[1]
                path = parts[2]
                if status_code.startswith("R"):
                    tree_entries.append(
                        {"path": old_path, "mode": "100644", "type": "blob", "sha": None}
                    )
            else:
                path = parts[1]

            if status_code == "D":
                tree_entries.append(
                    {"path": path, "mode": "100644", "type": "blob", "sha": None}
                )
                continue

            tree_line = git("ls-tree", local_sha, "--", path, capture=True).stdout.strip()
            if not tree_line:
                raise RuntimeError(f"missing tree entry for {local_sha}:{path}")
            metadata, listed_path = tree_line.split("\\t", 1)
            mode, object_type, _local_blob_sha = metadata.split()
            if listed_path != path or object_type != "blob":
                raise RuntimeError(f"unexpected tree entry for {local_sha}:{path}")
            blob = subprocess.run(
                ["git", "show", f"{local_sha}:{path}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
            blob_response = github_json(
                "POST",
                f"{api_root}/blobs",
                {
                    "content": base64.b64encode(blob).decode("ascii"),
                    "encoding": "base64",
                },
            )
            tree_entries.append(
                {
                    "path": path,
                    "mode": mode,
                    "type": object_type,
                    "sha": blob_response["sha"],
                }
            )

        tree_response = github_json(
            "POST",
            f"{api_root}/trees",
            {"base_tree": remote_base_tree, "tree": tree_entries},
        )
        commit_response = github_json(
            "POST",
            f"{api_root}/commits",
            {
                "message": commit_record["message"],
                "tree": tree_response["sha"],
                "parents": [remote_parent],
            },
        )
        published_commits.append(
            {
                "index": commit_index,
                "message": commit_record["message"],
                "validated_local_sha": local_sha,
                "remote_sha": commit_response["sha"],
                "tree_sha": tree_response["sha"],
            }
        )
        remote_parent = commit_response["sha"]
        remote_base_tree = tree_response["sha"]

    remote_check = git(
        "ls-remote",
        "origin",
        f"refs/heads/{BRANCH}",
        capture=True,
    ).stdout.strip().split()[0]
    if remote_check != EXPECTED_HEAD:
        raise RuntimeError(
            f"remote head changed during detached publication: expected {EXPECTED_HEAD}, got {remote_check}"
        )

    publication = {
        "schema_version": 1,
        "base_head": EXPECTED_HEAD,
        "validated_local_final_head": final_head,
        "remote_final_commit": remote_parent,
        "commits": published_commits,
    }
    (EVIDENCE / "remote-commit-chain.json").write_text(
        json.dumps(publication, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(publication, ensure_ascii=False, indent=2))
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
