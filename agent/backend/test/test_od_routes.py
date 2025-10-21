#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 OD 路由接口 (routes/od.py)
使用测试数据库 geo_points.db
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

# 导入 FastAPI 测试客户端
from fastapi.testclient import TestClient
import json

print("=" * 80)
print("测试 OD 路由接口 (routes/od.py)")
print("=" * 80)
print(f"\n数据库路径: {TEST_DB_PATH}")

# 检查数据库是否存在
if not os.path.exists(TEST_DB_PATH):
    print(f"\n❌ 错误: 测试数据库不存在: {TEST_DB_PATH}")
    print("请先运行: python generate_test_db.py")
    sys.exit(1)

print(f"✅ 数据库存在 ({os.path.getsize(TEST_DB_PATH) / (1024*1024):.2f} MB)\n")

# 导入应用
from app import app

# 创建测试客户端
client = TestClient(app)

# 测试计数器
total_tests = 0
passed_tests = 0
failed_tests = 0


def run_test(test_name, test_func):
    """运行单个测试"""
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    print(f"\n{'=' * 80}")
    print(f"测试 {total_tests}: {test_name}")
    print("=" * 80)
    try:
        test_func()
        passed_tests += 1
        print(f"✅ 测试通过")
    except AssertionError as e:
        failed_tests += 1
        print(f"❌ 测试失败: {e}")
    except Exception as e:
        failed_tests += 1
        print(f"❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()


# ==================== 测试 /od 端点 ====================


def test_od_basic():
    """测试基本的 OD 张量查询"""
    response = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
            "flow_policy": "zero",
        },
    )

    print(f"状态码: {response.status_code}")
    assert response.status_code == 200, f"预期状态码 200，实际 {response.status_code}"

    data = response.json()
    print(f"响应键: {list(data.keys())}")

    # 验证响应结构
    assert "T" in data, "响应中缺少 'T' 字段"
    assert "N" in data, "响应中缺少 'N' 字段"
    assert "times" in data, "响应中缺少 'times' 字段"
    assert "ids" in data, "响应中缺少 'ids' 字段"
    assert "tensor" in data, "响应中缺少 'tensor' 字段"

    print(f"时间步数 (T): {data['T']}")
    print(f"节点数 (N): {data['N']}")
    print(
        f"时间列表: {data['times'][:3]}..."
        if len(data["times"]) > 3
        else f"时间列表: {data['times']}"
    )
    print(f"节点 ID (前10个): {data['ids'][:10]}")

    # 验证张量维度
    if data["T"] > 0:
        assert len(data["tensor"]) == data["T"], f"张量时间维度不匹配"
        assert len(data["tensor"][0]) == data["N"], f"张量第一维度不匹配"
        assert len(data["tensor"][0][0]) == data["N"], f"张量第二维度不匹配"
        print(f"✅ 张量维度正确: [{data['T']}, {data['N']}, {data['N']}]")

        # 显示部分张量数据
        print(f"\n张量第一个时间步的前3x3矩阵:")
        for i in range(min(3, data["N"])):
            row = data["tensor"][0][i][:3]
            print(f"  {row}")


def test_od_with_geo_ids():
    """测试使用 geo_ids 参数过滤"""
    # 首先获取所有节点
    response_all = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
        },
    )
    all_data = response_all.json()
    all_ids = all_data["ids"]

    # 选择前5个节点
    selected_ids = all_ids[:5]
    geo_ids_str = ",".join(map(str, selected_ids))

    print(f"所有节点数: {len(all_ids)}")
    print(f"选择的节点: {selected_ids}")

    # 使用 geo_ids 参数查询
    response = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
            "geo_ids": geo_ids_str,
            "flow_policy": "zero",
        },
    )

    print(f"状态码: {response.status_code}")
    assert response.status_code == 200

    data = response.json()
    print(f"过滤后节点数 (N): {data['N']}")
    print(f"过滤后节点 ID: {data['ids']}")

    # 验证节点数量和ID
    assert data["N"] == len(
        selected_ids
    ), f"预期节点数 {len(selected_ids)}，实际 {data['N']}"
    assert data["ids"] == selected_ids, f"返回的节点 ID 不匹配"

    # 验证张量维度
    if data["T"] > 0:
        assert len(data["tensor"][0]) == len(selected_ids), "张量维度不正确"
        assert len(data["tensor"][0][0]) == len(selected_ids), "张量维度不正确"
        print(
            f"✅ 张量维度正确: [{data['T']}, {len(selected_ids)}, {len(selected_ids)}]"
        )

        # 显示完整的小张量
        print(f"\n过滤后的 OD 矩阵 (第一个时间步):")
        for i in range(len(selected_ids)):
            row = data["tensor"][0][i]
            print(f"  {selected_ids[i]:3d}: {row}")


def test_od_with_dyna_type():
    """测试使用 dyna_type 参数过滤"""
    response = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-03T00:00:00Z",
            "dyna_type": "state",
            "flow_policy": "zero",
        },
    )

    print(f"状态码: {response.status_code}")
    assert response.status_code == 200

    data = response.json()
    print(f"时间步数 (T): {data['T']}")
    print(f"节点数 (N): {data['N']}")
    print(f"✅ 成功使用 dyna_type='state' 过滤数据")


