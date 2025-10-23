#!/bin/bash

# OD-Agent 项目快速启动脚本
# 不使用Docker，直接使用Python和Streamlit

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 打印彩色消息
print_colored() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 检查Python版本
check_python() {
    print_colored $CYAN "🐍 检查Python版本..."
    if ! command -v python3 &> /dev/null; then
        print_colored $RED "❌ 未找到Python3，请先安装Python 3.8+"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_colored $GREEN "✅ Python版本: $python_version"
}

# 安装依赖
install_deps() {
    print_colored $CYAN "📦 安装项目依赖..."
    
    # 安装后端依赖
    if [ -f "agent/backend/requirements.txt" ]; then
        print_colored $YELLOW "安装后端依赖..."
        cd agent/backend
        python3 -m pip install -r requirements.txt
        cd ../..
    fi
    
    # 安装Agent依赖
    if [ -f "agent/agent/requirements.txt" ]; then
        print_colored $YELLOW "安装Agent依赖..."
        cd agent/agent
        python3 -m pip install -r requirements.txt
        cd ../..
    fi
    
    # 安装前端依赖
    if [ -f "frontend/requirements.txt" ]; then
        print_colored $YELLOW "安装前端依赖..."
        cd frontend
        python3 -m pip install -r requirements.txt
        cd ..
    fi
    
    print_colored $GREEN "✅ 所有依赖安装完成"
}

# 启动服务
start_services() {
    print_colored $CYAN "🚀 启动所有服务..."
    
    # 创建日志目录
    mkdir -p logs
    
    # 启动后端服务
    print_colored $YELLOW "启动后端服务 (端口: 8502)..."
    cd agent/backend
    nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 8502 --reload > ../../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    cd ../..
    
    # 等待后端启动
    sleep 3
    
    # 启动Agent服务
    print_colored $YELLOW "启动Agent服务 (端口: 8503)..."
    cd agent/agent
    nohup python3 agent_service.py > ../../logs/agent.log 2>&1 &
    AGENT_PID=$!
    cd ../..
    
    # 等待Agent启动
    sleep 3
    
    # 启动前端服务
    print_colored $YELLOW "启动前端服务 (端口: 8501)..."
    cd frontend
    nohup python3 -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    
    # 保存PID到文件
    echo $BACKEND_PID > logs/backend.pid
    echo $AGENT_PID > logs/agent.pid
    echo $FRONTEND_PID > logs/frontend.pid
    
    print_colored $GREEN "✅ 所有服务启动完成！"
}

# 显示访问信息
show_info() {
    print_colored $WHITE "============================================================"
    print_colored $GREEN "🎉 OD-Agent 项目启动成功！"
    print_colored $WHITE "============================================================"
    print_colored $CYAN "📱 前端界面: http://localhost:8501"
    print_colored $CYAN "🔧 后端API: http://localhost:8502"
    print_colored $CYAN "🤖 Agent服务: http://localhost:8503"
    print_colored $YELLOW "💡 查看日志: tail -f logs/*.log"
    print_colored $YELLOW "💡 停止服务: ./stop.sh"
    print_colored $WHITE "============================================================"
}

# 清理函数
cleanup() {
    print_colored $YELLOW "🛑 正在停止所有服务..."
    
    # 读取PID并停止进程
    if [ -f "logs/backend.pid" ]; then
        kill $(cat logs/backend.pid) 2>/dev/null || true
        rm logs/backend.pid
    fi
    
    if [ -f "logs/agent.pid" ]; then
        kill $(cat logs/agent.pid) 2>/dev/null || true
        rm logs/agent.pid
    fi
    
    if [ -f "logs/frontend.pid" ]; then
        kill $(cat logs/frontend.pid) 2>/dev/null || true
        rm logs/frontend.pid
    fi
    
    print_colored $GREEN "✅ 所有服务已停止"
}

# 设置信号处理
trap cleanup EXIT INT TERM

# 主函数
main() {
    print_colored $WHITE "============================================================"
    print_colored $PURPLE "🚀 OD-Agent 项目快速启动"
    print_colored $WHITE "============================================================"
    
    check_python
    install_deps
    start_services
    show_info
    
    # 等待用户中断
    print_colored $YELLOW "按 Ctrl+C 停止所有服务"
    while true; do
        sleep 1
    done
}

# 运行主函数
main "$@"
