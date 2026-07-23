# API Specification

The current platform backend API prefix is `/api/v1`.

Key local endpoints:

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/api/v1/system/info`
- `GET http://127.0.0.1:8000/api/v1/strategies/definitions`
- `GET http://127.0.0.1:8000/api/v1/strategies/instances`
- `GET http://127.0.0.1:8000/api/v1/accounts`
- `GET http://127.0.0.1:8000/api/v1/instruments`
- `GET http://127.0.0.1:8000/api/v1/trading/orders`

Source of truth for implementation: `platform-backend/app/main.py`.
