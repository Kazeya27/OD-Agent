import csv
import argparse
import requests
import os
import time
import json
from itertools import product
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 常量配置 ---
# 注意：v5的路径规划API参数不同，根据您代码中的 'extensions': 'base' 参数，应使用v3的API
GAODE_API_URL = "https://restapi.amap.com/v3/direction/driving"
MAX_RETRIES = 3  # 单次请求失败后的最大重试次数
RETRY_DELAY = 1  # 重试前的等待秒数


def read_geo_file(input_file_path):
    """读取 .geo 文件并将其内容解析到一个字典中。"""
    city_data = {}
    try:
        with open(input_file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    geo_id = int(row["geo_id"])
                    coords_str = (
                        row["coordinates"]
                        .strip()
                        .replace("[", "")
                        .replace("]", "")
                        .replace(" ", "")
                    )
                    city_data[geo_id] = {"name": row["name"], "coords": coords_str}
                except (ValueError, KeyError) as e:
                    print(f"警告：跳过格式错误的行: {row}. 错误: {e}")
    except FileNotFoundError:
        print(f"错误：找不到输入文件 '{input_file_path}'。")
        return None
    print(f"成功从 '{input_file_path}' 读取 {len(city_data)} 个城市数据。")
    return city_data


def get_driving_distance(origin_coords, dest_coords, api_key):
    """使用高德API获取驾车距离，并加入重试逻辑。"""
    params = {
        "key": api_key,
        "origin": origin_coords,
        "destination": dest_coords,
        "extensions": "base",
    }
    try:
        response = requests.get(GAODE_API_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "1" and data.get("route") and data["route"]["paths"]:
            distance_meters = int(data["route"]["paths"][0]["distance"])
            return round(distance_meters / 1000.0, 2)
        # 如果API明确返回错误，也返回-1
        elif data.get("status") == "0":
            # print(f"\nAPI返回错误: {data.get('info', '')}")
            return None
    except requests.exceptions.RequestException as e:
        return None
    # 所有重试失败后返回-1
    return None


def process_pair(origin_id, dest_id, city_data, api_key, cache_dir):
    """
    单个线程执行的工作单元。
    计算一对城市的距离，并将结果存入缓存文件。
    """
    cache_file = os.path.join(cache_dir, f"{origin_id}_{dest_id}.tmp")

    # 如果缓存已存在，则直接返回，不执行任何操作
    if os.path.exists(cache_file):
        return None

    origin = city_data[origin_id]
    destination = city_data[dest_id]

    cost = 0.0
    if origin_id != dest_id:
        cost = None
        while not cost:
            cost = get_driving_distance(
                origin["coords"], destination["coords"], api_key
            )
        time.sleep(0.05)

    # 将结果写入独立的缓存文件
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            # 写入核心数据即可，整合时再加其他字段
            f.write(f"{origin_id},{dest_id},{cost}")
    except Exception as e:
        print(f"\n写入缓存文件 {cache_file} 失败: {e}")

    return f"{origin['name']}->{destination['name']}"


def consolidate_cache(cache_dir, output_file):
    """
    整合所有缓存文件，生成最终的 .rel 文件。
    """
    print("\n所有任务已完成，开始整合缓存文件...")
    cache_files = [f for f in os.listdir(cache_dir) if f.endswith(".tmp")]

    if not cache_files:
        print("没有找到任何缓存文件，无法生成输出。")
        return

    try:
        with open(output_file, "w", encoding="utf-8", newline="") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["rel_id", "type", "origin_id", "destination_id", "cost"])

            rel_id_counter = 0
            # 使用tqdm显示整合进度
            for filename in tqdm(cache_files, desc="Consolidating", unit="file"):
                try:
                    with open(
                        os.path.join(cache_dir, filename), "r", encoding="utf-8"
                    ) as f_in:
                        content = f_in.read().strip()
                        if not content:
                            continue
                        origin_id, dest_id, cost = content.split(",")

                        writer.writerow(
                            [rel_id_counter, "geo", origin_id, dest_id, cost]
                        )
                        rel_id_counter += 1
                except Exception as e:
                    print(f"\n处理缓存文件 {filename} 失败: {e}")

        print(f"成功整合 {rel_id_counter} 条记录到 '{output_file}'。")
    except Exception as e:
        print(f"\n写入最终输出文件时发生错误: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="使用多线程计算城市间的驾车距离并生成 rel.csv 文件。",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--dataset", default="baidu", help="数据集名称，用于构建输入/输出路径。"
    )
    parser.add_argument(
        "--api_key",
        default="30d31b7586b104cf0eeaef5105a1e912",
        help="您的高德地图 Web 服务 API Key。",
    )
    parser.add_argument(
        "-t", "--threads", type=int, default=16, help="使用的线程数量。"
    )
    args = parser.parse_args()

    # --- 路径设置 ---
    geo_file = os.path.join(args.dataset, f"{args.dataset}.geo")
    out_file = os.path.join(args.dataset, f"{args.dataset}.rel")
    cache_dir = f"{args.dataset}_cache"

    # --- 1. 准备阶段 ---
    city_data = read_geo_file(geo_file)
    if not city_data:
        return

    os.makedirs(cache_dir, exist_ok=True)

    sorted_geo_ids = sorted(city_data.keys())
    all_pairs = list(product(sorted_geo_ids, repeat=2))
    all_pairs = all_pairs[:85020]
    total_tasks = len(all_pairs)
    print(f"总共有 {total_tasks} 对城市需要计算。")

    # --- 2. 多线程执行 ---
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        # 提交所有任务，让executor管理
        futures = [
            executor.submit(
                process_pair, origin_id, dest_id, city_data, args.api_key, cache_dir
            )
            for origin_id, dest_id in all_pairs
        ]

        # 使用tqdm来显示已完成任务的进度
        progress_bar = tqdm(
            as_completed(futures), total=total_tasks, desc="Executing Tasks"
        )
        for future in progress_bar:
            result = future.result()  # 获取worker的返回值
            if result:
                # 可以在进度条后显示当前完成的任务
                progress_bar.set_postfix_str(result, refresh=True)

    # --- 3. 整合阶段 ---
    consolidate_cache(cache_dir, out_file)
    print("\n所有操作完成！")


if __name__ == "__main__":
    main()
