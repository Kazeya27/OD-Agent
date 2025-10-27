#!/bin/bash

# ===========================================
# 切换到生产环境脚本
# ===========================================

echo "🔄 切换到生产环境..."

# 停止当前服务
echo "🛑 停止当前服务..."
docker-compose down

# 启动生产环境服务
echo "🚀 启动生产环境服务..."
docker-compose -f docker-compose.prod.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 20

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "✅ 生产环境启动完成！"
echo ""
echo "🌐 外网访问地址："
echo "   主站点: http://43.143.167.2"
echo "   后端API: http://43.143.167.2/api"
echo "   Agent API: http://43.143.167.2/agent"
echo "   健康检查: http://43.143.167.2/health"
echo ""
echo "📋 管理命令："
echo "   查看状态: docker-compose -f docker-compose.prod.yml ps"
echo "   查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo "   停止服务: docker-compose -f docker-compose.prod.yml down"
