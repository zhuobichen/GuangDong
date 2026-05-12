#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run_NationStationValidation.py — 国家监测站 MCIP 气象校验入口

与 Run_WeatherValidation.py (ISD/NOAA) 对应，本脚本用于中国环境监测总站
逐小时 xlsx 数据。

差异:
  - 数据源:   Data/Station/Nation/ (中国监测站) vs Data/Station/ (ISD)
  - 时间:     UTC+8 → 转 UTC 匹配 MCIP
  - 分辨率:   逐小时 vs 3小时
  - 站点 ID:  数字编号 vs USGS 11位

用法:
    python Run_NationStationValidation.py [--year 2023] [--step all|convert|extract|plot|report]
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Core_NationStationValidation import (
    convert_nation_xlsx_to_table,
    match_stations_to_grid,
    extract_mcip_for_nation_stations,
    plot_nation_timeseries,
    generate_nation_report,
)

# ====================== 路径配置 ======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NATION_DATA   = os.path.join(BASE_DIR, "Data", "Station", "Nation")
RAW_DIR       = os.path.join(NATION_DATA, "Raw")
PROCESSED_DIR = os.path.join(NATION_DATA, "Processed")
VALIDATION_DIR = os.path.join(NATION_DATA, "Validation")
SITE_INFO_CSV = os.path.join(NATION_DATA, "GD_125nation_site_v01.csv")
GRID_CSV      = os.path.join(NATION_DATA, "GD_125nation_grid_v01.csv")
MCIP_BASE     = os.path.join(BASE_DIR, "mcipout")
PICTURE_DIR   = os.path.join(BASE_DIR, "Picture", "Station", "Nation", "Timeseries")

# ====================== 站点配置 ======================
# 14 个广东省国家监测站点（含气象+污染数据）
STATIONS = {
    "440100051": "广雅中学",
    "440200057": "碧湖山庄",
    "440300051": "通心岭子站",
    "440400055": "斗门",
    "440500915": "潮南峡山",
    "440600455": "容桂街道办",
    "44070051":  "北街",
    "440900403": "高岭",
    "441200402": "城中子站",
    "441300751": "下埔横江三路子站",
    "441500401": "市环保局",
    "441600403": "老城",
    "441723001": "阳东陶然",
    "442000915": "中山南区",
}

# ====================== 年份/月份配置 ======================
YEAR = 2023
MONTHS_EXTRACT = [1, 7]         # 提取月份
MONTHS_REPORT = (1, 7)          # 报表月份
VARIABLES_PLOT = ["Temperature", "Humidity", "AirPress", "WindSpeed"]
VARIABLES_REPORT = ["Temperature", "Humidity", "WindSpeed"]


# ====================== 主流程 ======================

def run_pipeline(year):
    mcip_dir = os.path.join(MCIP_BASE, str(year))
    picture_dir = os.path.join(PICTURE_DIR, str(year))
    report_file = os.path.join(VALIDATION_DIR, f"校验结果数据表_国家站_{year}.xlsx")

    print(f"\n{'='*60}")
    print(f"  国家监测站 MCIP 气象校验 {year} 年")
    print(f"  站点数: {len(STATIONS)}")
    print(f"  提取月份: {MONTHS_EXTRACT}")
    print(f"{'='*60}")

    # Step 1: xlsx → 校验表
    print(f"\n--- Step 1: xlsx → 校验表 ---")
    convert_nation_xlsx_to_table(
        RAW_DIR, SITE_INFO_CSV, PROCESSED_DIR,
        year, months=MONTHS_EXTRACT, station_ids=list(STATIONS.keys()),
    )

    # Step 2: 网格匹配
    print(f"\n--- Step 2: 站点→网格匹配 ---")
    # 优先用预计算 CSV，回退 KDTree
    griddot_files = sorted([f for f in os.listdir(mcip_dir)
                            if f.startswith("GRIDDOT2D_")]) if os.path.exists(mcip_dir) else []
    griddot_path = os.path.join(mcip_dir, griddot_files[0]) if griddot_files else None

    station_grids = match_stations_to_grid(
        SITE_INFO_CSV,
        griddot_file=griddot_path,
        grid_csv=GRID_CSV,
        station_ids=list(STATIONS.keys()),
    )

    # Step 3: MCIP 提取
    print(f"\n--- Step 3: MCIP 数据提取 ---")
    extract_mcip_for_nation_stations(
        PROCESSED_DIR, VALIDATION_DIR, mcip_dir,
        year, station_grids, months=MONTHS_EXTRACT,
    )

    # Step 4: 时间序列图
    print(f"\n--- Step 4: 时间序列对比图 ---")
    plot_nation_timeseries(
        VALIDATION_DIR, picture_dir, year, STATIONS,
        variables=VARIABLES_PLOT,
    )

    # Step 5: 报表
    print(f"\n--- Step 5: 校验报表 ---")
    generate_nation_report(
        VALIDATION_DIR, report_file, year, STATIONS,
        variables=VARIABLES_REPORT,
        months=MONTHS_REPORT,
    )

    print(f"\n{'='*60}")
    print(f"  ✅ {year} 年国家站校验完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="国家监测站 MCIP 气象校验")
    p.add_argument("--year", type=int, default=2023, help="年份 (默认 2023)")
    p.add_argument("--step", type=str, default="all",
                   help="步骤: all/convert/extract/plot/report")
    p.add_argument("--station", type=str, nargs="*",
                   help="指定站点ID, 如 --station 440100051")
    args = p.parse_args()

    y = args.year
    mid = os.path.join(MCIP_BASE, str(y))
    gfiles = sorted([f for f in os.listdir(mid) if f.startswith("GRIDDOT2D_")]) \
             if os.path.exists(mid) else []
    gdot = os.path.join(mid, gfiles[0]) if gfiles else None

    station_ids = args.station if args.station else list(STATIONS.keys())
    active_stations = {k: STATIONS[k] for k in station_ids if k in STATIONS}

    if args.step == "all":
        run_pipeline(y)
    elif args.step == "convert":
        convert_nation_xlsx_to_table(
            RAW_DIR, SITE_INFO_CSV, PROCESSED_DIR,
            y, months=MONTHS_EXTRACT, station_ids=list(active_stations.keys()),
        )
    elif args.step == "extract":
        sgs = match_stations_to_grid(
            SITE_INFO_CSV, griddot_file=gdot, grid_csv=GRID_CSV,
            station_ids=list(active_stations.keys()),
        )
        extract_mcip_for_nation_stations(
            PROCESSED_DIR, VALIDATION_DIR, mid,
            y, sgs, months=MONTHS_EXTRACT,
        )
    elif args.step == "plot":
        plot_nation_timeseries(
            VALIDATION_DIR, os.path.join(PICTURE_DIR, str(y)),
            y, active_stations, variables=VARIABLES_PLOT,
        )
    elif args.step == "report":
        generate_nation_report(
            VALIDATION_DIR,
            os.path.join(VALIDATION_DIR, f"校验结果数据表_国家站_{y}.xlsx"),
            y, active_stations, variables=VARIABLES_REPORT,
        )
    else:
        print(f"未知步骤: {args.step}")
