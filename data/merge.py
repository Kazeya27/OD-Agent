#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def read_rel(path: Path) -> pd.DataFrame:
    # 兼容带 BOM、空行；不把字符串当成 NA
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        keep_default_na=False,
        skip_blank_lines=True,
    )
    return df

def main(file1, file2, out):
    f1, f2, out = Path(file1), Path(file2), Path(out)

    df1 = read_rel(f1)
    df2 = read_rel(f2)

    # 以第一个文件的列顺序作为标准（若不一致会自动对齐）
    cols = list(df1.columns) if len(df1.columns) else list(df2.columns)

    # 合并
    df = pd.concat([df1, df2], ignore_index=True)

    # 若没有 rel_id 列就加一个；有则覆盖为连续编号
    if "rel_id" not in df.columns:
        cols = ["rel_id"] + cols  # 把 rel_id 放到第一列

    df["rel_id"] = np.arange(len(df), dtype=int)

    # 尽量按标准列顺序输出（将 rel_id 放到第一列）
    preferred_order = ["rel_id", "type", "origin_id", "destination_id", "cost"]
    final_cols = [c for c in preferred_order if c in df.columns]
    # 加入其他可能存在的列（保持其相对顺序）
    final_cols += [c for c in df.columns if c not in final_cols]

    df = df[final_cols]

    # 导出
    df.to_csv(out, index=False, encoding="utf-8")

    print(f"合并完成，共 {len(df)} 行，已输出到：{out}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="合并两个 .rel/.csv 文件，并将 rel_id 重新编号为从 0 递增。"
    )
    parser.add_argument("--file1", default="./baidu/baidu1.rel", help="第一个输入文件路径（如 baidu.rel）")
    parser.add_argument("--file2", default="./baidu/baidu2.rel", help="第二个输入文件路径（如 baidu2.rel）")
    parser.add_argument("-o", "--out", default="./baidu/baidu.rel", help="输出文件路径（默认 merged.rel）")
    args = parser.parse_args()

    main(args.file1, args.file2, args.out)
