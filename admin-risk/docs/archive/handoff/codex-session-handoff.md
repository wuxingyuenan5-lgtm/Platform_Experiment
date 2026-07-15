# Admin-Risk 项目交接文档

## 1. 项目与仓库基线

- 项目目录：
  `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk`
- Git 仓库根目录：
  `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main`
- GitHub 仓库：
  [wuxingyuenan5-lgtm/liuchengtu](https://github.com/wuxingyuenan5-lgtm/liuchengtu)
- 远端名：
  `origin`
- 默认分支：
  `main`

## 2. 当前 Git 真实状态

截至本次更新时：

- `HEAD` 位于 `main`
- `origin/main` 当前同步到提交 `363705c`
- 最新已推送正式版本仍是 `v4`
- 本地存在一批未提交改动，当前并不是“工作区干净”的状态

结论：

- 如果后续要继续开发，应默认在当前本地修改基础上继续推进
- 如果要“git 一下当前版本”，不能直接沿用旧结论，必须先复核本地改动、确认是否提交，再推送

## 3. 当前最新正式版本

- 最新正式提交号：
  `363705c`
- 最新正式提交信息：
  `Release platform v4 strategy management refresh`
- 当前主要版本口径：
  `v4`

这个版本仍然是当前远端基线版本。后续新提交如果形成稳定版本，应从 `v4` 继续往后编号。

## 4. 已知版本历史

按 `git log` 当前可追溯到的提交顺序如下：

1. `1fc61a0`
   `Initialize repository`
2. `3c671c2`
   `Initial platform import`
3. `9d430be`
   `Remove generated cache artifacts`
4. `158ee81`
   `Release platform v2 trading tools sync`
5. `289af67`
   `Release platform v3 strategy and risk updates`
6. `363705c`
   `Release platform v4 strategy management refresh`

因此目前口径不变：

- `commit` 总数：`6`
- 主要版本数：`4`

## 5. 当前这轮本地未提交改动的范围

本地当前已出现未提交修改，主要集中在以下几块：

- `strategy/management` 策略管理页及其子组件
- `strategy/funding-carry` 资金策略页及其子组件
- `strategy/spread-carry` 跨市场/海内外价差相关页面
- `hedgeBoard` 看板页、终端页、交易工具页
- `risk` 风控页面局部组件
- 全局设计层：
  `design`、`menu`、`loading`、`landing`、`platform`
- 文档与脚本：
  `docs`、`scripts`、交易工具数据文件

当前还能确认的新增/特殊状态包括：

- 新增：
  `admin-risk/docs/codex-session-handoff.md`
- 新增：
  `admin-risk/docs/2026-07-15-项目上下文交接.md`
- 新增：
  `admin-risk/scripts/`
- 新增：
  `admin-risk/src/views/hedgeBoard/tradingTools/data/catalog.ts`
- 删除状态：
  `admin-risk/src/views/strategy/management/components/StrategyDeskTabs.vue`

这说明当前本地已经进入新一轮结构和样式并行调整阶段，但尚未形成新的正式 Git 版本。

## 6. 当前项目的重点工作区域

后续新对话默认优先关注以下目录：

- `src/views/hedgeBoard/**`
- `src/views/strategy/**`
- `src/views/newsCalendar/**`
- `docs/trading-tools-bookmarks-review.md`
- `scripts/**`

其中最容易持续发生修改的是：

- 策略管理页
- 资金策略页
- 交易工具页
- 跨市场执行与市场洞察页
- 设计主题和局部样式收口

## 7. 已落地的重要机制

### 7.1 交易工具页由 Markdown 驱动

- 源文档：
  `docs/trading-tools-bookmarks-review.md`
- 同步脚本：
  `scripts/sync-trading-tools-from-md.cjs`
- npm script：
  `pnpm sync:trading-tools`
- 关联数据文件：
  - `src/views/hedgeBoard/tradingTools/data/marketTools.ts`
  - `src/views/hedgeBoard/tradingTools/data/catalog.ts`

原则：

- 如果改的是交易工具内容，优先修改 Markdown 源文档
- 不要优先直接手改生成后的 TS 数据，除非本次任务明确就是修数据结构或同步逻辑

### 7.2 策略模块仍处于高频重构区

重点区域：

- `src/views/strategy/management/**`
- `src/views/strategy/funding-carry/**`
- `src/views/strategy/spread-carry/**`

原则：

- 优先做小范围、可控改动
- 修改前先判断是否属于共享样式或共享结构
- 不要因为局部页面问题，顺手重写整块公共 CSS 或整页结构

## 8. 当前阶段最容易出问题的点

### 8.1 中文文案与编码

历史上已经出现过文档乱码/终端显示乱码风险。

原则：

- 以文件实际编码内容为准，不以终端显示为准
- 大段中文修改前先确认文件编码正常
- 尽量避免基于乱码输出直接做替换

### 8.2 Vue 模板闭合和局部 patch 误伤

高频风险：

- 标签未闭合
- 局部替换时破坏模板结构
- 修改通用类名导致全局联动异常

原则：

- 对 `.vue` 文件优先做小步修改
- 改共享选择器时必须先确认影响范围
- 不要随意扩大 `.input-row`、`.card-head`、`.select` 这类通用样式选择器的作用域

### 8.3 页面同类结构未同步

这个项目很多页面是“同模式多副本”。

常见问题：

- 只修了一个策略页，另外两个同类页仍然保留旧样式
- 只修了一个执行卡片，监控卡片/统计卡片没有同步

原则：

- 改动前先判断是不是共享交互模式
- 如果是同类页面共用样式，优先抽到共享层统一处理

## 9. Git 操作默认习惯

后续如果用户说“帮我 git 一下当前版本”，默认理解为：

1. 检查当前改动范围
2. 判断是否适合形成一个稳定版本
3. 提交到 `main`
4. 推送到 `origin/main`
5. 回报：
   - 当前提交号
   - 提交信息
   - 当前 `commit` 总数
   - 当前主要版本数

当前提交命名风格继续建议保持：

- `Release platform v5 ...`
- `Release platform v6 ...`

例如：

- `Release platform v5 strategy visual redesign`
- `Release platform v6 hedge board and trading tools refinement`

## 10. 后续版本管理建议

建议从下一次稳定提交开始补强两件事：

- 打 tag：
  `platform-v5`、`platform-v6`
- 维护版本说明文件：
  `admin-risk/docs/version-changelog.md`

建议每个稳定版本记录：

- 版本号
- 提交号
- 改动模块
- 是否已推送
- 是否已交付

## 11. 新对话可直接继承的简短口径

可以直接把下面这段发给新的对话窗口：

> 平台仓库根目录是 `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main`，前端项目目录是 `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk`，GitHub 仓库是 `wuxingyuenan5-lgtm/liuchengtu`。当前远端正式基线仍是 `v4`，提交号 `363705c`，提交信息是 `Release platform v4 strategy management refresh`。但本地现在已经有一批未提交改动，主要集中在 `hedgeBoard`、`strategy management`、`funding-carry`、`spread-carry`、设计主题和交易工具数据同步相关文件。后续所有修改都应在当前本地改动基础上继续推进；如果需要 git，默认先检查改动、再提交、再推送，并汇报当前版本号与版本总数。

