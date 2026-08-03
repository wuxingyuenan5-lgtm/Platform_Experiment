# Platform Web

[中文说明](./README.zh-CN.md)

Platform Web is the Vue 3 product frontend of Variable-Global (全球变量金融平台), covering research, market data, strategy, trading, execution, risk, accounting, reconciliation, user access and member portfolio workflows.

## Architecture boundary

```text
Platform Web
    ↓ Browser Session / REST
Platform API
    ↓ versioned Runtime contracts
Platform Execution Runtime
```

The browser must not hold Venue credentials or perform external execution side effects. Trading, permissions, accounting and reconciliation rules remain authoritative in Platform API and Platform Execution Runtime.

## Local development

From the repository root on Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

Frontend-only commands from `platform-web/`:

```bash
pnpm install --frozen-lockfile
pnpm dev
pnpm type:check
pnpm build
```

The authoritative package manager is declared in `package.json#packageManager`.

## Engineering entry points

- Current state: `../docs/codex/current-state.md`
- Frontend agent rules: `AGENTS.md`
- Product and architecture docs: `../docs/README.md`
- Frontend design history and module detail: `docs/`
- Git workflow: `../docs/engineering/GIT_WORKFLOW.md`

## Upstream attribution

The frontend retains components and build infrastructure derived from Vue Vben Admin. The applicable MIT license is preserved in `LICENSE`. Upstream history is retained only for attribution and maintenance context; this repository, its issue tracker and its release state are authoritative for Variable-Global.
