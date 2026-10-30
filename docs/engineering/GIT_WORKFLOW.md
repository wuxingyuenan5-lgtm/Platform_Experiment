# Git Workflow and Version Governance

## Branch and review

- Ordinary local work may continue in the current checkout; a new branch or PR is not a prerequisite. When a new branch is useful or requested, use `codex/<slug>` unless the Owner specifies another name. If the Owner explicitly asks to make the current local snapshot the latest `main`, a direct local commit on `main` is allowed; that instruction still does not authorize pushing or rewriting history.
- Use one pull request for one coherent outcome.
- Keep non-trivial work Draft until implementation and validation are complete.
- Do not merge, tag, release or deploy without an explicit owner decision.
- Prefer one to four logical commits rather than one commit per file.

## Change classes

| Class | Scope | Validation |
|---|---|---|
| Fast | documentation or synchronized version metadata | repository quality, version and Secret Scan |
| Standard | bounded module behavior without protected semantics | affected module CI |
| Critical | trading, execution, risk, auth, credentials, database, contracts, CI governance or Live behavior | full affected safety matrix |

Critical changes preserve explicit rollback/forward-fix and protected semantics in the PR description. A completed phase document or evidence ledger is not required in the worktree.

Line counts are maintenance signals, not correctness or architecture acceptance.
The frontend boundary check reports large owners without forcing a split only
to meet a number; missing owners, forbidden dependencies, unsafe data sources
and route/permission violations remain blocking. Split only a demonstrated
second responsibility. Local outputs belong in ignored `tmp/`; retained source
references belong in `references/`, never in product/runtime import paths.

After changing formal route modules, regenerate the validation-only manifest
with `node platform-web/scripts/formal-route-manifest.cjs --write`, then run
`node platform-web/scripts/check-codebase-boundaries.cjs`. Generated paths use
forward slashes and source hashes normalize CRLF to LF so Windows and CI agree;
the manifest does not grant routes, permissions or trading authority.

## Maintained CI

- `.github/workflows/platform-ci.yml` — Platform API, Runtime and frontend build/test matrix;
- `.github/workflows/repository-quality.yml` — version, documentation, data ownership and architecture boundaries;
- `.github/workflows/secret-scan.yml` — secret detection;
- maintained browser E2E workflows;
- `.github/workflows/platform-visual-baseline.yml` — existing visual workflow, changed only by dedicated visual work.

Historical branch-, phase- and PR-specific workflows are not retained.

Each check owns its concern: the version checker owns synchronized version
declarations, the documentation checker owns navigation and stage continuity,
and the structure checker owns executable architecture boundaries. Formatting
or missing migration commentary may prompt review, but not impose a new approval
step. Product data ownership is maintained directly in
`config/product-data-owner-matrix.json`; there is no separate override layer.
This inventory describes ownership and declared availability, not runtime health
or authority to enable Live Write.

## Version

Root `VERSION` is authoritative. `scripts/bump-version.py` and `scripts/check-version-consistency.py` own synchronized declarations.

```bash
python scripts/bump-version.py 0.10.1
python scripts/check-version-consistency.py
```

A product version change does not change Runtime contract versions, database migration versions or Live Write gates.

## Local commit and recovery procedure

For a local release or version-promotion request:

1. Check `git status --short --branch`, active `git` processes, `.git/index.lock`, `git diff --check`, the diff summary, recent log and repository connectivity. Check important ignored files with `git check-ignore -v`.
2. Preserve all current worktree changes. `git add -A` is allowed only after the Owner has scoped the current local changes for inclusion; ignored runtime databases remain untracked unless explicitly requested.
3. Run staged diff checks before committing. Run the repository hook in its supported native shell; never bypass it or modify hook/configuration files to make it pass.
4. After committing, verify status, the new commit summary and repository connectivity. Push is a separate operation requiring an explicit request.

If Git metadata is corrupt (`bad HEAD`, missing objects, invalid refs/index or pack errors), do not hand-edit `.git` or retry writes. After explicit Owner authorization to restore Git, create a clean clone from the verified remote, retain the old worktree and recovery copy, copy the worktree content without `.git` or local runtime data, install the clean repository metadata as one operation, and verify the result with `status`, `log`, `fsck --full --no-reflogs --connectivity-only` and the complete diff. Do not run `gc`, `repack`, `prune`, force push or history rewriting as part of recovery.

External-data code has a separate boundary: inspecting it and running mocked tests is local work; executing public endpoints, using hard-coded proxies or disabling TLS verification requires explicit scope and must be stopped until corrected.

## Pull-request description

Use the short repository template: result, actual validation, documentation impact,
and material risks or operation prerequisites. Add contract, safety and recovery
detail when the change affects them; a small documentation edit does not need
role, Context Pack, token accounting, staged gates or historical receipts.
Do not duplicate commit history.
