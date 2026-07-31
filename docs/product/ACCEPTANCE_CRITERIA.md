# Acceptance Criteria

## Current Global Criteria

- Local frontend opens at `http://127.0.0.1:4373/index.html#/strategy/platform`.
- Start page opens at `http://127.0.0.1:4373/#/` as the dark star-map Variable Global landing screen.
- Start-page navigation must not show legacy labels `平台入口`, `研究框架`, or `新闻日历`; the AI entry is named `金融AI分析`.
- Clicking protected start-page entries routes to `/login?redirect=...`; after account login, the app redirects to the intended subpage.
- Start-page core entry cards use large gold functional icons and serif-style titles, and point to product modules such as `对冲基金看板`, `新闻日历与理财`, `策略研究`, `风控管理`, and `金融AI分析`.
- Logged-in top navigation uses readable 16px menu text at regular 400 weight and functional icons for every primary product entry, including `首页`, `新闻日历与理财`, `风控管理`, and `金融AI分析`.
- `#/home/index` is the logged-in Home Dashboard, not the public start page; it uses the butterfly-water topology visual as the hero background and shows market, portfolio, strategy, and calendar summary modules.
- Home Dashboard hero art must not expose baked-in legacy text from source images; the butterfly-water topology should use the high-resolution original-color asset as a controlled local visual layer behind the intended dashboard copy.
- Home Dashboard hero should render as one continuous butterfly-water visual field, not a split left-image/right-empty background; lower dashboard modules may overlap the hero edge to match the reference layout.
- Platform API health check returns 200 at `http://127.0.0.1:8000/health`.
- Execution Runtime health check returns 200 at `http://127.0.0.1:8100/health` when runtime integration is enabled.
- Product pages must not show debug-only backend or runtime panels.
- Trading and account behavior changes require separate approval.
- Routine code search does not scan `node_modules`, `.venv`, `dist`, or `outputs`.
- Root SQL references live under `references/database/`.
- Large external reference code does not live in the project root.
- Shared documentation and default configuration must not bind the platform to a named developer workstation.
