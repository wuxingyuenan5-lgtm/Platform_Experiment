# Platform Execution Runtime Test Taxonomy

Runtime tests are classified during collection by `conftest.py` and every test receives exactly one primary execution layer.

- `unit`: deterministic protocol, adapter, and isolated calculation behavior.
- `integration`: gateway, journal, bridge, market, and venue component collaboration.
- `live_safety`: credential handling, connectivity, atomic claims, redaction, and live-write safety.

Classification is based on the test module name, with live-safety rules taking precedence and `unit` as the explicit default. Pytest runs with `--strict-markers`, so undeclared markers fail collection. CI executes each layer independently and tests must not depend on suite ordering or state left by another layer.
