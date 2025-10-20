#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Geo-related endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from database import get_db, T_PLACES
from models import GeoIdResponse

router = APIRouter()


@router.get("/geo-id", response_model=GeoIdResponse)
def get_geo_id(name: str = Query(..., description="城市名（精确匹配优先，失败再模糊）")):
    """
    Get geo_id by city name
    - Exact match first, then fuzzy match
    - Returns candidates for ambiguous names
    """
    q = name.strip()
    if not q:
        raise HTTPException(400, "missing name")
    
    with get_db() as conn:
        # Try exact match
        exact = conn.execute(
            f"SELECT geo_id, name FROM {T_PLACES} WHERE name = ? LIMIT 1;", (q,)
        ).fetchone()
        
        if exact:
            # Get other similar candidates
            cands = conn.execute(
                f"SELECT geo_id, name FROM {T_PLACES} WHERE name LIKE ? AND geo_id != ? LIMIT 10;",
                (f"%{q}%", int(exact['geo_id']))
            ).fetchall()
            return GeoIdResponse(
                geo_id=int(exact["geo_id"]),
                name=str(exact["name"]),
                candidates=[{"geo_id": int(r["geo_id"]), "name": r["name"]} for r in cands],
            )
        
        # Fuzzy match
        like = conn.execute(
            f"SELECT geo_id, name FROM {T_PLACES} WHERE name LIKE ? LIMIT 10;", (f"%{q}%",)
        ).fetchall()
        
        if not like:
            return GeoIdResponse(geo_id=None, name=None, candidates=[])
        
        # Return first candidate with all candidates
        top = like[0]
        return GeoIdResponse(
            geo_id=int(top["geo_id"]),
            name=str(top["name"]),
            candidates=[{"geo_id": int(r["geo_id"]), "name": r["name"]} for r in like],
        )