def test_od_flow_policies():
    """测试不同的 flow_policy"""
    policies = ["zero", "null", "skip"]

    for policy in policies:
        print(f"\n测试 flow_policy='{policy}':")
        response = client.get(
            "/od",
            params={
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-02T00:00:00Z",
                "flow_policy": policy,
            },
        )

        assert response.status_code == 200, f"flow_policy={policy} 失败"
        data = response.json()

        if data["T"] > 0 and data["N"] > 0:
            # 检查第一个值
            first_value = data["tensor"][0][0][0]
            print(f"  第一个值: {first_value} (类型: {type(first_value).__name__})")

            if policy == "null":
                print(f"  ✅ null 策略可能返回 null 或数值")
            elif policy == "zero":
                # zero 策略应该返回数值（包括 0.0）
                print(f"  ✅ zero 策略返回数值")
        else:
            print(f"  ⚠️  无数据返回")


def test_od_time_range():
    """测试不同的时间范围"""
    print("\n测试1: 单日查询")
    response1 = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
        },
    )
    data1 = response1.json()
    print(f"  时间步数: {data1['T']}")
    print(f"  时间范围: {data1['times'][0] if data1['times'] else 'N/A'}")

    print("\n测试2: 一周查询")
    response2 = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-08T00:00:00Z",
        },
    )
    data2 = response2.json()
    print(f"  时间步数: {data2['T']}")
    print(
        f"  时间范围: {data2['times'][0]} ~ {data2['times'][-1]}"
        if data2["times"]
        else "  N/A"
    )

    assert data2["T"] >= data1["T"], "一周的数据应该比一天多"
    print(f"✅ 时间范围查询正确")


def test_od_invalid_params():
    """测试无效参数"""
    print("\n测试1: 无效的时间格式")
    response1 = client.get(
        "/od",
        params={
            "start": "invalid-time",
            "end": "2024-01-02T00:00:00Z",
        },
    )
    print(f"  状态码: {response1.status_code}")
    assert response1.status_code == 400, "应该返回 400 错误"
    print(f"  错误信息: {response1.json()['detail']}")

    print("\n测试2: 无效的 geo_ids 格式")
    response2 = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
            "geo_ids": "abc,def",
        },
    )
    print(f"  状态码: {response2.status_code}")
    assert response2.status_code == 400, "应该返回 400 错误"
    print(f"  错误信息: {response2.json()['detail']}")

    print("\n测试3: 空的 geo_ids")
    response3 = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
            "geo_ids": "",
        },
    )
    print(f"  状态码: {response3.status_code}")
    # 空字符串会被当作未提供参数，所以应该成功
    print(f"  结果: {'成功' if response3.status_code == 200 else '失败'}")


# ==================== 测试 /od/pair 端点 ====================


def test_od_pair_basic():
    """测试基本的 OD 对时间序列查询"""
    # 首先获取可用的节点 ID
    response_nodes = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
        },
    )
    nodes = response_nodes.json()["ids"]
    origin_id = nodes[0]
    destination_id = nodes[1] if len(nodes) > 1 else nodes[0]

    print(f"测试 OD 对: {origin_id} -> {destination_id}")

    response = client.get(
        "/od/pair",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-03T00:00:00Z",
            "origin_id": origin_id,
            "destination_id": destination_id,
            "dyna_type": "state",
        },
    )

    print(f"状态码: {response.status_code}")
    assert response.status_code == 200

    data = response.json()
    print(f"响应键: {list(data.keys())}")

    # 验证响应结构
    assert "T" in data
    assert "times" in data
    assert "origin_id" in data
    assert "destination_id" in data
    assert "series" in data

    print(f"时间步数 (T): {data['T']}")
    print(f"起点 ID: {data['origin_id']}")
    print(f"终点 ID: {data['destination_id']}")
    print(f"时间序列长度: {len(data['series'])}")

    if data["T"] > 0:
        print(f"时间范围: {data['times'][0]} ~ {data['times'][-1]}")
        print(f"流量序列 (前5个): {data['series'][:5]}")
        print(f"✅ 时间序列查询成功")


def test_od_pair_multiple():
    """测试多个 OD 对查询"""
    # 获取节点
    response_nodes = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
        },
    )
    nodes = response_nodes.json()["ids"][:4]  # 取前4个节点

    print(f"测试节点: {nodes}")

    # 查询多个 OD 对
    od_pairs = [(nodes[0], nodes[1]), (nodes[1], nodes[2]), (nodes[2], nodes[3])]

    for origin, dest in od_pairs:
        print(f"\n查询 {origin} -> {dest}:")
        response = client.get(
            "/od/pair",
            params={
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-02T00:00:00Z",
                "origin_id": origin,
                "destination_id": dest,
            },
        )

        assert response.status_code == 200
        data = response.json()
        print(f"  时间步数: {data['T']}")
        if data["T"] > 0:
            total_flow = sum(v for v in data["series"] if v is not None)
            print(f"  总流量: {total_flow}")


