# Changelog

## Unreleased

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
