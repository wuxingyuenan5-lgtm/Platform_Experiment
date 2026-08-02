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
