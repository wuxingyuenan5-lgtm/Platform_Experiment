# Task: Homepage Responsive Layout and Visual Hierarchy

Issue: #87
Status: review
Branch: `fix/issue-87-homepage-responsive-layout`
Base commit: `8f9afae0d8991468624d88853ec0585e575da03e`

## Objective

Stabilize the homepage across supported desktop viewports by replacing resolution-specific placement with a documented, content-driven layout while preserving existing content, routes and placeholder data.

## Non-goals

- No Backend or Runtime changes.
- No real data integration.
- No navigation or business-information redesign.
- No broad responsive cleanup of other pages.
- No Playwright dependency addition.
- No trading, risk or Live Write behavior changes.

## Changed files

- `admin-risk/src/views/dashboard/index.vue`
- `admin-risk/docs/design/homepage-layout-standard.md`
- `admin-risk/tsconfig.full.json`
- `docs/codex/current-state.md`
- this task packet

Temporary diagnostic workflow changes were removed before final validation and are not part of the formal diff.

## Existing defects confirmed

1. At `max-width: 1500px`, `.home-hero` became one column while the two Hero summary cards remained assigned to grid column 2.
2. The Hero copy remained assigned to rows 1–3 after the responsive transition, allowing implicit grid tracks and unpredictable placement.
3. The main panel grid used four heterogeneous columns above 1500px, producing large density changes between adjacent widths.
4. The main panel grid overlapped the Hero through a negative top margin.
5. The page assumed a 64px header through `min-height: calc(100vh - 64px)`.
6. Several inner rows used fixed tracks without compact fallback, increasing overflow risk.
7. Changed-file type-aware ESLint could not parse the homepage because it was absent from both maintained TypeScript project scopes.

## Implemented layout decisions

- Homepage content is bounded by a wide `1840px` desktop frame instead of stretching indefinitely.
- Hero is two regions: brand copy and a summary stack.
- Large desktop: brand copy + vertical summary stack.
- Standard desktop: brand copy followed by two summary cards in a row.
- Compact fallback: all Hero regions become one column.
- Main dashboard remains two columns throughout the supported 1280–2560px range.
- Main dashboard becomes one column only below the formal desktop support range.
- No negative-margin overlap or viewport-height subtraction is used.
- Width, spacing and typography use bounded `clamp()` values.
- Inner rows use `min-width: 0`, flexible tracks and explicit compact fallbacks.
- Existing routes, labels and placeholder data remain unchanged.
- Dashboard Vue files are now included in `tsconfig.full.json` so changed-file type-aware ESLint can protect the page.

## Required verification

```text
python scripts/check-workstream.py
python scripts/scan-secrets.py
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
```

Final delivery also requires:

- Frontend maintained lint.
- Frontend no-new-debt gate.
- Strategy frontend type-check.
- Frontend production build.
- Platform Backend and Runtime CI.
- Secret Scan.

## Stop conditions

- Stop if the change requires modifying shared PageWrapper behavior for all pages.
- Stop if existing business routes or data behavior must change.
- Stop if a new visual asset is required.
- Stop if implementation expands into multiple business pages.
- Stop if the layout can only be made stable with resolution-specific offsets or negative margins.

## Acceptance criteria

- [x] Homepage-specific layout standard exists.
- [x] The 1500px implicit-grid defect is removed.
- [x] Hero order is deterministic at every breakpoint.
- [x] Main cards use a stable two-column desktop grid.
- [x] No viewport-height subtraction or negative panel overlap remains.
- [x] Inner rows have compact fallbacks and `min-width: 0` where needed.
- [x] Existing content, routes and placeholder values are preserved.
- [x] Homepage is included in the full TypeScript project used by type-aware ESLint.
- [ ] Required CI passes on the exact final head after documentation and diagnostic cleanup.

## Progress

- Done: repository verification, Issue creation, homepage and PageWrapper audit, layout standard, homepage refactor, TypeScript project inclusion, zero-debt lint correction, temporary diagnostic cleanup and current-state update.
- Current: validate the exact final five-file diff.
- Next: record final CI evidence, update PR, squash merge and close Issue.
- Blocked by: none.

## Completion

- PR: #89
- Superseded PR: #88, closed before review because its branch prefix was not permitted by repository governance.
- Merge commit:
- Application behavior changed: responsive placement and visual hierarchy only.
- Business behavior changed: none.
- Tests/CI: final head pending; implementation head passed Repository Safety, Backend, Runtime, frontend lint/no-new-debt/type-check/build and Secret Scan.
- Follow-up: remaining pages should be handled only from concrete S0/S1 defects or shared-shell evidence; automated viewport screenshots remain a separate scope.
