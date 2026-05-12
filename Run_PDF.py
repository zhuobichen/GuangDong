#!/usr/bin/env python3
"""
Run_PDF.py — KDE 概率密度分布图入口
=====================================
输入: Data/Processed/ 或 Data/Masked/
输出: Picture/PDF/

用法:
    python Run_PDF.py                     # 默认全部数据源
    python Run_PDF.py --source cmaq       # 仅 CMAQ
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Core_PDF import run_pdf_pipeline

# ============================================================
# 项目路径配置
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent

# 数据源 → 输入目录 / 输出目录映射
SOURCE_MAP = {
    "cmaq": {
        "input": str(PROJECT_ROOT / "Data" / "Processed" / "CMAQ"),
        "output": str(PROJECT_ROOT / "Picture" / "PDF" / "CMAQ"),
    },
    "mcip": {
        "input": str(PROJECT_ROOT / "Data" / "Processed" / "MCIP"),
        "output": str(PROJECT_ROOT / "Picture" / "PDF" / "MCIP"),
    },
    "emission": {
        "input": str(PROJECT_ROOT / "Data" / "Processed" / "Emission"),
        "output": str(PROJECT_ROOT / "Picture" / "PDF" / "Emission"),
    },
}

# 默认配置
REFERENCE_YEAR = 2023
COMPARE_YEARS = [2000, 2030, 2060]
MONTHS = ["01", "07"]
REGIONS = ["GuangDong", "HuiZhou", "Land"]


def main():
    parser = argparse.ArgumentParser(description="GuangDong KDE 分布对比图")
    parser.add_argument("--source", action="append", dest="sources",
                        choices=["cmaq", "mcip", "emission"],
                        help="数据源 (可重复指定)")
    args = parser.parse_args()

    sources = args.sources or ["cmaq", "mcip", "emission"]

    for src in sources:
        cfg = SOURCE_MAP[src]
        if not os.path.isdir(cfg["input"]):
            print(f"\n[SKIP] {src}: 输入目录不存在: {cfg['input']}")
            continue

        run_pdf_pipeline(
            data_dir=cfg["input"],
            output_dir=cfg["output"],
            data_source=src,
            reference_year=REFERENCE_YEAR,
            compare_years=COMPARE_YEARS,
            months=MONTHS,
            regions=REGIONS,
        )

    print("\n全部完成。")


if __name__ == "__main__":
    main()
