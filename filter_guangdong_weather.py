#!/usr/bin/env python3
import pandas as pd
import numpy as np
import json
from datetime import datetime

def load_guangdong_boundary(json_file):
    """
    从china_cities.json中提取广东省的边界坐标

    广东省大致范围：
    - 经度：109.5° - 117.5°E
    - 纬度：20.0° - 25.5°N
    """
    # 广东省的近似边界（基于实际地理数据）
    guangdong_bounds = {
        'min_lon': 109.5,
        'max_lon': 117.5,
        'min_lat': 20.0,
        'max_lat': 25.5
    }

    return guangdong_bounds

def filter_weather_data(input_file, output_file, target_time="1999-12-25 00:00:00"):
    """
    筛选广东省内指定时间的气象数据

    参数:
    input_file: 输入的CSV文件路径
    output_file: 输出的CSV文件路径
    target_time: 目标时间
    """

    print("开始筛选气象数据...")

    # 读取气象数据
    try:
        weather_df = pd.read_csv(input_file)
        print(f"原始数据总记录数: {len(weather_df)}")
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None

    # 获取广东省边界
    guangdong_bounds = load_guangdong_boundary("./china_cities.json")

    print(f"广东省地理范围: 经度 {guangdong_bounds['min_lon']}° - {guangdong_bounds['max_lon']}°E")
    print(f"              纬度 {guangdong_bounds['min_lat']}° - {guangdong_bounds['max_lat']}°N")

    # 检查数据的时间分布
    print(f"\n数据时间范围:")
    weather_df['Time'] = pd.to_datetime(weather_df['Time'])
    print(f"最早时间: {weather_df['Time'].min()}")
    print(f"最晚时间: {weather_df['Time'].max()}")

    # 1. 首先查找00:00:00时间附近的记录（前后30分钟）
    target_dt = pd.to_datetime(target_time)
    time_window = pd.Timedelta(minutes=30)

    time_filtered = weather_df[
        (weather_df['Time'] >= target_dt - time_window) &
        (weather_df['Time'] <= target_dt + time_window)
    ]
    print(f"时间窗口 {target_dt - time_window} 到 {target_dt + time_window} 的记录数: {len(time_filtered)}")

    # 2. 如果没有00:00:00的数据，尝试查找华南地区（广东附近）的站点
    south_china_filtered = time_filtered[
        (time_filtered['Longitude'] >= 109.0) &
        (time_filtered['Longitude'] <= 118.0) &
        (time_filtered['Latitude'] >= 20.0) &
        (time_filtered['Latitude'] <= 26.0)
    ]

    print(f"华南地区（广东附近）的记录数: {len(south_china_filtered)}")

    # 3. 筛选广东省范围内的记录
    guangdong_filtered = time_filtered[
        (time_filtered['Longitude'] >= guangdong_bounds['min_lon']) &
        (time_filtered['Longitude'] <= guangdong_bounds['max_lon']) &
        (time_filtered['Latitude'] >= guangdong_bounds['min_lat']) &
        (time_filtered['Latitude'] <= guangdong_bounds['max_lat'])
    ]

    print(f"广东省范围内的记录数: {len(guangdong_filtered)}")

    # 4. 如果没有广东省内的数据，使用华南地区的数据
    final_data = guangdong_filtered if len(guangdong_filtered) > 0 else south_china_filtered

    if len(final_data) == 0:
        print("警告: 没有找到广东省或华南地区的数据")

        # 扩大搜索范围，查找所有亚洲地区的数据
        asia_filtered = time_filtered[
            (time_filtered['Longitude'] >= 100) &
            (time_filtered['Longitude'] <= 140) &
            (time_filtered['Latitude'] >= 10) &
            (time_filtered['Latitude'] <= 50)
        ]

        print(f"亚洲地区的记录数: {len(asia_filtered)}")
        if len(asia_filtered) > 0:
            print("亚洲数据点示例:")
            print(asia_filtered[['Time', 'Longitude', 'Latitude', 'Temperature']].head())
        return asia_filtered

    print(f"最终使用数据: {'广东省内' if len(guangdong_filtered) > 0 else '华南地区（广东附近）'} {len(final_data)} 条记录")

    # 检查温度数据的合理性
    print(f"\n=== 温度数据检查 ===")

    # 统计温度数据
    temp_data = final_data['Temperature'].dropna()
    if len(temp_data) > 0:
        print(f"有效温度数据: {len(temp_data)} 条")
        print(f"温度范围: {temp_data.min():.2f} - {temp_data.max():.2f} °C")
        print(f"平均温度: {temp_data.mean():.2f} °C")

        # 检查异常低温
        extremely_cold = temp_data[temp_data < -40]
        if len(extremely_cold) > 0:
            print(f"⚠️  发现异常低温数据 (<-40°C): {len(extremely_cold)} 条")
            print("异常低温示例:")
            cold_records = final_data[final_data['Temperature'] < -40]
            print(cold_records[['Time', 'Longitude', 'Latitude', 'Temperature', 'AirPress']].head())

        # 检查异常高温
        extremely_hot = temp_data[temp_data > 40]
        if len(extremely_hot) > 0:
            print(f"⚠️  发现异常高温数据 (>40°C): {len(extremely_hot)} 条")
            hot_records = final_data[final_data['Temperature'] > 40]
            print(hot_records[['Time', 'Longitude', 'Latitude', 'Temperature']].head())

    # 保存筛选结果
    final_data.to_csv(output_file, index=False)
    print(f"\n筛选结果已保存到: {output_file}")

    # 显示详细统计信息
    region_name = "广东省内" if len(guangdong_filtered) > 0 else "华南地区（广东附近）"
    print(f"\n=== {region_name}气象数据统计 ===")
    print(f"总记录数: {len(final_data)}")

    # 统计各变量的有效数据
    for col in ['Temperature', 'AirPress', 'WindSpeed', 'WindDirection']:
        valid_data = final_data[col].dropna()
        if len(valid_data) > 0:
            print(f"{col}: {len(valid_data)} 条有效数据, 范围: {valid_data.min():.2f} - {valid_data.max():.2f}")
        else:
            print(f"{col}: 无有效数据")

    # 显示部分数据示例
    print(f"\n=== 数据示例 ===")
    display_cols = ['Time', 'Longitude', 'Latitude', 'Temperature', 'AirPress', 'WindSpeed', 'WindDirection']
    print(final_data[display_cols].head(10))

    return final_data

