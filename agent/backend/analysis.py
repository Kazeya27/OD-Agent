#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analysis functions for flow and corridor analysis
"""

from typing import Dict, Optional
import pandas as pd
from functools import lru_cache
from database import get_db, T_PLACES, T_DYNA


@lru_cache(maxsize=128)
def _get_city_province_mapping() -> Dict[int, str]:
    """获取城市到省份的映射关系，使用缓存避免重复查询"""
    with get_db() as conn:
        query = f"SELECT geo_id, province FROM {T_PLACES} WHERE province IS NOT NULL AND province != ''"
        rows = conn.execute(query).fetchall()
        return {row["geo_id"]: row["province"] for row in rows}


def _precompute_city_flow(
    start: str,
    end: str,
    direction: str = "send",
    dyna_type: Optional[str] = None,
) -> pd.DataFrame:
    """
    预计算城市级别的流量数据

    Returns:
        DataFrame with columns: ['time', 'city_id', 'flow']
    """
    with get_db() as conn:
        # 构建查询条件
        where_conditions = ["d.time >= ?", "d.time < ?"]
        params = [start, end]

        if dyna_type:
            where_conditions.append("d.type = ?")
            params.append(dyna_type)

        where_clause = " AND ".join(where_conditions)

        # 选择聚合字段
        group_field = "d.origin_id" if direction == "send" else "d.destination_id"

        query = f"""
            SELECT d.time, {group_field} as city_id, SUM(d.flow) as flow
            FROM {T_DYNA} d
            WHERE {where_clause}
            GROUP BY d.time, {group_field}
            ORDER BY d.time ASC, flow DESC
        """

        rows = conn.execute(query, params).fetchall()

        if not rows:
            return pd.DataFrame(columns=["time", "city_id", "flow"])

        data = []
        for r in rows:
            data.append(
                {
                    "time": str(r["time"]),
                    "city_id": int(r["city_id"]),
                    "flow": float(r["flow"]) if r["flow"] is not None else 0.0,
                }
            )

        return pd.DataFrame(data)


def analyze_province_flow_optimized(
    period_type: str,
    start: str,
    end: str,
    date_mode: str = "daily",
    direction: str = "send",
    dyna_type: Optional[str] = None,
) -> pd.DataFrame:
    """
    优化版本的省级流量分析 - 通过预计算城市流量来加速

    Args:
        period_type: Period type identifier
        start: Start time (ISO8601)
        end: End time (ISO8601)
        date_mode: 'daily' | 'total'
        direction: 'send' | 'receive'
        dyna_type: Optional dyna.type filter

    Returns:
        DataFrame(columns=['province', 'date', 'flow', 'rank'])
    """
    # 1. 预计算城市流量
    city_flow_df = _precompute_city_flow(start, end, direction, dyna_type)

    if city_flow_df.empty:
        return pd.DataFrame(columns=["province", "date", "flow", "rank"])

    # 2. 获取城市到省份的映射
    city_province_map = _get_city_province_mapping()

    # 3. 将城市流量映射到省份
    city_flow_df["province"] = city_flow_df["city_id"].map(
        lambda x: city_province_map.get(x, "Unknown")
    )

    # 4. 按省份聚合
    if date_mode == "daily":
        result = city_flow_df.groupby(["time", "province"])["flow"].sum().reset_index()
        result.columns = ["date", "province", "flow"]
        result["rank"] = (
            result.groupby("date")["flow"]
            .rank(ascending=False, method="min")
            .astype(int)
        )
    else:  # total
        result = city_flow_df.groupby("province")["flow"].sum().reset_index()
        result.columns = ["province", "flow"]
        result["date"] = None
        result["rank"] = result["flow"].rank(ascending=False, method="min").astype(int)

    result = result.sort_values("rank")
    return result


def create_performance_indexes():
    """创建性能优化所需的数据库索引"""
    with get_db() as conn:
        # 为 dyna 表创建复合索引
        conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_dyna_time_type_origin 
            ON {T_DYNA} (time, type, origin_id)
        """
        )

        conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_dyna_time_type_destination 
            ON {T_DYNA} (time, type, destination_id)
        """
        )

        # 为 places 表创建索引
        conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_places_geo_id_province 
            ON {T_PLACES} (geo_id, province)
        """
        )

        conn.commit()
        print("✅ 性能索引创建完成")


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
    使用优化版本以提高性能

    Args:
        period_type: Period type identifier
        start: Start time (ISO8601)
        end: End time (ISO8601)
        date_mode: 'daily' | 'total'
        direction: 'send' | 'receive'
        dyna_type: Optional dyna.type filter

    Returns:
        DataFrame(columns=['province', 'date', 'flow', 'rank'])
    """
    # 使用优化版本
    return analyze_province_flow_optimized(
        period_type, start, end, date_mode, direction, dyna_type
    )


def analyze_province_flow_original(
    period_type: str,
    start: str,
    end: str,
    date_mode: str = "daily",
    direction: str = "send",
    dyna_type: Optional[str] = None,
) -> pd.DataFrame:
    """
    原始版本的省级流量分析（保留用于对比）
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
        # 构建过滤条件
        where_parts = ["d.time >= ?", "d.time < ?"]
        params = [start, end]
        if dyna_type:
            where_parts.append("d.type = ?")
            params.append(dyna_type)
        where_clause = " AND ".join(where_parts)

        # 方向：发送/接收
        city_join = (
            "LEFT JOIN {places} p ON d.origin_id = p.geo_id"
            if direction == "send"
            else "LEFT JOIN {places} p ON d.destination_id = p.geo_id"
        ).format(places=T_PLACES)

        if date_mode == "daily":
            # 在 SQL 端完成聚合，显著减少数据量
            query = f"""
                SELECT d.time AS date,
                       COALESCE(p.name, 'Unknown') AS city,
                       SUM(d.flow) AS flow
                FROM {T_DYNA} d
                {city_join}
                WHERE {where_clause}
                GROUP BY d.time, city
                ORDER BY d.time ASC
            """
            rows = conn.execute(query, params).fetchall()
            if not rows:
                return pd.DataFrame(columns=["city", "date", "flow", "rank"])

            result = pd.DataFrame(
                [
                    {
                        "date": str(r["date"]),
                        "city": str(r["city"]),
                        "flow": float(r["flow"]) if r["flow"] is not None else 0.0,
                    }
                    for r in rows
                ]
            )
            result["rank"] = (
                result.groupby("date")["flow"]
                .rank(ascending=False, method="min")
                .astype(int)
            )
        else:
            # total 模式：仅按城市聚合
            query = f"""
                SELECT COALESCE(p.name, 'Unknown') AS city,
                       SUM(d.flow) AS flow
                FROM {T_DYNA} d
                {city_join}
                WHERE {where_clause}
                GROUP BY city
            """
            rows = conn.execute(query, params).fetchall()
            if not rows:
                return pd.DataFrame(columns=["city", "date", "flow", "rank"])
            result = pd.DataFrame(
                [
                    {
                        "city": str(r["city"]),
                        "flow": float(r["flow"]) if r["flow"] is not None else 0.0,
                    }
                    for r in rows
                ]
            )
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
        # 构建过滤条件
        where_parts = ["d.time >= ?", "d.time < ?"]
        params = [start, end]
        if dyna_type:
            where_parts.append("d.type = ?")
            params.append(dyna_type)
        where_clause = " AND ".join(where_parts)

        # 在 SQL 端完成聚合，显著减少数据量
        query = f"""
            SELECT COALESCE(p1.province, 'Unknown') AS send_province,
                   COALESCE(p2.province, 'Unknown') AS arrive_province,
                   SUM(d.flow) AS flow
            FROM {T_DYNA} d
            LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
            LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
            WHERE {where_clause}
            GROUP BY send_province, arrive_province
            ORDER BY flow DESC
            LIMIT ?
        """

        params.append(topk)
        rows = conn.execute(query, params).fetchall()

        if not rows:
            return pd.DataFrame(
                columns=["send_province", "arrive_province", "flow", "rank"]
            )

        # 构建结果 DataFrame
        result = pd.DataFrame(
            [
                {
                    "send_province": str(r["send_province"]),
                    "arrive_province": str(r["arrive_province"]),
                    "flow": float(r["flow"]) if r["flow"] is not None else 0.0,
                }
                for r in rows
            ]
        )

        # 添加排名（因为已经按流量降序排列）
        result["rank"] = range(1, len(result) + 1)

        return result


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
        # 构建过滤条件
        where_parts = ["d.time >= ?", "d.time < ?"]
        params = [start, end]
        if dyna_type:
            where_parts.append("d.type = ?")
            params.append(dyna_type)
        where_clause = " AND ".join(where_parts)

        # 查询省内走廊（在 SQL 端完成聚合和过滤）
        intra_query = f"""
            SELECT COALESCE(p1.name, 'Unknown') AS send_city,
                   COALESCE(p2.name, 'Unknown') AS arrive_city,
                   SUM(d.flow) AS flow
            FROM {T_DYNA} d
            LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
            LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
            WHERE {where_clause}
              AND COALESCE(p1.province, '') = COALESCE(p2.province, '')
              AND COALESCE(p1.province, '') != ''
            GROUP BY send_city, arrive_city
            ORDER BY flow DESC
            LIMIT ?
        """

        intra_rows = conn.execute(intra_query, params + [topk_intra]).fetchall()

        # 查询省际走廊（在 SQL 端完成聚合和过滤）
        inter_query = f"""
            SELECT COALESCE(p1.name, 'Unknown') AS send_city,
                   COALESCE(p2.name, 'Unknown') AS arrive_city,
                   SUM(d.flow) AS flow
            FROM {T_DYNA} d
            LEFT JOIN {T_PLACES} p1 ON d.origin_id = p1.geo_id
            LEFT JOIN {T_PLACES} p2 ON d.destination_id = p2.geo_id
            WHERE {where_clause}
              AND COALESCE(p1.province, '') != COALESCE(p2.province, '')
              AND COALESCE(p1.province, '') != ''
              AND COALESCE(p2.province, '') != ''
            GROUP BY send_city, arrive_city
            ORDER BY flow DESC
            LIMIT ?
        """

        inter_rows = conn.execute(inter_query, params + [topk_inter]).fetchall()

        # 构建省内走廊结果
        if intra_rows:
            intra_df = pd.DataFrame(
                [
                    {
                        "send_city": str(r["send_city"]),
                        "arrive_city": str(r["arrive_city"]),
                        "flow": float(r["flow"]) if r["flow"] is not None else 0.0,
                    }
                    for r in intra_rows
                ]
            )
            intra_df["rank"] = range(1, len(intra_df) + 1)
        else:
            intra_df = pd.DataFrame(
                columns=["send_city", "arrive_city", "flow", "rank"]
            )

        # 构建省际走廊结果
        if inter_rows:
            inter_df = pd.DataFrame(
                [
                    {
                        "send_city": str(r["send_city"]),
                        "arrive_city": str(r["arrive_city"]),
                        "flow": float(r["flow"]) if r["flow"] is not None else 0.0,
                    }
                    for r in inter_rows
                ]
            )
            inter_df["rank"] = range(1, len(inter_df) + 1)
        else:
            inter_df = pd.DataFrame(
                columns=["send_city", "arrive_city", "flow", "rank"]
            )

        return {"intra_province": intra_df, "inter_province": inter_df}


