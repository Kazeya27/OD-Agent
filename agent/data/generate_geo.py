#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
csv_to_sqlite.py
把包含列：geo_id,type,coordinates,name 的 CSV 转成 SQLite。
- 表名：places（可通过 --table-name 改）
- 主键：geo_id（可通过 --pk-field 改）
- 解析 coordinates（形如 "[lon, lat]"）为 longitude / latitude
- 默认开启外键支持（PRAGMA foreign_keys=ON），便于后续其它表引用本表主键

用法示例：
    python csv_to_sqlite.py points.csv geo_points.db
    python csv_to_sqlite.py points.csv geo_points.db --table-name places --drop
    python csv_to_sqlite.py points.csv geo_points.db --print-child-template
"""

import argparse
import csv
import re
import sqlite3
from pathlib import Path

COORDS_PATTERN = re.compile(r"[-+]?\d*\.\d+|[-+]?\d+")

def parse_coords(s: str):
    """从类似 '[91.171924, 29.653491]' 的字符串中解析 (lon, lat) 浮点数"""
    if s is None:
        raise ValueError("coordinates 为空")
    nums = COORDS_PATTERN.findall(s)
    if len(nums) < 2:
        raise ValueError(f"坐标格式无法解析：{s!r}")
    lon = float(nums[0])
    lat = float(nums[1])
    return lon, lat

def create_parent_table(cur: sqlite3.Cursor, table: str, pk_field: str):
    """
    创建主表（父表），主键使用 INTEGER PRIMARY KEY，便于其它表做外键引用。
    说明：SQLite 的 INTEGER PRIMARY KEY 会成为 rowid，外键可直接引用。
    """
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS "{table}" (
      "{pk_field}" INTEGER PRIMARY KEY,
      "type"      TEXT NOT NULL,
      "longitude" REAL NOT NULL,
      "latitude"  REAL NOT NULL,
      "name"      TEXT NOT NULL
    );
    """)
    # 视需要可给 name 建索引
    cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_{table}_name" ON "{table}"("name");')

def insert_rows(cur: sqlite3.Cursor, table: str, pk_field: str, rows):
    cur.executemany(
        f'INSERT INTO "{table}" ("{pk_field}", "type", "longitude", "latitude", "name") '
        f'VALUES (?, ?, ?, ?, ?);',
        rows
    )

def child_table_template(child_table: str, parent_table: str, parent_pk: str):
    """
    返回示例子表 SQL（带外键约束），供后续扩展时参考或直接使用。
    """
    return f"""-- 示例：创建引用 {parent_table}({parent_pk}) 的子表
CREATE TABLE IF NOT EXISTS "{child_table}" (
  "id"       INTEGER PRIMARY KEY,
  "{parent_pk}" INTEGER NOT NULL,
  "note"     TEXT,
  "created_at" TEXT DEFAULT (datetime('now')),
  FOREIGN KEY("{parent_pk}") REFERENCES "{parent_table}"("{parent_pk}") ON UPDATE CASCADE ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS "idx_{child_table}_{parent_pk}" ON "{child_table}"("{parent_pk}");
"""

def main():
    ap = argparse.ArgumentParser(description="将 geo CSV 转成 SQLite，主键可被其它表作为外键引用。")
    ap.add_argument("--input_csv", default=r"D:\File\研究生\研二\公路院\data\baidu\baidu.geo", help="输入 CSV 文件路径（需含列：geo_id,type,coordinates,name）")
    ap.add_argument("--output_db", default=r"D:\File\研究生\研二\公路院\agent\data\geo.db", help="输出 SQLite 数据库路径")
    ap.add_argument("--table-name", default="geo", help="主表表名（默认：places）")
    ap.add_argument("--pk-field", default="geo_id", help="主键字段名（默认：geo_id）")
    ap.add_argument("--encoding", default="utf-8-sig", help="CSV 编码（默认：utf-8-sig）")
    ap.add_argument("--delimiter", default=",", help="CSV 分隔符（默认：,）")
    ap.add_argument("--coords-field", default="coordinates", help="坐标字段名（默认：coordinates）")
    ap.add_argument("--type-field", default="type", help="类型字段名（默认：type）")
    ap.add_argument("--name-field", default="name", help="名称字段名（默认：name）")
    ap.add_argument("--drop", action="store_true", help="如已存在则先 DROP 该表后重建")
    ap.add_argument("--print-child-template", action="store_true",
                    help="打印一个引用主键为外键的子表建表 SQL 模板并退出")
    ap.add_argument("--child-table-name", default="observations",
                    help="子表模板名称（默认：observations，与 --print-child-template 配合）")
    args = ap.parse_args()

    in_path = Path(args.input_csv)
    out_path = Path(args.output_db)
    if not in_path.exists():
        raise SystemExit(f"找不到输入文件：{in_path}")

    # 可选：只打印子表模板
    if args.print_child_template:
        print(child_table_template(args.child_table_name, args.table_name, args.pk_field))
        return

    conn = sqlite3.connect(str(out_path))
    try:
        cur = conn.cursor()
        # 打开外键支持
        cur.execute("PRAGMA foreign_keys = ON;")

        if args.drop:
            cur.execute(f'DROP TABLE IF EXISTS "{args.table_name}";')

        create_parent_table(cur, args.table_name, args.pk_field)

        required = {args.pk_field, args.type_field, args.coords_field, args.name_field}
        rows_to_insert = []

        with open(in_path, "r", encoding=args.encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=args.delimiter)
            if not reader.fieldnames:
                raise SystemExit("CSV 读取失败：未检测到表头。")
            missing = required - set(reader.fieldnames)
            if missing:
                raise SystemExit(f"CSV 缺少字段：{', '.join(sorted(missing))}")

            for i, row in enumerate(reader, start=2):
                try:
                    pk = int((row[args.pk_field] or "").strip())
                    typ = (row[args.type_field] or "").strip()
                    name = (row[args.name_field] or "").strip()
                    lon, lat = parse_coords(row[args.coords_field] or "")
                except Exception as e:
                    raise SystemExit(f"第 {i} 行解析错误：{e}")
                rows_to_insert.append((pk, typ, lon, lat, name))

        insert_rows(cur, args.table_name, args.pk_field, rows_to_insert)
        conn.commit()
        print(f"已写入 {len(rows_to_insert)} 条记录到 {out_path} 的表 {args.table_name}。")
        print("提示：外键已启用（PRAGMA foreign_keys=ON）。后续子表可引用本表主键。")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
