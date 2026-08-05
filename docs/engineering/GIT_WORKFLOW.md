# Git Workflow and Version Governance

## Branch and review

- Work on a named branch; never commit directly to `main`.
- Use one pull request for one coherent outcome.
- Keep non-trivial work Draft until implementation and validation are complete.
- Do not merge, tag, release or deploy without an explicit owner decision.
- Prefer one to four logical commits rather than one commit per file.

Typical prefixes are `feature/`, `fix/`, `refactor/`, `hardening/`, `docs/` and `chore/`.

## Change classes

| Class | Scope | Validation |
|---|---|---|
| Fast | documentation or synchronized version metadata | repository quality, version and Secret Scan |
| Standard | bounded module behavior without protected semantics | affected module CI |
| Critical | trading, execution, risk, auth, credentials, database, contracts, CI governance or Live behavior | full affected safety matrix |

Critical changes preserve explicit rollback/forward-fix and protected semantics in the PR description. A completed phase document or evidence ledger is not required in the worktree.

## Maintained CI

- `.github/workflows/platform-ci.yml` — Platform API, Runtime and frontend build/test matrix;
- `.github/workflows/repository-quality.yml` — version, context, documentation and architecture boundaries;
- `.github/workflows/secret-scan.yml` — secret detection;
- maintained browser E2E workflows;
- `.github/workflows/platform-visual-baseline.yml` — existing visual workflow, changed only by dedicated visual work.

Historical branch-, phase- and PR-specific workflows are not retained.

## Version

Root `VERSION` is authoritative. `scripts/bump-version.py` and `scripts/check-version-consistency.py` own synchronized declarations.

```bash
python scripts/bump-version.py 0.10.1
python scripts/check-version-consistency.py
```

A product version change does not change Runtime contract versions, database migration versions or Live Write gates.

## Pull-request description

Record:

- baseline and head;
- scope and explicit exclusions;
- contract and safety impact;
- actual validation commands/results;
- deployment prerequisites and known limits.

Do not duplicate commit history or historical phase receipts.