def benchmark_province_flow_performance(
    start: str,
    end: str,
    direction: str = "send",
    dyna_type: Optional[str] = None,
    iterations: int = 3,
) -> Dict[str, float]:
    """
    性能基准测试：比较优化版本和原始版本的执行时间

    Returns:
        Dict with performance metrics
    """
    import time

    print("🚀 开始性能基准测试...")

    # 测试优化版本
    print("📊 测试优化版本...")
    optimized_times = []
    for i in range(iterations):
        start_time = time.time()
        result_opt = analyze_province_flow_optimized(
            "test", start, end, "total", direction, dyna_type
        )
        end_time = time.time()
        optimized_times.append(end_time - start_time)
        print(f"  第{i+1}次: {end_time - start_time:.3f}秒")

    # 测试原始版本
    print("📊 测试原始版本...")
    original_times = []
    for i in range(iterations):
        start_time = time.time()
        result_orig = analyze_province_flow_original(
            "test", start, end, "total", direction, dyna_type
        )
        end_time = time.time()
        original_times.append(end_time - start_time)
        print(f"  第{i+1}次: {end_time - start_time:.3f}秒")

    # 计算平均时间
    avg_optimized = sum(optimized_times) / len(optimized_times)
    avg_original = sum(original_times) / len(original_times)
    speedup = avg_original / avg_optimized if avg_optimized > 0 else 0

    print(f"\n📈 性能测试结果:")
    print(f"  优化版本平均时间: {avg_optimized:.3f}秒")
    print(f"  原始版本平均时间: {avg_original:.3f}秒")
    print(f"  性能提升: {speedup:.2f}x")
    print(f"  时间节省: {((avg_original - avg_optimized) / avg_original * 100):.1f}%")

    # 验证结果一致性
    if not result_opt.empty and not result_orig.empty:
        # 比较结果
        opt_sorted = result_opt.sort_values(["province"]).reset_index(drop=True)
        orig_sorted = result_orig.sort_values(["province"]).reset_index(drop=True)

        # 检查省份列表是否一致
        provinces_match = set(opt_sorted["province"]) == set(orig_sorted["province"])
        print(f"  结果一致性: {'✅ 通过' if provinces_match else '❌ 失败'}")

        if provinces_match:
            # 检查流量总和是否接近
            flow_diff = abs(opt_sorted["flow"].sum() - orig_sorted["flow"].sum())
            flow_match = flow_diff < 0.01
            print(
                f"  流量一致性: {'✅ 通过' if flow_match else '❌ 失败'} (差异: {flow_diff:.6f})"
            )

    return {
        "optimized_avg": avg_optimized,
        "original_avg": avg_original,
        "speedup": speedup,
        "time_saved_percent": (avg_original - avg_optimized) / avg_original * 100,
    }
