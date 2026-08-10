# Platform Agent Rules

This repository is the engineering source for 全球变量金融平台（Variable-Global）.

## Read first

1. `docs/codex/current-state.md`
2. the nearest module `AGENTS.md`
3. directly affected source and tests
4. one owning contract or architecture document only when the change crosses that boundary

Use `python scripts/context-for.py <pack>` for bounded task context. Context Pack definitions and budgets remain authoritative in `scripts/context-packs.json`.

## Repository boundaries

- Deployable subjects are `platform-web`, `platform-api` and `execution-runtime`.
- Platform API is a modular monolith. Do not add a service, database, queue or global dependency-injection framework without an approved architecture decision.
- External venue SDKs and order side effects belong to `execution-runtime`; Platform API communicates through versioned contracts.
- Formal accounting is rebuilt from immutable Financial Facts. Operational projections are not formal accounting inputs.
- Preserve exact Decimal values and timezone-aware timestamps at financial boundaries.
- Live Write is disabled by default. Kill Switch, idempotency and Result Unknown semantics are protected invariants. A narrow Platform 0.11.1 exception permits single-responsible-person controlled Live Write only on a local machine, using a founder-owned test account under the founder's direct supervision. It requires a time-limited manual unlock, Account/Strategy/Symbol allowlists, hard limits, one active execution batch, Kill Switch, automatic close-on-anomaly, end-of-day reconciliation and complete audit evidence. This exception does not extend to external client funds, multi-person operation, unattended trading, long-lived Live Write, production deployment, or any expansion of funds, symbols or concurrency.
- Restored product pages must not expose developer-facing provider, owner, source, `actionable`, static-design or architecture explanations to ordinary users. Keep those facts in data envelopes, contracts and tests.

## Change discipline

- Work on a branch and a pull request; never commit directly to `main`.
- Keep public API paths, schemas and persistent semantics compatible unless the task explicitly changes a contract.
- Prefer the smallest ownership boundary that makes pure rules independently testable.
- Update the current authority instead of creating handoff, evidence-ledger or phase-history documents.
- For AI-assisted restoration, one executor owns code changes. Additional agents should default to read-only investigation, review or acceptance unless explicitly assigned implementation ownership.
- Do not infer external production status from repository files. Servers, domains, databases, credentials and venue connectivity require separate evidence.

## Validation

Run the checks owned by the changed modules plus:

```bash
git diff --check
python scripts/context-for.py --check-budgets --json
python scripts/check-version-consistency.py
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
```

See `.github/workflows/` for the maintained CI commands.
