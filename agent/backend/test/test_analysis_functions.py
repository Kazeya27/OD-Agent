#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新增的分析函数
使用临时生成的测试数据，无需 FastAPI 依赖
"""

import sqlite3
import tempfile
import random
import os
from datetime import datetime, timedelta

# 尝试导入 pandas
try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    print("⚠️  警告: pandas 未安装，部分功能将不可用")
    print("   请运行: pip install pandas")
    HAS_PANDAS = False
    exit(1)

# 模拟环境变量
T_PLACES = "places"
T_DYNA = "dyna"


def get_db_connection(db_path):
    """获取数据库连接"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def analyze_province_flow_test(
    conn,
    start: str,
    end: str,
    date_mode: str = "daily",
    direction: str = "send",
    dyna_type: str = None,
) -> pd.DataFrame:
    """
    测试版本的省级流动分析函数
    """
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

    if direction == "send":
        group_col = "origin_province"
    else:
        group_col = "destination_province"

    if date_mode == "daily":
        result = df.groupby(["time", group_col])["flow"].sum().reset_index()
        result.columns = ["date", "province", "flow"]
        result["rank"] = (
            result.groupby("date")["flow"]
            .rank(ascending=False, method="min")
            .astype(int)
        )
    else:
        result = df.groupby(group_col)["flow"].sum().reset_index()
        result.columns = ["province", "flow"]
        result["date"] = None
        result["rank"] = result["flow"].rank(ascending=False, method="min").astype(int)

    result = result.sort_values("rank")
    return result


