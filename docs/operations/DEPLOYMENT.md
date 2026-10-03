# Deployment Boundary

The maintained topology is:

```text
platform-web
    ↓ Browser Session / REST
platform-api
    ↓ versioned Runtime contracts
execution-runtime
    ↓ external venues and brokers
```

## Local development

- Platform Web: `http://127.0.0.1:4373/index.html`
- Platform API: `http://127.0.0.1:8000/health`
- Execution Runtime: `http://127.0.0.1:8100/health`

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

Simulation/Fake Gateway and disabled Platform/Runtime Live Write remain the default safety state.

## Reversible local web publication

The supported local publication path is `scripts/publish-local-web.ps1`. It builds `platform-web`, copies `index.html`, formal brand configuration and only the output files listed by the current Vite manifest into a UTC timestamped `.codex/releases/web/<timestamp>/` directory. This prevents stale files left in the local build directory from accumulating in new releases. The script validates the generated `deploy/Caddyfile.windows` configuration with the existing portable Caddy binary, then updates `.codex/releases/web/current.json`. Failed builds or Caddy validation leave the previous marker unchanged. `dev-platform.ps1 -Action restart-web` activates only the Web release; the API and Runtime stay running. Caddy binds to loopback and serves built artifacts, independent of source-file HMR. This is a local release switch only; it does not register Windows services, alter trading mode, accounts or databases, or establish an external deployment. Preparation, rollback and development-port commands are in [RUNBOOK.md](RUNBOOK.md).

## Live acceptance is separate

A successful deployment or health check does not authorize live trading. Controlled instruction-bounded validation follows [`../operations/LIVE_ACCEPTANCE_RUNBOOK.md`](../operations/LIVE_ACCEPTANCE_RUNBOOK.md), and any failed step returns the system to read-only mode.

## External deployment contract

Actual server directories and public endpoints are external configuration:

```text
PLATFORM_WEB_DEPLOY_DIR
PLATFORM_WEB_PUBLIC_URL
PLATFORM_API_DEPLOY_DIR
PLATFORM_API_PUBLIC_URL
```

Repository automation must not provide server-specific defaults. Missing variables fail deployment. See `../../deploy/README.md` for the operator contract.

A successful build does not prove external server, domain, TLS, database, reverse-proxy, credential, monitoring, backup or broker readiness. Those require separate operator evidence.
