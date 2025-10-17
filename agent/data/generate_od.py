#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
dyna_to_sqlite.py
把时序流量 CSV (dyna_id,type,time,origin_id,destination_id,flow) 导入到已有的 geo SQLite 数据库，
并将 origin_id / destination_id 作为外键引用节点表（默认 places.geo_id）。

用法示例：
  python dyna_to_sqlite.py --geo-db geo_points.db --dyna-csv dyna.csv
  python dyna_to_sqlite.py --geo-db geo_points.db --dyna-csv dyna.csv \
      --geo-table geo --dyna-table dyna --drop --strict-fk

说明：
- 默认“跳过并警告”外键不存在的记录；加 --strict-fk 改为严格报错。
- time 以 TEXT(ISO8601) 存储，并建索引；如需 epoch，可加 --store-epoch 一并存到 time_epoch。
"""

import argparse
import csv
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

MISSING_TOKENS = {"", "na", "n/a", "null", "none", "nan"}

def is_missing(s: str) -> bool:
    if s is None:
        return True
    t = s.strip().lower()
    return t in MISSING_TOKENS

def check_geo_table(cur, geo_table: str, geo_pk: str):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (geo_table,))
    if not cur.fetchone():
        raise SystemExit(f"找不到节点表：{geo_table}")
    cur.execute(f'PRAGMA table_info("{geo_table}");')
    cols = {r[1] for r in cur.fetchall()}
    if geo_pk not in cols:
        raise SystemExit(f"节点表 {geo_table} 不含主键列 {geo_pk}")

def load_geo_ids(cur, geo_table: str, geo_pk: str) -> set:
    cur.execute(f'SELECT "{geo_pk}" FROM "{geo_table}";')
    return {r[0] for r in cur.fetchall()}

def create_dyna_table(cur, dyna_table: str, dyna_pk: str,
                      geo_table: str, geo_pk: str,
                      store_epoch: bool, flow_not_null: bool):
    extra_epoch_col = ', "time_epoch" INTEGER' if store_epoch else ''
    flow_null_sql = "REAL NOT NULL" if flow_not_null else "REAL"
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS "{dyna_table}" (
      "{dyna_pk}"       INTEGER PRIMARY KEY,
      "type"            TEXT NOT NULL,
      "time"            TEXT NOT NULL,
      "origin_id"       INTEGER NOT NULL,
      "destination_id"  INTEGER NOT NULL,
      "flow"            {flow_null_sql}
      {extra_epoch_col},
      FOREIGN KEY("origin_id")      REFERENCES "{geo_table}"("{geo_pk}") ON UPDATE CASCADE ON DELETE RESTRICT,
      FOREIGN KEY("destination_id") REFERENCES "{geo_table}"("{geo_pk}") ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """)
    cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_{dyna_table}_time" ON "{dyna_table}"("time");')
    cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_{dyna_table}_origin" ON "{dyna_table}"("origin_id");')
    cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_{dyna_table}_destination" ON "{dyna_table}"("destination_id");')

def parse_iso8601_to_epoch(s: str) -> int:
    if s.endswith("Z"):
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    else:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

