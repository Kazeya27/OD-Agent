#!/bin/bash

# OD-Agent 项目停止脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印彩色消息
print_colored() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_colored $CYAN "🛑 正在停止OD-Agent所有服务..."

# 停止后端服务
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if kill $BACKEND_PID 2>/dev/null; then
        print_colored $GREEN "✅ 后端服务已停止 (PID: $BACKEND_PID)"
    else
        print_colored $YELLOW "⚠️  后端服务可能已经停止"
    fi
    rm logs/backend.pid
else
    print_colored $YELLOW "⚠️  未找到后端服务PID文件"
fi

# 停止Agent服务
if [ -f "logs/agent.pid" ]; then
    AGENT_PID=$(cat logs/agent.pid)
    if kill $AGENT_PID 2>/dev/null; then
        print_colored $GREEN "✅ Agent服务已停止 (PID: $AGENT_PID)"
    else
        print_colored $YELLOW "⚠️  Agent服务可能已经停止"
    fi
    rm logs/agent.pid
else
    print_colored $YELLOW "⚠️  未找到Agent服务PID文件"
fi

# 停止前端服务
if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if kill $FRONTEND_PID 2>/dev/null; then
        print_colored $GREEN "✅ 前端服务已停止 (PID: $FRONTEND_PID)"
    else
        print_colored $YELLOW "⚠️  前端服务可能已经停止"
    fi
    rm logs/frontend.pid
else
    print_colored $YELLOW "⚠️  未找到前端服务PID文件"
fi

# 强制清理可能残留的进程
print_colored $CYAN "🧹 清理可能残留的进程..."

# 清理Streamlit进程
pkill -f "streamlit run" 2>/dev/null && print_colored $GREEN "✅ 清理Streamlit进程"

# 清理uvicorn进程
pkill -f "uvicorn app:app" 2>/dev/null && print_colored $GREEN "✅ 清理uvicorn进程"

# 清理agent_service进程
pkill -f "agent_service.py" 2>/dev/null && print_colored $GREEN "✅ 清理agent_service进程"

print_colored $GREEN "🎉 所有服务已停止完成！"
