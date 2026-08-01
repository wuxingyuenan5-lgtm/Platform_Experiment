# 全球变量金融平台（Variable-Global）文档导航

`Platform`是工程与架构层通用简称；正式产品品牌仍为全球变量金融平台（Variable-Global）。本文件只负责文档导航，不拥有版本、阶段、服务拓扑、业务规则或运行命令；所有权权威为`docs/architecture/OWNERSHIP.md`。

## A1 — top-level authorities

The controlled A1 set contains ten entrypoints:

| Document | Sole responsibility |
|---|---|
| `../README.md` | Project purpose and shortest startup entry |
| `../AGENTS.md` | AI and engineering execution constraints |
| `codex/current-state.md` | Current version, branch, phase and known limits |
| `codex/context-map.md` | Minimal context selection by task |
| `architecture/SYSTEM_MAP.md` | Services, data flow and system boundaries |
| `architecture/OWNERSHIP.md` | Business-rule, code and data owners |
| `operations/RUNBOOK.md` | Start, stop, troubleshooting and safe operations |
| `database/README.md` | Database, migration, backup and recovery entry |
| `contracts/README.md` | Current domain-contract index |
| `README.md` | Documentation navigation |

`codex/CURRENT_CONTEXT.md` is a compatibility pointer and is not an A1 authority.

## A2 — domain contracts

`contracts/README.md` indexes the current Identity & Permission, Live Write, Trading, Execution, Risk, Accounting, Reconciliation, Member Portfolio, Research and Market Data contracts. A1 documents link to contracts and do not copy their rules.

## B — specialist references

| Reference type | Location | Use |
|---|---|---|
| Platform Web product and page design | `../platform-web/docs/` | Product detail and page-specific design |
| Technical and provider references | `technical/` | Domain implementation detail beyond the A2 index |
| Architecture discussions and standards | `architecture/` | Specialist design rationale; `SYSTEM_MAP.md` and `OWNERSHIP.md` remain the A1 authorities |
| Acceptance and operational supplements | `operations/` | Task-specific acceptance; `RUNBOOK.md` remains the operating authority |
| Legacy production evidence | `architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md`, `architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md` | External migration evidence only |
| Product requirements | `product/` | Product scope and acceptance reference |
| Release history | `releases/` | Historical release evidence only |

Plan, Handoff, Audit, Task, Superseded and archived materials are not current authorities and are excluded from default context. Their cleanup belongs to Phase 2.

## Governance

- Current delivery state is updated only in `codex/current-state.md` and GitHub PR #141.
- Service topology changes update `architecture/SYSTEM_MAP.md`.
- Owner changes update `architecture/OWNERSHIP.md`.
- Domain-rule changes update the owning A2 contract and executable tests.
- Startup or recovery command changes update `operations/RUNBOOK.md`.
- Do not create a parallel document for a responsibility already owned above.