def insert_dyna(cur, dyna_table: str, dyna_pk: str, dyna_csv: Path,
                encoding: str, delimiter: str,
                strict_fk: bool, geo_ids: set,
                store_epoch: bool,
                flow_policy: str, flow_fill: float) -> tuple[int, int, int]:
    """返回 (成功数, 跳过数, 空值数)"""
    ok = skipped = nulls = 0
    with open(dyna_csv, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        required = {"dyna_id", "type", "time", "origin_id", "destination_id", "flow"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"dyna CSV 缺少字段：{', '.join(sorted(missing))}")

        if store_epoch:
            sql = (f'INSERT INTO "{dyna_table}" ("{dyna_pk}", "type", "time", "origin_id", '
                   f'"destination_id", "flow", "time_epoch") VALUES (?, ?, ?, ?, ?, ?, ?);')
        else:
            sql = (f'INSERT INTO "{dyna_table}" ("{dyna_pk}", "type", "time", "origin_id", '
                   f'"destination_id", "flow") VALUES (?, ?, ?, ?, ?, ?);')

        batch = []
        for i, row in enumerate(reader, start=2):
            try:
                dyna_id = int((row["dyna_id"] or "").strip())
                typ = (row["type"] or "").strip()
                t = (row["time"] or "").strip()
                origin = int((row["origin_id"] or "").strip())
                dest = int((row["destination_id"] or "").strip())
                flow_raw = row["flow"]
            except Exception as e:
                raise SystemExit(f"[dyna] 第 {i} 行解析错误：{e}")

            # 外键检查
            o_ok = origin in geo_ids
            d_ok = dest in geo_ids
            if not (o_ok and d_ok):
                miss = []
                if not o_ok: miss.append(f"origin_id={origin}")
                if not d_ok: miss.append(f"destination_id={dest}")
                if strict_fk:
                    raise SystemExit(f"[dyna] 外键不存在（行 {i}）：{', '.join(miss)}")
                else:
                    print(f"[dyna] 警告：跳过无效外键记录（行 {i}）：{', '.join(miss)}")
                    skipped += 1
                    continue

            # flow 解析
            flow = None
            if not is_missing(flow_raw):
                try:
                    flow = float(str(flow_raw).strip())
                except Exception:
                    # 视为缺失
                    flow = None

            if flow is None:
                nulls += 1
                if flow_policy == "skip":
                    skipped += 1
                    continue
                elif flow_policy == "fill":
                    flow = flow_fill
                else:
                    # null：保留为 None，要求 flow 列允许 NULL
                    pass

            if store_epoch:
                epoch = parse_iso8601_to_epoch(t)
                batch.append((dyna_id, typ, t, origin, dest, flow, epoch))
            else:
                batch.append((dyna_id, typ, t, origin, dest, flow))

        if batch:
            cur.executemany(sql, batch)
            ok += len(batch)
    return ok, skipped, nulls

def main():
    ap = argparse.ArgumentParser(description="将时序 dyna CSV 导入到已有的 geo SQLite 数据库（含外键校验）。")
    ap.add_argument("--geo-db", default=r"D:\File\研究生\研二\公路院\agent\data\geo.db", help="已有 SQLite 数据库路径（包含节点表）")
    ap.add_argument("--dyna-csv", default=r"D:\File\研究生\研二\公路院\data\baidu\baidu.od", help="dyna CSV 路径（含 dyna_id,type,time,origin_id,destination_id,flow）")
    ap.add_argument("--geo-table", default="geo", help="节点表名（默认：places；如为 geo 则 --geo-table geo）")
    ap.add_argument("--geo-pk", default="geo_id", help="节点表主键列名（默认：geo_id）")
    ap.add_argument("--dyna-table", default="od", help="dyna 表名（默认：dyna）")
    ap.add_argument("--dyna-pk", default="dyna_id", help="dyna 表主键列名（默认：dyna_id）")
    ap.add_argument("--drop", action="store_true", help="如已存在 dyna 表则先 DROP 再建")
    ap.add_argument("--strict-fk", action="store_true", help="严格外键：外键不存在则报错（默认跳过并警告）")
    ap.add_argument("--store-epoch", action="store_true", help="额外生成 time_epoch(秒) 列并写入")
    # flow 空值策略
    ap.add_argument("--flow-policy", choices=["null", "fill", "skip"], default="null",
                    help="flow 空值处理：null=存为NULL；fill=用指定数值填充；skip=跳过该行（默认：null）")
    ap.add_argument("--flow-fill", type=float, default=0.0, help="当 --flow-policy=fill 时用于填充值（默认 0.0）")
    ap.add_argument("--flow-not-null", action="store_true",
                    help="将 flow 设为 NOT NULL（如启用，请确保不存在空值或使用 --flow-policy=fill）")
    # CSV 读取
    ap.add_argument("--encoding", default="utf-8-sig", help="CSV 编码（默认：utf-8-sig）")
    ap.add_argument("--delimiter", default=",", help="CSV 分隔符（默认：,）")
    args = ap.parse_args()

    db_path = Path(args.geo_db)
    if not db_path.exists():
        raise SystemExit(f"找不到数据库：{db_path}")

    dyna_csv = Path(args.dyna_csv)
    if not dyna_csv.exists():
        raise SystemExit(f"找不到 dyna CSV：{dyna_csv}")

    # 策略一致性检查
    if args.flow_not_null and args.flow_policy == "null":
        raise SystemExit("参数冲突：--flow-not-null 与 --flow-policy=null 不兼容。请改为 fill 或 skip。")

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

        # 校验并加载节点表
        check_geo_table(cur, args.geo_table, args.geo_pk)
        geo_ids = load_geo_ids(cur, args.geo_table, args.geo_pk)

        # 建/重建 dyna 表
        if args.drop:
            cur.execute(f'DROP TABLE IF EXISTS "{args.dyna_table}";')
        create_dyna_table(cur, args.dyna_table, args.dyna_pk,
                          args.geo_table, args.geo_pk,
                          args.store_epoch, args.flow_not_null)

        ok, skipped, nulls = insert_dyna(cur, args.dyna_table, args.dyna_pk, dyna_csv,
                                         args.encoding, args.delimiter,
                                         args.strict_fk, geo_ids,
                                         args.store_epoch,
                                         args.flow_policy, args.flow_fill)
        conn.commit()
        print(f"[dyna] 成功写入 {ok} 条；跳过 {skipped} 条；检测到空值 {nulls} 次。完成。")
    finally:
        conn.close()

if __name__ == "__main__":
    main()