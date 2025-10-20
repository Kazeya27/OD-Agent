#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relations matrix endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from database import get_db, load_nodes, T_REL
from models import MatrixResponse

router = APIRouter()


@router.get("/relations/matrix", response_model=MatrixResponse)
def relations_matrix(
    fill: str = Query("nan", description="缺失填充值，可为 'nan' 或数值字符串，如 '0'、'1e9'")
):
    """
    Get N×N relations matrix
    - matrix[i][j] = cost(origin_id=ids[i], destination_id=ids[j])
    """
    # Parse fill value
    fill_value: Optional[float]
    if fill.lower() == "nan":
        fill_value = None  # None represents JSON null
    else:
        try:
            fill_value = float(fill)
        except Exception:
            raise HTTPException(400, "invalid fill value; use 'nan' or a float")

    with get_db() as conn:
        ids, id_to_idx = load_nodes(conn)
        N = len(ids)
        
        # Initialize matrix
        matrix: List[List[Optional[float]]] = [
            [fill_value for _ in range(N)] for _ in range(N)
        ]
        
        # Load edges
        rows = conn.execute(
            f"SELECT origin_id, destination_id, cost FROM {T_REL};"
        ).fetchall()
        
        for r in rows:
            o, d = int(r["origin_id"]), int(r["destination_id"])
            if o not in id_to_idx or d not in id_to_idx:
                continue  # Skip invalid foreign keys
            
            i, j = id_to_idx[o], id_to_idx[d]
            cost = r["cost"]
            matrix[i][j] = None if cost is None else float(cost)

    return MatrixResponse(N=N, ids=ids, matrix=matrix)

