# OD-Agent Docker 部署指南

## 概述

本项目包含三个主要服务：
- **Backend**: FastAPI 后端服务 (端口 8502)
- **Agent**: 智能代理服务 (端口 8503) 
- **Frontend**: Streamlit 前端界面 (端口 8501)

## 快速部署

### 方法一：一键部署脚本

```bash
# 运行快速部署脚本
./quick-deploy.sh
```

### 方法二：完整部署脚本

```bash
# 运行完整部署脚本（包含详细检查）
./deploy.sh
```

### 方法三：手动部署

```bash
# 1. 复制环境配置文件
cp env.example .env

# 2. 编辑环境配置（重要！）
# 设置 GOOGLE_API_KEY 等必要的 API Key
vim .env

# 3. 启动服务
docker-compose up -d

# 4. 查看服务状态
docker-compose ps
```

## 环境配置

### 必需配置

在 `.env` 文件中设置以下配置：

```bash
# LLM 配置
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key_here

# 服务端口（可选，使用默认值）
BACKEND_PORT=8502
AGENT_PORT=8503
FRONTEND_PORT=8501
```

### 获取 Google API Key

1. 访问 [Google AI Studio](https://aistudio.google.com/)
2. 创建新的 API Key
3. 将 API Key 设置到 `.env` 文件中

## 服务访问

部署完成后，可以通过以下地址访问服务：

- **前端界面**: http://localhost:8501
- **后端API**: http://localhost:8502
- **代理API**: http://localhost:8503

## 管理命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看服务日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f agent
docker-compose logs -f frontend
```

### 停止服务
```bash
docker-compose down
```

### 重启服务
```bash
docker-compose restart
```

### 重新构建
```bash
# 重新构建所有服务
docker-compose build --no-cache

# 重新构建特定服务
docker-compose build --no-cache backend
```

## 数据持久化

以下数据会被持久化保存：

- **Backend数据**: `./agent/backend/data/`
- **聊天历史**: `./agent/agent/chat_history/`
- **日志文件**: `./agent/agent/logs/`, `./frontend/logs/`

## 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 查看详细日志
   docker-compose logs
   ```

2. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :8502
   netstat -tulpn | grep :8503
   netstat -tulpn | grep :8501
   ```

3. **API Key 错误**
   - 检查 `.env` 文件中的 `GOOGLE_API_KEY` 是否正确设置
   - 确认 API Key 有效且有足够的配额

4. **服务间通信问题**
   ```bash
   # 检查网络连接
   docker-compose exec backend curl http://agent:8503/
   ```

### 清理和重置

```bash
# 停止并删除所有容器
docker-compose down

# 删除所有相关镜像
docker-compose down --rmi all

# 清理未使用的资源
docker system prune -f
```

## 生产环境部署

### 使用 Docker Swarm

```bash
# 初始化 Swarm
docker swarm init

# 部署服务栈
docker stack deploy -c docker-compose.yml od-agent
```

### 使用 Kubernetes

可以将 `docker-compose.yml` 转换为 Kubernetes 配置文件进行部署。

## 监控和日志

### 健康检查

各服务都配置了健康检查：
- Backend: `http://localhost:8502/`
- Agent: `http://localhost:8503/`
- Frontend: `http://localhost:8501/`

### 日志管理

```bash
# 查看实时日志
docker-compose logs -f --tail=100

# 导出日志
docker-compose logs > deployment.log
```

## 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建和部署
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 支持

如果遇到问题，请检查：
1. Docker 和 Docker Compose 是否正确安装
2. 环境配置文件是否正确设置
3. 网络连接是否正常
4. API Key 是否有效
