# Task: VG-0111-SF-01 Integration

Status: active
Branch: `codex/vg-0111-integration`
Base commit: `d7a9c5dda7a35825058e02f63c2ea974bad7694c`

## Role

Single temporary integration owner. No business-source editing authority.

## Objective

Integrate the Critical-accepted `VG-0111-SF-01` branch into the latest governance authority with immutable ancestry and record closure evidence.

## Context Pack

`governance`

## Authority

The Program Orchestrator authorized integration of `codex/vg-0111-sf-01` at accepted head `86cf530efeab1b5d7ca0e1f292c5aa4b5cf8e2f8` into base `d7a9c5d`. External connections, credentials, Live Write and real operations remain unauthorized.

## Write Scope

- Git merge metadata on `codex/vg-0111-integration`.
- `docs/codex/tasks/VG-0111-SF-01.md` status and immutable integration evidence after a clean merge.
- This integration task card status.

## Non-Goals

- No conflict resolution by editing business source, contracts or tests.
- No frontend changes, credentials, external connections, Live Write, real operations, deployment or history rewriting.

## Acceptance

- Source range `f576470..86cf530` has no path overlap with the six dirty frontend files in the shared checkout.
- Merge uses preserved ancestry and produces a traceable merge commit; no squash or amend.
- Integrated diff contains no `platform-web` path.
- Original task card records accepted ranges, integration commit, validation evidence and `done` status.
- `git diff --check`, version, structure and documentation consistency checks pass; known global Context Pack budget failures remain explicitly unclaimed.

## Stop Conditions

- Any merge conflict, unexpected path, missing accepted commit, frontend overlap, history rewrite requirement or change beyond task-card metadata.

## Output Contract

Return only `outcome`, `changed_files`, `validations`, `evidence`, `contract_impact`, `unproven_facts`, `residual_risks`, and `next_gate`.
