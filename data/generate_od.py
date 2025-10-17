import argparse
from cgi import print_arguments
import glob
import os
import pandas as pd
from tqdm import tqdm
import numpy as np
import csv

def load_geo_data(geo_file_path):
    """
    读取 .geo 文件，返回所有有效的 geo_id 对的有序列表。
    """
    try:
        df = pd.read_csv(geo_file_path)
        valid_ids = sorted(list(set(df['geo_id'].astype(int))))
        od_pairs = [(origin, dest) for origin in valid_ids for dest in valid_ids]
        print(f"成功从 '{os.path.basename(geo_file_path)}' 加载 {len(valid_ids)} 个城市，生成 {len(od_pairs)} 个有效OD对。")
        return od_pairs, max(valid_ids) if valid_ids else 0
    except Exception as e:
        print(f"读取 .geo 文件时发生错误: {e}")
        return None, 0

def load_all_od_data_to_memory(od_files, max_geo_id):
    """
    Pass 1: 遍历所有OD文件一次，将数据加载到内存中的一个字典里。
    键是时间戳，值是Numpy矩阵。
    """
    od_data_by_time = {}
    none_file = 0
    for file_path in tqdm(od_files, desc="Pass 1: Loading all OD data into memory"):
        filename = os.path.basename(file_path)
        date_str = filename.split('.')[0]
        time_iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}T00:00:00Z"

        try:
            with open(file_path, 'r', encoding='gbk') as f:
                first_char = f.read(1)
                if first_char == '{':
                    # 对于缺失数据的文件，用一个特殊标记
                    od_data_by_time[time_iso] = None
                    none_file += 1
                    continue
            
            # 使用Pandas高效读取，然后立即转换为Numpy
            raw_df = pd.read_csv(file_path, sep='\t', encoding='gbk', header=None)
            
            # 提取OD矩阵部分
            end_row = min(raw_df.shape[0], max_geo_id + 2)
            end_col = min(raw_df.shape[1], max_geo_id + 3)
            # .iloc[1:, 2:] -> 跳过表头行/列和省份列
            od_matrix = raw_df.iloc[1:end_row, 2:end_col].values
            
            # 转换为数值类型，无法转换的变为NaN
            od_matrix_numeric = pd.to_numeric(od_matrix.flatten(), errors='coerce').reshape(od_matrix.shape)
            
            # 使用float32以节省内存
            od_data_by_time[time_iso] = od_matrix_numeric.astype(np.float32)

        except Exception as e:
            print(f"\n  -> 处理文件 {filename} 时发生错误: {e}, 当天数据将标记为缺失。")
            od_data_by_time[time_iso] = None
    print(f"成功加载 {len(od_data_by_time)} 个时间戳的OD数据，其中 {none_file} 个文件为空。")
    return od_data_by_time

def main():
    parser = argparse.ArgumentParser(
        description="高效处理多个OD矩阵，生成单一、有序的.dyna文件。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--dataset", default="baidu")
    args = parser.parse_args()

    # 准备阶段
    geo_file = os.path.join(args.dataset, f'{args.dataset}.geo')
    valid_od_pairs, max_geo_id = load_geo_data(geo_file)
    if not valid_od_pairs:
        return

    od_files = sorted(glob.glob(os.path.join(args.dataset, 'orig', '*.txt')))
    if not od_files:
        print(f"错误：在目录 '{args.od_dir}' 中没有找到任何 .txt 文件。")
        return

    # Pass 1: 一次性将所有数据加载到内存字典中
    od_data_by_time = load_all_od_data_to_memory(od_files, max_geo_id)
    
    # 获取有序的时间戳列表
    sorted_timestamps = sorted(od_data_by_time.keys())

    # Pass 2: 按要求的顺序遍历并写入文件
    dyna_id_counter = 0
    print(f"\nPass 2: Writing {len(valid_od_pairs) * len(sorted_timestamps):,} records to output file...")
    output_file = os.path.join(args.dataset, f'{args.dataset}.od') 
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            # 写入表头
            writer.writerow(['dyna_id', 'type', 'time', 'origin_id', 'destination_id', 'flow'])
            
            # 外层循环：遍历每一个OD对 (已按origin, dest排序)
            for origin_id, dest_id in tqdm(valid_od_pairs, desc="Writing OD pairs"):
                # 内层循环：遍历每一天 (已按时间排序)
                for time_iso in sorted_timestamps:
                    matrix = od_data_by_time[time_iso]
                    
                    flow = np.nan
                    if matrix is not None:
                        # 检查矩阵维度是否足够大，防止索引越界
                        if origin_id < matrix.shape[0] and dest_id < matrix.shape[1]:
                            flow = matrix[origin_id, dest_id]
                    
                    writer.writerow([
                        dyna_id_counter,
                        'state',
                        time_iso,
                        origin_id,
                        dest_id,
                        # 如果flow是NaN，则写入空字符串，符合CSV习惯
                        '' if np.isnan(flow) else flow 
                    ])
                    dyna_id_counter += 1

        print(f"\n成功！最终结果已保存到 '{output_file}'。")
        print(f"总共生成 {dyna_id_counter} 条记录。")

    except Exception as e:
        print(f"\n在写入最终文件时发生严重错误: {e}")

if __name__ == "__main__":
    main()