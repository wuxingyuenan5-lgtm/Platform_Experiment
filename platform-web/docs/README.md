# Platform Web 文档

本目录只维护前端实现、视觉和前端验收。产品范围与策略已经统一迁到 [产品总览](../../docs/product/PRD.md)，系统边界与跨模块合同位于根级 `docs/`。

| 需要 | 文档 |
| --- | --- |
| 前端分层、状态、路由和数据适配 | [FRONTEND.md](FRONTEND.md) |
| 页面壳层、视觉语言和交互 | [DESIGN.md](DESIGN.md) |
| 前端完成检查 | [ACCEPTANCE.md](ACCEPTANCE.md) |
| 对冲基金看板交易工具母表 | [trading-tools-bookmarks-review.md](trading-tools-bookmarks-review.md) |

前端任务还必须遵守 [platform-web/AGENTS.md](../AGENTS.md)。本目录不维护项目阶段、后端架构、领域合同、Runtime 设计、产品模块需求或历史 ADR。

修改母表后，在 `platform-web/` 执行 `pnpm sync:trading-tools`，并运行 `pnpm test:hedge-board-layout`。
