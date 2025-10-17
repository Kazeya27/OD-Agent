#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
from datetime import datetime
from typing import List, Optional, Any, Dict

import requests
from dotenv import load_dotenv

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables.history import RunnableWithMessageHistory

from langchain_google_genai import ChatGoogleGenerativeAI

# ------------------ 环境 & 代理 ------------------
load_dotenv()

# 可在命令行覆盖
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# 如需代理，取消注释并按需修改
os.environ["http_proxy"]  = "http://127.0.0.1:10808"
os.environ["https_proxy"] = "http://127.0.0.1:10808"

# ------------------ Pydantic 工具入参 schema ------------------

class GeoQuery(BaseModel):
    name: str = Field(description="城市中文名，例如：拉萨、那曲、昆明")

class RelationsMatrixArgs(BaseModel):
    fill: str = Field(default="nan", description="缺失填充值：'nan' 或数字字符串，如 '0'、'1e9'")

class ODTensorArgs(BaseModel):
    start: str = Field(description="起始时间 ISO8601，如 2022-01-11T00:00:00Z")
    end: str = Field(description="结束时间 ISO8601（半开区间），如 2022-01-19T00:00:00Z")
    dyna_type: Optional[str] = Field(default=None, description="dyna.type 过滤，如 state")
    flow_policy: Optional[str] = Field(default="zero", description="zero|null|skip，默认 zero")

class PairODArgs(ODTensorArgs):
    origin_id: int = Field(description="起点 geo_id")
    destination_id: int = Field(description="终点 geo_id")

class PredictArgs(BaseModel):
    history: Dict[str, Any] = Field(description="历史张量字典：{T,N,ids,tensor}")
    horizon: int = Field(description="预测步数 T2")
    method: str = Field(default="moving_average", description="预测方法：naive|moving_average")
    window: Optional[int] = Field(default=3, description="moving_average 的窗口大小")

class GrowthArgs(BaseModel):
    a: float = Field(description="基期数值")
    b: float = Field(description="对比期数值")
    safe: bool = Field(default=True, description="True 时 a=0 返回 null；False 时返回 +/-inf")

class MetricsArgs(BaseModel):
    y_true: Any = Field(description="真实值，可为标量/1D/2D/3D 列表（None/NaN 会被忽略）")
    y_pred: Any = Field(description="预测值，形状与 y_true 对齐")

# ------------------ 工具（全部通过 HTTP，带兜底） ------------------

def _http_get(path: str, params: dict, timeout=120) -> str:
    r = requests.get(f"{BASE_URL}{path}", params=params, timeout=timeout)
    r.raise_for_status()
    return r.text

