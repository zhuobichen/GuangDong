#!/usr/bin/env python3
"""
Run_BarCharts.py — 柱状图（超标面积×天数）入口
==============================================
输入: Data/Masked/GuangDong/
输出: Picture/BarCharts/

用法:
    python Run_BarCharts.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Core_Charts import plot_area_days_barchart

# ============================================================
# 项目路径配置
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "Data" / "Masked" / "GuangDong" / "cmaq"
OUTPUT_DIR = PROJECT_ROOT / "Picture" / "BarCharts"

# CASE 列表
CASES = ["CASE1", "CASE2", "CASE3", "CASE4", "CASE5", "CASE6"]

# 柱状图配置: (var_name, var_column, var_title, var_ylabel)
BAR_CONFIGS = [
    ("O3", "O3_Days", "O3 超标面积×天数", "Area × Days (km²·days)"),
    ("PM2.5", "PM2.5_Days", "PM2.5 超标面积×天数", "Area × Days (km²·days)"),
]

MONTHS = ["01", "07"]


def main():
    print("=" * 60)
    print("Run_BarCharts — 柱状图（超标面积×天数）")
    print(f"  Data: {DATA_DIR}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)

    os.makedirs(str(OUTPUT_DIR), exist_ok=True)

    for var_name, var_column, var_title, var_ylabel in BAR_CONFIGS:
        for month in MONTHS:
            plot_area_days_barchart(
                cases=CASES,
                var_name=var_name,
                var_column=var_column,
                var_title=var_title,
                var_ylabel=var_ylabel,
                month_code=month,
                data_dir=DATA_DIR,
                file_suffix="_GuangDong",
                output_dir=OUTPUT_DIR,
            )

    print("\n全部完成。")


if __name__ == "__main__":
    main()
