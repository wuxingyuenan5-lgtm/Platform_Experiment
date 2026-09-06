# Platform Execution Runtime Agent Rules

Scope: `execution-runtime/`.

- Own Venue/Broker SDKs, external side effects and Runtime Journal evidence.
- Runtime changes are Critical by default.
- Preserve idempotency, external identity, ACK/Fill separation and fail-closed unknown-result handling.
- Do not import Platform business services or persist formal accounting truth.
- Live Write remains disabled unless a dedicated approved operational task changes it.

Runtime changes are Critical, so select directly relevant tests first and expand to this broader set whenever the affected safety or adapter boundary requires it:

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pyright
.\.venv\Scripts\python.exe -m pytest -m "unit or integration or live_safety"
```
