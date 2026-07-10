#!/bin/bash
set -e

# 定义环境变量
export DB_DSN='ymy:88368403@Ymy@tcp(127.0.0.1:3306)/risk_control?parseTime=true'
export JWT_SECRET='88368403Ymy'
export PORT=8080

# 启动服务
echo "正在启动 auth-service 服务..."
mkdir -p bin
go build -o bin/auth-service ./cmd
./bin/auth-service