def _http_post(path: str, payload: dict, timeout=120) -> str:
    r = requests.post(f"{BASE_URL}{path}", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.text

@tool("get_geo_id", args_schema=GeoQuery, return_direct=False)
def get_geo_id_tool(name: str) -> str:
    """
    根据地名获取 geo_id（HTTP: GET /geo-id）。
    入参示例：{"name":"拉萨"}
    """
    try:
        return _http_get("/geo-id", {"name": name}, timeout=30)
    except Exception as e:
        return json.dumps({"error": f"/geo-id request failed: {e}"}, ensure_ascii=False)

@tool("get_relations_matrix", args_schema=RelationsMatrixArgs, return_direct=False)
def get_relations_matrix_tool(fill: str = "nan") -> str:
    """
    获取关系矩阵 N×N（HTTP: GET /relations/matrix）。
    入参示例：{"fill":"0"}
    """
    try:
        return _http_get("/relations/matrix", {"fill": str(fill)}, timeout=60)
    except Exception as e:
        return json.dumps({"error": f"/relations/matrix failed: {e}"}, ensure_ascii=False)

@tool("get_od_demand", args_schema=ODTensorArgs, return_direct=False)
def get_od_demand_tool(start: str, end: str, dyna_type: Optional[str] = None,
                       flow_policy: Optional[str] = "zero") -> str:
    """
    获取时间段内的全量 OD 张量 [T,N,N]（HTTP: GET /od）。
    入参示例：{"start":"...Z","end":"...Z","dyna_type":"state","flow_policy":"zero"}
    """
    try:
        params = {"start": start, "end": end}
        if dyna_type: params["dyna_type"] = dyna_type
        if flow_policy: params["flow_policy"] = flow_policy
        return _http_get("/od", params, timeout=180)
    except Exception as e:
        return json.dumps({"error": f"/od failed: {e}"}, ensure_ascii=False)

@tool("get_pair_od", args_schema=PairODArgs, return_direct=False)
def get_pair_od_tool(start: str, end: str, origin_id: int, destination_id: int,
                     dyna_type: Optional[str] = None, flow_policy: Optional[str] = "zero") -> str:
    """
    获取指定 O/D 的时间序列（HTTP: GET /od/pair；若不可用则回退：/od + 本地筛选）。
    入参示例：{"start":"...Z","end":"...Z","origin_id":0,"destination_id":1,"dyna_type":"state","flow_policy":"zero"}
    """
    # 先试 /od/pair
    try:
        params = {
            "start": start, "end": end,
            "origin_id": origin_id, "destination_id": destination_id
        }
        if dyna_type: params["dyna_type"] = dyna_type
        if flow_policy: params["flow_policy"] = flow_policy
        r = requests.get(f"{BASE_URL}/od/pair", params=params, timeout=120)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass

    # 回退：/od + 客户端筛选
    try:
        od_params = {"start": start, "end": end}
        if dyna_type: od_params["dyna_type"] = dyna_type
        if flow_policy: od_params["flow_policy"] = flow_policy
        R = requests.get(f"{BASE_URL}/od", params=od_params, timeout=180)
        R.raise_for_status()
        data = R.json()
        T, ids, tensor, times = data.get("T", 0), data.get("ids", []), data.get("tensor", []), data.get("times", [])
        if T == 0:
            return json.dumps({"T": 0, "times": [], "origin_id": origin_id, "destination_id": destination_id, "series": []}, ensure_ascii=False)
        id2idx = {gid: i for i, gid in enumerate(ids)}
        if origin_id not in id2idx or destination_id not in id2idx:
            return json.dumps({"error": f"origin_id/destination_id not in ids: {origin_id},{destination_id}"}, ensure_ascii=False)
        i, j = id2idx[origin_id], id2idx[destination_id]
        series = [
            (tensor[t][i][j] if tensor[t][i][j] is not None else (0.0 if (flow_policy or "zero") == "zero" else None))
            for t in range(T)
        ]
        return json.dumps({"T": T, "times": times, "origin_id": origin_id, "destination_id": destination_id, "series": series}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"/od fallback failed: {e}"}, ensure_ascii=False)

@tool("predict_od", args_schema=PredictArgs, return_direct=False)
def predict_od_tool(history: Dict[str, Any], horizon: int, method: str = "moving_average", window: int = 3) -> str:
    """
    调用预测服务（HTTP: POST /predict；失败则本地 baseline 兜底）。
    入参示例：{"history":{...}, "horizon":12, "method":"moving_average", "window":3}
    """
    # 服务端
    payload = {"history": history, "horizon": horizon, "method": method, "window": window}
    try:
        return _http_post("/predict", payload, timeout=180)
    except Exception:
        pass

    # 兜底：naive / moving_average
    try:
        T1 = int(history["T"]); N = int(history["N"])
        ids = history["ids"]; tensor = history["tensor"]
        if T1 == 0 or horizon <= 0:
            return json.dumps({"T": 0, "N": N, "ids": ids, "tensor": []})
        if method == "naive":
            last = tensor[-1]
            pred = [last for _ in range(horizon)]
        else:  # moving_average
            w = max(1, min(int(window), T1))
            acc = [[0.0 for _ in range(N)] for _ in range(N)]
            for t in tensor[-w:]:
                for i in range(N):
                    for j in range(N):
                        v = t[i][j]
                        acc[i][j] += 0.0 if v is None else float(v)
            avg = [[acc[i][j]/w for j in range(N)] for i in range(N)]
            pred = [avg for _ in range(horizon)]
        return json.dumps({"T": horizon, "N": N, "ids": ids, "tensor": pred})
    except Exception as e:
        return json.dumps({"error": f"local fallback failed: {e}"}, ensure_ascii=False)

@tool("growth_rate", args_schema=GrowthArgs, return_direct=False)
def growth_rate_tool(a: float, b: float, safe: bool = True) -> str:
    """
    计算增长率（HTTP: POST /growth；失败则本地计算）。
    """
    try:
        return _http_post("/growth", {"a": a, "b": b, "safe": safe}, timeout=30)
    except Exception:
        pass
    # local
    import math
    if a == 0.0:
        return json.dumps({"growth": None if safe else (math.inf if b >= 0 else -math.inf)})
    return json.dumps({"growth": (b - a) / abs(a)})

