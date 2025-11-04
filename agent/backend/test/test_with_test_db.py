#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用生成的测试数据库 geo_points.db 测试分析函数
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量指向测试数据库
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "../geo_points.db")
os.environ["DB_PATH"] = TEST_DB_PATH
os.environ["TABLE_PLACES"] = "places"
os.environ["TABLE_RELATIONS"] = "relations"
os.environ["TABLE_DYNA"] = "dyna"

# 导入分析函数
from analysis import (
    analyze_province_flow,
    analyze_city_flow,
    analyze_province_corridor,
    analyze_city_corridor,
)

print("=" * 70)
print("使用测试数据库测试分析函数")
print("=" * 70)
print(f"\n数据库路径: {TEST_DB_PATH}")

# 检查数据库是否存在
if not os.path.exists(TEST_DB_PATH):
    print(f"\n❌ 错误: 测试数据库不存在: {TEST_DB_PATH}")
    print("请先运行: python generate_test_db.py")
    sys.exit(1)

print(f"✅ 数据库存在 ({os.path.getsize(TEST_DB_PATH) / (1024*1024):.2f} MB)\n")

# 测试 1: 省级流量分析
print("\n" + "=" * 70)
print("测试 1: 省级流量分析 (总量模式)")
print("=" * 70)

try:
    result = analyze_province_flow(
        period_type="test",
        start="2025-01-01T00:00:00Z",
        end="2025-01-08T00:00:00Z",
        date_mode="total",
        direction="send",
        dyna_type="state",
    )
    print(f"\n✅ 返回 {len(result)} 条记录")
    print("\n前 10 名发送省份:")
    print(result.head(10).to_string(index=False))
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()

# 测试 2: 城市流量分析
print("\n" + "=" * 70)
print("测试 2: 城市流量分析 (每日模式)")
print("=" * 70)

try:
    result = analyze_city_flow(
        period_type="test",
        start="2025-01-01T00:00:00Z",
        end="2025-01-03T00:00:00Z",
        date_mode="daily",
        direction="send",
        dyna_type="state",
    )
    print(f"\n✅ 返回 {len(result)} 条记录")
    print("\n前 15 条城市流量记录:")
    print(result.head(15).to_string(index=False))
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()

# 测试 3: 省级通道分析
print("\n" + "=" * 70)
print("测试 3: 省级通道分析 (Top 10)")
print("=" * 70)

try:
    result = analyze_province_corridor(
        period_type="test",
        start="2025-01-01T00:00:00Z",
        end="2025-01-31T00:00:00Z",
        date_mode="total",
        topk=10,
        dyna_type="state",
    )
    print(f"\n✅ 返回 {len(result)} 条记录")
    print("\n前 10 名省际通道:")
    print(result.to_string(index=False))
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()

# 测试 4: 城市通道分析
print("\n" + "=" * 70)
print("测试 4: 城市通道分析 (省内/省际)")
print("=" * 70)

try:
    result = analyze_city_corridor(
        period_type="test",
        start="2025-01-01T00:00:00Z",
        end="2025-01-31T00:00:00Z",
        date_mode="total",
        topk_intra=5,
        topk_inter=10,
        dyna_type="state",
    )

    print(f"\n✅ 返回省内通道 {len(result['intra_province'])} 条")
    print(f"✅ 返回省际通道 {len(result['inter_province'])} 条")

    print("\n前 5 名省内通道:")
    print(result["intra_province"].to_string(index=False))

    print("\n前 10 名省际通道:")
    print(result["inter_province"].to_string(index=False))
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ 所有测试完成!")
print("=" * 70)
print("\n提示:")
print("  1. 测试数据库包含 24 个城市，16,560 条 OD 记录")
print("  2. 时间范围: 2025-01-01 到 2025-01-30")
print("  3. 如需重新生成数据库: python generate_test_db.py")
print("=" * 70)
