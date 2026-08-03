#!/bin/bash
set -euo pipefail

: "${DB_DSN:?Set DB_DSN in the process environment before starting auth-service}"
: "${JWT_SECRET:?Set JWT_SECRET in the process environment before starting auth-service}"
export DB_DSN
export JWT_SECRET
export PORT="${PORT:-8080}"

echo "正在启动 auth-service 服务..."
mkdir -p bin
go build -o bin/auth-service ./cmd
./bin/auth-service
