#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成测试数据库 geo_points.db
创建与 build_db_from_baidu.py 一致的表结构，并填充测试数据
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta

# 数据库配置
DB_FILE = "geo_points.db"
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(TEST_DIR, DB_FILE)

print("\n" + "=" * 70)
print("生成测试数据库")
print("=" * 70)

# 删除旧数据库
if os.path.exists(DB_PATH):
    confirm = input(f"\n⚠️  数据库 {DB_FILE} 已存在，是否删除并重建? (y/N): ")
    if confirm.lower() == "y":
        os.remove(DB_PATH)
        print(f"✅ 已删除旧数据库")
    else:
        print("❌ 操作取消")
        exit(0)

print(f"\n📁 创建数据库: {DB_PATH}")

# 创建数据库连接
conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
c = conn.cursor()

# 创建表结构（与 build_db_from_baidu.py 一致）
print("\n📐 创建表结构...")

c.execute(
    """
    CREATE TABLE places (
        geo_id INTEGER PRIMARY KEY,
        type TEXT,
        coordinates TEXT,
        name TEXT NOT NULL,
        province TEXT
    )
"""
)

c.execute(
    """
    CREATE TABLE relations (
        rel_id INTEGER PRIMARY KEY,
        type TEXT,
        origin_id INTEGER NOT NULL,
        destination_id INTEGER NOT NULL,
        cost REAL
    )
"""
)

c.execute(
    """
    CREATE TABLE dyna (
        dyna_id INTEGER PRIMARY KEY,
        type TEXT,
        time TEXT NOT NULL,
        origin_id INTEGER NOT NULL,
        destination_id INTEGER NOT NULL,
        flow REAL
    )
"""
)

print("✅ 表结构创建完成")

# 插入测试地点数据
print("\n📍 插入测试地点数据...")

test_places = [
    # 直辖市
    (0, "Point", "116.4074,39.9042", "北京", "北京"),
    (1, "Point", "121.4737,31.2304", "上海", "上海"),
    (2, "Point", "106.5516,29.5630", "重庆", "重庆"),
    (3, "Point", "117.2008,39.0842", "天津", "天津"),
    # 广东省
    (10, "Point", "113.2644,23.1291", "广州", "广东"),
    (11, "Point", "114.0579,22.5431", "深圳", "广东"),
    (12, "Point", "113.5107,23.3790", "佛山", "广东"),
    (13, "Point", "113.1220,23.0250", "东莞", "广东"),
    # 浙江省
    (20, "Point", "120.1551,30.2741", "杭州", "浙江"),
    (21, "Point", "121.5440,29.8683", "宁波", "浙江"),
    (22, "Point", "120.7520,28.0002", "温州", "浙江"),
    # 江苏省
    (30, "Point", "118.7969,32.0603", "南京", "江苏"),
    (31, "Point", "120.5853,31.2989", "苏州", "江苏"),
    (32, "Point", "120.3019,31.5747", "无锡", "江苏"),
    # 山东省
    (40, "Point", "117.1205,36.6519", "济南", "山东"),
    (41, "Point", "120.3826,36.0671", "青岛", "山东"),
    (42, "Point", "117.0230,36.8140", "淄博", "山东"),
    # 四川省
    (50, "Point", "104.0665,30.5723", "成都", "四川"),
    (51, "Point", "104.7770,29.3520", "自贡", "四川"),
    # 湖北省
    (60, "Point", "114.3055,30.5931", "武汉", "湖北"),
    (61, "Point", "112.1387,32.0426", "襄阳", "湖北"),
    # 陕西省
    (70, "Point", "108.9398,34.3416", "西安", "陕西"),
    # 河南省
    (80, "Point", "113.6254,34.7466", "郑州", "河南"),
    # 湖南省
    (90, "Point", "112.9388,28.2282", "长沙", "湖南"),
]

c.executemany("INSERT INTO places VALUES (?,?,?,?,?)", test_places)
print(f"✅ 已插入 {len(test_places)} 个地点")

# 插入测试关系数据
print("\n🔗 插入测试关系数据...")

test_relations = []
rel_id = 0

# 为每对城市创建距离关系
for i, place1 in enumerate(test_places):
    for j, place2 in enumerate(test_places):
        if i != j:
            origin_id = place1[0]
            dest_id = place2[0]
            # 生成随机距离（单位：公里）
            distance = random.uniform(100, 2000)
            test_relations.append(
                (rel_id, "geo", origin_id, dest_id, round(distance, 2))
            )
            rel_id += 1

c.executemany("INSERT INTO relations VALUES (?,?,?,?,?)", test_relations)
print(f"✅ 已插入 {len(test_relations)} 条关系记录")

# 插入测试 OD 数据（2024年及之后）
print("\n📊 插入测试 OD 数据...")

test_dyna = []
dyna_id = 0

# 生成2024年1月的数据（30天）
start_date = datetime(2025, 1, 1)

