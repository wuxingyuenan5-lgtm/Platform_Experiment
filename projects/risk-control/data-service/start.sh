#!/bin/bash
set -euo pipefail

: "${DB_DSN:?Set DB_DSN in the process environment before starting data-service}"
: "${JWT_SECRET:?Set JWT_SECRET in the process environment before starting data-service}"
: "${ACCOUNT_ENCRYPTION_KEY:?Set ACCOUNT_ENCRYPTION_KEY separately before starting data-service}"

export TZ="${TZ:-Asia/Shanghai}"
export DB_DSN
export PORT="${PORT:-8082}"
export JWT_SECRET
export ACCOUNT_ENCRYPTION_KEY
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
