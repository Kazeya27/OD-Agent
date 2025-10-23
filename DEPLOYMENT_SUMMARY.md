# OD-Agent Docker 部署方案总结

## 🎯 部署目标

为 OD-Agent 项目创建完整的 Docker 部署方案，实现一键部署到服务器。

## 📁 项目结构

```
OD-Agent/
├── agent/
│   ├── backend/          # 后端API服务
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app.py
│   └── agent/            # 智能代理服务
│       ├── Dockerfile
│       ├── requirements.txt
│       └── agent_service.py
├── frontend/             # 前端界面
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
├── docker-compose.yml    # 开发环境配置
├── docker-compose.prod.yml # 生产环境配置
├── nginx.conf           # Nginx反向代理配置
├── deploy.sh            # 完整部署脚本
├── quick-deploy.sh      # 快速部署脚本
├── deploy-prod.sh       # 生产环境部署脚本
├── env.example          # 环境配置模板
└── DOCKER_DEPLOYMENT.md # 详细部署文档
```

## 🚀 部署方式

### 1. 快速部署（推荐）

```bash
# 一键部署
./quick-deploy.sh
```

### 2. 完整部署

```bash
# 包含详细检查和错误处理
./deploy.sh
```

### 3. 生产环境部署

```bash
# 生产环境部署（包含Nginx反向代理）
./deploy-prod.sh
```

## 🔧 服务配置

### 开发环境 (docker-compose.yml)
- **Backend**: 端口 8000
- **Agent**: 端口 8001  
- **Frontend**: 端口 8501
- 使用本地卷挂载数据

### 生产环境 (docker-compose.prod.yml)
- 添加资源限制
- 健康检查配置
- 数据持久化卷
- Nginx反向代理
- 自动重启策略

## 📋 环境配置

### 必需配置
```bash
# .env 文件
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key_here
```

### 可选配置
```bash
LLM_MODEL=gemini-2.5-flash-preview-05-20
LLM_TEMPERATURE=0.6
BACKEND_PORT=8000
AGENT_PORT=8001
FRONTEND_PORT=8501
```

## 🌐 访问地址

### 开发环境
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- Agent API: http://localhost:8001

### 生产环境（带Nginx）
- 主站点: http://localhost
- Backend API: http://localhost/api
- Agent API: http://localhost/agent
- 健康检查: http://localhost/health

## 📊 数据持久化

### 开发环境
- 数据目录直接挂载到宿主机
- 便于开发和调试

### 生产环境
- 使用Docker卷管理数据
- 数据备份和恢复
- 日志轮转

## 🛠️ 管理命令

### 基本操作
```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

### 生产环境操作
```bash
# 使用生产配置
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
docker-compose -f docker-compose.prod.yml down
```

## 🔍 监控和健康检查

### 健康检查端点
- Backend: `GET /`
- Agent: `GET /`
- Frontend: `GET /`

### 日志管理
```bash
# 查看实时日志
docker-compose logs -f --tail=100

# 导出日志
docker-compose logs > deployment.log
```

## 🔒 安全考虑

### 生产环境安全
- 使用Nginx反向代理
- 配置SSL证书（可选）
- 资源限制
- 网络隔离

### 数据安全
- 定期备份数据
- 敏感信息环境变量管理
- 日志审计

## 📈 扩展性

### 水平扩展
- 支持Docker Swarm部署
- 支持Kubernetes部署
- 负载均衡配置

### 垂直扩展
- 资源限制配置
- 性能监控
- 自动扩缩容

## 🚨 故障排除

### 常见问题
1. **端口冲突**: 检查端口占用情况
2. **API Key错误**: 验证环境配置
3. **服务启动失败**: 查看详细日志
4. **网络问题**: 检查Docker网络配置

### 调试命令
```bash
# 进入容器调试
docker-compose exec backend bash
docker-compose exec agent bash
docker-compose exec frontend bash

# 查看网络
docker network ls
docker network inspect od-agent_od-network
```

## 📝 部署检查清单

### 部署前检查
- [ ] Docker 和 Docker Compose 已安装
- [ ] 环境配置文件已设置
- [ ] API Key 已配置
- [ ] 端口未被占用
- [ ] 磁盘空间充足

### 部署后验证
- [ ] 所有服务正常运行
- [ ] 健康检查通过
- [ ] 前端界面可访问
- [ ] API接口正常响应
- [ ] 日志无错误信息

## 🎉 总结

本部署方案提供了：
- ✅ 一键部署脚本
- ✅ 开发和生产环境配置
- ✅ 完整的监控和日志
- ✅ 数据持久化方案
- ✅ 安全配置
- ✅ 故障排除指南

通过这套方案，可以快速、安全、可靠地部署 OD-Agent 项目到任何支持 Docker 的服务器上。
