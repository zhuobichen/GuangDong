#!/usr/bin/env python3
"""
Run_BoxPlots.py — 箱线图入口
=============================
输入: Data/Processed/CMAQ/ + Data/Masked/HuiZhou/
输出: Picture/BoxPlots/

用法:
    python Run_BoxPlots.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Core_Charts import plot_case_boxplot

# ============================================================
# 项目路径配置
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "Data" / "Processed" / "CMAQ"
OUTPUT_DIR = PROJECT_ROOT / "Picture" / "BoxPlots"

# CASE 列表
CASES = ["CASE1", "CASE2", "CASE3", "CASE4", "CASE5", "CASE6"]

# 箱线图配置: (var_name, var_column, var_title, var_ylabel)
BOX_CONFIGS = [
    ("O3", "O3", "O3 Concentration", "O3 (ppb)"),
    ("PM2.5", "PM2.5", "PM2.5 Concentration", "PM2.5 (μg/m³)"),
]

MONTHS = ["01", "07"]
REGIONS = ["GuangDong", "HuiZhou"]


def main():
    print("=" * 60)
    print("Run_BoxPlots — 箱线图")
    print(f"  Data: {DATA_DIR}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)

    os.makedirs(str(OUTPUT_DIR), exist_ok=True)

    for var_name, var_column, var_title, var_ylabel in BOX_CONFIGS:
        for month in MONTHS:
            plot_case_boxplot(
                cases=CASES,
                var_name=var_name,
                var_column=var_column,
                var_title=var_title,
                var_ylabel=var_ylabel,
                month_code=month,
                data_dir=DATA_DIR,
                regions=REGIONS,
                output_dir=OUTPUT_DIR,
            )

    print("\n全部完成。")


if __name__ == "__main__":
    main()
