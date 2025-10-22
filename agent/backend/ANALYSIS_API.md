# Analysis API 接口文档

## 概述

本文档描述了 OD-Agent 系统中的人员流动分析相关接口，包括省级和城市级的流动强度分析、省际和城市间通道分析等功能。

**基础 URL**: `http://localhost:8502` (默认)

**Content-Type**: `application/json`

---

## 接口列表

### 1. 省级人员流动分析

分析指定时期内各省的人员流动强度和排名。

#### 接口信息

- **路径**: `/analyze/province-flow`
- **方法**: `POST`
- **描述**: 分析省级人员流动强度，支持日常分析和春运预测，可按日或总量统计，可选发送或到达维度

#### 请求参数

**Request Body** (JSON):

```json
{
  "period_type": "string",          // 必填，时期类型，如 "daily"（日常）、"2025_spring_festival"（26年春运）等
  "start": "string",                // 必填，起始时间（ISO8601格式），如 "2022-01-11T00:00:00Z"
  "end": "string",                  // 必填，结束时间（ISO8601格式，不包含该时刻）
  "date_mode": "daily" | "total",   // 可选，时间维度，默认 "daily"
                                    // "daily": 每日统计
                                    // "total": 时期总量统计
  "direction": "send" | "arrive",   // 可选，计算维度，默认 "send"
                                    // "send": 发送（流出）
                                    // "arrive": 到达（流入）
  "dyna_type": "string" | null      // 可选，按 dyna.type 过滤，默认 null（不过滤）
}
```

#### 响应格式

**成功响应** (200 OK):

```json
{
  "period_type": "string",          // 时期类型
  "date_mode": "string",            // 时间维度
  "direction": "string",            // 计算维度
  "total_records": 0,               // 记录总数
  "data": [
    {
      "province": "string",         // 省份名称
      "date": "string" | null,      // 日期（date_mode="daily"时有值）
      "flow": 0.0,                  // 流动强度/规模
      "rank": 1                     // 排名（1为最高）
    }
  ]
}
```

**错误响应** (500):

```json
{
  "detail": "分析失败: {错误信息}"
}
```

#### 调用示例

**示例 1: 查询2025春运期间各省流出总量排名**

```bash
curl -X POST "http://localhost:8502/analyze/province-flow" \
  -H "Content-Type: application/json" \
  -d '{
    "period_type": "2025_spring_festival",
    "start": "2025-01-10T00:00:00Z",
    "end": "2025-02-17T00:00:00Z",
    "date_mode": "total",
    "direction": "send"
  }'
```

**示例 2: 查询日常每日各省流入量**

```bash
curl -X POST "http://localhost:8502/analyze/province-flow" \
  -H "Content-Type: application/json" \
  -d '{
    "period_type": "daily",
    "start": "2025-10-01T00:00:00Z",
    "end": "2025-10-02T00:00:00Z",
    "date_mode": "daily",
    "direction": "arrive"
  }'
```

---

### 2. 城市级人员流动分析

分析指定时期内各城市的人员流动强度和排名。

#### 接口信息

- **路径**: `/analyze/city-flow`
- **方法**: `POST`
- **描述**: 分析城市级人员流动强度和排名

#### 请求参数

**Request Body** (JSON):

```json
{
  "period_type": "string",          // 必填，时期类型
  "start": "string",                // 必填，起始时间（ISO8601格式）
  "end": "string",                  // 必填，结束时间（ISO8601格式）
  "date_mode": "daily" | "total",   // 可选，时间维度，默认 "daily"
  "direction": "send" | "arrive",   // 可选，计算维度，默认 "send"
  "dyna_type": "string" | null      // 可选，按 dyna.type 过滤
}
```

#### 响应格式

**成功响应** (200 OK):

```json
{
  "period_type": "string",
  "date_mode": "string",
  "direction": "string",
  "total_records": 0,
  "data": [
    {
      "city": "string",             // 城市名称
      "date": "string" | null,      // 日期（date_mode="daily"时有值）
      "flow": 0.0,                  // 流动强度/规模
      "rank": 1                     // 排名
    }
  ]
}
```

#### 调用示例

```bash
curl -X POST "http://localhost:8502/analyze/city-flow" \
  -H "Content-Type: application/json" \
  -d '{
    "period_type": "2025_spring_festival",
    "start": "2025-01-10T00:00:00Z",
    "end": "2025-02-17T00:00:00Z",
    "date_mode": "total",
    "direction": "send"
  }'
```

---

### 3. 省际通道分析

分析指定时期内省际间的主要人员流动通道（OD对）。

#### 接口信息

- **路径**: `/analyze/province-corridor`
- **方法**: `POST`
- **描述**: 分析省际间TOP K条人员流动通道

#### 请求参数

**Request Body** (JSON):

```json
{
  "period_type": "string",          // 必填，时期类型
  "start": "string",                // 必填，起始时间（ISO8601格式）
  "end": "string",                  // 必填，结束时间（ISO8601格式）
  "date_mode": "daily" | "total",   // 可选，时间维度，默认 "total"（建议使用 "total"）
  "topk": 10,                       // 可选，返回TOP K条通道，默认 10
  "dyna_type": "string" | null      // 可选，按 dyna.type 过滤
}
```

