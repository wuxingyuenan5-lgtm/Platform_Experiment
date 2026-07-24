# Outputs

`outputs/` contains disposable task results such as reports, generated comparisons and local analysis artifacts.

Rules:

- An output is not a source of truth.
- Production code must not import from this directory.
- Architecture, API and operational facts must be promoted to the appropriate `docs/` file before relying on them.
- Do not store secrets, credentials, database backups or user data here.
- Prefer one subdirectory per task and delete obsolete generated artifacts through a reviewed PR.
- A task completion summary should link the durable document or code change, not only an output file.
