from __future__ import annotations

import json

from runtime_guardrails import hook_context_response, load_payload, resolve_cwd, resolve_runtime_state


def main() -> None:
    payload = load_payload()
    cwd = resolve_cwd(payload)
    state = resolve_runtime_state(cwd)
    event_name = str(payload.get("hook_event_name") or "SessionStart")
    print(json.dumps(hook_context_response(event_name, state), ensure_ascii=False))


if __name__ == "__main__":
    main()
