#!/bin/bash

# ===========================================
# OD-Agent 快速部署脚本
# ===========================================

echo "🚀 开始部署 OD-Agent..."


# 创建环境文件（如果不存在）
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        echo "📝 创建环境配置文件..."
        cp env.example .env
        echo "⚠️  请编辑 .env 文件，设置 GOOGLE_API_KEY"
    fi
fi

# 创建必要目录
echo "📁 创建目录..."
mkdir -p agent/backend/data
mkdir -p agent/agent/chat_history
mkdir -p agent/agent/logs
mkdir -p frontend/logs
mkdir -p frontend/dumps/traces

# 停止现有服务
echo "🛑 停止现有服务..."
docker-compose down 2>/dev/null || true

# 构建和启动
echo "🔨 构建镜像..."
docker-compose build

echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 15

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

echo ""
echo "✅ 部署完成！"
echo ""
echo "🌐 访问地址："
echo "   Frontend: http://localhost:8501"
echo "   Backend:  http://localhost:8502"
echo "   Agent:    http://localhost:8503"
echo ""
echo "📋 管理命令："
echo "   查看状态: docker-compose ps"
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
