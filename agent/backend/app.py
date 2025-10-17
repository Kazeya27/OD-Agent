#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI backend for a React agent over the geo SQLite database.

Endpoints:
  1) GET /geo-id?name=拉萨
     -> { "geo_id": 0, "name": "拉萨", "candidates": [ {geo_id, name}, ... ] }

  2) GET /relations/matrix?fill=nan
     -> { "N": 7, "ids": [0,1,2,...], "matrix": [[...], ...] }
     fill: 缺失时填充值，可选：0、nan（默认 nan）、或任意浮点数

  3) GET /od?start=2022-01-11T00:00:00Z&end=2022-01-19T00:00:00Z&flow_policy=zero
     -> { "T": T, "N": N, "times": ["2022-01-11T00:00:00Z", ...],
          "ids": [geo_ids...], "tensor": [[[...N],...N], ...T] }
     flow_policy: zero/null/skip（默认 zero）
       - zero: 空值按 0 处理
       - null: 空值保留为 null（JSON）
       - skip: 遇到空值的记录跳过，不写入（相当于默认值留空）

Env:
  DB_PATH, TABLE_PLACES, TABLE_RELATIONS, TABLE_DYNA, PORT
"""

from __future__ import annotations
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "./geo_points.db")
T_PLACES = os.getenv("TABLE_PLACES", "places")
T_REL    = os.getenv("TABLE_RELATIONS", "relations")
T_DYNA   = os.getenv("TABLE_DYNA", "dyna")

app = FastAPI(title="Geo OD API", version="1.0.0")

# ----------------------- DB helpers -----------------------

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()

def _load_nodes(conn: sqlite3.Connection) -> Tuple[List[int], Dict[int, int]]:
    """
    返回 (ids, id_to_idx)
      ids: 升序的 geo_id 列表
      id_to_idx: geo_id -> 稠密索引 [0..N-1]
    """
    rows = conn.execute(f"SELECT geo_id FROM {T_PLACES} ORDER BY geo_id ASC;").fetchall()
    ids = [int(r["geo_id"]) for r in rows]
    id_to_idx = {gid: i for i, gid in enumerate(ids)}
    return ids, id_to_idx

def _iso_to_epoch(s: str) -> int:
    # 支持末尾 Z；无时区按 UTC 处理
    if s.endswith("Z"):
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    else:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

# ----------------------- Schemas -----------------------

class GeoIdResponse(BaseModel):
    geo_id: Optional[int] = None
    name: Optional[str] = None
    candidates: List[Dict[str, Any]] = []

class MatrixResponse(BaseModel):
    N: int
    ids: List[int]
    matrix: List[List[Optional[float]]]

class TensorResponse(BaseModel):
    T: int
    N: int
    times: List[str]
    ids: List[int]
    tensor: List[List[List[Optional[float]]]]

# ----------------------- 1) /geo-id -----------------------

@app.get("/geo-id", response_model=GeoIdResponse)
def get_geo_id(name: str = Query(..., description="城市名（精确匹配优先，失败再模糊）")):
    q = name.strip()
    if not q:
        raise HTTPException(400, "missing name")
    with get_db() as conn:
        sql = f"SELECT geo_id, name FROM {T_PLACES} WHERE name = {q} LIMIT 1;"
        exact = conn.execute(
            f"SELECT geo_id, name FROM {T_PLACES} WHERE name = ? LIMIT 1;", (q,)
        ).fetchone()
        print(f"sql={sql}, rst={exact}")
        if exact:
            cands = conn.execute(
                f"SELECT geo_id, name FROM {T_PLACES} WHERE name LIKE ? AND geo_id != ? LIMIT 10;",
                (f"%{q}%", int(exact['geo_id']))
            ).fetchall()
            return GeoIdResponse(
                geo_id=int(exact["geo_id"]),
                name=str(exact["name"]),
                candidates=[{"geo_id": int(r["geo_id"]), "name": r["name"]} for r in cands],
            )
        # 模糊匹配
        like = conn.execute(
            f"SELECT geo_id, name FROM {T_PLACES} WHERE name LIKE ? LIMIT 10;", (f"%{q}%",)
        ).fetchall()
        if not like:
            return GeoIdResponse(geo_id=None, name=None, candidates=[])
        # 返回第一个候选，并附带所有候选
        top = like[0]
        return GeoIdResponse(
            geo_id=int(top["geo_id"]),
            name=str(top["name"]),
            candidates=[{"geo_id": int(r["geo_id"]), "name": r["name"]} for r in like],
        )

# ----------------------- 2) /relations/matrix -----------------------

@app.get("/relations/matrix", response_model=MatrixResponse)
def relations_matrix(
    fill: str = Query("nan", description="缺失填充值，可为 'nan' 或数值字符串，如 '0'、'1e9'")
):
    """
    返回 N×N 矩阵 matrix[i][j] = cost(origin_id=ids[i], destination_id=ids[j])
    """
    # 解析填充值
    fill_value: Optional[float]
    if fill.lower() == "nan":
        fill_value = None  # 用 None 表示 JSON 的 null
    else:
        try:
            fill_value = float(fill)
        except Exception:
            raise HTTPException(400, "invalid fill value; use 'nan' or a float")

    with get_db() as conn:
        ids, id_to_idx = _load_nodes(conn)
        N = len(ids)
        # 初始化矩阵
        matrix: List[List[Optional[float]]] = [
            [fill_value for _ in range(N)] for _ in range(N)
        ]
        # 读取所有边
        rows = conn.execute(
            f"SELECT origin_id, destination_id, cost FROM {T_REL};"
        ).fetchall()
        for r in rows:
            o, d = int(r["origin_id"]), int(r["destination_id"])
            if o not in id_to_idx or d not in id_to_idx:
                # 跳过无效外键（理论上不会出现，防御性处理）
                continue
            i, j = id_to_idx[o], id_to_idx[d]
            cost = r["cost"]
            matrix[i][j] = None if cost is None else float(cost)

    return MatrixResponse(N=N, ids=ids, matrix=matrix)

# ----------------------- 3) /od -----------------------

@app.get("/od", response_model=TensorResponse)
def od_tensor(
    start: str = Query(..., description="起始时间（ISO8601，如 2022-01-11T00:00:00Z）"),
    end: str = Query(..., description="结束时间（ISO8601，**不包含**该时刻）"),
    dyna_type: Optional[str] = Query(None, description="按 dyna.type 过滤（可选）"),
    flow_policy: str = Query("zero", pattern="^(zero|null|skip)$",
                             description="空值策略：zero|null|skip（默认 zero）"),
):
    """
    在 [start, end) 范围内生成张量 tensor[t][i][j] = flow。
    - 时间去重后按字典序排序
    - flow_policy:
        zero: 空值按 0 写入
        null: 空值保留为 null
        skip: 空值记录不写入（保持默认值）
    """
    # 校验时间并构造范围
    try:
        _ = _iso_to_epoch(start)
        _ = _iso_to_epoch(end)
    except Exception:
        raise HTTPException(400, "invalid start/end time")

    with get_db() as conn:
        ids, id_to_idx = _load_nodes(conn)
        N = len(ids)

        # 读出时间范围内的记录
        if dyna_type:
            rows = conn.execute(
                f"""
                SELECT time, origin_id, destination_id, flow
                FROM {T_DYNA}
                WHERE time >= ? AND time < ? AND type = ?
                ORDER BY time ASC;
                """,
                (start, end, dyna_type),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT time, origin_id, destination_id, flow
                FROM {T_DYNA}
                WHERE time >= ? AND time < ?
                ORDER BY time ASC;
                """,
                (start, end),
            ).fetchall()

        if not rows:
            return TensorResponse(T=0, N=N, times=[], ids=ids, tensor=[])

        # 收集并排序唯一 time 列表
        times: List[str] = sorted({str(r["time"]) for r in rows})
        t_index = {t: idx for idx, t in enumerate(times)}
        T = len(times)

        # 默认值（zero: 0.0；null/skip: None）
        default_value: Optional[float] = 0.0 if flow_policy == "zero" else None

        # 初始化张量 [T, N, N]
        tensor: List[List[List[Optional[float]]]] = [
            [[default_value for _ in range(N)] for _ in range(N)]
            for _ in range(T)
        ]

        # 填充
        for r in rows:
            t = str(r["time"])
            o, d = int(r["origin_id"]), int(r["destination_id"])
            if o not in id_to_idx or d not in id_to_idx:
                continue  # 防御性：无效外键
            ti = t_index[t]
            i, j = id_to_idx[o], id_to_idx[d]

            flow = r["flow"]
            if flow is None:
                if flow_policy == "skip":
                    # 保持默认值不写
                    continue
                elif flow_policy == "null":
                    tensor[ti][i][j] = None
                else:  # zero
                    tensor[ti][i][j] = 0.0
            else:
                tensor[ti][i][j] = float(flow)

    return TensorResponse(T=T, N=N, times=times, ids=ids, tensor=tensor)

