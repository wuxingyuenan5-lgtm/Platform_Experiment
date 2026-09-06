# Platform API Agent Rules

Scope: `platform-api/`.

- Own business APIs, risk, orchestration, persistence coordination and accounting.
- Never import Bybit, MT5 or other Venue SDKs; external effects belong in `execution-runtime/`.
- Keep Decimal and timezone-aware values at financial boundaries.
- Direct SQL and protected transactions stay in established Repository owners.
- Trading, risk, auth, database, migration, formal accounting and Runtime-contract changes are Critical.
- Avoid new Policy/Repository/Service modules unless a real second responsibility or test boundary exists.

Select focused checks according to the root risk-based validation rule. Run the broader set for Critical or shared-contract changes rather than treating it as mandatory for every local edit:

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pyright
.\.venv\Scripts\python.exe -m pytest -m "architecture or unit or integration or live_safety"
```
