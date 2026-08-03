# Git Workflow and Version Governance

Use the smallest workstream that safely fits the change.

Current GitHub repository for future upload:

```text
wuxingyuenan5-lgtm/Platform_Experiment
```

## 1. Three workstreams

| Workstream | Typical scope | Issue | Task packet | CI |
|---|---|---:|---:|---|
| Fast | Markdown and synchronized release versions | No | No | repository checks, version check when relevant, Secret Scan |
| Standard | bounded single-module UI/API/tooling/bug work outside Critical paths | Optional | No | affected application jobs |
| Critical | trading/execution, Runtime, risk, auth, credentials, database/migration, contracts, CI governance, Live behavior, cross-service or cross-session work | Yes | Yes | affected jobs; shared governance/contract changes force full matrix |

When classification is genuinely unclear, use Critical. Do not classify ordinary single-module work as Critical merely because it changes code.

## 2. Fast

Branch:

```text
docs/<slug>
chore/<slug>
```

PR declarations:

```text
Workstream: fast
Behavior change: none
Safety change: none
```

Allowed files are machine-limited to Markdown and the maintained Platform version declarations. A version update must change every governed package, display, runtime and current-document declaration together.

## 3. Standard

Branch:

```text
feature/<slug>
fix/<slug>
refactor/<slug>
chore/<slug>
```

PR declaration:

```text
Workstream: standard
```

No Issue or task packet is required. An Issue may still be used for backlog or product discussion, but it is not repository ceremony.

Standard is not allowed to modify Runtime, trading/execution, risk, auth, credentials, migrations, contracts, CI workflows or repository safety enforcement. `scripts/check-workstream.py` rejects those paths.

## 4. Critical

Relationship:

```text
one Issue
→ one tasks/issue-<number>-<slug>.md
→ one <type>/issue-<number>-<slug> branch
→ one linked PR
→ squash merge main
```

Branch example:

```text
hardening/issue-123-recover-live-order
```

PR declarations:

```text
Workstream: critical
Issue: #123
```

Critical PRs keep the existing uniqueness, open-Issue and task-packet checks.

## 5. Commit and push discipline

- Form the complete patch before pushing when possible.
- Run local targeted checks first.
- Prefer one to three logical commits per PR.
- Do not create one commit per edited file.
- Do not repeatedly update task/PR metadata between every code fix.
- Push a coherent checkpoint, read one CI result, then apply grouped fixes.

## 6. CI behavior

- Feature branches normally use PRs as the branch validation surface.
- During Platform 0.9.3 candidate work, `refactor/platform-0-9-3-repository-and-context-optimization` has a temporary no-Path-Filter `push` trigger across the nine candidate workflows because PR #141 targets a Base branch outside their maintained PR branch lists.
- `main` always runs the full Backend, Runtime and Frontend matrix.
- PRs run Repository Safety plus only affected application jobs.
- Contract/shared CI changes force the full matrix.
- Secret Scan is a separate required workflow and is not duplicated inside Platform CI.

## 7. Pull requests

A PR needs only:

- workstream declaration;
- measurable outcome;
- concise scope;
- relevant verification;
- risk/rollback for non-trivial changes.

Do not reproduce the task packet, commit log or repository history in the PR body.

## 8. Platform version

Root `VERSION` is authoritative. Maintained declarations include:

- `platform-web/package.json`;
- `platform-web/.env.development`;
- `platform-web/.env.production`;
- `platform-api/pyproject.toml`;
- `platform-api/app/application.py` for OpenAPI and `/api/v1/system/info`;
- `execution-runtime/pyproject.toml`;
- `execution-runtime/app/main.py` and `/status`;
- `README.md`, `docs/README.md` and `docs/codex/current-state.md`.

Update the governed declarations with:

```powershell
python scripts/bump-version.py 0.9.3
python scripts/check-version-consistency.py
```

The product version does not change Runtime contract versions, database schema versions or Live Write gates. Historical Release Notes, Legacy production evidence and compatibility fixtures keep their original versions.

## 9. Cross-session continuation

For Critical work, provide only repository, Issue number and task-packet path. For Standard/Fast work, provide the branch or PR and target outcome. Always verify current GitHub state rather than copying old chat history.
