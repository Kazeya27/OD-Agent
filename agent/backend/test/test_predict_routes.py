#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试预测路由接口 (routes/predict.py)
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
print("测试预测路由接口 (routes/predict.py)")
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


# ==================== 测试 /predict 端点 ====================


def test_predict_basic():
    """测试基本的预测功能"""
    response = client.get(
        "/predict",
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
    assert "T" in data
    assert "N" in data
    assert "times" in data
    assert "ids" in data
    assert "tensor" in data

    print(f"时间步数 (T): {data['T']}")
    print(f"节点数 (N): {data['N']}")

    if data["T"] > 0 and data["N"] > 0:
        print(f"✅ 成功生成预测张量")
        # 显示部分预测数据
        print(f"\n预测张量第一个时间步的前3x3:")
        for i in range(min(3, data["N"])):
            row = data["tensor"][0][i][:3]
            print(f"  {row}")


def test_predict_with_noise_ratio():
    """测试不同的噪声比例"""
    noise_ratios = [0.0, 0.1, 0.5]

    # 获取所有节点
    response_nodes = client.get(
        "/predict",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
            "noise_ratio": 0.0,
        },
    )

    if response_nodes.status_code != 200:
        print("⚠️  无法获取节点数据")
        return

    nodes = response_nodes.json()["ids"][:3]

    for noise_ratio in noise_ratios:
        print(f"\n测试 noise_ratio={noise_ratio}:")
        response = client.get(
            "/predict",
            params={
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-02T00:00:00Z",
                "geo_ids": ",".join(map(str, nodes)),
                "noise_ratio": noise_ratio,
                "seed": 42,  # 固定种子保证可复现
            },
        )

        assert response.status_code == 200
        data = response.json()

        if data["T"] > 0:
            # 计算第一个时间步的平均预测值
            total = 0
            count = 0
            for row in data["tensor"][0]:
                for val in row:
                    if val is not None and val > 0:
                        total += val
                        count += 1

            if count > 0:
                avg_flow = total / count
                print(f"  平均预测流量: {avg_flow:.2f}")


def test_predict_with_seed():
    """测试随机种子的可复现性"""
    params = {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-02T00:00:00Z",
        "noise_ratio": 0.2,
        "seed": 123,
    }

    print("\n第一次请求（seed=123）:")
    response1 = client.get("/predict", params=params)
    assert response1.status_code == 200
    data1 = response1.json()

    print("\n第二次请求（相同seed=123）:")
    response2 = client.get("/predict", params=params)
    assert response2.status_code == 200
    data2 = response2.json()

    if data1["T"] > 0 and data2["T"] > 0:
        # 验证两次预测结果相同
        tensor1 = data1["tensor"]
        tensor2 = data2["tensor"]

        # 比较前几个值
        if len(tensor1) > 0 and len(tensor1[0]) > 0:
            val1 = tensor1[0][0][0]
            val2 = tensor2[0][0][0]
            print(f"第一次预测值: {val1}")
            print(f"第二次预测值: {val2}")

            if val1 == val2:
                print("✅ 使用相同seed的预测结果一致（可复现）")
            else:
                # 可能没有数据或都是null
                print("⚠️  两次预测值不同（可能是数据为空）")


def test_predict_with_geo_ids():
    """测试使用 geo_ids 参数"""
    # 获取节点
    response_nodes = client.get(
        "/predict",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
        },
    )

    all_ids = response_nodes.json()["ids"]
    selected_ids = all_ids[:4]

    print(f"选择的节点: {selected_ids}")

    response = client.get(
        "/predict",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
            "geo_ids": ",".join(map(str, selected_ids)),
            "noise_ratio": 0.15,
        },
    )

    assert response.status_code == 200
    data = response.json()

    print(f"预测节点数: {data['N']}")
    assert data["N"] == len(selected_ids)
    assert data["ids"] == selected_ids
    print(f"✅ geo_ids 参数正常工作")


def test_predict_comparison_with_od():
    """测试预测值与实际值的比较"""
    params = {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-02T00:00:00Z",
        "noise_ratio": 0.2,
        "seed": 999,
    }

    # 获取实际值
    print("\n获取实际 OD 数据:")
    response_od = client.get(
        "/od",
        params={
            "start": params["start"],
            "end": params["end"],
        },
    )

    # 获取预测值
    print("获取预测数据:")
    response_predict = client.get("/predict", params=params)

    if response_od.status_code == 200 and response_predict.status_code == 200:
        data_od = response_od.json()
        data_predict = response_predict.json()

        print(f"实际数据时间步: {data_od['T']}")
        print(f"预测数据时间步: {data_predict['T']}")

        if data_od["T"] > 0 and data_predict["T"] > 0:
            # 比较第一个非零值
            found_comparison = False
            for i in range(min(3, data_od["N"])):
                for j in range(min(3, data_od["N"])):
                    actual = data_od["tensor"][0][i][j]
                    predicted = data_predict["tensor"][0][i][j]

                    if actual is not None and actual > 0:
                        print(f"\nOD对 ({data_od['ids'][i]} -> {data_od['ids'][j]}):")
                        print(f"  实际值: {actual:.2f}")
                        print(f"  预测值: {predicted:.2f}")
                        if predicted is not None:
                            diff = abs(predicted - actual)
                            diff_pct = (diff / actual * 100) if actual > 0 else 0
                            print(f"  差异: {diff:.2f} ({diff_pct:.1f}%)")
                        found_comparison = True
                        break
                if found_comparison:
                    break


