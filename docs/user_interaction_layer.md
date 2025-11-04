## 用户交互层技术文档（Streamlit 前端 + Agent 服务）

### 概览
- **前端应用**: `frontend/app.py`（Streamlit）
- **Agent 服务**: `agent/agent/agent_service.py`（HTTP 接口，默认端口 8503）
- **后端 API**: `agent/backend/app.py`（FastAPI，默认端口 8502）
- **环境变量**: 前端通过 `AGENT_SERVICE_URL` 调用 Agent

前端提供多会话聊天界面，用户输入自然语言问题，由 Agent 服务生成答案（可包含 Markdown/表格/图表代码块），前端渲染结果并持久化对话记录。

---

### 架构与数据流
1) 用户在 Streamlit 聊天输入框提交问题
2) 前端调用 Agent 服务 `POST /chat`，携带 `{ session_id, question }`
3) Agent 根据业务能力/工具链访问后端 API（如 OD 分析、指标计算）
4) Agent 返回文本答案（可能包含 Markdown）
5) 前端保存会话消息并渲染展示

时序简图（文字版）
- User -> Frontend: 输入问题
- Frontend -> Agent: POST /chat
- Agent -> Backend: 调用诸 API（如 /predict, /analyze/*）
- Agent -> Frontend: 答案文本
- Frontend -> Storage: 写入会话历史

---

### 关键模块与职责
- `frontend/app.py`
  - UI 布局与交互（侧边栏会话管理、示例问题、聊天窗口）
  - 与 Agent 服务交互：`call_agent_service()`、`call_agent_service_stream()`
  - 会话存储：`ChatStorage`（JSON 文件，目录 `frontend/chat_history/`）
  - 环境变量：`AGENT_SERVICE_URL`（默认 `http://127.0.0.1:8503`）
- `agent/agent/agent_service.py`
  - 暴露 `/chat` 等接口（详见项目内 API 文档）
  - 协调对 `agent/backend` 的调用，聚合分析结果
- `agent/backend/app.py`
  - FastAPI 路由聚合：`routes/` 目录下各模块（geo/relations/od/metrics/analysis）
  - 健康检查 `GET /`；OpenAPI 文档 `/docs`

---

### 前端交互细节
- 页面设置：`st.set_page_config(page_title="OD流量预测", page_icon="🚗", layout="wide")`
- 多会话：侧边栏支持创建、切换、删除会话；每个会话独立保存为 JSON
- 聊天：
  - 用户消息与 AI 消息以 `st.chat_message` 渲染
  - 生成中显示 `st.status` 状态提示
  - AI 内容以 `st.markdown` 渲染（支持 Markdown）
- 示例问题：`frontend/examples.py` 提供快捷问题按钮

---

### 配置与环境变量
- `AGENT_SERVICE_URL`：Agent 服务地址（前端使用）。示例：
  - 本地开发：`http://127.0.0.1:8503`
  - Docker Compose（同网络）：`http://agent:8503`
- `.env` 由 `python-dotenv` 自动加载

---

### 与后端 API 的接口约定
- Agent 侧会调用后端这些典型端点（见 `agent/backend/ANALYSIS_API.md` 与 `routes/`）：
  - `GET /geo-id`、`GET /relations/matrix`
  - `GET /od`、`GET /od/pair`
  - `POST /predict`、`POST /growth`、`POST /metrics`
  - `POST /analyze/province-flow`、`/analyze/city-flow`、`/analyze/province-corridor`、`/analyze/city-corridor`

---

### 本地运行（仅前端 + Agent）
```bash
# 1) 启动 Agent（确保已配置 API Key/后端地址等）
# 进入 agent/agent 目录（参考项目脚本/文档启动）

# 2) 启动前端
cd frontend
pip install -r requirements.txt
export AGENT_SERVICE_URL=http://127.0.0.1:8503
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```
访问：`http://localhost:8501`

---

### 错误处理与可用性
- 前端对 Agent 请求异常进行明确提示（超时、连接失败）
- 会话写入失败会返回错误消息并不中断 UI
- 健康检查：
  - 后端：`GET http://localhost:8502/`
  - Agent：`GET http://localhost:8503/`

---

