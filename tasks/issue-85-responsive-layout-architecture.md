# Task: Responsive Layout Architecture and Cross-Viewport Acceptance

Issue: #85
Status: active
Branch: `docs/issue-85-responsive-layout-architecture`
Base commit: `9b0617c2f4339234e4dde06282450c41dc8be84b`

## Objective

Define one canonical responsive-layout architecture for the `admin-risk` frontend and a measurable plan for later page remediation, without changing application code in this Issue.

## Non-goals

- No Vue, TypeScript, Less/CSS or component implementation changes.
- No visual redesign of product information architecture.
- No Playwright or screenshot-baseline implementation yet.
- No claim that existing pages already meet the new standard.
- No resolution-specific CSS patches or page-by-page repair in this documentation task.

## Expected changed files

- `admin-risk/docs/architecture/frontend/responsive-layout-architecture.md`
- `admin-risk/docs/architecture/decisions/ADR-013-响应式布局体系与页面壳层治理.md`
- `admin-risk/docs/quality/responsive-layout-acceptance.md`
- `admin-risk/docs/architecture/frontend/frontend-overview.md`
- `admin-risk/docs/architecture/shared-ui-governance.md`
- `admin-risk/docs/design/platform-ui-guidelines.md`
- `admin-risk/docs/README.md`
- `docs/codex/current-state.md`
- this task packet

## Canonical ownership

- Responsive layout architecture, viewport support, page-shell ownership, scroll/overflow/fixed-position rules and component reflow behavior: `admin-risk/docs/architecture/frontend/responsive-layout-architecture.md`.
- Historical decision and rationale: ADR-013.
- Test cases, defect severity and release acceptance: `admin-risk/docs/quality/responsive-layout-acceptance.md`.
- Visual language and design tokens remain owned by `admin-risk/docs/design/platform-ui-guidelines.md`.
- Shared-component extraction and theme boundaries remain owned by `admin-risk/docs/architecture/shared-ui-governance.md`.

## Protected semantics

- Existing product module hierarchy and navigation names.
- Existing business data, trading commands and risk behavior.
- Existing Backend and Runtime contracts.
- Desktop workstation priority.
- Existing page code remains unchanged in this Issue.

## Required verification

```text
python scripts/check-workstream.py
python scripts/scan-secrets.py
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
```

Final delivery requires Platform CI and Secret Scan on the final PR head.

## Stop conditions

- Stop if the work requires changing frontend runtime code or layout CSS.
- Stop if another active document already owns the exact same responsive-layout authority.
- Stop if the proposed rules require mobile-first redesign of the product.
- Stop if acceptance criteria cannot be measured from viewport, zoom and observable layout behavior.

## Acceptance criteria

- [ ] One canonical responsive-layout architecture document exists.
- [ ] Width, height, browser zoom and OS scaling are included in the support matrix.
- [ ] Page-shell, scroll, overflow, fixed/sticky and overlay ownership are explicit.
- [ ] Component reflow behavior is defined by component category.
- [ ] Prohibited patch patterns and exceptions are documented.
- [ ] A phased implementation sequence separates shell, shared primitives and page remediation.
- [ ] A measurable acceptance checklist and defect severity model exist.
- [ ] Existing active frontend/design docs link to the canonical owner without duplicating conflicting rules.
- [ ] Documentation checks, Platform CI and Secret Scan pass.

## Progress

- Done: baseline verification, duplicate-Issue search, existing frontend/design document audit, Issue and branch creation.
- Current: write canonical architecture, ADR and acceptance plan.
- Next: update document entrypoints and cross-session state, validate and merge.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Application behavior changed: none.
- Documentation authority changed: responsive layout rules become explicit and canonical.
- Tests/CI:
- Follow-up: implementation must be split into later Issues, beginning with application shell and page container governance.
