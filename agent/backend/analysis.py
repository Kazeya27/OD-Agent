#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analysis functions for flow and corridor analysis
"""

from typing import Dict, Optional
import pandas as pd
from database import get_db, T_PLACES, T_DYNA


def analyze_province_flow(
    period_type: str,
    start: str,
    end: str,
    date_mode: str = "daily",
    direction: str = "send",
    dyna_type: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate province-level flow intensity and ranking

    Args:
        period_type: Period type identifier
        start: Start time (ISO8601)
        end: End time (ISO8601)
        date_mode: 'daily' | 'total'
        direction: 'send' | 'arrive'
        dyna_type: Optional dyna.type filter

    Returns:
        DataFrame(columns=['province', 'date', 'flow', 'rank'])
    """
    with get_db() as conn:
        # Query data with province information
        if dyna_type:
            query = f"""
                SELECT d.time, d.origin_id, d.destination_id, d.flow, 
                       p1.province as origin_province, p2.province as destination_province
                FROM {T_DYNA} d
                LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
                LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
                WHERE d.time >= ? AND d.time < ? AND d.type = ?
                ORDER BY d.time ASC;
            """
            rows = conn.execute(query, (start, end, dyna_type)).fetchall()
        else:
            query = f"""
                SELECT d.time, d.origin_id, d.destination_id, d.flow,
                       p1.province as origin_province, p2.province as destination_province
                FROM {T_DYNA} d
                LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
                LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
                WHERE d.time >= ? AND d.time < ?
                ORDER BY d.time ASC;
            """
            rows = conn.execute(query, (start, end)).fetchall()

        # Convert to list
        data = []
        for r in rows:
            data.append(
                {
                    "time": str(r["time"]),
                    "origin_province": (
                        str(r["origin_province"]) if r["origin_province"] else "Unknown"
                    ),
                    "destination_province": (
                        str(r["destination_province"])
                        if r["destination_province"]
                        else "Unknown"
                    ),
                    "flow": float(r["flow"]) if r["flow"] is not None else 0.0,
                }
            )

        if not data:
            return pd.DataFrame(columns=["province", "date", "flow", "rank"])

        df = pd.DataFrame(data)

        # Choose aggregation dimension based on direction
        group_col = "origin_province" if direction == "send" else "destination_province"

        # Aggregate by date_mode
        if date_mode == "daily":
            result = df.groupby(["time", group_col])["flow"].sum().reset_index()
            result.columns = ["date", "province", "flow"]
            result["rank"] = (
                result.groupby("date")["flow"]
                .rank(ascending=False, method="min")
                .astype(int)
            )
        else:  # total
            result = df.groupby(group_col)["flow"].sum().reset_index()
            result.columns = ["province", "flow"]
            result["date"] = None
            result["rank"] = (
                result["flow"].rank(ascending=False, method="min").astype(int)
            )

        result = result.sort_values("rank")
        return result


