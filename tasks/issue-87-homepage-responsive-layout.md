# Task: Homepage Responsive Layout and Visual Hierarchy

Issue: #87
Status: active
Branch: `frontend/issue-87-homepage-responsive-layout`
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

## Expected changed files

- `admin-risk/src/views/dashboard/index.vue`
- `admin-risk/docs/design/homepage-layout-standard.md`
- `docs/codex/current-state.md`
- this task packet

Additional files require a concrete defect and must remain within frontend layout/documentation scope.

## Existing defects confirmed

1. At `max-width: 1500px`, `.home-hero` becomes one column while `.hero-side--market` and `.hero-side--portfolio` remain assigned to grid column 2.
2. The hero copy remains assigned to rows 1–3 after the responsive transition, allowing implicit grid tracks and unpredictable placement.
3. The main panel grid uses four heterogeneous columns above 1500px, producing large density changes between adjacent widths.
4. The main panel grid overlaps the hero through a negative top margin.
5. The page assumes a 64px header through `min-height: calc(100vh - 64px)`.
6. Several inner rows use fixed tracks without compact fallback, increasing overflow risk.

## Layout decisions

- Homepage content is bounded by a wide desktop frame instead of stretching indefinitely.
- Hero is two regions: brand copy and a summary stack.
- Large desktop: brand copy + vertical summary stack.
- Standard desktop: brand copy followed by two summary cards in a row.
- Compact fallback: all hero regions become one column.
- Main dashboard remains two columns throughout the supported 1280–2560px range.
- Main dashboard becomes one column only below the formal desktop support range.
- No negative-margin overlap is used.
- Width, spacing and typography use bounded `clamp()` values.
- Existing routes, labels and placeholder data remain unchanged.

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

- [ ] Homepage-specific layout standard exists.
- [ ] The 1500px implicit-grid defect is removed.
- [ ] Hero order is deterministic at every breakpoint.
- [ ] Main cards use a stable two-column desktop grid.
- [ ] No viewport-height subtraction or negative panel overlap remains.
- [ ] Inner rows have compact fallbacks and `min-width: 0` where needed.
- [ ] Existing content, routes and placeholder values are preserved.
- [ ] Required CI passes on the final head.

## Progress

- Done: main/open-PR verification, Issue creation, current homepage and PageWrapper audit.
- Current: define the layout standard and refactor the homepage.
- Next: validate, review the final diff, merge and close Issue.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Application behavior changed: responsive placement and visual hierarchy only.
- Business behavior changed: none.
- Tests/CI:
- Follow-up: remaining pages should be handled only from concrete S0/S1 defects or shared-shell evidence.