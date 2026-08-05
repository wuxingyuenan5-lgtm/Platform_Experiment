# 全球变量金融平台文档导航

Stable baseline, target scope and known limits belong in the authorities below. Volatile branch, HEAD and pull-request facts must be read from Git and GitHub. Completed plans, handoffs, evidence ledgers, phase receipts and release-status snapshots belong in Git history and pull requests, not in the active documentation tree.

## A1 authorities

| Document | Sole responsibility |
|---|---|
| `../README.md` | Project purpose and shortest startup entry |
| `../AGENTS.md` | Engineering and AI execution constraints |
| `codex/current-state.md` | Current stable baseline, target scope and known limits |
| `codex/context-map.md` | Bounded context selection |
| `architecture/SYSTEM_MAP.md` | Runtime topology and dependency direction |
| `architecture/OWNERSHIP.md` | Code, policy and persistence ownership |
| `operations/RUNBOOK.md` | Start, stop, health checks and safe operations |
| `operations/LIVE_ACCEPTANCE_RUNBOOK.md` | Controlled live acceptance, fail-closed handling, EOD and forced reset |
| `database/README.md` | Database, DDL and migration authority |
| `contracts/README.md` | Current domain-contract index |
| `engineering/GIT_WORKFLOW.md` | Branch, review and CI workflow |

## Specialist references

- `technical/` contains active Platform 0.10.x implementation contracts.
- `product/` contains current product requirements.
- `../platform-web/docs/` contains maintained frontend design and acceptance references.
- `operations/` contains durable operational procedures; temporary acceptance receipts are not authorities.

## Maintenance rules

- Change stable baseline, target scope and known limits only in `codex/current-state.md`.
- Read active branch, HEAD and pull-request status from Git and GitHub rather than copying them into long-term Markdown.
- Change service topology only in `architecture/SYSTEM_MAP.md`.
- Change ownership only in `architecture/OWNERSHIP.md`.
- Change startup and recovery commands only in `operations/RUNBOOK.md`.
- Change controlled live-acceptance rules only in `operations/LIVE_ACCEPTANCE_RUNBOOK.md` and the owning executable contracts.
- Change a business rule in its owning contract and executable tests.
- Do not create parallel “start here”, handoff, audit, phase or evidence documents.