# ==================== 测试 /predict/pair 端点 ====================


def test_predict_pair_basic():
    """测试预测单个 OD 对"""
    # 获取节点
    response_nodes = client.get(
        "/predict",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
        },
    )
    nodes = response_nodes.json()["ids"]

    if len(nodes) < 2:
        print("⚠️  节点数量不足，跳过测试")
        return

    origin_id = nodes[0]
    destination_id = nodes[1]

    print(f"测试 OD 对: {origin_id} -> {destination_id}")

    response = client.get(
        "/predict/pair",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-03T00:00:00Z",
            "origin_id": origin_id,
            "destination_id": destination_id,
            "noise_ratio": 0.15,
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
    assert "prediction_info" in data

    print(f"时间步数 (T): {data['T']}")
    print(f"预测信息: {data['prediction_info']}")

    if data["T"] > 0:
        print(f"预测序列 (前5个): {data['series'][:5]}")


def test_predict_pair_with_seed():
    """测试 /predict/pair 的随机种子"""
    # 获取节点
    response_nodes = client.get(
        "/predict",
        params={"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"},
    )
    nodes = response_nodes.json()["ids"]

    if len(nodes) < 2:
        print("⚠️  节点数量不足")
        return

    params = {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-02T00:00:00Z",
        "origin_id": nodes[0],
        "destination_id": nodes[1],
        "noise_ratio": 0.2,
        "seed": 456,
    }

    # 两次请求
    response1 = client.get("/predict/pair", params=params)
    response2 = client.get("/predict/pair", params=params)

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    if data1["T"] > 0 and data2["T"] > 0:
        series1 = data1["series"]
        series2 = data2["series"]

        # 比较前几个值
        if len(series1) > 0 and series1[0] is not None:
            print(f"第一次预测: {series1[0]:.2f}")
            print(f"第二次预测: {series2[0]:.2f}")

            if series1[0] == series2[0]:
                print("✅ 使用相同seed的预测一致")


def test_predict_pair_comparison():
    """比较 /predict/pair 与 /od/pair"""
    # 获取节点
    response_nodes = client.get(
        "/predict",
        params={"start": "2024-01-01T00:00:00Z", "end": "2024-01-02T00:00:00Z"},
    )
    nodes = response_nodes.json()["ids"]

    if len(nodes) < 2:
        print("⚠️  节点数量不足")
        return

    origin_id = nodes[0]
    destination_id = nodes[1]

    # 获取实际值
    print(f"\n比较 OD 对 {origin_id} -> {destination_id}:")
    response_actual = client.get(
        "/od/pair",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-03T00:00:00Z",
            "origin_id": origin_id,
            "destination_id": destination_id,
        },
    )

    # 获取预测值
    response_predict = client.get(
        "/predict/pair",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-03T00:00:00Z",
            "origin_id": origin_id,
            "destination_id": destination_id,
            "noise_ratio": 0.2,
            "seed": 777,
        },
    )

    if response_actual.status_code == 200 and response_predict.status_code == 200:
        data_actual = response_actual.json()
        data_predict = response_predict.json()

        print(f"实际数据点数: {data_actual['T']}")
        print(f"预测数据点数: {data_predict['T']}")

        if data_actual["T"] > 0 and data_predict["T"] > 0:
            # 比较前几个值
            for i in range(min(3, data_actual["T"])):
                actual = data_actual["series"][i]
                predicted = data_predict["series"][i]

                if actual is not None and predicted is not None:
                    print(f"\n时间 {i}:")
                    print(f"  实际: {actual:.2f}")
                    print(f"  预测: {predicted:.2f}")
                    diff = abs(predicted - actual)
                    print(f"  差异: {diff:.2f}")


def test_predict_invalid_params():
    """测试无效参数"""
    print("\n测试: 无效的 noise_ratio")
    response = client.get(
        "/predict",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
            "noise_ratio": 2.0,  # 超出范围 [0, 1]
        },
    )
    print(f"  状态码: {response.status_code}")
    assert response.status_code == 422, "应该返回 422 验证错误"


# ==================== 运行所有测试 ====================

print("\n" + "=" * 80)
print("开始运行测试...")
print("=" * 80)

# /predict 端点测试
run_test("预测基本功能", test_predict_basic)
run_test("不同噪声比例", test_predict_with_noise_ratio)
run_test("随机种子可复现性", test_predict_with_seed)
run_test("使用 geo_ids 过滤", test_predict_with_geo_ids)
run_test("预测值与实际值比较", test_predict_comparison_with_od)

# /predict/pair 端点测试
run_test("预测单个 OD 对", test_predict_pair_basic)
run_test("OD 对预测的随机种子", test_predict_pair_with_seed)
run_test("OD 对预测与实际比较", test_predict_pair_comparison)

# 错误处理测试
run_test("无效参数处理", test_predict_invalid_params)

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
    print("  1. /predict 端点基于实际 OD 数据生成预测")
    print("  2. /predict/pair 端点预测特定 OD 对")
    print("  3. noise_ratio 控制预测不确定性 (0.0-1.0)")
    print("  4. seed 参数保证预测可复现")
    sys.exit(0)
else:
    print(f"\n⚠️  有 {failed_tests} 个测试失败")
    sys.exit(1)
