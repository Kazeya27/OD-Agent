## 部署技术文档（本地、Docker、生产环境）

本指南整合现有 `DEPLOYMENT_SUMMARY.md`、`DOCKER_DEPLOYMENT.md` 与脚本，提供一站式部署说明。

### 组件与默认端口
- Frontend（Streamlit）：8501
- Backend（FastAPI）：8502
- Agent（HTTP 服务）：8503
- Nginx（可选，生产反代）：80/443

---

### 一、快速开始
- 最快方式：
```bash
./quick-deploy.sh
```
- 开发环境编排：
```bash
docker-compose up -d --build
```
- 生产环境编排（含 Nginx）：
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

---

### 二、环境变量
创建 `.env`（或复制 `env.example`）：
```bash
# LLM / Agent 配置
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key_here
LLM_MODEL=gemini-2.5-flash-preview-05-20
LLM_TEMPERATURE=0.6

# 端口可自定义
BACKEND_PORT=8502
AGENT_PORT=8503
FRONTEND_PORT=8501

# 后端数据库（容器内路径）
DB_PATH=/app/agent/backend/geo_points.db
TABLE_PLACES=places
TABLE_RELATIONS=relations
TABLE_DYNA=dyna
```

前端需能访问 Agent：
- Docker Compose 内：`AGENT_SERVICE_URL=http://agent:8503`
- 本地开发：`AGENT_SERVICE_URL=http://127.0.0.1:8503`

---

### 三、本地开发部署（非 Docker）
1) 启动后端（FastAPI）
```bash
cd agent/backend
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8502 --reload
```
2) 启动 Agent 服务
```bash
cd agent/agent
pip install -r requirements.txt
# 参考项目内文档/脚本启动 agent_service.py（需配置后端地址与 API Key）
python agent_service.py
```
3) 启动前端（Streamlit）
```bash
cd frontend
pip install -r requirements.txt
export AGENT_SERVICE_URL=http://127.0.0.1:8503
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

---

### 四、Docker 开发环境
- 文件：`docker-compose.yml`
- 特性：热更新、端口映射、本地卷挂载

常用命令：
```bash
docker-compose up -d --build
docker-compose ps
docker-compose logs -f --tail=100
docker-compose restart
docker-compose down
```

访问：
- 前端：`http://localhost:8501`
- 后端：`http://localhost:8502/docs`
- Agent：`http://localhost:8503`

---

### 五、生产环境部署
- 文件：`docker-compose.prod.yml`、`nginx.conf`、`deploy-prod.sh`
- 特性：资源限制、健康检查、数据卷、自动重启、Nginx 反向代理

一键部署：
```bash
./deploy-prod.sh
```

Nginx 反代（摘要）：
- `/` -> Frontend（Streamlit）
- `/api` -> Backend（FastAPI）
- `/agent` -> Agent 服务

健康检查端点：
- Backend：`GET /`
- Agent：`GET /`
- Frontend：`GET /`

---

### 六、数据持久化与日志
- 开发环境：挂载宿主机目录，便于调试
- 生产环境：使用 Docker 卷，建议开启日志轮转

导出日志：
```bash
docker-compose logs > deployment.log
```

---

### 七、常见问题与排错
1) 端口冲突：检查宿主机端口占用（lsof/netstat）
2) API Key 无效：确认 `.env` 与容器环境一致
3) 服务启动失败：`docker-compose logs -f` 查看错误
4) 网络不可达：检查 `docker network` 与服务名称解析
5) 前端无法连 Agent：确认 `AGENT_SERVICE_URL` 指向可达地址

调试命令：
```bash
docker-compose exec backend bash
docker-compose exec agent bash
docker-compose exec frontend bash

docker network ls
docker network inspect od-agent_od-network
```

---

### 八、发布与升级建议
- 使用标签化镜像并记录变更
- 滚动重启：`docker-compose up -d --no-deps --build <service>`
- 配置健康检查与自动重启策略（已在 prod 编排中体现）
- 加固安全：启用 SSL、限制暴露端口、环境变量管理
