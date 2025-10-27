#!/bin/bash

# ===========================================
# OD-Agent 生产环境部署脚本
# ===========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查环境
check_environment() {
    print_info "检查生产环境..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装"
        exit 1
    fi
    
    # 检查环境文件
    if [ ! -f ".env" ]; then
        print_error "未找到 .env 文件，请先配置环境变量"
        exit 1
    fi
    
    print_success "环境检查完成"
}

# 创建生产环境目录
create_prod_directories() {
    print_info "创建生产环境目录..."
    
    mkdir -p data/backend
    mkdir -p data/agent/chat_history
    mkdir -p data/agent/logs
    mkdir -p data/frontend/logs
    mkdir -p data/frontend/dumps
    mkdir -p ssl
    
    print_success "目录创建完成"
}

# 备份现有数据
backup_data() {
    if [ -d "data" ]; then
        print_info "备份现有数据..."
        timestamp=$(date +%Y%m%d_%H%M%S)
        tar -czf "backup_${timestamp}.tar.gz" data/
        print_success "数据备份完成: backup_${timestamp}.tar.gz"
    fi
}

# 停止现有服务
stop_services() {
    print_info "停止现有服务..."
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    print_success "服务已停止"
}

# 清理旧镜像
cleanup_images() {
    print_info "清理旧镜像..."
    docker system prune -f
    print_success "清理完成"
}

# 构建和启动服务
deploy_services() {
    print_info "构建生产镜像..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    print_info "启动生产服务..."
    docker-compose -f docker-compose.prod.yml up -d
    
    print_success "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    print_info "等待服务就绪..."
    
    services=("backend:8502" "agent:8503" "frontend:8501")
    max_attempts=30
    
    for service in "${services[@]}"; do
        name=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        
        print_info "检查 $name 服务..."
        
        for i in $(seq 1 $max_attempts); do
            if curl -f -s "http://localhost:$port/" > /dev/null 2>&1; then
                print_success "$name 服务就绪"
                break
            fi
            
            if [ $i -eq $max_attempts ]; then
                print_warning "$name 服务可能未完全启动"
            else
                sleep 2
            fi
        done
    done
}

# 显示部署信息
show_deployment_info() {
    print_success "生产环境部署完成！"
    echo ""
    print_info "服务访问地址："
    echo "  🌐 主站点: http://localhost"
    echo "  🔧 Backend API: http://localhost/api"
    echo "  🤖 Agent API: http://localhost/agent"
    echo "  📊 健康检查: http://localhost/health"
    echo ""
    print_info "管理命令："
    echo "  查看状态: docker-compose -f docker-compose.prod.yml ps"
    echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"
    echo ""
    print_info "数据目录："
    echo "  Backend数据: ./data/backend/"
    echo "  聊天历史: ./data/agent/chat_history/"
    echo "  日志文件: ./data/*/logs/"
    echo ""
    print_warning "生产环境注意事项："
    echo "  1. 定期备份数据目录"
    echo "  2. 监控服务健康状态"
    echo "  3. 配置SSL证书（如需要）"
    echo "  4. 设置防火墙规则"
}

# 主函数
main() {
    echo "==========================================="
    echo "    OD-Agent 生产环境部署"
    echo "==========================================="
    echo ""
    
    check_environment
    create_prod_directories
    backup_data
    stop_services
    cleanup_images
    deploy_services
    wait_for_services
    show_deployment_info
}

# 运行主函数
main "$@"
