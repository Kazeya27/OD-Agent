#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pydantic models for API requests and responses
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ----------------------- Enums -----------------------

class DateMode(str, Enum):
    """时间维度枚举"""
    daily = "daily"
    total = "total"


class Direction(str, Enum):
    """方向枚举"""
    send = "send"
    arrive = "arrive"


# ----------------------- Basic Models -----------------------

class GeoIdResponse(BaseModel):
    """地理ID查询响应"""
    geo_id: Optional[int] = None
    name: Optional[str] = None
    candidates: List[Dict[str, Any]] = []


class MatrixResponse(BaseModel):
    """关系矩阵响应"""
    N: int
    ids: List[int]
    matrix: List[List[Optional[float]]]


class TensorResponse(BaseModel):
    """OD张量响应"""
    T: int
    N: int
    times: List[str]
    ids: List[int]
    tensor: List[List[List[Optional[float]]]]


# ----------------------- Province Flow Models -----------------------

class ProvinceFlowRequest(BaseModel):
    """省级人员流动分析请求参数"""
    period_type: str = Field(..., description="时期类型：如 'daily'（日常）、'2026_spring_festival'（26年春运）等")
    start: str = Field(..., description="起始时间（ISO8601，如 2022-01-11T00:00:00Z）")
    end: str = Field(..., description="结束时间（ISO8601，不包含该时刻）")
    date_mode: DateMode = Field(default=DateMode.daily, description="时间维度：'daily'（每日）或 'total'（假期总量）")
    direction: Direction = Field(default=Direction.send, description="计算维度：'send'（发送）或 'arrive'（到达）")
    dyna_type: Optional[str] = Field(default=None, description="按 dyna.type 过滤（可选）")


class ProvinceFlowRecord(BaseModel):
    """单条省级流动记录"""
    province: str = Field(..., description="省份名称")
    date: Optional[str] = Field(None, description="日期（date_mode='daily'时有值，'total'时为空）")
    flow: float = Field(..., description="流动强度/规模")
    rank: int = Field(..., description="排名（1为最高）")


class ProvinceFlowResponse(BaseModel):
    """省级人员流动分析响应"""
    period_type: str
    date_mode: str
    direction: str
    total_records: int
    data: List[ProvinceFlowRecord]


# ----------------------- City Flow Models -----------------------

class CityFlowRequest(BaseModel):
    """城市人员流动分析请求参数"""
    period_type: str = Field(..., description="时期类型：如 'daily'（日常）、'2026_spring_festival'（26年春运）等")
    start: str = Field(..., description="起始时间（ISO8601）")
    end: str = Field(..., description="结束时间（ISO8601）")
    date_mode: DateMode = Field(default=DateMode.daily, description="时间维度：'daily'（每日）或 'total'（假期总量）")
    direction: Direction = Field(default=Direction.send, description="计算维度：'send'（发送）或 'arrive'（到达）")
    dyna_type: Optional[str] = Field(default=None, description="按 dyna.type 过滤（可选）")


class CityFlowRecord(BaseModel):
    """单条城市流动记录"""
    city: str = Field(..., description="城市名称")
    date: Optional[str] = Field(None, description="日期（date_mode='daily'时有值）")
    flow: float = Field(..., description="流动强度/规模")
    rank: int = Field(..., description="排名（1为最高）")


class CityFlowResponse(BaseModel):
    """城市人员流动分析响应"""
    period_type: str
    date_mode: str
    direction: str
    total_records: int
    data: List[CityFlowRecord]


# ----------------------- Corridor Models -----------------------

class ProvinceCorridorRequest(BaseModel):
    """省际通道分析请求参数"""
    period_type: str = Field(..., description="时期类型")
    start: str = Field(..., description="起始时间（ISO8601）")
    end: str = Field(..., description="结束时间（ISO8601）")
    date_mode: DateMode = Field(default=DateMode.total, description="时间维度（建议使用'total'）")
    topk: int = Field(default=10, description="返回TOP K条通道，默认10")
    dyna_type: Optional[str] = Field(default=None, description="按 dyna.type 过滤（可选）")


class CorridorRecord(BaseModel):
    """通道记录"""
    send_province: str = Field(..., description="发送省份")
    arrive_province: str = Field(..., description="到达省份")
    flow: float = Field(..., description="流量强度")
    rank: int = Field(..., description="排名")


class ProvinceCorridorResponse(BaseModel):
    """省际通道分析响应"""
    period_type: str
    date_mode: str
    topk: int
    total_records: int
    data: List[CorridorRecord]


class CityCorridorRequest(BaseModel):
    """城市通道分析请求参数"""
    period_type: str = Field(..., description="时期类型")
    start: str = Field(..., description="起始时间（ISO8601）")
    end: str = Field(..., description="结束时间（ISO8601）")
    date_mode: DateMode = Field(default=DateMode.total, description="时间维度（建议使用'total'）")
    topk_intra: int = Field(default=10, description="省内通道TOP K，默认10")
    topk_inter: int = Field(default=30, description="省际通道TOP K，默认30")
    dyna_type: Optional[str] = Field(default=None, description="按 dyna.type 过滤（可选）")


class CityCorridorRecord(BaseModel):
    """城市通道记录"""
    send_city: str = Field(..., description="发送城市")
    arrive_city: str = Field(..., description="到达城市")
    flow: float = Field(..., description="流量强度")
    rank: int = Field(..., description="排名")
    corridor_type: str = Field(..., description="通道类型：'intra_province'（省内）或 'inter_province'（省际）")


class CityCorridorResponse(BaseModel):
    """城市通道分析响应"""
    period_type: str
    date_mode: str
    topk_intra: int
    topk_inter: int
    intra_province: List[CityCorridorRecord] = Field(..., description="省内通道列表")
    inter_province: List[CityCorridorRecord] = Field(..., description="省际通道列表")