#### 响应格式

**成功响应** (200 OK):

```json
{
  "period_type": "string",
  "date_mode": "string",
  "topk": 10,
  "total_records": 0,
  "data": [
    {
      "send_province": "string",    // 发送省份
      "arrive_province": "string",  // 到达省份
      "flow": 0.0,                  // 流量强度
      "rank": 1                     // 排名
    }
  ]
}
```

#### 调用示例

```bash
curl -X POST "http://localhost:8502/analyze/province-corridor" \
  -H "Content-Type: application/json" \
  -d '{
    "period_type": "2025_spring_festival",
    "start": "2025-01-10T00:00:00Z",
    "end": "2025-02-17T00:00:00Z",
    "date_mode": "total",
    "topk": 20
  }'
```

---

### 4. 城市通道分析

分析指定时期内城市间的主要人员流动通道，区分省内通道和省际通道。

#### 接口信息

- **路径**: `/analyze/city-corridor`
- **方法**: `POST`
- **描述**: 分析城市间TOP K条人员流动通道，分别返回省内和省际通道

#### 请求参数

**Request Body** (JSON):

```json
{
  "period_type": "string",          // 必填，时期类型
  "start": "string",                // 必填，起始时间（ISO8601格式）
  "end": "string",                  // 必填，结束时间（ISO8601格式）
  "date_mode": "daily" | "total",   // 可选，时间维度，默认 "total"
  "topk_intra": 10,                 // 可选，省内通道TOP K，默认 10
  "topk_inter": 30,                 // 可选，省际通道TOP K，默认 30
  "dyna_type": "string" | null      // 可选，按 dyna.type 过滤
}
```

#### 响应格式

**成功响应** (200 OK):

```json
{
  "period_type": "string",
  "date_mode": "string",
  "topk_intra": 10,
  "topk_inter": 30,
  "intra_province": [               // 省内通道列表
    {
      "send_city": "string",        // 发送城市
      "arrive_city": "string",      // 到达城市
      "flow": 0.0,                  // 流量强度
      "rank": 1,                    // 排名
      "corridor_type": "intra_province"
    }
  ],
  "inter_province": [               // 省际通道列表
    {
      "send_city": "string",
      "arrive_city": "string",
      "flow": 0.0,
      "rank": 1,
      "corridor_type": "inter_province"
    }
  ]
}
```

#### 调用示例

```bash
curl -X POST "http://localhost:8502/analyze/city-corridor" \
  -H "Content-Type: application/json" \
  -d '{
    "period_type": "2025_spring_festival",
    "start": "2025-01-10T00:00:00Z",
    "end": "2025-02-17T00:00:00Z",
    "date_mode": "total",
    "topk_intra": 15,
    "topk_inter": 40
  }'
```

---

## 通用说明

### 时间格式

所有时间参数使用 **ISO8601** 格式，建议使用 UTC 时区：
- 格式：`YYYY-MM-DDTHH:MM:SSZ`
- 示例：`2025-01-10T00:00:00Z`
- 说明：`end` 时间点不包含在查询范围内（左闭右开区间）

### 时期类型 (period_type)

常见的时期类型包括：
- `"daily"`: 日常时期
- `"2025_spring_festival"`: 2025年春运时期
- `"2025_national_day"`: 2025年国庆时期
- 其他自定义时期类型

### 时间维度 (date_mode)

- `"daily"`: 按日统计，返回每天的数据，`data` 中的记录会包含 `date` 字段
- `"total"`: 按时期总量统计，返回整个时期的汇总数据，`data` 中的 `date` 字段为 `null`

### 计算维度 (direction)

- `"send"`: 发送维度，计算流出量（如某省/城市向外输出的人员数量）
- `"arrive"`: 到达维度，计算流入量（如某省/城市接收的人员数量）

### 数据过滤 (dyna_type)

- 可选参数，用于按动态数据类型进行过滤
- 如果为 `null` 或不提供，则不进行过滤
- 具体可用的 `dyna_type` 值取决于数据库中的实际数据

### 错误处理

所有接口在发生错误时返回 HTTP 500 状态码，响应体格式如下：

```json
{
  "detail": "分析失败: {具体错误信息}"
}
```

---

## Agent 调用建议

### 1. 基本流程

```python
import requests
import json

# 基础配置
BASE_URL = "http://localhost:8502"

# 调用示例
def analyze_province_flow(period_type, start, end, **kwargs):
    """省级流动分析"""
    url = f"{BASE_URL}/analyze/province-flow"
    payload = {
        "period_type": period_type,
        "start": start,
        "end": end,
        **kwargs
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

# 使用
result = analyze_province_flow(
    period_type="2025_spring_festival",
    start="2025-01-10T00:00:00Z",
    end="2025-02-17T00:00:00Z",
    date_mode="total",
    direction="send"
)
```

### 2. 常见查询场景

#### 场景 1: 春运省级流出排名