for day in range(365):
    current_date = start_date + timedelta(days=day)
    time_str = current_date.strftime("%Y-%m-%dT00:00:00Z")

    # 为每对城市生成流量数据
    for place1 in test_places:
        for place2 in test_places:
            if place1[0] != place2[0]:
                origin_id = place1[0]
                dest_id = place2[0]
                origin_province = place1[4]
                dest_province = place2[4]

                # 基础流量
                base_flow = random.uniform(100, 500)

                # 热门线路流量更大
                hot_routes = [
                    (0, 1),  # 北京-上海
                    (1, 0),  # 上海-北京
                    (10, 11),  # 广州-深圳
                    (11, 10),  # 深圳-广州
                    (20, 21),  # 杭州-宁波
                    (30, 31),  # 南京-苏州
                ]
                if (origin_id, dest_id) in hot_routes:
                    base_flow *= random.uniform(5, 10)

                # 同省流量加成
                if origin_province == dest_province:
                    base_flow *= random.uniform(1.5, 2.5)

                # 周末流量增加
                if current_date.weekday() >= 5:
                    base_flow *= random.uniform(1.2, 1.5)

                test_dyna.append(
                    (
                        dyna_id,
                        "state",
                        time_str,
                        origin_id,
                        dest_id,
                        round(base_flow, 2),
                    )
                )
                dyna_id += 1

# 批量插入
batch_size = 5000
for i in range(0, len(test_dyna), batch_size):
    batch = test_dyna[i : i + batch_size]
    c.executemany("INSERT INTO dyna VALUES (?,?,?,?,?,?)", batch)

conn.commit()
print(f"✅ 已插入 {len(test_dyna)} 条 OD 记录")

# 创建索引
print("\n📑 创建索引...")

indexes = [
    ("idx_dyna_time", "dyna", "time"),
    ("idx_dyna_origin", "dyna", "origin_id"),
    ("idx_dyna_destination", "dyna", "destination_id"),
    ("idx_dyna_type", "dyna", "type"),
    ("idx_relations_origin", "relations", "origin_id"),
    ("idx_relations_destination", "relations", "destination_id"),
]

for idx_name, table, column in indexes:
    c.execute(f"CREATE INDEX {idx_name} ON {table}({column})")

print("✅ 索引创建完成")

# 统计信息
print("\n🔍 数据库统计:")
place_count = c.execute("SELECT COUNT(*) FROM places").fetchone()[0]
rel_count = c.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
dyna_count = c.execute("SELECT COUNT(*) FROM dyna").fetchone()[0]

print(f"   地点数: {place_count:,}")
print(f"   关系数: {rel_count:,}")
print(f"   OD记录数: {dyna_count:,}")

if dyna_count > 0:
    time_range = c.execute("SELECT MIN(time), MAX(time) FROM dyna").fetchone()
    print(f"   时间范围: {time_range[0]} 到 {time_range[1]}")

    # 按类型统计
    type_stats = c.execute("SELECT type, COUNT(*) FROM dyna GROUP BY type").fetchall()
    print("\n   按类型统计:")
    for t, cnt in type_stats:
        print(f"     {t}: {cnt:,}")

# 示例数据
print("\n📋 示例地点 (前 10 个):")
places = c.execute("SELECT geo_id, name, province FROM places LIMIT 10").fetchall()
for p in places:
    print(f"   ID {p[0]:2d}: {p[1]:6s} ({p[2]})")

print("\n📋 示例 OD 记录 (前 10 条):")
records = c.execute(
    """
    SELECT d.time, d.origin_id, d.destination_id, d.flow, d.type,
           p1.name as origin_name, p1.province as origin_province,
           p2.name as dest_name, p2.province as dest_province
    FROM dyna d
    LEFT JOIN places p1 ON d.origin_id = p1.geo_id
    LEFT JOIN places p2 ON d.destination_id = p2.geo_id
    LIMIT 10
"""
).fetchall()

for r in records:
    print(f"   {r[0]}: {r[5]}({r[6]}) -> {r[7]}({r[8]}), flow={r[3]:.2f}, type={r[4]}")

# 按省份统计流量（前10名）
print("\n📊 按发送省份统计总流量 (Top 10):")
province_stats = c.execute(
    """
    SELECT p.province, SUM(d.flow) as total_flow
    FROM dyna d
    LEFT JOIN places p ON d.origin_id = p.geo_id
    GROUP BY p.province
    ORDER BY total_flow DESC
    LIMIT 10
"""
).fetchall()

for idx, (province, total) in enumerate(province_stats, 1):
    print(f"   {idx:2d}. {province:6s}: {total:12,.2f}")

conn.close()

# 最终信息
db_size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
print("\n" + "=" * 70)
print("✅ 测试数据库构建完成!")
print("=" * 70)
print(f"\n数据库位置: {DB_PATH}")
print(f"数据库大小: {db_size_mb:.2f} MB")

print("\n使用说明:")
print("1. 将此数据库用于测试:")
print(f"   export DB_PATH={DB_PATH}")
print("\n2. 或在 .env 文件中配置:")
print(f"   DB_PATH={DB_PATH}")
print("   TABLE_PLACES=places")
print("   TABLE_RELATIONS=relations")
print("   TABLE_DYNA=dyna")

print("\n" + "=" * 70)
