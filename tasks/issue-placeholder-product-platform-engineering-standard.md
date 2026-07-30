# Task: Product platform engineering standard

Status: review
Branch: `docs/platform-product-engineering-standard`
Base commit: `a4e22021c71cf5cd703cb0bc35676ff5adbfec36`

## Objective

Define one durable engineering standard for product-facing research, data and dashboard implementation without changing runtime behavior.

## Protected semantics

- No execution, risk, accounting, authorization or live-write behavior change.
- Preserve Frontend → Platform Backend → Execution Runtime boundaries.
- Documentation-only change.

## Scope

- Add `docs/architecture/PRODUCT_PLATFORM_ENGINEERING_STANDARD.md`.
- Record frontend, backend, provider, data-quality, testing and governance rules.
- No code, schema, dependency or deployment change.

## Verification

- `python scripts/check-repository-structure.py`
- `python scripts/check-documentation-consistency.py`
- `python scripts/check-codex-context.py`

## Progress

- Done: standard document drafted.
- Current: review and repository checks.
- Next: owner approval; no merge without explicit instruction.
- Blocked by: none.
