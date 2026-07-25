# Task: Responsive Layout Architecture and Cross-Viewport Acceptance

Issue: #85
Status: review
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

## Changed files

- `admin-risk/docs/architecture/frontend/responsive-layout-architecture.md`
- `admin-risk/docs/architecture/decisions/ADR-013-响应式布局体系与页面壳层治理.md`
- `admin-risk/docs/quality/responsive-layout-acceptance.md`
- `admin-risk/docs/architecture/frontend/frontend-overview.md`
- `admin-risk/docs/architecture/frontend/README.md`
- `docs/codex/current-state.md`
- this task packet

## Canonical ownership

- Responsive layout architecture, viewport support, page-shell ownership, scroll/overflow/fixed-position rules and component reflow behavior: `admin-risk/docs/architecture/frontend/responsive-layout-architecture.md`.
- Historical decision and rationale: ADR-013.
- Test cases, defect severity and release acceptance: `admin-risk/docs/quality/responsive-layout-acceptance.md`.
- Visual language and design tokens remain owned by `admin-risk/docs/design/platform-ui-guidelines.md`.
- Shared-component extraction and theme boundaries remain owned by `admin-risk/docs/architecture/shared-ui-governance.md`.
- The new `admin-risk/docs/architecture/frontend/README.md` is the frontend architecture reading-order and authority index.

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

- [x] One canonical responsive-layout architecture document exists.
- [x] Width, height, browser zoom and OS scaling are included in the support matrix.
- [x] Page-shell, scroll, overflow, fixed/sticky and overlay ownership are explicit.
- [x] Component reflow behavior is defined by component category.
- [x] Prohibited patch patterns and controlled exceptions are documented.
- [x] A phased implementation sequence separates baseline, shell, shared primitives, page remediation and visual regression.
- [x] A measurable acceptance checklist and S0–S3 defect severity model exist.
- [x] The active frontend architecture overview and new frontend document index link to the canonical owner without duplicating another responsive standard.
- [x] Existing visual-token and shared-component authorities remain separate and are linked from the canonical document.
- [ ] Documentation checks, Platform CI and Secret Scan pass on the final head.

## Progress

- Done: baseline verification, duplicate-Issue search, existing frontend/design document audit, canonical architecture, ADR, acceptance standard, frontend overview integration, document index and cross-session state.
- Current: validate the final documentation-only diff.
- Next: record CI evidence, update PR, squash merge and close Issue.
- Blocked by: none.

## Completion

- PR: #86
- Merge commit:
- Application behavior changed: none.
- Documentation authority changed: responsive layout rules are explicit and canonical; existing visual and shared-component authorities remain unchanged.
- Tests/CI: pending final head.
- Follow-up: implementation must be split into later Issues, beginning with viewport/screenshot baseline and Application Shell scroll ownership.
