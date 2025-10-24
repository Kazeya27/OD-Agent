#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OD Agent Tools - 工具函数定义."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from langchain.tools import tool
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE / ".env")
load_dotenv(_HERE.parent / "backend" / ".env")

_BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8502").rstrip("/")
_SESSION = requests.Session()


def set_base_url(url: str) -> None:
    """Override backend base URL."""
    global _BASE_URL
    _BASE_URL = url.rstrip("/")


def _url(path: str) -> str:
    return f"{_BASE_URL}{path}"


def _serialize_response(resp: requests.Response) -> str:
    try:
        return json.dumps(resp.json(), ensure_ascii=False)
    except ValueError:
        return resp.text


def _safe_get(path: str, params: Dict[str, Any], timeout: int = 60) -> str:
    try:
        resp = _SESSION.get(_url(path), params=params, timeout=timeout)
        resp.raise_for_status()
        return _serialize_response(resp)
    except Exception as exc:
        return json.dumps({"error": f"GET {path} failed: {exc}"}, ensure_ascii=False)


def _safe_post(path: str, payload: Dict[str, Any], timeout: int = 120) -> str:
    try:
        resp = _SESSION.post(_url(path), json=payload, timeout=timeout)
        resp.raise_for_status()
        return _serialize_response(resp)
    except Exception as exc:
        return json.dumps({"error": f"POST {path} failed: {exc}"}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool input schemas
# ---------------------------------------------------------------------------


class GeoIdArgs(BaseModel):
    name: str = Field(..., description="城市中文名，例如：拉萨、昆明")


class RelationsMatrixArgs(BaseModel):
    fill: Optional[str] = Field(
        default="nan", description="缺失值填充值：'nan' 或 '0' 等字符串"
    )


class ODTensorArgs(BaseModel):
    start: str = Field(..., description="起始时间 ISO8601，如 2022-01-11T00:00:00Z")
    end: str = Field(..., description="结束时间 ISO8601（半开区间）")
    geo_ids: Optional[str] = Field(
        ..., description="获取指定geo_ids间的OD（逗号分隔，如 '1,2,3'）"
    )
    flow_policy: Optional[str] = Field(
        default="zero", description="缺失策略：zero|null|skip"
    )


class PairODArgs(ODTensorArgs):
    start: str = Field(..., description="起始时间 ISO8601，如 2022-01-11T00:00:00Z")
    end: str = Field(..., description="结束时间 ISO8601（半开区间）")
    origin_id: int = Field(..., description="起点 geo_id")
    destination_id: int = Field(..., description="终点 geo_id")
    flow_policy: Optional[str] = Field(
        default="zero", description="缺失策略：zero|null|skip"
    )


class PredictArgs(BaseModel):
    start: str = Field(..., description="起始时间 ISO8601，如 2022-01-11T00:00:00Z")
    end: str = Field(..., description="结束时间 ISO8601（半开区间）")
    geo_ids: Optional[str] = Field(
        ..., description="仅获取指定geo_ids间的OD（逗号分隔，如 '1,2,3'）"
    )
    flow_policy: Optional[str] = Field(
        default="zero", description="缺失策略：zero|null|skip"
    )


class PredictPairArgs(PredictArgs):
    start: str = Field(..., description="起始时间 ISO8601，如 2022-01-11T00:00:00Z")
    end: str = Field(..., description="结束时间 ISO8601（半开区间）")
    origin_id: int = Field(..., description="起点 geo_id")
    destination_id: int = Field(..., description="终点 geo_id")
    flow_policy: Optional[str] = Field(
        default="zero", description="缺失策略：zero|null|skip"
    )


class GrowthArgs(BaseModel):
    a: float = Field(..., description="数值a")
    b: float = Field(..., description="数值b")
    safe: bool = Field(default=True, description="安全模式，避免除零错误")


class MetricsArgs(BaseModel):
    y_true: Any = Field(..., description="真实值列表")
    y_pred: Any = Field(..., description="预测值列表")


class ProvinceFlowArgs(BaseModel):
    start: str = Field(..., description="起始时间 ISO8601")
    end: str = Field(..., description="结束时间 ISO8601")
    date_mode: str = Field(default="daily", description="时间维度：daily|total")
    direction: str = Field(default="send", description="方向：send|receive")


class CityFlowArgs(BaseModel):
    start: str = Field(..., description="起始时间 ISO8601")
    end: str = Field(..., description="结束时间 ISO8601")
    date_mode: str = Field(default="daily", description="时间维度：daily|total")
    direction: str = Field(default="send", description="方向：send|receive")


class ProvinceCorridorArgs(BaseModel):
    start: str = Field(..., description="起始时间 ISO8601")
    end: str = Field(..., description="结束时间 ISO8601")
    date_mode: str = Field(default="total", description="时间维度，推荐total")
    topk: int = Field(default=10, description="返回Top K条通道")


class CityCorridorArgs(BaseModel):
    start: str = Field(..., description="起始时间 ISO8601")
    end: str = Field(..., description="结束时间 ISO8601")
    date_mode: str = Field(default="total", description="时间维度，推荐total")
    topk_intra: int = Field(default=10, description="省内通道数量")
    topk_inter: int = Field(default=30, description="省际通道数量")


# ---------------------------------------------------------------------------
# Tools wrapping backend endpoints
# ---------------------------------------------------------------------------


@tool("get_geo_id", args_schema=GeoIdArgs)
def get_geo_id_tool(name: str) -> str:
    """根据地名查询 geo_id"""
    return _safe_get("/geo-id", {"name": name}, timeout=30)


@tool("get_relations_matrix", args_schema=RelationsMatrixArgs)
def get_relations_matrix_tool(fill: Optional[str] = "nan") -> str:
    """获取不同城市间的关系矩阵"""
    params: Dict[str, Any] = {}
    if fill is not None:
        params["fill"] = str(fill)
    return _safe_get("/relations/matrix", params, timeout=60)


@tool("get_od_tensor", args_schema=ODTensorArgs)
def get_od_tensor_tool(
    start: str,
    end: str,
    geo_ids: Optional[str] = None,
    flow_policy: Optional[str] = "zero",
) -> str:
    """给定时间范围和所有预测地点的geo_id，返回所有预测地点间的OD**真实值**"""
    params: Dict[str, Any] = {"start": start, "end": end}
    params["dyna_type"] = "state"
    params["geo_ids"] = geo_ids
    if flow_policy:
        params["flow_policy"] = flow_policy
    return _safe_get("/od", params, timeout=180)


@tool("get_pair_od", args_schema=PairODArgs)
def get_pair_od_tool(
    start: str,
    end: str,
    origin_id: int,
    destination_id: int,
    flow_policy: Optional[str] = "zero",
) -> str:
    """获取指定时间段内，指定 O/D 对的时间序列**真实值**"""
    params: Dict[str, Any] = {
        "start": start,
        "end": end,
        "origin_id": origin_id,
        "destination_id": destination_id,
    }
    params["dyna_type"] = "state"
    if flow_policy:
        params["flow_policy"] = flow_policy
    return _safe_get("/od/pair", params, timeout=120)


@tool("predict_od", args_schema=PredictArgs)
def predict_od_tool(
    start: str,
    end: str,
    geo_ids: Optional[str] = None,
    flow_policy: Optional[str] = "zero",
) -> str:
    """给定时间范围和所有预测地点的geo_id，返回所有预测地点间的OD**预测值**"""
    params: Dict[str, Any] = {"start": start, "end": end}
    params["dyna_type"] = "state"
    params["geo_ids"] = geo_ids
    if flow_policy:
        params["flow_policy"] = flow_policy
    return _safe_get("/predict", params, timeout=120)


@tool("predict_pair_od", args_schema=PredictPairArgs)
def predict_pair_od_tool(
    start: str,
    end: str,
    origin_id: int,
    destination_id: int,
    flow_policy: Optional[str] = "zero",
) -> str:
    """获取指定时间段内，指定 O/D 对的时间序列**预测值**"""
    params: Dict[str, Any] = {
        "start": start,
        "end": end,
        "origin_id": origin_id,
        "destination_id": destination_id,
    }
    params["dyna_type"] = "state"
    if flow_policy:
        params["flow_policy"] = flow_policy
    return _safe_get("/predict/pair", params, timeout=120)


@tool("growth_rate", args_schema=GrowthArgs)
def growth_rate_tool(a: float, b: float, safe: bool = True) -> str:
    """计算增长率（POST /growth）"""
    payload = {"a": a, "b": b, "safe": safe}
    return _safe_post("/growth", payload, timeout=30)


@tool("calc_metrics", args_schema=MetricsArgs)
def calc_metrics_tool(y_true: Any, y_pred: Any) -> str:
    """计算 RMSE/MAE/MAPE（POST /metrics）"""
    payload = {"y_true": y_true, "y_pred": y_pred}
    return _safe_post("/metrics", payload, timeout=60)


@tool("analyze_province_flow", args_schema=ProvinceFlowArgs)
def analyze_province_flow_tool(
    start: str,
    end: str,
    date_mode: str = "daily",
    direction: str = "send",
) -> str:
    """分析省级人员流动强度，按序返回所有省份的OD流量"""
    payload: Dict[str, Any] = {
        "period_type": "11",
        "start": start,
        "end": end,
        "date_mode": date_mode,
        "direction": direction,
        "dyna_type": "state",
    }
    return _safe_post("/analyze/province-flow", payload, timeout=180)


@tool("analyze_city_flow", args_schema=CityFlowArgs)
def analyze_city_flow_tool(
    start: str,
    end: str,
    date_mode: str = "daily",
    direction: str = "send",
) -> str:
    """返回城市级人员流动强度，即按序返回所有城市的OD流量"""
    payload: Dict[str, Any] = {
        "period_type": "period_type",
        "start": start,
        "end": end,
        "date_mode": date_mode,
        "direction": direction,
        "dyna_type": "state",
    }
    return _safe_post("/analyze/city-flow", payload, timeout=180)


@tool("analyze_province_corridor", args_schema=ProvinceCorridorArgs)
def analyze_province_corridor_tool(
    start: str,
    end: str,
    date_mode: str = "total",
    topk: int = 10,
) -> str:
    """返回指定时期内省际间的topk条人员流动通道"""
    payload: Dict[str, Any] = {
        "period_type": "period_type",
        "start": start,
        "end": end,
        "date_mode": date_mode,
        "topk": topk,
        "dyna_type": "state",
    }
    return _safe_post("/analyze/province-corridor", payload, timeout=180)


@tool("analyze_city_corridor", args_schema=CityCorridorArgs)
def analyze_city_corridor_tool(
    start: str,
    end: str,
    date_mode: str = "total",
    topk_intra: int = 10,
    topk_inter: int = 30,
) -> str:
    """分析城市间TOP K条人员流动通道，分别返回省内和省际通道"""
    payload: Dict[str, Any] = {
        "period_type": "period_type",
        "start": start,
        "end": end,
        "date_mode": date_mode,
        "topk_intra": topk_intra,
        "topk_inter": topk_inter,
        "dyna_type": "state",
    }
    return _safe_post("/analyze/city-corridor", payload, timeout=180)


# ---------------------------------------------------------------------------
# Tool list and error handling
# ---------------------------------------------------------------------------

TOOLS = [
    get_geo_id_tool,
    # get_pair_od_tool,
    # predict_pair_od_tool,
    get_relations_matrix_tool,
    get_od_tensor_tool,
    predict_od_tool,
    growth_rate_tool,
    calc_metrics_tool,
    analyze_province_flow_tool,
    analyze_city_flow_tool,
    analyze_province_corridor_tool,
    analyze_city_corridor_tool,
]


def _make_tool_error_handler(tool_name: str):
    def _handler(error: Exception) -> str:
        return (
            f"工具 `{tool_name}` 调用失败: {error}. "
            "请根据错误提示检查参数或选择其他工具重试。"
        )

    return _handler


# Apply error handlers to all tools
for _tool in TOOLS:
    _tool.handle_tool_error = _make_tool_error_handler(_tool.name)