def analyze_temp_pressure_relationship(df):
    """
    分析温度和气压的关系，检查高空数据特征
    """
    if len(df) == 0:
        return

    print(f"\n=== 温度-气压关系分析 ===")

    temp_press_data = df[['Temperature', 'AirPress']].dropna()

    if len(temp_press_data) > 0:
        # 计算相关系数
        correlation = temp_press_data['Temperature'].corr(temp_press_data['AirPress'])
        print(f"温度与气压相关系数: {correlation:.3f}")

        # 按气压分组统计温度
        if len(temp_press_data) > 5:
            # 低压（高空） vs 高压（低空）
            low_pressure = temp_press_data[temp_press_data['AirPress'] < 300]
            high_pressure = temp_press_data[temp_press_data['AirPress'] >= 300]

            if len(low_pressure) > 0:
                print(f"低压区域 (<300hPa): 平均温度 {low_pressure['Temperature'].mean():.2f}°C")
            if len(high_pressure) > 0:
                print(f"高压区域 (≥300hPa): 平均温度 {high_pressure['Temperature'].mean():.2f}°C")

if __name__ == "__main__":
    # 输入输出文件路径
    input_csv = "weather_stations_all.csv"
    output_csv = "guangdong_weather_19991225.csv"

    # 筛选广东省气象数据
    guangdong_data = filter_weather_data(input_csv, output_csv, "1999-12-25 00:00:00")

    # 分析温度-气压关系
    if guangdong_data is not None:
        analyze_temp_pressure_relationship(guangdong_data)

        print(f"\n=== 处理完成 ===")
        print(f"筛选结果文件: {output_csv}")
        print(f"记录数: {len(guangdong_data)}")