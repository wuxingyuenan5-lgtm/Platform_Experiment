# data-service

Go service for account data monitoring. The first implemented adapter is Bybit V5 wallet balance.

## Runtime

- Port: `8082`
- Sync frequency: `5m`
- Database connection is supplied through the required `DB_DSN` environment variable.
- Bybit credentials are read from `BYBIT_API_KEY` and `BYBIT_API_SECRET`. If they are not set, the service reads `bitget-data-service/bybitapi.txt`.
- Bybit request receive window defaults to `10000ms` via `BYBIT_RECV_WINDOW`.
- Bybit signed timestamp uses Bybit server time by default. `BYBIT_TIMESTAMP_OFFSET_MS` defaults to `0`.

## Start On Windows

```powershell
cd "D:\variable global\Variable-Global\projects\risk-control\data-service"
.\start.ps1
```

If PowerShell blocks local scripts, run this once in the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Main APIs

- `POST /api/v1/data/sync`: manually sync Bybit wallet balance.
- `GET /api/v1/accounts`: list accounts with latest asset snapshot.
- `GET /api/v1/data/total`: latest total asset summary.
- `GET /api/v1/data/net-value?account_id=1`: net value history.
- `GET /product/navplatformNetValueList?checkCode=bybit-unified&platform=crypto`: frontend-compatible net value chart data.

Every scheduled sync inserts one row into `assets`, so the frontend can render `created_at` and `unit_net_worth` as a line chart.