# ---- 追加到 app.py 末尾（或合适位置），在已有 imports 基础上 ----


@app.post("/predict")
def predict_endpoint(payload: dict):
    """
    输入:
      {
        "history": { "T": T1, "N": N, "ids": [...], "tensor": [[[...]]]},
        "horizon": 12,
        "method": "naive" | "moving_average",
        "window": 3
      }
    输出:
      { "T": T2, "N": N, "ids": [...], "tensor": [[[...]]] }
    """
    hist = payload.get("history", {})
    horizon = int(payload.get("horizon", 0))
    method = payload.get("method", "naive")
    window = int(payload.get("window", 3))

    T1 = int(hist.get("T", 0)); N = int(hist.get("N", 0))
    ids = hist.get("ids", []); tensor = hist.get("tensor", [])
    if T1 == 0 or horizon <= 0 or not tensor:
        return {"T": 0, "N": N, "ids": ids, "tensor": []}

    if method == "naive":
        last = tensor[-1]
        pred = [last for _ in range(horizon)]
    elif method == "moving_average":
        w = max(1, min(window, T1))
        acc = [[0.0 for _ in range(N)] for _ in range(N)]
        for t in tensor[-w:]:
            for i in range(N):
                for j in range(N):
                    v = t[i][j]
                    acc[i][j] += 0.0 if v is None else float(v)
        avg = [[acc[i][j]/w for j in range(N)] for i in range(N)]
        pred = [avg for _ in range(horizon)]
    else:
        pred = [[[0.0 for _ in range(N)] for _ in range(N)] for _ in range(horizon)]

    return {"T": horizon, "N": N, "ids": ids, "tensor": pred}