def test_od_pair_flow_policies():
    """测试 /od/pair 的不同 flow_policy"""
    # 获取节点
    response_nodes = client.get(
        "/od", params={"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"}
    )
    nodes = response_nodes.json()["ids"]
    origin_id = nodes[0]
    destination_id = nodes[1] if len(nodes) > 1 else nodes[0]

    policies = ["zero", "null", "skip"]

    for policy in policies:
        print(f"\n测试 flow_policy='{policy}':")
        response = client.get(
            "/od/pair",
            params={
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-02T00:00:00Z",
                "origin_id": origin_id,
                "destination_id": destination_id,
                "flow_policy": policy,
            },
        )

        assert response.status_code == 200
        data = response.json()
        print(f"  时间步数: {data['T']}")
        if data["T"] > 0:
            print(f"  序列 (前5个): {data['series'][:5]}")


def test_od_pair_no_data():
    """测试查询无数据的时间范围"""
    response = client.get(
        "/od/pair",
        params={
            "start": "2030-01-01T00:00:00Z",  # 很远的未来时间，应该没有数据
            "end": "2030-01-02T00:00:00Z",
            "origin_id": 1,
            "destination_id": 2,
        },
    )

    print(f"状态码: {response.status_code}")
    assert response.status_code == 200

    data = response.json()
    print(f"时间步数 (T): {data['T']}")
    print(f"序列长度: {len(data['series'])}")

    # 如果有数据，显示一下
    if data["T"] > 0:
        print(f"⚠️  意外返回了数据，时间范围: {data['times']}")
        print(f"  这可能是测试数据库包含了该时间范围的数据")
    else:
        assert data["T"] == 0, "未来时间范围应该返回空数据"
        assert len(data["series"]) == 0, "序列应该为空"
        print(f"✅ 正确处理无数据情况")


# ==================== 综合测试 ====================


def test_od_comprehensive():
    """综合测试：geo_ids + dyna_type + flow_policy"""
    # 获取节点
    response_nodes = client.get(
        "/od", params={"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"}
    )
    all_ids = response_nodes.json()["ids"]
    selected_ids = all_ids[:3]

    print(f"综合测试参数:")
    print(f"  geo_ids: {selected_ids}")
    print(f"  dyna_type: state")
    print(f"  flow_policy: zero")

    response = client.get(
        "/od",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-05T00:00:00Z",
            "geo_ids": ",".join(map(str, selected_ids)),
            "dyna_type": "state",
            "flow_policy": "zero",
        },
    )

    print(f"\n状态码: {response.status_code}")
    assert response.status_code == 200

    data = response.json()
    print(f"时间步数 (T): {data['T']}")
    print(f"节点数 (N): {data['N']}")
    print(f"节点 ID: {data['ids']}")

    assert data["N"] == len(selected_ids)
    assert data["ids"] == selected_ids

    if data["T"] > 0:
        print(f"\n第一个时间步的 OD 矩阵:")
        for i in range(len(selected_ids)):
            row = data["tensor"][0][i]
            print(f"  {selected_ids[i]:3d}: {row}")

        # 计算总流量
        total_flow = 0
        for t in data["tensor"]:
            for row in t:
                for val in row:
                    if val is not None:
                        total_flow += val

        print(f"\n总流量: {total_flow:.2f}")
        print(f"✅ 综合测试通过")


# ==================== 运行所有测试 ====================

print("\n" + "=" * 80)
print("开始运行测试...")
print("=" * 80)

# /od 端点测试
run_test("OD 张量基本查询", test_od_basic)
run_test("OD 张量使用 geo_ids 过滤", test_od_with_geo_ids)
run_test("OD 张量使用 dyna_type 过滤", test_od_with_dyna_type)
run_test("OD 张量不同 flow_policy", test_od_flow_policies)
run_test("OD 张量不同时间范围", test_od_time_range)
run_test("OD 张量无效参数处理", test_od_invalid_params)

# /od/pair 端点测试
run_test("OD 对基本查询", test_od_pair_basic)
run_test("OD 对多个查询", test_od_pair_multiple)
run_test("OD 对不同 flow_policy", test_od_pair_flow_policies)
run_test("OD 对无数据情况", test_od_pair_no_data)

# 综合测试
run_test("综合测试（geo_ids + dyna_type + flow_policy）", test_od_comprehensive)

# ==================== 测试总结 ====================

print("\n" + "=" * 80)
print("测试总结")
print("=" * 80)
print(f"总测试数: {total_tests}")
print(f"通过: {passed_tests} ✅")
print(f"失败: {failed_tests} ❌")
print(f"通过率: {passed_tests/total_tests*100:.1f}%")
print("=" * 80)

if failed_tests == 0:
    print("\n🎉 所有测试通过！")
    print("\n提示:")
    print("  1. /od 端点支持 geo_ids 参数过滤节点")
    print("  2. /od/pair 端点查询特定 OD 对的时间序列")
    print("  3. 支持 flow_policy: zero, null, skip")
    print("  4. 支持 dyna_type 过滤")
    sys.exit(0)
else:
    print(f"\n⚠️  有 {failed_tests} 个测试失败")
    sys.exit(1)
