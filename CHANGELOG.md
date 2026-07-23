# Changelog

## Unreleased

### Trading safety hardening — Phase 1

- Established `main@76effbff6391533db7b9954965aaf1b09051081f` as the V6 engineering baseline.
- Added `docs/planning/V6-交易安全加固实施计划.md`, Pull Request #3, and GitHub Issue #2 as the authoritative delivery trail.
- Changed order validation to fail closed for unknown accounts, inactive accounts, unknown instruments, missing contract specifications, invalid quantity steps, and invalid price ticks.
- Preserved the global Live trading switch and strengthened the safety policy to require every account to be active before submission.
- Replaced the Runtime check-then-insert command flow with an atomic database claim before any Gateway side effect.
- Added tests proving duplicate Runtime commands reuse persisted events and do not call the Gateway twice.
- Added backend tests for unknown accounts, unknown instruments, contract quantity validation, and catalog-authoritative execution batches.
- Split Windows-only MetaTrader5 and Crypto gateway packages into optional Runtime dependencies so core Linux CI remains reproducible.
- Expanded GitHub Actions to cover `main`, hardening branches, and pull requests into `main`.
- Aligned frontend CI and the lockfile on `pnpm@9.15.9`, disabled Husky installation in CI, and retained failure artifacts for dependency and type-check diagnostics.
- Added the `/@/* -> src/*` TypeScript path mapping so Vite imports resolve under `vue-tsc`.
- Upgraded frontend CI from type checking only to frozen-lockfile installation, strategy type checking, and a production build.
- Completed Platform CI run `29983926790`: Platform Backend, Execution Runtime, frontend type-check, and frontend production build all passed.
- Updated the root README, START-HERE, V6 release gate, implementation plan, and this Changelog so code, tests, operational limits, and Markdown documentation use the same baseline.

### Previous V6 workspace changes

- Standardized local development around frontend port `5173` and platform backend `/api/v1`.
- Removed backend/debug UI panels from strategy product pages.
- Restored the start page to the dark star-map Variable Global landing screen, removed legacy top-right labels `平台入口` / `研究框架` / `新闻日历`, renamed `金融AI` to `金融AI分析`, and routed protected start-page clicks through `/login?redirect=...`.
- Increased the logged-in top navigation font size to 16px with regular 400 weight, and added functional icons for `首页`, `新闻日历与理财`, `风控管理`, and `金融AI分析`.
- Adjusted the public start-page entry cards to match the larger icon and serif-title treatment in the reference landing layout.
- Restored `#/home/index` as the logged-in Home Dashboard: butterfly-water topology hero background, right-side market/portfolio summaries, and four product cards for market pulse, portfolio, strategy, and calendar.
- Refined the Home Dashboard hero so the butterfly-water topology uses the high-resolution original-color asset as a controlled local visual layer without baked-in legacy text, and softened dashboard typography to match the reference layout.
- Changed the Home Dashboard hero to use one continuous butterfly-water image across the full top area, with summary cards floating over it and the four dashboard modules pulled upward into the hero edge.
- Started non-destructive project folder reorganization.
- Added `.ignore` and expanded `.gitignore` to reduce Codex/search noise from dependencies, virtual environments, build outputs, generated files, and large reference code.
- Moved root SQL reference files into `references/database/` without deleting source material.
- Moved the large `参考代码/` reference-code directory out of the project root to `C:\Users\jiuxi\Desktop\codex\平台设计其他辅助内容\平台移动文件夹，例如参考代码等\参考代码`.
