#!/bin/bash

# 停止 auth-service 进程
pid=$(ps -ef | grep auth-service | grep -v grep | awk '{print $2}')
if [ -n "$pid" ];then
    kill -9 $pid
    echo "已停止 auth-service 进程 PID:$pid"
else
    echo "未找到运行中的 auth-service 进程"
fi
