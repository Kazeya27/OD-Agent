#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 baidu.geo、baidu.od、baidu.rel 构建数据库
注意：baidu.od 只导入 2024 年之后的数据
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
from tqdm import tqdm

print("\n" + "="*60)
print("从百度数据文件构建数据库")
print("="*60)

# 配置
DB_FILE = 'geo_points.db'
DATA_DIR = './agent/data'
BATCH_SIZE = 10000  # 批量插入大小
MIN_YEAR = 2024  # 只导入此年份及之后的数据

# 文件路径
GEO_FILE = os.path.join(DATA_DIR, 'baidu.geo')
REL_FILE = os.path.join(DATA_DIR, 'baidu.rel')
OD_FILE = os.path.join(DATA_DIR, 'baidu.od')

# 检查文件是否存在
for file_path in [GEO_FILE, REL_FILE, OD_FILE]:
    if not os.path.exists(file_path):
        print(f"❌ 错误: 文件不存在: {file_path}")
        exit(1)

# 删除旧数据库
if os.path.exists(DB_FILE):
    confirm = input(f"\n⚠️  数据库 {DB_FILE} 已存在，是否删除并重建? (y/N): ")
    if confirm.lower() == 'y':
        os.remove(DB_FILE)
        print(f"✅ 已删除旧数据库")
    else:
        print("❌ 操作取消")
        exit(0)

# 创建数据库连接
print(f"\n📁 创建数据库: {DB_FILE}")
conn = sqlite3.connect(DB_FILE, timeout=60, isolation_level=None)  # 增加超时到60秒
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
conn.execute("PRAGMA busy_timeout=60000")  # 60秒忙等待
c = conn.cursor()

# 创建表结构
print("\n📐 创建表结构...")
c.execute('''
    CREATE TABLE places (
        geo_id INTEGER PRIMARY KEY,
        type TEXT,
        coordinates TEXT,
        name TEXT NOT NULL,
        province TEXT
    )
''')

c.execute('''
    CREATE TABLE relations (
        rel_id INTEGER PRIMARY KEY,
        type TEXT,
        origin_id INTEGER NOT NULL,
        destination_id INTEGER NOT NULL,
        cost REAL
    )
''')

c.execute('''
    CREATE TABLE dyna (
        dyna_id INTEGER PRIMARY KEY,
        type TEXT,
        time TEXT NOT NULL,
        origin_id INTEGER NOT NULL,
        destination_id INTEGER NOT NULL,
        flow REAL
    )
''')

print("✅ 表结构创建完成")

# 1. 导入地理数据 (places)
print(f"\n📍 导入地理数据: {GEO_FILE}")
df_geo = pd.read_csv(GEO_FILE, encoding='utf-8')

# 填充缺失的 province 字段
if 'province' not in df_geo.columns:
    df_geo['province'] = ''
else:
    df_geo['province'] = df_geo['province'].fillna('')

# 准备数据并插入
records = df_geo[['geo_id', 'type', 'coordinates', 'name', 'province']].values.tolist()
c.executemany('INSERT INTO places VALUES (?,?,?,?,?)', records)
print(f"✅ 已导入 {len(records)} 个地点")

# 2. 导入关系数据 (relations)
print(f"\n🔗 导入关系数据: {REL_FILE}")
print("   ⏳ 正在处理...")

df_rel = pd.read_csv(REL_FILE, encoding='utf-8')

# 准备数据
df_rel['cost'] = df_rel['cost'].fillna(value=0)
records = df_rel[['rel_id', 'type', 'origin_id', 'destination_id', 'cost']].values.tolist()

# 批量插入
count = 0
for i in tqdm(range(0, len(records), BATCH_SIZE), desc="导入关系"):
    batch = records[i:i+BATCH_SIZE]
    c.executemany('INSERT INTO relations VALUES (?,?,?,?,?)', batch)
    count += len(batch)

print(f"✅ 已导入 {count} 条关系记录")

# 3. 导入 OD 数据 (dyna) - 只导入 2024 年及之后的数据
print(f"\n📊 导入 OD 数据: {OD_FILE}")
print(f"   ⚠️  只导入 {MIN_YEAR} 年及之后的数据")
print("   ⏳ 正在处理...")

# 读取 OD 数据
df_od = pd.read_csv(OD_FILE, encoding='utf-8')

# 检查文件是否为空
if len(df_od) == 0:
    print(f"⚠️  警告: {OD_FILE} 文件为空，跳过 OD 数据导入")
    count = 0
    skipped = 0
