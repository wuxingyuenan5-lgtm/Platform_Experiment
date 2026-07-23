# Security

Current security posture:

- Do not commit real API keys, passwords, tokens, or populated `.env` files.
- Live trading is disabled by default.
- Trading, account, permission, and deployment changes require explicit review.

Relevant backend files:

- `platform-backend/app/security.py`
- `platform-backend/app/config.py`
- `execution-runtime/app/secret_resolver.py`