def analyze_city_flow(
    period_type: str,
    start: str,
    end: str,
    date_mode: str = "daily",
    direction: str = "send",
    dyna_type: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate city-level flow intensity and ranking

    Returns:
        DataFrame(columns=['city', 'date', 'flow', 'rank'])
    """
    with get_db() as conn:
        if dyna_type:
            query = f"""
                SELECT d.time, d.origin_id, d.destination_id, d.flow, 
                       p1.name as origin_name, p2.name as destination_name
                FROM {T_DYNA} d
                LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
                LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
                WHERE d.time >= ? AND d.time < ? AND d.type = ?
                ORDER BY d.time ASC;
            """
            rows = conn.execute(query, (start, end, dyna_type)).fetchall()
        else:
            query = f"""
                SELECT d.time, d.origin_id, d.destination_id, d.flow,
                       p1.name as origin_name, p2.name as destination_name
                FROM {T_DYNA} d
                LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
                LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
                WHERE d.time >= ? AND d.time < ?
                ORDER BY d.time ASC;
            """
            rows = conn.execute(query, (start, end)).fetchall()

        if not rows:
            return pd.DataFrame(columns=["city", "date", "flow", "rank"])

        data = []
        for r in rows:
            data.append(
                {
                    "time": str(r["time"]),
                    "origin_name": (
                        str(r["origin_name"]) if r["origin_name"] else "Unknown"
                    ),
                    "destination_name": (
                        str(r["destination_name"])
                        if r["destination_name"]
                        else "Unknown"
                    ),
                    "flow": float(r["flow"]) if r["flow"] is not None else 0.0,
                }
            )

        df = pd.DataFrame(data)
        group_col = "origin_name" if direction == "send" else "destination_name"

        if date_mode == "daily":
            result = df.groupby(["time", group_col])["flow"].sum().reset_index()
            result.columns = ["date", "city", "flow"]
            result["rank"] = (
                result.groupby("date")["flow"]
                .rank(ascending=False, method="min")
                .astype(int)
            )
        else:
            result = df.groupby(group_col)["flow"].sum().reset_index()
            result.columns = ["city", "flow"]
            result["date"] = None
            result["rank"] = (
                result["flow"].rank(ascending=False, method="min").astype(int)
            )

        result = result.sort_values("rank")
        return result


def analyze_province_corridor(
    period_type: str,
    start: str,
    end: str,
    date_mode: str = "total",
    topk: int = 10,
    dyna_type: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate inter-province corridor flow intensity and ranking

    Returns:
        DataFrame(columns=['send_province', 'arrive_province', 'flow', 'rank'])
    """
    with get_db() as conn:
        if dyna_type:
            query = f"""
                SELECT d.time, d.origin_id, d.destination_id, d.flow,
                       p1.province as origin_province, p2.province as destination_province
                FROM {T_DYNA} d
                LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
                LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
                WHERE d.time >= ? AND d.time < ? AND d.type = ?
                ORDER BY d.time ASC;
            """
            rows = conn.execute(query, (start, end, dyna_type)).fetchall()
        else:
            query = f"""
                SELECT d.time, d.origin_id, d.destination_id, d.flow,
                       p1.province as origin_province, p2.province as destination_province
                FROM {T_DYNA} d
                LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
                LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
                WHERE d.time >= ? AND d.time < ?
                ORDER BY d.time ASC;
            """
            rows = conn.execute(query, (start, end)).fetchall()

        if not rows:
            return pd.DataFrame(
                columns=["send_province", "arrive_province", "flow", "rank"]
            )

        data = []
        for r in rows:
            data.append(
                {
                    "origin_province": (
                        str(r["origin_province"]) if r["origin_province"] else "Unknown"
                    ),
                    "destination_province": (
                        str(r["destination_province"])
                        if r["destination_province"]
                        else "Unknown"
                    ),
                    "flow": float(r["flow"]) if r["flow"] is not None else 0.0,
                }
            )

        df = pd.DataFrame(data)
        result = (
            df.groupby(["origin_province", "destination_province"])["flow"]
            .sum()
            .reset_index()
        )
        result.columns = ["send_province", "arrive_province", "flow"]
        result["rank"] = result["flow"].rank(ascending=False, method="min").astype(int)
        result = result.sort_values("rank")

        return result.head(topk)


def analyze_city_corridor(
    period_type: str,
    start: str,
    end: str,
    date_mode: str = "total",
    topk_intra: int = 10,
    topk_inter: int = 30,
    dyna_type: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Calculate city-level corridor flow (intra-province and inter-province)

    Returns:
        {'intra_province': df1, 'inter_province': df2}
    """
    with get_db() as conn:
        if dyna_type:
            query = f"""
                SELECT d.time, d.origin_id, d.destination_id, d.flow,
                       p1.name as origin_name, p2.name as destination_name,
                       p1.province as origin_province, p2.province as destination_province
                FROM {T_DYNA} d
                LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
                LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
                WHERE d.time >= ? AND d.time < ? AND d.type = ?
                ORDER BY d.time ASC;
            """
            rows = conn.execute(query, (start, end, dyna_type)).fetchall()
        else:
            query = f"""
                SELECT d.time, d.origin_id, d.destination_id, d.flow,
                       p1.name as origin_name, p2.name as destination_name,
                       p1.province as origin_province, p2.province as destination_province
                FROM {T_DYNA} d
                LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
                LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
                WHERE d.time >= ? AND d.time < ?
                ORDER BY d.time ASC;
            """
            rows = conn.execute(query, (start, end)).fetchall()

        if not rows:
            empty_df = pd.DataFrame(
                columns=["send_city", "arrive_city", "flow", "rank"]
            )
            return {"intra_province": empty_df, "inter_province": empty_df}

        data = []
        for r in rows:
            data.append(
                {
                    "origin_name": (
                        str(r["origin_name"]) if r["origin_name"] else "Unknown"
                    ),
                    "destination_name": (
                        str(r["destination_name"])
                        if r["destination_name"]
                        else "Unknown"
                    ),
                    "origin_province": (
                        str(r["origin_province"]) if r["origin_province"] else "Unknown"
                    ),
                    "destination_province": (
                        str(r["destination_province"])
                        if r["destination_province"]
                        else "Unknown"
                    ),
                    "flow": float(r["flow"]) if r["flow"] is not None else 0.0,
                }
            )

        df = pd.DataFrame(data)
        result = (
            df.groupby(
                [
                    "origin_name",
                    "destination_name",
                    "origin_province",
                    "destination_province",
                ]
            )["flow"]
            .sum()
            .reset_index()
        )

        # Separate intra-province and inter-province
        intra = result[
            result["origin_province"] == result["destination_province"]
        ].copy()
        inter = result[
            result["origin_province"] != result["destination_province"]
        ].copy()

        # Rank separately
        if not intra.empty:
            intra["rank"] = (
                intra["flow"].rank(ascending=False, method="min").astype(int)
            )
            intra = intra.sort_values("rank").head(topk_intra)
            intra = intra[["origin_name", "destination_name", "flow", "rank"]]
            intra.columns = ["send_city", "arrive_city", "flow", "rank"]
        else:
            intra = pd.DataFrame(columns=["send_city", "arrive_city", "flow", "rank"])

        if not inter.empty:
            inter["rank"] = (
                inter["flow"].rank(ascending=False, method="min").astype(int)
            )
            inter = inter.sort_values("rank").head(topk_inter)
            inter = inter[["origin_name", "destination_name", "flow", "rank"]]
            inter.columns = ["send_city", "arrive_city", "flow", "rank"]
        else:
            inter = pd.DataFrame(columns=["send_city", "arrive_city", "flow", "rank"])

        return {"intra_province": intra, "inter_province": inter}
