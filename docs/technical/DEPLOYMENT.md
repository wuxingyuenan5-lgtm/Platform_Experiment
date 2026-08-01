# Deployment

The current primary workflow is local Platform development and GitHub acceptance.

## Local services

- Platform Web: `http://127.0.0.1:4373/index.html`
- Platform API: `http://127.0.0.1:8000`
- Platform Execution Runtime: `http://127.0.0.1:8100`

Windows PowerShell entry:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

The default local state remains Simulation, Fake Gateway and Platform/Runtime Live Write disabled.

## Target topology

```text
Platform Web
    ↓ Browser Session / REST
Platform API
    ↓ versioned Runtime contracts
Platform Execution Runtime
    ↓ Venue / Broker / MT5 / Bybit
```

## Legacy deployment boundary

`deploy/`, `projects/risk-control/`, `platform-web/.gitlab-ci.yml` and the production frontend Legacy API routes describe a second historical production topology. They remain frozen until authorized server, GitLab Runner, MySQL, consumer, TLS and rollback evidence is reviewed.

Do not infer from repository contents that the Legacy stack is inactive. Do not switch production routes, stop services, migrate MySQL automatically or delete those assets as part of routine deployment cleanup.

Authoritative references:

- `../architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md`
- `../architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md`
- `../operations/LEGACY_PRODUCTION_EVIDENCE_HANDOFF.md`
