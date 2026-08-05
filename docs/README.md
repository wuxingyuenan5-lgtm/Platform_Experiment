# 全球变量金融平台文档导航

Current facts belong in the authorities below. Completed plans, handoffs, evidence ledgers, phase receipts and release-status snapshots belong in Git history and pull requests, not in the active documentation tree.

## A1 authorities

| Document | Sole responsibility |
|---|---|
| `../README.md` | Project purpose and shortest startup entry |
| `../AGENTS.md` | Engineering and AI execution constraints |
| `codex/current-state.md` | Current baseline, target, branch, review and known limits |
| `codex/context-map.md` | Bounded context selection |
| `architecture/SYSTEM_MAP.md` | Runtime topology and dependency direction |
| `architecture/OWNERSHIP.md` | Code, policy and persistence ownership |
| `operations/RUNBOOK.md` | Start, stop, health checks and safe operations |
| `database/README.md` | Database, DDL and migration authority |
| `contracts/README.md` | Current domain-contract index |
| `engineering/GIT_WORKFLOW.md` | Branch, review and CI workflow |

## Specialist references

- `technical/` contains active implementation contracts.
- `product/` contains current product requirements.
- `platform-web/docs/` contains maintained frontend design and acceptance references.
- `operations/` may contain durable operational procedures; temporary acceptance receipts are not authorities.

## Maintenance rules

- Change current delivery state only in `codex/current-state.md`.
- Change service topology only in `architecture/SYSTEM_MAP.md`.
- Change ownership only in `architecture/OWNERSHIP.md`.
- Change startup and recovery commands only in `operations/RUNBOOK.md`.
- Change a business rule in its owning contract and executable tests.
- Do not create parallel “start here”, handoff, audit, phase or evidence documents.
