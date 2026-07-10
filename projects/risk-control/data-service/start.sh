#!/bin/bash
set -e

export TZ="${TZ:-Asia/Shanghai}"
export DB_DSN="${DB_DSN:-ymy:88368403@Ymy@tcp(127.0.0.1:3306)/risk_control?parseTime=true&loc=Asia%2FShanghai&time_zone=%27%2B08%3A00%27}"
export PORT="${PORT:-8082}"
export JWT_SECRET="${JWT_SECRET:-88368403Ymy}"
export ACCOUNT_ENCRYPTION_KEY="${ACCOUNT_ENCRYPTION_KEY:-$JWT_SECRET}"
export SYNC_INTERVAL="${SYNC_INTERVAL:-5m}"
export SYNC_ON_START="${SYNC_ON_START:-true}"
export SCHEDULER_ENABLED="${SCHEDULER_ENABLED:-true}"
export BYBIT_CREDENTIAL_FILE="${BYBIT_CREDENTIAL_FILE:-bitget-data-service/bybitapi.txt}"
export BYBIT_ACCOUNT_TYPE="${BYBIT_ACCOUNT_TYPE:-UNIFIED}"
export BYBIT_RECV_WINDOW="${BYBIT_RECV_WINDOW:-10000}"
export BYBIT_TIMESTAMP_OFFSET_MS="${BYBIT_TIMESTAMP_OFFSET_MS:-0}"
export BYBIT_ACCOUNT_ADDRESS="${BYBIT_ACCOUNT_ADDRESS:-bybit-unified}"
export BYBIT_ACCOUNT_NAME="${BYBIT_ACCOUNT_NAME:-Bybit Unified Account}"

mkdir -p bin
go build -o bin/data-service ./cmd
./bin/data-service
