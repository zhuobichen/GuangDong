#!/usr/bin/env python3
"""
Run_WeatherValidation.py — 气象站点 MCIP 校验入口

用法:
    python Run_WeatherValidation.py [--year 2000|2023] [--step all|check|convert|extract|plot|report]

默认: 处理 2000 + 2023 两年全流程
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Core_WeatherValidation import (
    check_data_completeness,
    convert_to_validation_table,
    extract_mcip_data,
    plot_timeseries_comparison,
    generate_validation_report,
)

# ====================== 路径配置 ======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR        = os.path.join(BASE_DIR, "Data", "Station", "Raw")
PROCESSED_DIR  = os.path.join(BASE_DIR, "Data", "Station", "Processed")
VALIDATION_DIR = os.path.join(BASE_DIR, "Data", "Station", "Validation")
MCIP_BASE      = os.path.join(BASE_DIR, "mcipout")
PICTURE_DIR    = os.path.join(BASE_DIR, "Picture", "Station", "Timeseries")

# ====================== 站点配置 ======================
STATIONS = {
    "59082099999": "韶关",
    "59316099999": "汕头",
    "59493099999": "深圳宝安",
    "59658099999": "湛江",
}

# ====================== 年份配置 ======================
YEAR_CONFIGS = {
    2000: {"all_label": "1-11月"},
    2023: {"all_label": "1-12月"},
}

VARIABLES_PLOT = ["Temperature", "Humidity", "AirPress", "WindSpeed"]
VARIABLES_REPORT = ["Temperature", "Humidity", "WindSpeed"]
MONTHS_REPORT = (1, 4, 7, 10)


def run_year(year):
    cfg = YEAR_CONFIGS[year]
    raw_dir        = os.path.join(RAW_DIR, str(year))
    processed_dir  = os.path.join(PROCESSED_DIR, str(year))
    validation_dir = os.path.join(VALIDATION_DIR, str(year))
    mcip_dir       = os.path.join(MCIP_BASE, str(year))
    picture_dir    = os.path.join(PICTURE_DIR, str(year))
    report_file    = os.path.join(validation_dir, f"校验结果数据表_{year}.xlsx")

    print(f"\n{'='*60}")
    print(f"  气象校验 {year} 年")
    print(f"{'='*60}")

    # Step 1: 数据完整性检查
    print(f"\n--- Step 1: 检查 {year} 年数据完整性 ---")
    check_data_completeness(raw_dir, raw_dir, year)

    # Step 2: 转换校验表
    print(f"\n--- Step 2: 转换为校验表 ---")
    convert_to_validation_table(raw_dir, processed_dir, year, STATIONS)

    # Step 3: MCIP 数据提取
    print(f"\n--- Step 3: MCIP 数据提取 ---")
    extract_mcip_data(mcip_dir, processed_dir, validation_dir, year, STATIONS)

    # Step 4: 时序图绘制
    print(f"\n--- Step 4: 时序图绘制 ---")
    plot_timeseries_comparison(
        validation_dir, picture_dir, year, STATIONS,
        variables=VARIABLES_PLOT,
        all_label=cfg["all_label"],
    )

    # Step 5: 报表生成
    print(f"\n--- Step 5: 报表生成 ---")
    generate_validation_report(
        validation_dir, report_file, year, STATIONS,
        variables=VARIABLES_REPORT,
        months=MONTHS_REPORT,
        metrics=("R", "RMSE", "MB"),
    )

    print(f"\n{'='*60}")
    print(f"  ✅ {year} 年校验完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="气象站点 MCIP 校验")
    parser.add_argument("--year", type=int, nargs="+", default=[2000, 2023],
                        help="目标年份 (默认: 2000 2023)")
    parser.add_argument("--step", type=str, default="all",
                        help="只运行指定步骤: check/convert/extract/plot/report")
    args = parser.parse_args()

    for y in args.year:
        if y not in YEAR_CONFIGS:
            print(f"⚠  不支持的年份 {y}, 跳过")
            continue
        if args.step == "all":
            run_year(y)
        elif args.step == "check":
            rd = os.path.join(RAW_DIR, str(y))
            check_data_completeness(rd, rd, y)
        elif args.step == "convert":
            rd = os.path.join(RAW_DIR, str(y))
            pd = os.path.join(PROCESSED_DIR, str(y))
            convert_to_validation_table(rd, pd, y, STATIONS)
        elif args.step == "extract":
            pd = os.path.join(PROCESSED_DIR, str(y))
            vd = os.path.join(VALIDATION_DIR, str(y))
            md = os.path.join(MCIP_BASE, str(y))
            extract_mcip_data(md, pd, vd, y, STATIONS)
        elif args.step == "plot":
            vd = os.path.join(VALIDATION_DIR, str(y))
            picd = os.path.join(PICTURE_DIR, str(y))
            plot_timeseries_comparison(vd, picd, y, STATIONS,
                                       all_label=YEAR_CONFIGS[y]["all_label"])
        elif args.step == "report":
            vd = os.path.join(VALIDATION_DIR, str(y))
            rf = os.path.join(vd, f"校验结果数据表_{y}.xlsx")
            generate_validation_report(vd, rf, y, STATIONS,
                                       variables=VARIABLES_REPORT)
        else:
            print(f"⚠  未知步骤: {args.step}")
