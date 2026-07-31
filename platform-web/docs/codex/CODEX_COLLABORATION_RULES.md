# Codex 协作规则

状态：`active`

## 范围控制

- UI 点选任务只读目标组件、直接父组件和必要样式，不先扫描全项目。
- 交易执行任务只读执行组件、lifecycle API、exit plan API 和相关类型。
- 持仓、账户和 observability 任务只读持仓组件、observability API、snapshot 类型。
- 启动、端口、CORS 任务只读 scripts、Vite 配置、后端配置和 env。
- 架构整理任务才读取 README、docs 和模块全貌。

## 产品界面纪律

- 不新增解释性 UI 文案。
- 不出现“设计保留”“真实执行请使用下方”“保护口径”“验收面板”等工程说明。
- 不新增独立交易区、独立验收区或工程说明卡片，除非用户明确要求。
- 优先复用用户已有组件结构；功能应合并到现有入口，而不是外挂新面板。
- 页面文案只承担操作、状态、字段名和结果反馈，不承担开发说明。

## 跨所价差页收口

- 交易能力统一进入 `价差执行指令`。
- 账户、风险和 observability 信息统一进入 `价差持仓总览`。
- `CrossSpreadMarketLifecyclePanel.vue` 和 `CrossSpreadLiveObservabilityPanel.vue` 不直接挂载到产品页。
- 未挂载的参考组件先标记 deprecated，不在小任务中批量删除。

## 验证命令

- 前端类型检查：`npx pnpm@9.15.9 type:check`
- 首页布局检查：`npx pnpm@9.15.9 test:homepage-layout`
- 跨所价差结构检查：`npx pnpm@9.15.9 test:cross-spread-layout`

## 文件操作

- 禁止批量删除文件或目录。
- 删除文件只能一次删除一个明确路径，并且需要用户明确要求。
- 长 Vue 文件修改优先用 ASCII 选择器、函数名、class 和脚本结构定位，避免依赖终端中的中文匹配。