@tool("metrics", args_schema=MetricsArgs, return_direct=False)
def metrics_tool(y_true: Any, y_pred: Any) -> str:
    """
    计算 RMSE/MAE/MAPE（HTTP: POST /metrics；失败则本地计算）。
    """
    try:
        return _http_post("/metrics", {"y_true": y_true, "y_pred": y_pred}, timeout=120)
    except Exception:
        pass

    # local
    import math
    def _flatten(v):
        if isinstance(v, (list, tuple)):
            for x in v: yield from _flatten(x)
        else:
            yield v
    yt = list(_flatten(y_true)); yp = list(_flatten(y_pred))
    if len(yt) != len(yp):
        return json.dumps({"error": "length mismatch between y_true and y_pred"})
    se = ae = ape_sum = 0.0
    n = n_mape = 0
    for a, b in zip(yt, yp):
        if a is None or b is None: continue
        a = float(a); b = float(b)
        if math.isnan(a) or math.isnan(b): continue
        se += (b - a) ** 2
        ae += abs(b - a)
        n += 1
        if a != 0.0:
            ape_sum += abs((b - a) / a)
            n_mape += 1
    if n == 0:
        return json.dumps({"error": "no valid numeric pairs"})
    rmse = (se / n) ** 0.5
    mae = ae / n
    mape = (ape_sum / n_mape) if n_mape > 0 else None
    return json.dumps({"rmse": rmse, "mae": mae, "mape": mape})

# ------------------ 会话记忆 & 工具集合 ------------------

store: Dict[str, ChatMessageHistory] = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

TOOLS = [
    get_geo_id_tool,
    get_relations_matrix_tool,
    get_od_demand_tool,
    get_pair_od_tool,
    predict_od_tool,
    growth_rate_tool,
    metrics_tool,
]

# ------------------ LLM 选择 ------------------

def get_llm(provider: str, model_name: str, temperature: float = 0.0):
    if provider == "gemini":
        # 强烈建议在 Windows/代理环境下强制 REST，避免 gRPC 卡住
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature, convert_system_message_to_human=True)
    raise ValueError(f"不支持的provider: {provider}")

# ------------------ Prompt & Agent ------------------

SYSTEM = (
    "你是一个 OD 需求分析与预测助手。只能通过提供的工具访问数据/服务，"
    "典型任务：根据城市名获取 geo_id，查询时间段内全体或指定 O/D 的出行需求，"
    "对历史 OD 进行预测，计算增长率与误差指标，并给出结构化、可复现的结论。\n"
    "注意：\n"
    "1) 如需 O/D 对的时间序列，优先使用 get_pair_od；\n"
    "2) 需要预测时先取历史张量作为 history，再调用 predict_od；\n"
    "3) 需要评估时调用 metrics；对比两个值使用 growth_rate；\n"
    "4) 工具入参请严格使用其 schema；时间区间为 [start, end)；\n"
    "5) 输出时给出关键数值与简明解释。"
)

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ]
)

# ------------------ 日志 ------------------

def log_to_file(lines: List[str]):
    ts = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    os.makedirs("./logs/", exist_ok=True)
    with open(f"./logs/{ts}.txt", "w", encoding="utf-8") as f:
        for l in lines:
            f.write(l + "\n")

# ------------------ CLI 主程序 ------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=str, default="gemini", choices=["openai", "gemini"])
    parser.add_argument("--model_name", type=str, default="gemini-2.5-flash-preview-05-20", help="LLM 模型名")
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--base_url", type=str, default="http://127.0.0.1:8000", help="覆盖 BASE_URL，如 http://127.0.0.1:8000")
    parser.add_argument("--session", type=str, default="<session-1>")
    args = parser.parse_args()

    if args.base_url:
        global BASE_URL
        BASE_URL = args.base_url.rstrip("/")

    # 默认模型
    if args.model_name is None:
        args.model_name = "gemini-1.5-flash" if args.provider == "gemini" else "gpt-3.5-turbo"

    llm = get_llm(args.provider, args.model_name, temperature=args.temperature)

    agent = create_tool_calling_agent(llm, TOOLS, PROMPT)
    executor = AgentExecutor(agent=agent, tools=TOOLS, verbose=True)
    agent_with_history = RunnableWithMessageHistory(
        executor, get_session_history, input_messages_key="input", history_messages_key="chat_history"
    )

    logs: List[str] = []
    cfg = {"configurable": {"session_id": args.session}}

    try:
        question = input("Q: ").strip()
        while question:
            resp = agent_with_history.invoke({"input": question}, config=cfg)
            output = resp["output"]
            print("\nA:", output, "\n")
            logs += [f"user: {question}", "-" * 40, f"AI: {output}", "-" * 40]
            question = input("Q: ").strip()
    finally:
        log_to_file(logs)

if __name__ == "__main__":
    main()
