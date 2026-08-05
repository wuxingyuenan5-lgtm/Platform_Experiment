# Deployment

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

## Live acceptance is separate

A successful deployment or health check does not authorize live trading. Controlled minimum-size validation follows [`../operations/LIVE_ACCEPTANCE_RUNBOOK.md`](../operations/LIVE_ACCEPTANCE_RUNBOOK.md), and any failed step returns the system to read-only mode.

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
