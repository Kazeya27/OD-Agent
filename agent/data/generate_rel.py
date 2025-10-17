#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
relations_to_sqlite.py
把关系表 CSV (rel_id,type,origin_id,destination_id,cost) 导入到已有的 geo SQLite 数据库中，
并用 origin_id / destination_id 外键引用已有的节点表（默认表名 places，主键 geo_id）。

用法示例：
  python relations_to_sqlite.py --geo-db geo_points.db --relations-csv rel.csv
  python relations_to_sqlite.py --geo-db geo_points.db --relations-csv rel.csv \
      --geo-table geo --relations-table relations --edges-drop
  python relations_to_sqlite.py --geo-db geo_points.db --relations-csv rel.csv --strict-fk

注意：
- 默认“跳过并警告”那些在节点表中找不到外键的关系记录；加 --strict-fk 可改为严格报错。
"""

import argparse
import csv
import sqlite3
from pathlib import Path

def check_geo_table(cur, geo_table: str, geo_pk: str):
    """确保节点表存在且含有主键列 geo_pk"""
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (geo_table,))
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"找不到节点表：{geo_table}")

    cur.execute(f'PRAGMA table_info("{geo_table}");')
    cols = {r[1] for r in cur.fetchall()}
    if geo_pk not in cols:
        raise SystemExit(f"节点表 {geo_table} 不含主键列 {geo_pk}")

def load_geo_ids(cur, geo_table: str, geo_pk: str) -> set:
    cur.execute(f'SELECT "{geo_pk}" FROM "{geo_table}";')
    return {r[0] for r in cur.fetchall()}

def create_relations_table(cur, rel_table: str, rel_pk: str, geo_table: str, geo_pk: str):
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS "{rel_table}" (
      "{rel_pk}"       INTEGER PRIMARY KEY,
      "type"           TEXT NOT NULL,
      "origin_id"      INTEGER NOT NULL,
      "destination_id" INTEGER NOT NULL,
      "cost"           REAL NOT NULL,
      FOREIGN KEY("origin_id")      REFERENCES "{geo_table}"("{geo_pk}") ON UPDATE CASCADE ON DELETE RESTRICT,
      FOREIGN KEY("destination_id") REFERENCES "{geo_table}"("{geo_pk}") ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """)
    cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_{rel_table}_origin" ON "{rel_table}"("origin_id");')
    cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_{rel_table}_destination" ON "{rel_table}"("destination_id");')

def insert_relations(cur, rel_table: str, rel_pk: str, rel_csv: Path,
                     encoding: str, delimiter: str,
                     geo_ids: set, strict_fk: bool) -> tuple[int, int]:
    ok = skipped = 0
    with open(rel_csv, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        required = {"rel_id", "type", "origin_id", "destination_id", "cost"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"关系 CSV 缺少字段：{', '.join(sorted(missing))}")

        batch = []
        for i, row in enumerate(reader, start=2):
            try:
                rel_id = int((row["rel_id"] or "").strip())
                typ = (row["type"] or "").strip()
                origin = int((row["origin_id"] or "").strip())
                dest = int((row["destination_id"] or "").strip())
                cost = float((row["cost"] or "").strip())
            except Exception as e:
                raise SystemExit(f"[relations] 第 {i} 行解析错误：{e}")

            o_ok = origin in geo_ids
            d_ok = dest in geo_ids
            if not (o_ok and d_ok):
                msg = []
                if not o_ok: msg.append(f"origin_id={origin}")
                if not d_ok: msg.append(f"destination_id={dest}")
                if strict_fk:
                    raise SystemExit("[relations] 外键不存在（行 {}）：{}".format(i, ", ".join(msg)))
                else:
                    print("[relations] 警告：跳过外键不存在的记录（行 {}）：{}".format(i, ", ".join(msg)))
                    skipped += 1
                    continue

            batch.append((rel_id, typ, origin, dest, cost))

        if batch:
            cur.executemany(
                f'INSERT INTO "{rel_table}" ("{rel_pk}", "type", "origin_id", "destination_id", "cost") '
                f'VALUES (?, ?, ?, ?, ?);',
                batch
            )
            ok += len(batch)
    return ok, skipped

def main():
    ap = argparse.ArgumentParser(description="把关系 CSV 导入到已有 geo SQLite 数据库，并建立外键。")
    ap.add_argument("--geo-db", default=r"D:\File\研究生\研二\公路院\agent\data\geo.db", help="已有 geo SQLite 数据库路径（包含节点表）")
    ap.add_argument("--relations-csv", default=r"D:\File\研究生\研二\公路院\data\baidu\baidu.rel", help="关系 CSV 路径（含 rel_id,type,origin_id,destination_id,cost）")
    ap.add_argument("--geo-table", default="geo", help="节点表名（默认：places；若你用的是 geo，请改为 --geo-table geo）")
    ap.add_argument("--geo-pk", default="geo_id", help="节点表主键列名（默认：geo_id）")
    ap.add_argument("--relations-table", default="relations", help="关系表表名（默认：relations）")
    ap.add_argument("--relations-pk", default="rel_id", help="关系表主键列名（默认：rel_id）")
    ap.add_argument("--edges-drop", action="store_true", help="如已存在关系表则先 DROP 再建")
    ap.add_argument("--strict-fk", action="store_true", help="严格外键：遇到无效外键直接报错（默认为跳过并警告）")
    ap.add_argument("--encoding", default="utf-8-sig", help="关系 CSV 编码（默认：utf-8-sig）")
    ap.add_argument("--delimiter", default=",", help="关系 CSV 分隔符（默认：,）")
    args = ap.parse_args()

    db_path = Path(args.geo_db)
    if not db_path.exists():
        raise SystemExit(f"找不到数据库：{db_path}")

    rel_csv = Path(args.relations_csv)
    if not rel_csv.exists():
        raise SystemExit(f"找不到关系 CSV：{rel_csv}")

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

        # 校验并加载节点表
        check_geo_table(cur, args.geo_table, args.geo_pk)
        geo_ids = load_geo_ids(cur, args.geo_table, args.geo_pk)

        # （可选）重建关系表
        if args.edges_drop:
            cur.execute(f'DROP TABLE IF EXISTS "{args.relations_table}";')
        create_relations_table(cur, args.relations_table, args.relations_pk, args.geo_table, args.geo_pk)

        ok, skipped = insert_relations(
            cur, args.relations_table, args.relations_pk, rel_csv,
            args.encoding, args.delimiter, geo_ids, args.strict_fk
        )
        conn.commit()
        print(f"[relations] 写入 {ok} 条；跳过 {skipped} 条无效外键。完成。")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