```python
# 查询2025年春运期间各省流出人员总量排名
result = analyze_province_flow(
    period_type="2025_spring_festival",
    start="2025-01-10T00:00:00Z",
    end="2025-02-17T00:00:00Z",
    date_mode="total",
    direction="send"
)

# 获取TOP 10
top_10 = [r for r in result['data'] if r['rank'] <= 10]
```

#### 场景 2: 节假日主要通道

```python
# 查询国庆期间TOP 20省际通道
result = requests.post(
    f"{BASE_URL}/analyze/province-corridor",
    json={
        "period_type": "2025_national_day",
        "start": "2025-10-01T00:00:00Z",
        "end": "2025-10-08T00:00:00Z",
        "date_mode": "total",
        "topk": 20
    }
).json()
```

#### 场景 3: 城市每日流动趋势

```python
# 查询一周内城市每日流动情况
result = requests.post(
    f"{BASE_URL}/analyze/city-flow",
    json={
        "period_type": "daily",
        "start": "2025-10-01T00:00:00Z",
        "end": "2025-10-08T00:00:00Z",
        "date_mode": "daily",
        "direction": "send"
    }
).json()

# 按日期分组
from collections import defaultdict
by_date = defaultdict(list)
for record in result['data']:
    by_date[record['date']].append(record)
```

### 3. 错误处理建议

```python
import requests
from requests.exceptions import RequestException

def safe_api_call(url, payload):
    """带错误处理的API调用"""
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        print(f"API调用失败: {e}")
        return None
    except json.JSONDecodeError:
        print("响应解析失败")
        return None
```

### 4. 批量查询优化

```python
from concurrent.futures import ThreadPoolExecutor
import requests

def batch_query(queries):
    """并发批量查询"""
    def query_one(q):
        return requests.post(f"{BASE_URL}{q['endpoint']}", json=q['payload']).json()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(query_one, queries))
    
    return results

# 使用示例
queries = [
    {
        "endpoint": "/analyze/province-flow",
        "payload": {"period_type": "daily", "start": "2025-10-01T00:00:00Z", "end": "2025-10-02T00:00:00Z"}
    },
    {
        "endpoint": "/analyze/city-flow",
        "payload": {"period_type": "daily", "start": "2025-10-01T00:00:00Z", "end": "2025-10-02T00:00:00Z"}
    }
]

results = batch_query(queries)
```

---

## 附录

### 完整的 Python Agent 示例

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OD-Agent Analysis API Client
"""

import requests
from typing import Optional, Dict, Any, List
from datetime import datetime


class AnalysisAPIClient:
    """分析API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8502"):
        self.base_url = base_url.rstrip('/')
    
    def province_flow(
        self,
        period_type: str,
        start: str,
        end: str,
        date_mode: str = "daily",
        direction: str = "send",
        dyna_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """省级人员流动分析"""
        url = f"{self.base_url}/analyze/province-flow"
        payload = {
            "period_type": period_type,
            "start": start,
            "end": end,
            "date_mode": date_mode,
            "direction": direction,
            "dyna_type": dyna_type
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def city_flow(
        self,
        period_type: str,
        start: str,
        end: str,
        date_mode: str = "daily",
        direction: str = "send",
        dyna_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """城市人员流动分析"""
        url = f"{self.base_url}/analyze/city-flow"
        payload = {
            "period_type": period_type,
            "start": start,
            "end": end,
            "date_mode": date_mode,
            "direction": direction,
            "dyna_type": dyna_type
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def province_corridor(
        self,
        period_type: str,
        start: str,
        end: str,
        date_mode: str = "total",
        topk: int = 10,
        dyna_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """省际通道分析"""
        url = f"{self.base_url}/analyze/province-corridor"
        payload = {
            "period_type": period_type,
            "start": start,
            "end": end,
            "date_mode": date_mode,
            "topk": topk,
            "dyna_type": dyna_type
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def city_corridor(
        self,
        period_type: str,
        start: str,
        end: str,
        date_mode: str = "total",
        topk_intra: int = 10,
        topk_inter: int = 30,
        dyna_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """城市通道分析"""
        url = f"{self.base_url}/analyze/city-corridor"
        payload = {
            "period_type": period_type,
            "start": start,
            "end": end,
            "date_mode": date_mode,
            "topk_intra": topk_intra,
            "topk_inter": topk_inter,
            "dyna_type": dyna_type
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()


# 使用示例
if __name__ == "__main__":
    client = AnalysisAPIClient()
    
    # 查询2025春运省级流出排名
    result = client.province_flow(
        period_type="2025_spring_festival",
        start="2025-01-10T00:00:00Z",
        end="2025-02-17T00:00:00Z",
        date_mode="total",
        direction="send"
    )
    
    print(f"总记录数: {result['total_records']}")
    print(f"TOP 5 省份:")
    for record in result['data'][:5]:
        print(f"  {record['rank']}. {record['province']}: {record['flow']:.2f}")
```

---

## 更新日志

- **2025-10-20**: 初始版本，包含4个分析接口的完整文档

