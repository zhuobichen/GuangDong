#!/usr/bin/env python3
"""
Run_Mask.py — 掩膜流程入口

对 CMAQ / MCIP / Emission 三种数据源的 CSV 文件，
应用 land / guangdong / huizhou 掩膜。

用法:
  python Run_Mask.py [--source cmaq] [--source mcip] [--source emission]
                     [--type land] [--type guangdong] [--type huizhou]
                     [--limit N]

示例:
  python Run_Mask.py                                    # 全部
  python Run_Mask.py --source cmaq --type land           # 仅 CMAQ→land
  python Run_Mask.py --source mcip --type guangdong --limit 5  # 测试
"""

from __future__ import annotations

import argparse
from pathlib import Path

from Core_Mask import run_masks

# ============================================================
# 项目路径配置 (唯一需要修改的地方)
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent

GRID_FILE = str(PROJECT_ROOT / "Data/Boundary/GRIDCRO2D_2000121_GuangDongD3")
CHINA_JSON = str(PROJECT_ROOT / "Data/Boundary/china.json")
PROVINCES_JSON = str(PROJECT_ROOT / "Data/Boundary/China_provinces.json")
FLAG_NC = str(PROJECT_ROOT / "Data/Boundary/HuiZhou_2000121_GuangDongD3.nc")

# 数据源 → 输入/输出映射 (Data/结构)
DATA_SOURCES = {
    "cmaq": {
        "input": PROJECT_ROOT / "Data" / "Processed" / "CMAQ",
        "outputs": {
            "guangdong": PROJECT_ROOT / "Data" / "Masked" / "GuangDong" / "cmaq",
            "land":      PROJECT_ROOT / "Data" / "Masked" / "Land" / "cmaq",
            "huizhou":   PROJECT_ROOT / "Data" / "Masked" / "HuiZhou" / "cmaq",
        },
    },
    "mcip": {
        "input": PROJECT_ROOT / "Data" / "Processed" / "MCIP",
        "outputs": {
            "guangdong": PROJECT_ROOT / "Data" / "Masked" / "GuangDong" / "mcip",
            "land":      PROJECT_ROOT / "Data" / "Masked" / "Land" / "mcip",
            "huizhou":   PROJECT_ROOT / "Data" / "Masked" / "HuiZhou" / "mcip",
        },
    },
    "emission": {
        "input": PROJECT_ROOT / "Data" / "Processed" / "Emission",
        "outputs": {
            "guangdong": PROJECT_ROOT / "Data" / "Masked" / "GuangDong" / "emission",
            "land":      PROJECT_ROOT / "Data" / "Masked" / "Land" / "emission",
            "huizhou":   PROJECT_ROOT / "Data" / "Masked" / "HuiZhou" / "emission",
        },
    },
}


def main():
    parser = argparse.ArgumentParser(description="GuangDong 掩膜流程")
    parser.add_argument("--source", action="append", dest="sources",
                        choices=["cmaq", "mcip", "emission"],
                        help="数据源 (可重复指定，默认全部)")
    parser.add_argument("--type", action="append", dest="mask_types",
                        choices=["land", "guangdong", "huizhou"],
                        help="掩膜类型 (可重复指定，默认全部)")
    parser.add_argument("--limit", type=int, default=None, help="限制处理文件数 (调试)")
    args = parser.parse_args()

    sources = args.sources or ["cmaq", "mcip", "emission"]
    mask_types = args.mask_types or ["guangdong", "land", "huizhou"]

    print("=" * 60)
    print("Run_Mask — 掩膜流程")
    print(f"  Sources: {sources}")
    print(f"  Mask types: {mask_types}")
    print(f"  Grid file: {GRID_FILE}")
    print("=" * 60)

    for src in sources:
        cfg = DATA_SOURCES[src]
        input_dir = cfg["input"]
        if not input_dir.exists():
            print(f"\n[SKIP] {src}: input dir not found: {input_dir}")
            continue

        print(f"\n--- {src} ---")
        print(f"  Input: {input_dir}")

        # 过滤出当前 source 需要的掩膜
        src_masks = [mt for mt in mask_types if mt in cfg["outputs"]]
        src_outputs = {mt: cfg["outputs"][mt] for mt in src_masks}

        results = run_masks(
            input_dir=input_dir,
            output_dirs=src_outputs,
            mask_types=src_masks,
            grid_file=GRID_FILE,
            extra_params={
                "china_json": CHINA_JSON,
                "provinces_json": PROVINCES_JSON,
                "flag_nc": FLAG_NC,
            },
            file_limit=args.limit,
        )
        for mt, ok in results.items():
            print(f"  [{mt}] → {cfg['outputs'][mt]}  (ok={ok})")

    print("\nDone.")


if __name__ == "__main__":
    main()
