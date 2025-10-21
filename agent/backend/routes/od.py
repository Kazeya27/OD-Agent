#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OD data query endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from database import get_db, load_nodes, T_DYNA
from models import TensorResponse
from utils import iso_to_epoch

router = APIRouter()


@router.get("/od", response_model=TensorResponse)
def od_tensor(
    start: str = Query(..., description="起始时间（ISO8601，如 2022-01-11T00:00:00Z）"),
    end: str = Query(..., description="结束时间（ISO8601，**不包含**该时刻）"),
    geo_ids: Optional[str] = Query(
        None, description="仅获取指定geo_ids间的OD（逗号分隔，如 '1,2,3'）"
    ),
    dyna_type: Optional[str] = Query(None, description="按 dyna.type 过滤（可选）"),
    flow_policy: str = Query(
        "zero",
        pattern="^(zero|null|skip)$",
        description="空值策略：zero|null|skip（默认 zero）",
    ),
):
    """
    Generate OD tensor in time range [start, end)

    If geo_ids is provided, only returns OD flows between the specified IDs.

    Flow policies:
    - zero: null values become 0
    - null: null values remain null
    - skip: skip null records (keep default value)
    """
    # Validate timestamps
    try:
        _ = iso_to_epoch(start)
        _ = iso_to_epoch(end)
    except Exception:
        raise HTTPException(400, "invalid start/end time")

    # Parse geo_ids if provided
    filter_ids: Optional[List[int]] = None
    if geo_ids:
        try:
            filter_ids = [int(x.strip()) for x in geo_ids.split(",") if x.strip()]
            if not filter_ids:
                raise ValueError("geo_ids cannot be empty")
        except ValueError as e:
            raise HTTPException(400, f"invalid geo_ids format: {e}")

    with get_db() as conn:
        # Load all nodes or only filtered nodes
        if filter_ids:
            # Only include specified IDs
            ids = filter_ids
            id_to_idx = {id_val: idx for idx, id_val in enumerate(ids)}
        else:
            # Load all nodes
            ids, id_to_idx = load_nodes(conn)

        N = len(ids)

        # Build query based on filters
        if filter_ids:
            # Filter by geo_ids in query
            id_placeholders = ",".join("?" * len(filter_ids))
            if dyna_type:
                query = f"""
                    SELECT time, origin_id, destination_id, flow
                    FROM {T_DYNA}
                    WHERE time >= ? AND time < ? AND type = ?
                      AND origin_id IN ({id_placeholders})
                      AND destination_id IN ({id_placeholders})
                    ORDER BY time ASC;
                """
                params = (start, end, dyna_type, *filter_ids, *filter_ids)
            else:
                query = f"""
                    SELECT time, origin_id, destination_id, flow
                    FROM {T_DYNA}
                    WHERE time >= ? AND time < ?
                      AND origin_id IN ({id_placeholders})
                      AND destination_id IN ({id_placeholders})
                    ORDER BY time ASC;
                """
                params = (start, end, *filter_ids, *filter_ids)
            rows = conn.execute(query, params).fetchall()
        else:
            # Query all data in time range
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

        # Collect and sort unique times
        times: List[str] = sorted({str(r["time"]) for r in rows})
        t_index = {t: idx for idx, t in enumerate(times)}
        T = len(times)

        # Default value based on flow_policy
        default_value: Optional[float] = 0.0 if flow_policy == "zero" else None

        # Initialize tensor [T, N, N]
        tensor: List[List[List[Optional[float]]]] = [
            [[default_value for _ in range(N)] for _ in range(N)] for _ in range(T)
        ]

        # Fill tensor
        for r in rows:
            t = str(r["time"])
            o, d = int(r["origin_id"]), int(r["destination_id"])
            if o not in id_to_idx or d not in id_to_idx:
                continue  # Skip invalid foreign keys

            ti = t_index[t]
            i, j = id_to_idx[o], id_to_idx[d]

            flow = r["flow"]
            if flow is None:
                if flow_policy == "skip":
                    continue  # Keep default value
                elif flow_policy == "null":
                    tensor[ti][i][j] = None
                else:  # zero
                    tensor[ti][i][j] = 0.0
            else:
                tensor[ti][i][j] = float(flow)

    return TensorResponse(T=T, N=N, times=times, ids=ids, tensor=tensor)


@router.get("/od/pair")
def od_pair(
    start: str,
    end: str,
    origin_id: int,
    destination_id: int,
    dyna_type: Optional[str] = "state",
    flow_policy: str = "zero",
):
    """
    Get time series for specific O/D pair

    Returns:
        {
            "T": int,
            "times": [str...],
            "origin_id": int,
            "destination_id": int,
            "series": [float|null...]
        }
    """
    # Validate timestamps
    try:
        _ = iso_to_epoch(start)
        _ = iso_to_epoch(end)
    except Exception:
        raise HTTPException(400, "invalid start/end time")

    with get_db() as conn:
        # Query data for specific O/D pair
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

        if not rows:
            return {
                "T": 0,
                "times": [],
                "origin_id": origin_id,
                "destination_id": destination_id,
                "series": [],
            }

        # Get unique sorted times
        times = sorted({str(r["time"]) for r in rows})
        t_index = {t: i for i, t in enumerate(times)}
        T = len(times)

        # Default value
        default_value = 0.0 if flow_policy == "zero" else None
        series: List[Optional[float]] = [default_value for _ in range(T)]

        # Fill series
        for r in rows:
            t = str(r["time"])
            ti = t_index[t]
            flow = r["flow"]

            if flow is None:
                if flow_policy == "skip":
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
