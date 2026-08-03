# 人工可读目录

这是给非开发者和未来自己的项目入口。先选择目的，不需要理解全部代码。

## 常用入口

| 目的 | 入口 |
|---|---|
| 直接本地运行 | 仓库根目录执行 `.\scripts\dev-platform.ps1` |
| 当前已经做到哪里 | `../docs/codex/current-state.md` |
| 产品模块 | `../platform-web/docs/modules/` |
| 系统如何连接 | `../docs/architecture/SYSTEM_MAP.md` |
| Git 与版本规则 | `../docs/engineering/GIT_WORKFLOW.md` |
| 数据库 | `../docs/database/README.md` |
| 实盘验收 | `../docs/operations/V6-小资金实盘验收手册.md` |
| 当前技术债 | `../docs/engineering/TECHNICAL_DEBT.md` |

## 当前状态

当前版本、分支、阶段和已知限制只从`../docs/codex/current-state.md`读取；服务边界只从`../docs/architecture/SYSTEM_MAP.md`读取。本目录不维护平行状态。

## 本地启动

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

脚本会按需安装依赖、启动三个窗口并检查 4373、8000 和 8100 服务是否就绪。

## 开发流程

- Fast：纯 Markdown 和同步版本。
- Standard：普通单模块功能或修复，不要求 Issue/任务包。
- Critical：交易、执行、风险、权限、数据库、合同、Runtime、Live 或跨服务任务，使用一个 Issue、一个任务包、一个分支和一个 PR。

新对话默认只读取根 `AGENTS.md`、当前状态、目标模块 `AGENTS.md`、直接代码和测试。不要加载所有历史任务包或关闭 PR。

## 产品模块

| 模块 | 定位 |
|---|---|
| 首页 | 品牌入口、摘要和导航 |
| 对冲基金看板 | 宏观、资产类别和跨市场研究 |
| 新闻日历与理财 | 新闻、日历和信息筛选 |
| 策略 | 策略分析、交易、管理、统计和复盘 |
| 风险管理 | 账户、资金、权限、审计和监控 |
| 金融 AI 分析 | 授权数据的归纳和结构化分析 |

策略文档位于 `../platform-web/docs/strategies/`。
