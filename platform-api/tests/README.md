# Platform API Test Taxonomy

Backend tests remain close to the modular-monolith codebase, but every collected test is assigned exactly one primary execution layer by `conftest.py`.

- `architecture`: static module, schema, and projection ownership boundaries.
- `unit`: deterministic calculations and isolated domain policies.
- `integration`: API, SQLite persistence, orchestration, and component collaboration.
- `live_safety`: fail-closed controls, production operations, and live-write safety.

Classification is based on the test module name, with architecture and live-safety rules taking precedence and `unit` as the explicit default. Pytest runs with `--strict-markers`, so undeclared markers fail collection. CI executes every layer separately; adding a test therefore requires it to remain compatible with its assigned layer and must not rely on execution order.

The shared settings fixture disables background research refresh as well as strategy
capture and Choice collection. Generic API tests must not start unrelated source
collectors during application startup or wait for them during shutdown. Tests of
collector lifecycle behavior must explicitly enable refresh and replace provider
I/O with isolated fixtures; direct refresh tests can continue to invoke the owned
refresh function. The socket isolation guard remains active in either case.
