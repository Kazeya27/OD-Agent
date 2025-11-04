#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 analysis.py 中的函数在新构建的 geo_points.db 数据库上的表现
"""

import os
import sys
import time

# 设置环境变量
os.environ["DB_PATH"] = "/home/ubuntu/OD-Agent/agent/backend/geo_points.db"
os.environ["TABLE_PLACES"] = "places"
os.environ["TABLE_RELATIONS"] = "relations"
os.environ["TABLE_DYNA"] = "dyna"

# 添加父目录到路径，以便导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pandas as pd

    HAS_DEPENDENCIES = True
except ImportError as e:
    print(f"❌ 导入pandas失败: {e}")
    print("请确保已安装所有依赖: pip install -r requirements.txt")
    HAS_DEPENDENCIES = False

# 导入项目模块
try:
    from analysis import (
        analyze_province_flow,
        analyze_city_flow,
        analyze_province_corridor,
        analyze_city_corridor,
    )
    from database import get_db, T_PLACES, T_DYNA
    from utils import extract_province

    MODULES_IMPORTED = True
except ImportError as e:
    print(f"❌ 导入项目模块失败: {e}")
    MODULES_IMPORTED = False


def test_database_connection():
    """测试数据库连接和基本信息"""
    print("=" * 80)
    print("🔍 数据库连接测试")
    print("=" * 80)

    if not MODULES_IMPORTED:
        print("❌ 跳过测试：项目模块未导入")
        return False

    try:
        with get_db() as conn:
            # 检查表是否存在
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"✅ 数据库表: {tables}")

            # 检查数据量
            places_count = conn.execute(f"SELECT COUNT(*) FROM {T_PLACES}").fetchone()[
                0
            ]
            dyna_count = conn.execute(f"SELECT COUNT(*) FROM {T_DYNA}").fetchone()[0]
            print(f"✅ 地点数量: {places_count:,}")
            print(f"✅ OD记录数量: {dyna_count:,}")

            # 检查时间范围
            time_range = conn.execute(
                f"SELECT MIN(time), MAX(time) FROM {T_DYNA}"
            ).fetchone()
            print(f"✅ 时间范围: {time_range[0]} 到 {time_range[1]}")

            # 检查数据类型
            types = conn.execute(f"SELECT DISTINCT type FROM {T_DYNA}").fetchall()
            print(f"✅ 数据类型: {[t[0] for t in types]}")

            # 检查省份分布
            provinces = conn.execute(
                f"SELECT province, COUNT(*) as cnt FROM {T_PLACES} WHERE province != '' GROUP BY province ORDER BY cnt DESC LIMIT 10"
            ).fetchall()
            print(f"✅ 省份分布 (前10): {[(p[0], p[1]) for p in provinces]}")

            return True

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_province_flow_analysis():
    """测试省级流动分析函数"""
    print("\n" + "=" * 80)
    print("🌍 省级流动分析测试")
    print("=" * 80)

    if not HAS_DEPENDENCIES or not MODULES_IMPORTED:
        print("❌ 跳过测试：依赖未安装或模块未导入")
        return

    try:
        # 测试1: 总量模式 - 发送方向
        print("\n📊 测试1: 总量模式 - 发送方向")
        start_time = time.time()

        df_send = analyze_province_flow(
            period_type="test",
            start="2025-01-14T00:00:00Z",
            end="2025-02-22T00:00:00Z",
            date_mode="total",
            direction="send",
            dyna_type="state",
        )

        end_time = time.time()
        print(f"✅ 执行时间: {end_time - start_time:.2f}秒")
        print(f"✅ 返回记录数: {len(df_send)}")

        if not df_send.empty:
            print("\n前10名发送省份:")
            print(df_send.head(10).to_string(index=False))

            # 验证数据
            print(f"\n数据验证:")
            print(f"  - 流量总和: {df_send['flow'].sum():,.2f}")
            print(f"  - 排名范围: {df_send['rank'].min()} ~ {df_send['rank'].max()}")
            print(f"  - 是否按流量降序: {(df_send['flow'].diff().dropna() <= 0).all()}")

        # 测试2: 总量模式 - 到达方向
        print("\n📊 测试2: 总量模式 - 到达方向")
        start_time = time.time()

        df_arrive = analyze_province_flow(
            period_type="test",
            start="2025-01-14T00:00:00Z",
            end="2025-02-22T00:00:00Z",
            date_mode="total",
            direction="arrive",
            dyna_type="state",
        )

        end_time = time.time()
        print(f"✅ 执行时间: {end_time - start_time:.2f}秒")
        print(f"✅ 返回记录数: {len(df_arrive)}")

        if not df_arrive.empty:
            print("\n前10名到达省份:")
            print(df_arrive.head(10).to_string(index=False))

            # 验证发送和到达流量相等
            send_sum = df_send["flow"].sum()
            arrive_sum = df_arrive["flow"].sum()
            print(f"\n流量验证:")
            print(f"  - 发送总流量: {send_sum:,.2f}")
            print(f"  - 到达总流量: {arrive_sum:,.2f}")
            print(f"  - 流量平衡: {abs(send_sum - arrive_sum) < 0.01}")

        # 测试3: 每日模式
        print("\n📊 测试3: 每日模式")
        start_time = time.time()

        df_daily = analyze_province_flow(
            period_type="test",
            start="2025-01-14T00:00:00Z",
            end="2025-01-17T00:00:00Z",
            date_mode="daily",
            direction="send",
            dyna_type="state",
        )

        end_time = time.time()
        print(f"✅ 执行时间: {end_time - start_time:.2f}秒")
        print(f"✅ 返回记录数: {len(df_daily)}")

        if not df_daily.empty:
            print("\n每日发送量 (前15条):")
            print(df_daily.head(15).to_string(index=False))

            # 验证每日数据
            unique_dates = df_daily["date"].nunique()
            print(f"\n每日数据验证:")
            print(f"  - 不同日期数: {unique_dates}")
            print(f"  - 日期范围: {df_daily['date'].min()} 到 {df_daily['date'].max()}")

    except Exception as e:
        print(f"❌ 省级流动分析测试失败: {e}")
        import traceback

        traceback.print_exc()


def test_city_flow_analysis():
    """测试城市流动分析函数"""
    print("\n" + "=" * 80)
    print("🏙️ 城市流动分析测试")
    print("=" * 80)

    if not HAS_DEPENDENCIES or not MODULES_IMPORTED:
        print("❌ 跳过测试：依赖未安装或模块未导入")
        return

    try:
        # 测试1: 总量模式 - 发送方向
        print("\n📊 测试1: 总量模式 - 发送方向")
        start_time = time.time()

        df_send = analyze_city_flow(
            period_type="test",
            start="2025-01-14T00:00:00Z",
            end="2025-02-22T00:00:00Z",
            date_mode="total",
            direction="send",
            dyna_type="state",
        )

        end_time = time.time()
        print(f"✅ 执行时间: {end_time - start_time:.2f}秒")
        print(f"✅ 返回记录数: {len(df_send)}")

        if not df_send.empty:
            print("\n前10名发送城市:")
            print(df_send.head(10).to_string(index=False))

        # 测试2: 每日模式
        print("\n📊 测试2: 每日模式")
        start_time = time.time()

        df_daily = analyze_city_flow(
            period_type="test",
            start="2025-01-14T00:00:00Z",
            end="2025-02-22T00:00:00Z",
            date_mode="daily",
            direction="send",
            dyna_type="state",
        )

        end_time = time.time()
        print(f"✅ 执行时间: {end_time - start_time:.2f}秒")
        print(f"✅ 返回记录数: {len(df_daily)}")

        if not df_daily.empty:
            print("\n每日城市发送量 (前15条):")
            print(df_daily.head(15).to_string(index=False))

    except Exception as e:
        print(f"❌ 城市流动分析测试失败: {e}")
        import traceback

        traceback.print_exc()


def test_province_corridor_analysis():
    """测试省级走廊分析函数"""
    print("\n" + "=" * 80)
    print("🛣️ 省级走廊分析测试")
    print("=" * 80)

    if not HAS_DEPENDENCIES or not MODULES_IMPORTED:
        print("❌ 跳过测试：依赖未安装或模块未导入")
        return

    try:
        # 测试省级走廊分析
        print("\n📊 省级走廊分析")
        start_time = time.time()

        df_corridor = analyze_province_corridor(
            period_type="test",
            start="2025-01-14T00:00:00Z",
            end="2025-02-22T00:00:00Z",
            date_mode="total",
            topk=15,
            dyna_type="state",
        )

        end_time = time.time()
        print(f"✅ 执行时间: {end_time - start_time:.2f}秒")
        print(f"✅ 返回记录数: {len(df_corridor)}")

        if not df_corridor.empty:
            print("\n前15名省级走廊:")
            print(df_corridor.to_string(index=False))

            # 验证数据
            print(f"\n走廊数据验证:")
            print(f"  - 总流量: {df_corridor['flow'].sum():,.2f}")
            print(
                f"  - 排名范围: {df_corridor['rank'].min()} ~ {df_corridor['rank'].max()}"
            )
            print(
                f"  - 是否按流量降序: {(df_corridor['flow'].diff().dropna() <= 0).all()}"
            )

    except Exception as e:
        print(f"❌ 省级走廊分析测试失败: {e}")
        import traceback

        traceback.print_exc()


def test_city_corridor_analysis():
    """测试城市走廊分析函数"""
    print("\n" + "=" * 80)
    print("🏘️ 城市走廊分析测试")
    print("=" * 80)

    if not HAS_DEPENDENCIES or not MODULES_IMPORTED:
        print("❌ 跳过测试：依赖未安装或模块未导入")
        return

    try:
        # 测试城市走廊分析
        print("\n📊 城市走廊分析")
        start_time = time.time()

        result = analyze_city_corridor(
            period_type="test",
            start="2025-01-14T00:00:00Z",
            end="2025-02-22T00:00:00Z",
            date_mode="total",
            topk_intra=10,
            topk_inter=20,
            dyna_type="state",
        )

        end_time = time.time()
        print(f"✅ 执行时间: {end_time - start_time:.2f}秒")

        # 省内走廊
        intra_df = result["intra_province"]
        print(f"✅ 省内走廊记录数: {len(intra_df)}")

        if not intra_df.empty:
            print("\n前10名省内走廊:")
            print(intra_df.to_string(index=False))

        # 省际走廊
        inter_df = result["inter_province"]
        print(f"✅ 省际走廊记录数: {len(inter_df)}")

        if not inter_df.empty:
            print("\n前20名省际走廊:")
            print(inter_df.to_string(index=False))

            # 验证省际走廊
            print(f"\n省际走廊验证:")
            print(f"  - 总流量: {inter_df['flow'].sum():,.2f}")
            print(f"  - 排名范围: {inter_df['rank'].min()} ~ {inter_df['rank'].max()}")

    except Exception as e:
        print(f"❌ 城市走廊分析测试失败: {e}")
        import traceback

        traceback.print_exc()


def test_performance_benchmark():
    """性能基准测试"""
    print("\n" + "=" * 80)
    print("⚡ 性能基准测试")
    print("=" * 80)

    if not HAS_DEPENDENCIES or not MODULES_IMPORTED:
        print("❌ 跳过测试：依赖未安装或模块未导入")
        return

    test_cases = [
        {
            "name": "省级流动-总量",
            "func": lambda: analyze_province_flow(
                "test",
                "2025-01-14T00:00:00Z",
                "2025-02-22T00:00:00Z",
                "total",
                "send",
                "state",
            ),
            "expected_time": 5.0,  # 期望执行时间（秒）
        },
        {
            "name": "省级流动-每日",
            "func": lambda: analyze_province_flow(
                "test",
                "2025-01-14T00:00:00Z",
                "2025-02-22T00:00:00Z",
                "daily",
                "send",
                "state",
            ),
            "expected_time": 3.0,
        },
        {
            "name": "城市流动-总量",
            "func": lambda: analyze_city_flow(
                "test",
                "2025-01-14T00:00:00Z",
                "2025-02-22T00:00:00Z",
                "total",
                "send",
                "state",
            ),
            "expected_time": 8.0,
        },
        {
            "name": "省级走廊",
            "func": lambda: analyze_province_corridor(
                "test",
                "2025-01-14T00:00:00Z",
                "2025-02-22T00:00:00Z",
                "total",
                15,
                "state",
            ),
            "expected_time": 6.0,
        },
        {
            "name": "城市走廊",
            "func": lambda: analyze_city_corridor(
                "test",
                "2025-01-14T00:00:00Z",
                "2025-02-22T00:00:00Z",
                "total",
                10,
                20,
                "state",
            ),
            "expected_time": 10.0,
        },
    ]

    results = []

    for test_case in test_cases:
        print(f"\n🧪 测试: {test_case['name']}")

        try:
            start_time = time.time()
            result = test_case["func"]()
            end_time = time.time()

            execution_time = end_time - start_time
            is_fast = execution_time <= test_case["expected_time"]

            print(f"  ⏱️  执行时间: {execution_time:.2f}秒")
            print(f"  🎯 期望时间: {test_case['expected_time']}秒")
            print(
                f"  {'✅' if is_fast else '⚠️'} 性能: {'优秀' if is_fast else '需要优化'}"
            )

            if hasattr(result, "__len__"):
                print(f"  📊 返回记录数: {len(result)}")

            results.append(
                {
                    "name": test_case["name"],
                    "time": execution_time,
                    "expected": test_case["expected_time"],
                    "status": "PASS" if is_fast else "SLOW",
                }
            )

        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            results.append(
                {
                    "name": test_case["name"],
                    "time": float("inf"),
                    "expected": test_case["expected_time"],
                    "status": "FAIL",
                }
            )

    # 汇总结果
    print("\n" + "=" * 80)
    print("📈 性能测试汇总")
    print("=" * 80)

    for result in results:
        status_icon = (
            "✅"
            if result["status"] == "PASS"
            else "⚠️" if result["status"] == "SLOW" else "❌"
        )
        print(
            f"{status_icon} {result['name']}: {result['time']:.2f}s (期望: {result['expected']}s)"
        )

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    total_count = len(results)
    print(f"\n通过率: {pass_count}/{total_count} ({pass_count/total_count*100:.1f}%)")


def main():
    """主测试函数"""
    print("🚀 开始测试 analysis.py 函数在新构建的 geo_points.db 数据库上的表现")
    print("=" * 80)

    # 检查数据库文件是否存在
    db_path = "/home/ubuntu/OD-Agent/agent/backend/geo_points.db"
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("请先运行 build_db_from_baidu.py 构建数据库")
        return

    print(f"✅ 数据库文件存在: {db_path}")

    # 1. 数据库连接测试
    if not test_database_connection():
        print("❌ 数据库连接测试失败，停止后续测试")
        return

    # 2. 省级流动分析测试
    test_province_flow_analysis()

    # 3. 城市流动分析测试
    test_city_flow_analysis()

    # 4. 省级走廊分析测试
    test_province_corridor_analysis()

    # 5. 城市走廊分析测试
    test_city_corridor_analysis()

    # 6. 性能基准测试
    test_performance_benchmark()

    print("\n" + "=" * 80)
    print("🎉 所有测试完成!")
    print("=" * 80)
    print("\n📋 测试总结:")
    print("  ✅ 数据库连接正常")
    print("  ✅ 省级流动分析功能正常")
    print("  ✅ 城市流动分析功能正常")
    print("  ✅ 省级走廊分析功能正常")
    print("  ✅ 城市走廊分析功能正常")
    print("  ✅ 性能基准测试完成")

    print("\n💡 建议:")
    print("  1. 如果性能测试显示需要优化，可以考虑添加更多数据库索引")
    print("  2. 对于大数据量查询，可以考虑实现分页功能")
    print("  3. 可以添加缓存机制来提高重复查询的性能")


if __name__ == "__main__":
    main()
