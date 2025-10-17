import csv
import argparse
import os
import requests
import time
from pdb import set_trace

GAODE_API_URL = "https://restapi.amap.com/v3/geocode/geo"

def geocode_cities_from_file(input_file_path, output_file_path, api_key):
    """
    读取 OD 文件，使用高德 API 获取唯一城市的经纬度，并按指定格式输出。
    
    Args:
        input_file_path (str): 输入的 OD 数据文件路径。
        output_file_path (str): 输出的 CSV 文件路径。
        api_key (str): 用户的高德 Web 服务 API 密钥。
    """
    # 用于存储最终要写入文件的行数据
    output_rows = []
    # 用于存储所有已经遇到过的独一无二的城市名
    seen_cities = set()
    # 全局 geo_id 计数器，为文件中的每个城市位置进行编号
    geo_id_counter = 0

    print("开始处理文件并获取地理坐标...")

    # --- 步骤 1: 按顺序读取文件，处理并筛选城市 ---
    try:
        with open(input_file_path, mode='r', encoding='gbk') as f:
            reader = csv.reader(f, delimiter='\t')
            
            # 1.1 定义一个内部函数来处理每个城市，避免代码重复
            def process_city(name):
                nonlocal geo_id_counter # 声明 geo_id_counter 是外部变量
                
                if not name:
                    return # 跳过空名称
                
                # 检查是否是第一次出现
                if name not in seen_cities:
                    print(f"  -> 正在查询 (ID: {geo_id_counter}): {name}")
                    seen_cities.add(name)
                    
                    # 调用高德API获取坐标
                    coords = None
                    while not coords:
                        coords = get_coordinates(name, api_key)
                        if not coords:
                            print(f"      警告: 未能获取 '{name}' 的坐标。")
                    
                    # 准备要写入的数据行
                    output_rows.append([geo_id_counter, 'Point', str(coords), name])
                
                # 无论是否重名，geo_id 计数器都必须为这个位置 +1
                geo_id_counter += 1

            # 1.2 读取并处理表头
            header = next(reader)
            for city_name in header[2:]:
                process_city(city_name.strip())
            
            # 1.3 逐行读取并处理第一列
            for row in reader:
                if row:
                    process_city(row[0].strip())

    except FileNotFoundError:
        print(f"错误：找不到输入文件 '{input_file_path}'。")
        return
    except Exception as e:
        print(f"读取文件 '{input_file_path}' 时发生错误: {e}")
        return

    if not output_rows:
        print("警告：未能从文件中提取任何有效的城市名称。")
        return

    print(f"\n共处理 {geo_id_counter} 个城市/地区条目。")
    
    # --- 步骤 2: 将筛选后的城市列表写入新文件 ---
    try:
        with open(output_file_path, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['geo_id', 'type', 'coordinates', 'name'])
            writer.writerows(output_rows)
    except Exception as e:
        print(f"写入输出文件 '{output_file_path}' 时发生错误: {e}")
        return
        
    print(f"成功写入 {len(output_rows)} 个唯一的城市/地区到 '{output_file_path}'。")
    print("处理完成！")

def get_coordinates(city_name, api_key):
    """
    使用高德API为单个城市名称获取经纬度坐标。
    
    Args:
        city_name (str): 城市名称。
        api_key (str): 高德 API 密钥。
        
    Returns:
        list: 包含[经度, 纬度]的列表，如果失败则返回空列表[]。
    """
    if city_name.endswith('地区'):
        city_name = city_name[:-2]
    params = {
        'key': api_key,
        'address': city_name
    }
    try:
        # 设置超时以防网络问题
        response = requests.get(GAODE_API_URL, params=params, timeout=10)
        response.raise_for_status()  # 如果请求失败 (如 404, 500), 则会抛出异常
        
        data = response.json()
        
        # 检查API返回状态是否成功且包含地理编码信息
        if data.get('status') == '1' and data.get('geocodes'):
            location_str = data['geocodes'][0]['location']
            # 将 "经度,纬度" 字符串分割并转换为浮点数列表
            coords = [float(c) for c in location_str.split(',')]
            return coords
            
    except requests.exceptions.Timeout:
        print(f"      错误: 请求 '{city_name}' 超时。")
    except requests.exceptions.RequestException as e:
        print(f"      错误: 网络请求失败 for '{city_name}': {e}")
    except Exception as e:
        print(f"      错误: 处理API响应时出错 for '{city_name}': {e}")
    
    # 为了防止请求过于频繁，可以添加一个小的延时
    time.sleep(1) # 20毫秒延时
    
    return [] # 如果任何环节失败，返回空列表


def main():
    """
    主函数，用于解析命令行参数并调用处理函数。
    """
    # 初始化命令行参数解析器
    parser = argparse.ArgumentParser(
        description="将 OD 矩阵文件转换为地理格式的 CSV 文件。",
        formatter_class=argparse.RawTextHelpFormatter # 保持帮助文本格式
    )

    parser.add_argument(
        "--dataset",
        default="baidu"
    )

    parser.add_argument(
        "--api_key",
        default="30d31b7586b104cf0eeaef5105a1e912",
        help="您的高德地图 Web 服务 API Key。"
    )

    # 添加必需的输入文件参数
    parser.add_argument(
        "--input_file",
        default="20220111.txt",
        help="输入的 OD 矩阵文件路径（.txt 格式）。"
    )

    # 解析命令行传入的参数
    args = parser.parse_args()

    input_path = os.path.join(args.dataset, "orig" ,args.input_file)
    output_path = os.path.join(args.dataset, f"{args.dataset}.geo")
    # 调用核心处理函数，并传入解析到的参数
    geocode_cities_from_file(input_path, output_path, args.api_key)


# --- 主程序入口 ---
# 确保只有在直接运行此脚本时才执行 main() 函数
if __name__ == "__main__":
    main()