def main():
    print("=" * 70)
    print("测试新增的分析函数")
    print("=" * 70)

    # 创建临时测试数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db_path = tmp.name

    print(f"\n📁 创建临时测试数据库: {test_db_path}")

    # 初始化测试数据库
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    # 创建表结构
    cursor.execute(
        f"""
        CREATE TABLE {T_PLACES} (
            geo_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            province TEXT
        )
    """
    )

    cursor.execute(
        f"""
        CREATE TABLE {T_DYNA} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            origin_id INTEGER NOT NULL,
            destination_id INTEGER NOT NULL,
            flow REAL,
            type TEXT,
            FOREIGN KEY (origin_id) REFERENCES {T_PLACES}(geo_id),
            FOREIGN KEY (destination_id) REFERENCES {T_PLACES}(geo_id)
        )
    """
    )

    # 插入测试地点数据 (geo_id, name, province)
    test_cities = [
        (0, "北京", "北京"),
        (1, "上海", "上海"),
        (2, "广州", "广东"),
        (3, "深圳", "广东"),
        (4, "杭州", "浙江"),
        (5, "南京", "江苏"),
        (6, "成都", "四川"),
        (7, "重庆", "重庆"),
        (8, "武汉", "湖北"),
        (9, "西安", "陕西"),
        (10, "郑州", "河南"),
        (11, "长沙", "湖南"),
        (12, "济南", "山东"),
        (13, "青岛", "山东"),
        (14, "天津", "天津"),
    ]

    cursor.executemany(
        f"INSERT INTO {T_PLACES} (geo_id, name, province) VALUES (?, ?, ?)", test_cities
    )

    # 生成测试 OD 数据
    print("📊 生成测试 OD 数据...")
    start_date = datetime(2022, 1, 11)
    test_data = []

    for day in range(8):
        current_date = start_date + timedelta(days=day)
        time_str = current_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        for origin_id in range(15):
            for dest_id in range(15):
                if origin_id != dest_id:
                    base_flow = random.uniform(100, 1000)
                    # 热门通道流量更大
                    if (origin_id, dest_id) in [
                        (0, 1),
                        (1, 0),
                        (2, 3),
                        (3, 2),
                        (4, 5),
                        (5, 4),
                    ]:
                        base_flow *= random.uniform(5, 10)

                    test_data.append(
                        (time_str, origin_id, dest_id, round(base_flow, 2), "state")
                    )

    cursor.executemany(
        f"INSERT INTO {T_DYNA} (time, origin_id, destination_id, flow, type) VALUES (?, ?, ?, ?, ?)",
        test_data,
    )

    conn.commit()
    conn.close()

    print(f"✅ 生成 {len(test_cities)} 个城市")
    print(f"✅ 生成 {len(test_data)} 条 OD 记录")

    # 重新连接用于测试
    conn = get_db_connection(test_db_path)

    # 测试 1: 省级人员流动分析 - 总量
    print("\n" + "=" * 70)
    print("测试 1: 省级人员流动分析 - 总量模式 (date_mode='total')")
    print("=" * 70)

    try:
        df_province = analyze_province_flow_test(
            conn,
            start="2022-01-11T00:00:00Z",
            end="2022-01-19T00:00:00Z",
            date_mode="total",
            direction="send",
            dyna_type="state",
        )
        print(f"\n✅ 返回 {len(df_province)} 条记录")
        print("\n前 10 名省份/城市发送量:")
        print(df_province.head(10).to_string(index=False))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()

    # 测试 2: 省级人员流动分析 - 每日
    print("\n" + "=" * 70)
    print("测试 2: 省级人员流动分析 - 每日模式 (date_mode='daily')")
    print("=" * 70)

    try:
        df_daily = analyze_province_flow_test(
            conn,
            start="2022-01-11T00:00:00Z",
            end="2022-01-14T00:00:00Z",
            date_mode="daily",
            direction="send",
            dyna_type="state",
        )
        print(f"\n✅ 返回 {len(df_daily)} 条记录")
        print("\n每日省份发送量 (前 15 条):")
        print(df_daily.head(15).to_string(index=False))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()

    # 测试 3: 到达方向
    print("\n" + "=" * 70)
    print("测试 3: 到达方向分析 (direction='arrive')")
    print("=" * 70)

    try:
        df_arrive = analyze_province_flow_test(
            conn,
            start="2022-01-11T00:00:00Z",
            end="2022-01-19T00:00:00Z",
            date_mode="total",
            direction="arrive",
            dyna_type="state",
        )
        print(f"\n✅ 返回 {len(df_arrive)} 条记录")
        print("\n前 10 名省份/城市到达量:")
        print(df_arrive.head(10).to_string(index=False))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()

    # 测试 4: 统计验证
    print("\n" + "=" * 70)
    print("测试 4: 数据统计验证")
    print("=" * 70)

    try:
        # 验证总流量
        cursor = conn.cursor()
        total_flow = cursor.execute(
            f"SELECT SUM(flow) as total FROM {T_DYNA} WHERE time >= ? AND time < ?",
            ("2022-01-11T00:00:00Z", "2022-01-19T00:00:00Z"),
        ).fetchone()

        send_sum = df_province["flow"].sum()
        arrive_sum = df_arrive["flow"].sum()

        print(f"\n数据库总流量: {total_flow['total']:.2f}")
        print(f"发送方向汇总: {send_sum:.2f}")
        print(f"到达方向汇总: {arrive_sum:.2f}")
        print(f"\n✅ 发送和到达流量应该相等: {abs(send_sum - arrive_sum) < 0.01}")

        # 验证排名
        print(f"\n排名验证:")
        print(
            f"  - 发送排名范围: {df_province['rank'].min()} ~ {df_province['rank'].max()}"
        )
        print(
            f"  - 到达排名范围: {df_arrive['rank'].min()} ~ {df_arrive['rank'].max()}"
        )
        print(f"  - 流量降序排列: {(df_province['flow'].diff().dropna() <= 0).all()}")

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback

        traceback.print_exc()

    # 清理
    print("\n" + "=" * 70)
    print("清理测试环境")
    print("=" * 70)

    conn.close()
    try:
        os.unlink(test_db_path)
        print(f"✅ 已删除临时数据库: {test_db_path}")
    except Exception as e:
        print(f"⚠️  删除临时数据库失败: {e}")

    print("\n" + "=" * 70)
    print("✅ 所有测试完成!")
    print("=" * 70)
    print("\n提示:")
    print("  1. 确保已安装所有依赖: pip install -r requirements.txt")
    print("  2. 使用 python -m uvicorn app:app --reload 启动 API 服务")
    print("  3. 访问 http://localhost:8000/docs 查看 API 文档")


if __name__ == "__main__":
    main()
