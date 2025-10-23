# OD Agent Service API 文档

这是一个基于 FastAPI 的 OD 智能问答服务，提供对话接口和历史记录查询功能。

## 功能特性

- ✅ 基于 session_id 的会话管理
- ✅ 聊天记录持久化（JSON 格式）
- ✅ 记录用户消息、助手回复、函数调用和函数响应
- ✅ RESTful API 接口

## 安装依赖

```bash
pip install fastapi uvicorn langchain==0.3.27 langchain-community==0.3.31 langchain-google-genai==2.1.12 python-dotenv pydantic requests
```

## 配置

在 `agent/agent/.env` 或 `agent/backend/.env` 中配置以下环境变量：

```env
# LLM 配置
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash-preview-05-20
LLM_TEMPERATURE=0.6

# 后端服务地址
BASE_URL=http://127.0.0.1:8502

# Agent 服务端口
AGENT_PORT=8503

# Google API Key (for Gemini)
GOOGLE_API_KEY=your_api_key_here
```

## 启动服务

```bash
cd agent/agent
python agent_service.py
```

服务将在 `http://0.0.0.0:8503` 启动。

## API 接口

### 1. 健康检查

**GET** `/`

**响应示例：**
```json
{
  "ok": true,
  "service": "OD Agent Service",
  "version": "1.0.0"
}
```

### 2. 聊天接口

**POST** `/chat`

向 Agent 发送问题并获取回答。

**请求体：**
```json
{
  "session_id": "user-123",
  "question": "查询北京到上海的人员流动情况"
}
```

**响应示例：**
```json
{
  "session_id": "user-123",
  "answer": "根据查询结果...",
  "timestamp": "2025-10-22T12:00:00.123456"
}
```

**cURL 示例：**
```bash
curl -X POST "http://localhost:8503/chat" \
  -H "Content-Type: application/json" \
  -d \'{"session_id": "user-123", "question": "你好"}\'  
```

### 3. 获取聊天历史

**POST** `/history`

获取指定会话的所有聊天记录。

**请求体：**
```json
{
  "session_id": "user-123"
}
```

**响应示例：**
```json
{
  "session_id": "user-123",
  "messages": [
    {
      "time": "2025-10-22T12:00:00.123456",
      "from": "user",
      "content": "你好"
    },
    {
      "time": "2025-10-22T12:00:01.234567",
      "from": "function_call",
      "content": "{\"tool\": \"get_geo_id\", \"tool_input\": {\"name\": \"北京\"}}"
    },
    {
      "time": "2025-10-22T12:00:02.345678",
      "from": "function_response",
      "content": "{\"geo_id\": 1, \"name\": \"北京\"}"
    },
    {
      "time": "2025-10-22T12:00:03.456789",
      "from": "assistant",
      "content": "你好！我可以帮你查询人员流动相关数据。"
    }
  ]
}
```

**cURL 示例：**
```bash
curl -X POST "http://localhost:8503/history" \
  -H "Content-Type: application/json" \
  -d \'{"session_id": "user-123"}\'  
```

## 日志格式

聊天记录保存在 `agent/agent/chat_history/{session_id}.json`，格式如下：

```json
[
  {
    "time": "2025-10-22T12:00:00.123456",
    "from": "user",
    "content": "用户的问题"
  },
  {
    "time": "2025-10-22T12:00:01.234567",
    "from": "function_call",
    "content": "{\"tool\": \"tool_name\", \"tool_input\": {...}}"
  },
  {
    "time": "2025-10-22T12:00:02.345678",
    "from": "function_response",
    "content": "函数返回的结果"
  },
  {
    "time": "2025-10-22T12:00:03.456789",
    "from": "assistant",
    "content": "助手的回答"
  }
]
```

### from 字段说明

- `user`: 用户发送的消息
- `assistant`: AI 助手的回复
- `function_call`: Agent 调用的工具函数及参数
- `function_response`: 工具函数的返回结果

## 使用示例

### Python 客户端

```python
import requests

# 基础 URL
BASE_URL = "http://localhost:8503"

# 发送聊天消息
def chat(session_id: str, question: str):
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"session_id": session_id, "question": question}
    )
    return response.json()

# 获取历史记录
def get_history(session_id: str):
    response = requests.post(
        f"{BASE_URL}/history",
        json={"session_id": session_id}
    )
    return response.json()

# 使用示例
if __name__ == "__main__":
    session = "user-123"
    
    # 发送问题
    result = chat(session, "查询北京的geo_id")
    print("回答:", result["answer"])
    
    # 获取历史
    history = get_history(session)
    print(f"\n共有 {len(history[\'messages\'])} 条消息")
    for msg in history["messages"]:
        print(f"[{msg[\'from\']}] {msg[\'content\']}")
```

### JavaScript/TypeScript 客户端

```javascript
const BASE_URL = "http://localhost:8503";

// 发送聊天消息
async function chat(sessionId, question) {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, question })
  });
  return await response.json();
}

// 获取历史记录
async function getHistory(sessionId) {
  const response = await fetch(`${BASE_URL}/history`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId })
  });
  return await response.json();
}

// 使用示例
(async () => {
  const session = "user-123";
  
  // 发送问题
  const result = await chat(session, "查询北京的geo_id");
  console.log("回答:", result.answer);
  
  // 获取历史
  const history = await getHistory(session);
  console.log(`\n共有 ${history.messages.length} 条消息`);
  history.messages.forEach(msg => {
    console.log(`[${msg.from}] ${msg.content}`);
  });
})();
```

## 与现有 od_agent.py 的区别

| 特性 | od_agent.py (CLI) | agent_service.py (Service) |
|------|-------------------|---------------------------|
| 运行方式 | 命令行交互 | HTTP API 服务 |
| 会话管理 | 基于命令行参数 | 基于 session_id |
| 日志格式 | 文本文件 (.txt) | JSON 文件 (.json) |
| 日志结构 | 简单文本记录 | 结构化 (time/from/content) |
| 函数调用记录 | 仅在 verbose 模式输出 | 完整记录到 JSON |
| 前端集成 | 不支持 | 通过 REST API 集成 |

## 注意事项

1. **后端服务依赖**：Agent 服务依赖后端 API 服务 (默认 `http://127.0.0.1:8502`)，请确保后端服务已启动。

2. **API Key**：使用 Gemini 需要配置 `GOOGLE_API_KEY` 环境变量。

3. **会话隔离**：不同的 `session_id` 维护独立的对话上下文和历史记录。

4. **文件存储**：聊天记录存储在 `agent/agent/chat_history/` 目录，按 `{session_id}.json` 命名。

5. **并发安全**：使用线程锁保证多并发请求时的文件读写安全。

## 调试

启用 verbose 模式查看详细日志：

```bash
cd agent/agent
python agent_service.py
```

查看控制台输出的 Agent 执行过程和工具调用详情。