@app.post("/growth")
def growth_endpoint(payload: dict):
    """
    输入: {"a": float, "b": float, "safe": true}
    输出: {"growth": float|null}
    """
    import math
    a = float(payload["a"]); b = float(payload["b"])
    safe = bool(payload.get("safe", True))
    if a == 0.0:
        return {"growth": None if safe else math.copysign(math.inf, 1.0 if b >= 0 else -1.0)}
    return {"growth": (b - a) / abs(a)}

@app.post("/metrics")
def metrics_endpoint(payload: dict):
    """
    输入: {"y_true": [[[...]]], "y_pred": [[[...]]]}
    输出: {"rmse": float, "mae": float, "mape": float|null}
    """
    import math

    def _flatten(v):
        if isinstance(v, (list, tuple)):
            for x in v:
                yield from _flatten(x)
        else:
            yield v

    y_true = list(_flatten(payload["y_true"]))
    y_pred = list(_flatten(payload["y_pred"]))
    if len(y_true) != len(y_pred):
        return {"error": "length mismatch between y_true and y_pred"}

    se = ae = ape_sum = 0.0
    n = n_mape = 0
    for yt, yp in zip(y_true, y_pred):
        if yt is None or yp is None:
            continue
        yt = float(yt); yp = float(yp)
        if math.isnan(yt) or math.isnan(yp):
            continue
        se += (yp - yt) ** 2
        ae += abs(yp - yt)
        n += 1
        if yt != 0.0:
            ape_sum += abs((yp - yt) / yt)
            n_mape += 1

    if n == 0:
        return {"error": "no valid numeric pairs"}

    rmse = math.sqrt(se / n)
    mae = ae / n
    mape = (ape_sum / n_mape) if n_mape > 0 else None
    return {"rmse": rmse, "mae": mae, "mape": mape}


@app.get("/od/pair")
def od_pair(
    start: str,
    end: str,
    origin_id: int,
    destination_id: int,
    dyna_type: Optional[str] = "state",
    flow_policy: str = "zero",  # zero|null|skip
):
    """
    返回给定 O/D 对的时间序列：
    { "T": int, "times": [str...], "origin_id": int, "destination_id": int, "series": [float|null...] }

    - 时间范围：[start, end) 半开区间
    - flow_policy: zero|null|skip
    """
    # 校验时间
    try:
        _ = _iso_to_epoch(start)
        _ = _iso_to_epoch(end)
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(400, "invalid start/end time")

    with get_db() as conn:
        # 读出所有时间点（范围内、按需过滤 type）
        if dyna_type:
            rows = conn.execute(
                f"""
                SELECT time, flow
                FROM {T_DYNA}
                WHERE time >= ? AND time < ? AND type = ? AND origin_id = ? AND destination_id = ?
                ORDER BY time ASC;
                """,
                (start, end, dyna_type, origin_id, destination_id),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT time, flow
                FROM {T_DYNA}
                WHERE time >= ? AND time < ? AND origin_id = ? AND destination_id = ?
                ORDER BY time ASC;
                """,
                (start, end, origin_id, destination_id),
            ).fetchall()
        print(rows)
        if not rows:
            return {
                "T": 0,
                "times": [],
                "origin_id": origin_id,
                "destination_id": destination_id,
                "series": [],
            }

        # 去重 & 排序后的时间轴
        times = sorted({str(r["time"]) for r in rows})
        t_index = {t: i for i, t in enumerate(times)}
        T = len(times)

        # 默认值
        default_value = 0.0 if flow_policy == "zero" else None
        series: List[Optional[float]] = [default_value for _ in range(T)]

        # 按时间写入
        for r in rows:
            t = str(r["time"])
            ti = t_index[t]
            flow = r["flow"]
            if flow is None:
                if flow_policy == "skip":
                    # 保持默认值
                    continue
                elif flow_policy == "null":
                    series[ti] = None
                else:
                    series[ti] = 0.0
            else:
                series[ti] = float(flow)

        return {
            "T": T,
            "times": times,
            "origin_id": origin_id,
            "destination_id": destination_id,
            "series": series,
        }

# ----------------------- 根路径健康检查 -----------------------

@app.get("/")
def root():
    return {"ok": True, "db": os.path.abspath(DB_PATH), "geo": T_PLACES, "rel": T_REL, "od": T_DYNA}

if __name__ == "__main__":
    print(get_geo_id("那曲"))