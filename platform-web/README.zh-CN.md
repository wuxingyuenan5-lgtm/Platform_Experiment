# Variable-Global Platform Web

[English](./README.md)

`platform-web/`是Variable-Global投研、策略、交易、风控、用户、资产与账务核对平台的Vue 3产品前端。

## 架构边界

```text
Platform Web
    ↓ Browser Session / REST
Platform API
    ↓ 版本化Runtime合同
Execution Runtime
```

浏览器不得持有Venue凭证，也不得直接执行外部下单副作用。权限、交易、正式账务、对账和执行安全规则继续由Platform API与Execution Runtime负责。

## 本地启动

Windows PowerShell，在仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

只运行或检查前端时，在`platform-web/`目录执行：

```bash
pnpm install --frozen-lockfile
pnpm dev
pnpm type:check
pnpm build
```

权威包管理器版本由`package.json#packageManager`声明。禁止在共享文档中记录固定测试密码；隔离演示账户和E2E凭据由对应脚本在运行时生成。

## 工程入口

- 当前工程状态：`../docs/codex/current-state.md`
- 前端Agent规则：`AGENTS.md`
- 产品与架构文档：`../docs/README.md`
- 前端历史设计与模块细节：`docs/`
- Git工作流：`../docs/engineering/GIT_WORKFLOW.md`

## 上游来源说明

当前前端保留了部分源自Vue Vben Admin的组件与构建基础设施，适用的MIT许可证保存在`LICENSE`。上游历史只用于许可证归属和维护参考；本仓库、Issue、版本与验收状态才是Variable-Global平台的权威来源。
