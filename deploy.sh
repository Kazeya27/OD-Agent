#!/bin/bash

# ===========================================
# OD-Agent 一键部署脚本
# ===========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker和Docker Compose是否安装
check_dependencies() {
    print_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_success "依赖检查通过"
}

# 检查环境配置文件
check_env_file() {
    print_info "检查环境配置..."
    
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            print_warning "未找到 .env 文件，从 env.example 创建..."
            cp env.example .env
            print_warning "请编辑 .env 文件，设置正确的 API Key 等配置"
            print_warning "特别是 GOOGLE_API_KEY 需要设置为您的实际 API Key"
        else
            print_error "未找到环境配置文件"
            exit 1
        fi
    fi
    
    print_success "环境配置检查完成"
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    
    mkdir -p agent/backend/data
    mkdir -p agent/agent/chat_history
    mkdir -p agent/agent/logs
    mkdir -p frontend/logs
    mkdir -p frontend/dumps/traces
    
    print_success "目录创建完成"
}

# 停止现有服务
stop_services() {
    print_info "停止现有服务..."
    
    if docker-compose ps -q | grep -q .; then
        docker-compose down
        print_success "现有服务已停止"
    else
        print_info "没有运行中的服务"
    fi
}

# 构建和启动服务
start_services() {
    print_info "构建和启动服务..."
    
    # 构建镜像
    print_info "构建Docker镜像..."
    docker-compose build --no-cache
    
    # 启动服务
    print_info "启动服务..."
    docker-compose up -d
    
    print_success "服务启动完成"
}

# 检查服务状态
check_services() {
    print_info "检查服务状态..."
    
    sleep 10  # 等待服务启动
    
    # 检查各服务健康状态
    services=("backend:8502" "agent:8503" "frontend:8501")
    
    for service in "${services[@]}"; do
        name=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        
        if curl -f -s "http://localhost:$port/" > /dev/null 2>&1; then
            print_success "$name 服务运行正常 (端口 $port)"
        else
            print_warning "$name 服务可能未完全启动，请稍等片刻"
        fi
    done
}

# 显示访问信息
show_access_info() {
    print_success "部署完成！"
    echo ""
    print_info "服务访问地址："
    echo "  🌐 Frontend (Web界面): http://localhost:8501"
    echo "  🔧 Backend API: http://localhost:8502"
    echo "  🤖 Agent API: http://localhost:8503"
    echo ""
    print_info "管理命令："
    echo "  查看服务状态: docker-compose ps"
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
    echo ""
    print_warning "注意：首次启动可能需要几分钟时间来下载依赖和初始化服务"
}

# 主函数
main() {
    echo "==========================================="
    echo "    OD-Agent 一键部署脚本"
    echo "==========================================="
    echo ""
    
    check_dependencies
    check_env_file
    create_directories
    stop_services
    start_services
    check_services
    show_access_info
}

# 运行主函数
main "$@"
