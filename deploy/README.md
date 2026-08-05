# Deployment Configuration

Repository files do not define or verify a production server, domain, database, proxy, credential or broker connection. Deployment is an operator-controlled action outside normal CI validation.

## Required neutral variables

Configure these in the external CI/CD system or operator environment:

```text
PLATFORM_WEB_DEPLOY_DIR
PLATFORM_WEB_PUBLIC_URL
PLATFORM_API_DEPLOY_DIR
PLATFORM_API_PUBLIC_URL
```

The repository intentionally provides no server-specific defaults. A deployment command must fail clearly when a required variable is absent.

## Platform Web

`platform-web/.gitlab-ci.yml` builds the maintained frontend and copies the generated `dist/` directory only to `PLATFORM_WEB_DEPLOY_DIR`. It verifies `index.html` and `assets/` after copying and reports `PLATFORM_WEB_PUBLIC_URL` without embedding an actual domain.

## Platform API

The maintained API is `platform-api`. External deployment automation must:

1. install the package from `platform-api/pyproject.toml`;
2. set environment-specific database and security configuration outside Git;
3. keep Live Write disabled by default;
4. expose the service only through the operator-approved process manager and reverse proxy;
5. verify `/health` before routing traffic;
6. preserve database backup and rollback procedures.

The destination and public endpoint are supplied through `PLATFORM_API_DEPLOY_DIR` and `PLATFORM_API_PUBLIC_URL`. No repository script claims those variables are already configured.

## Execution Runtime

`execution-runtime` is deployed separately from Platform API and remains the exclusive venue side-effect boundary. Credentials, live-routing permissions and Live Write activation require the dedicated controlled-operation process; they are not part of a normal application deployment.

## Safety

- Do not enable Live Write as a deployment side effect.
- Do not infer external readiness from a successful repository build.
- Do not commit absolute server paths, public domains, credentials or database connection strings.
- A production rollout requires separate monitoring, backup, restore and rollback evidence.
