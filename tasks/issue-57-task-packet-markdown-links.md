# Issue #57 — Lightweight task packet and Markdown link hardening

Issue: #57
Status: active
Branch: `docs/issue-57-task-packet-markdown-links`
Base commit: `79aa9d2a0c44eec65ccb4a333ddb6f09d8d1ec2a`

## Objective

Add three lightweight task controls and make missing local Markdown file links fail the existing documentation-consistency gate.

## Non-goals

- No ADR, YAML metadata, Context Compiler, Import Graph, compatibility registry or task state machine.
- No application, Runtime, API, SQL, Schema, Seed, formula, trading, credential, deployment or Live Write change.
- No external URL availability or Markdown heading-anchor validation.
- No mass historical-document cleanup.

## Allowed scope

- `docs/codex/task-template.md`
- `scripts/check-documentation-consistency.py`
- `platform-backend/tests/test_architecture_documentation_consistency.py`
- `docs/codex/current-state.md`
- `CHANGELOG.md`
- this task packet
- only active Markdown files with concrete broken local links reported by the new checker

## Expected changed files

- `docs/codex/task-template.md`
- `scripts/check-documentation-consistency.py`
- `platform-backend/tests/test_architecture_documentation_consistency.py`
- `docs/codex/current-state.md`
- `CHANGELOG.md`
- `tasks/issue-57-task-packet-markdown-links.md`

Conditional: a specific active Markdown file may change only when the checker proves that one of its local file links is broken.

## Protected semantics

- Existing canonical context and ownership entrypoints remain unchanged.
- Existing documentation ownership checks continue to run through Repository Safety.
- External links and fragment-only links are not network-checked.
- Historical/generated directories remain outside the active link gate.
- Runtime behavior, public interfaces, persistence and both Live Write defaults remain unchanged.

## Context packet

Read only:

1. `AGENTS.md`;
2. `docs/codex/current-state.md`;
3. `docs/codex/context-map.md`;
4. `docs/codex/task-template.md`;
5. `scripts/check-documentation-consistency.py`;
6. `platform-backend/tests/test_architecture_documentation_consistency.py`;
7. `.github/workflows/platform-ci.yml`.

Additional context:

- Active Markdown files reported by the checker — only to repair a concrete missing local target.

## Required verification

```text
python scripts/check-documentation-consistency.py
cd platform-backend && pytest -m architecture tests/test_architecture_documentation_consistency.py
```

Final delivery additionally requires full Platform CI and independent Secret Scan on the frozen PR head.

## Stop conditions

- Stop if implementation requires application or Runtime source changes.
- Stop if implementation requires external URL requests or heading-anchor parsing.
- Stop if more than concrete checker-reported active Markdown links require cleanup.
- Stop if the change expands into task-state automation or a second documentation metadata source.

## Acceptance criteria

- [ ] Canonical task template contains Expected changed files, Required verification and Stop conditions.
- [ ] Current task packet demonstrates those fields.
- [ ] Missing active local Markdown file targets fail deterministically.
- [ ] External URLs, fragment-only links and placeholders are ignored.
- [ ] Historical/generated exclusions are deterministic.
- [ ] Existing ownership/context checks remain green.
- [ ] Diff contains no unrelated cleanup.
- [ ] Platform CI and Secret Scan pass on the frozen head.

## Risk and rollback

Risk: low

- Failure modes: false-positive documentation failures or an accidentally skipped active link.
- Detection: direct architecture tests and Repository Safety.
- Rollback: revert the final squash commit.

## Progress

- Done: baseline verified; Issue, branch and task packet created.
- Current: implement template fields and local link validation.
- Next: direct tests, active-document repairs if reported, full CI and merge.
- Blocked by: none.

## Completion

- PR: pending
- Merge commit: pending
- Behavior changed: none
- Behavior intentionally unchanged: all runtime, API, persistence, trading and Live Write behavior
- Tests/CI: pending
- Follow-up debt: none planned