else:
    # 提取年份并过滤数据
    df_od['year'] = pd.to_datetime(df_od['time']).dt.year
    skipped = len(df_od[df_od['year'] < MIN_YEAR])
    df_od = df_od[df_od['year'] >= MIN_YEAR]
    
    # 准备数据
    if 'type' not in df_od.columns:
        df_od['type'] = 'state'
    df_od['flow'] = df_od['flow'].fillna(value=0)
    
    # 删除临时列并准备插入
    df_od = df_od.drop('year', axis=1)
    records = df_od[['dyna_id', 'type', 'time', 'origin_id', 'destination_id', 'flow']].values.tolist()
    
    # 批量插入
    count = 0
    for i in tqdm(range(0, len(records), BATCH_SIZE), desc="导入OD数据"):
        batch = records[i:i+BATCH_SIZE]
        c.executemany('INSERT INTO dyna VALUES (?,?,?,?,?,?)', batch)
        count += len(batch)

print(f"✅ 已导入 {count} 条 OD 记录 (跳过 {skipped} 条早期数据)")

# 4. 创建索引
print("\n📑 创建索引...")
print("   ⏳ 这可能需要一些时间...")

indexes = [
    ('idx_dyna_time', 'dyna', 'time'),
    ('idx_dyna_origin', 'dyna', 'origin_id'),
    ('idx_dyna_destination', 'dyna', 'destination_id'),
    ('idx_dyna_type', 'dyna', 'type'),
    ('idx_relations_origin', 'relations', 'origin_id'),
    ('idx_relations_destination', 'relations', 'destination_id'),
]

for idx_name, table, column in tqdm(indexes, desc="创建索引"):
    c.execute(f'CREATE INDEX {idx_name} ON {table}({column})')

print("✅ 索引创建完成")

# 5. 验证数据
print("\n🔍 数据库统计:")
place_count = c.execute('SELECT COUNT(*) FROM places').fetchone()[0]
rel_count = c.execute('SELECT COUNT(*) FROM relations').fetchone()[0]
dyna_count = c.execute('SELECT COUNT(*) FROM dyna').fetchone()[0]

print(f"   地点数: {place_count:,}")
print(f"   关系数: {rel_count:,}")
print(f"   OD记录数: {dyna_count:,}")

if dyna_count > 0:
    time_range = c.execute('SELECT MIN(time), MAX(time) FROM dyna').fetchone()
    print(f"   时间范围: {time_range[0]} 到 {time_range[1]}")
    
    # 按类型统计
    type_stats = c.execute('SELECT type, COUNT(*) FROM dyna GROUP BY type').fetchall()
    print("\n   按类型统计:")
    for t, cnt in type_stats:
        print(f"     {t}: {cnt:,}")

# 示例数据
print("\n📋 示例地点 (前 5 个):")
places = c.execute('SELECT geo_id, name FROM places LIMIT 5').fetchall()
for p in places:
    print(f"   {p[0]}: {p[1]}")

if dyna_count > 0:
    print("\n📋 示例 OD 记录 (前 5 条):")
    records = c.execute('''
        SELECT d.time, d.origin_id, d.destination_id, d.flow, d.type,
               p1.name as origin_name, p2.name as dest_name
        FROM dyna d
        LEFT JOIN places p1 ON d.origin_id = p1.geo_id
        LEFT JOIN places p2 ON d.destination_id = p2.geo_id
        LIMIT 5
    ''').fetchall()
    for r in records:
        print(f"   {r[0]}: {r[5]} -> {r[6]}, flow={r[3]}, type={r[4]}")

conn.close()

# 最终信息
db_size_mb = os.path.getsize(DB_FILE) / (1024 * 1024)
print("\n" + "="*60)
print("✅ 数据库构建完成!")
print("="*60)
print(f"\n数据库位置: {os.path.abspath(DB_FILE)}")
print(f"数据库大小: {db_size_mb:.2f} MB")

print("\n下一步:")
print("1. 配置环境变量 (.env 文件):")
print(f"   DB_PATH={os.path.abspath(DB_FILE)}")
print(f"   TABLE_PLACES=places")
print(f"   TABLE_RELATIONS=relations")
print(f"   TABLE_DYNA=dyna")
print("\n2. 启动服务:")
print("   python -m uvicorn app:app --reload")
print("\n3. 访问 API 文档:")
print("   http://localhost:8000/docs")

print("\n" + "="*60)

