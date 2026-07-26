# Platform Backend Agent Rules

Scope: `platform-backend/`.

- Own business APIs, risk, orchestration, persistence coordination and accounting.
- Never import Bybit, MT5 or other Venue SDKs; external effects belong in `execution-runtime/`.
- Keep Decimal and timezone-aware values at financial boundaries.
- Direct SQL and protected transactions stay in established Repository owners.
- Trading, risk, auth, database, migration, formal accounting and Runtime-contract changes are Critical.
- Avoid new Policy/Repository/Service modules unless a real second responsibility or test boundary exists.

Checks:

```powershell
python -m ruff check app tests
python -m pyright
python -m pytest -m "architecture or unit or integration or live_safety"
```
