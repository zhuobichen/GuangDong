#!/usr/bin/env python3
"""
Run_Extract.py — CMAQ NC 数据提取入口

从 CMAQ Daily COMBINE ACONC NetCDF 文件提取网格化污染物和气象数据。
每个 FileConfig 描述: NC 输入 → (emission CSV, meteo CSV) 输出。

用法:
  python Run_Extract.py [--limit N]

配置文件在脚本内修改 FILE_CONFIGS / BASE_CONFIGS。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from Core_Extract import extract_and_output

# ============================================================
# 项目路径
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent
CMAQ_DIR = str(PROJECT_ROOT / "Data" / "Raw" / "CMAQ")
PROCESSED_EMISSION = str(PROJECT_ROOT / "Data" / "Processed" / "CMAQ")
PROCESSED_METEO = str(PROJECT_ROOT / "Data" / "Processed" / "MCIP")


# ============================================================
# 文件配置
# ============================================================
class FileConfig:
    """单个 CMAQ NC 文件的提取配置。"""

    def __init__(
        self,
        nc_file: str,
        output_name: str,
        year: int = 2000,
        month: int = 7,
    ):
        self.nc_file = nc_file
        self.output_name = output_name
        self.year = year
        self.month = month


# ============================================================
# 情景配置 - 不同场景组
# ============================================================

# 2000 vs. 2023 对比 (7月 + 1月)
SCENARIO_2000V2023 = [
    # Case2: 2000排放 + 2023气象
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_2023met_2000emis_GD_layer_1_2023-06-26_2023-07-31_18species.nc",
        "2000_Emission[2023met]_07", 2000, 7,
    ),
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_2023met_2000emis_GD_layer_1_2022-12-27_2023-01-31_18species.nc",
        "2000_Emission[2023met]_01", 2000, 1,
    ),
    # Case4: 2023排放 + 2000气象
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_2000met_2023emis_GD_layer_1_2000-06-26_2000-07-31_18species.nc",
        "2023_Emission[2000met]_07", 2023, 7,
    ),
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_2000met_2023emis_GD_layer_1_1999-12-27_2000-01-31_18species.nc",
        "2023_Emission[2000met]_01", 2023, 1,
    ),
]

# 基础情景 (2000 / 2023 / 2030 / 2060)
SCENARIO_BASELINE = [
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_ssp126_2000_GD_layer_1_1999-12-27_2000-01-31_18species.nc",
        "2000_Emission[2000met]_01", 2000, 1,
    ),
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_ssp126_2000_GD_layer_1_2000-06-26_2000-07-31_18species.nc",
        "2000_Emission[2000met]_07", 2000, 7,
    ),
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_ssp126_2023_GD_layer_1_2022-12-27_2023-01-31_18species.nc",
        "2023_Emission[2023met]_01", 2023, 1,
    ),
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_ssp126_2023_GD_layer_1_2023-06-26_2023-07-31_18species.nc",
        "2023_Emission[2023met]_07", 2023, 7,
    ),
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_ssp126_2030_GD_layer_1_2029-12-27_2030-01-31_18species.nc",
        "2030_Emission[2030met]_01", 2030, 1,
    ),
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_ssp126_2030_GD_layer_1_2030-06-26_2030-07-31_18species.nc",
        "2030_Emission[2030met]_07", 2030, 7,
    ),
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_ssp126_2060_GD_layer_1_2059-12-27_2060-01-31_18species.nc",
        "2060_Emission[2060met]_01", 2060, 1,
    ),
    FileConfig(
        f"{CMAQ_DIR}/Daily_COMBINE_ACONC_v54_D3_ssp126_2060_GD_layer_1_2060-06-26_2060-07-31_18species.nc",
        "2060_Emission[2060met]_07", 2060, 7,
    ),
]

# 默认使用的场景
FILE_CONFIGS = SCENARIO_2000V2023


# ============================================================
# 主流程
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CMAQ NC → CSV 数据提取")
    parser.add_argument("--limit", type=int, default=None, help="限制处理文件数")
    args = parser.parse_args()

    configs = FILE_CONFIGS[: args.limit] if args.limit else FILE_CONFIGS

    print("=" * 60)
    print(f"Run_Extract — 处理 {len(configs)} 个 NC 文件")
    print(f"  输出目录: emission={PROCESSED_EMISSION}, meteo={PROCESSED_METEO}")
    print("=" * 60)

    for i, cfg in enumerate(configs):
        print(f"\n[{i+1}/{len(configs)}] {os.path.basename(cfg.nc_file)}")
        print(f"  年份={cfg.year}, 月份={cfg.month}")

        if not os.path.exists(cfg.nc_file):
            print(f"  ⚠️ NC 文件不存在，跳过: {cfg.nc_file}")
            continue

        try:
            # 全区域提取 (emission + meteo)
            extract_and_output(
                cfg.nc_file, cfg.month, "emission",
                PROCESSED_EMISSION, cfg.output_name,
            )
            extract_and_output(
                cfg.nc_file, cfg.month, "meteo",
                PROCESSED_METEO, cfg.output_name,
            )
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            continue

    print(f"\n{'=' * 60}")
    print("完成。")


if __name__ == "__main__":
    main()
