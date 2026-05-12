#!/usr/bin/env python3
"""
Core_PDF.py — KDE 概率密度分布图核心模块
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'

YEAR_COLORS = {2000: 'orange', 2023: 'purple', 2030: 'blue', 2060: 'red'}
YEAR_LINESTYLES = {2000: '-', 2023: '--', 2030: '-.', 2060: ':'}
MONTH_NAMES_CN = {'01':'1月','02':'2月','03':'3月','04':'4月','05':'5月','06':'6月',
                  '07':'7月','08':'8月','09':'9月','10':'10月','11':'11月','12':'12月'}

def kde_fit(data: np.ndarray, x: np.ndarray) -> np.ndarray:
    kde = gaussian_kde(data)
    pdf = kde(x)
    area = np.trapz(pdf, x)
    if area > 1e-10: pdf /= area
    return pdf

def plot_kde_comparison(
    csv_paths: Dict[int, str], variable: str, output_path: str,
    month: str = "07", title: str = "", xlabel: str = "",
    variable_column: Optional[str] = None, clean_range: tuple = (0, 500),
) -> str:
    col = variable_column or variable
    month_cn = MONTH_NAMES_CN.get(str(month).zfill(2), f"{month}月")
    all_data: Dict[int, np.ndarray] = {}
    global_min, global_max = float('inf'), float('-inf')
    for year, csv_path in sorted(csv_paths.items()):
        if not os.path.exists(csv_path): continue
        df = pd.read_csv(csv_path)
        if col not in df.columns: continue
        data = df[col].dropna().values
        low, high = clean_range
        data = data[(data >= low) & (data <= high)]
        if len(data) < 5: continue
        all_data[year] = data
        global_min = min(global_min, data.min())
        global_max = max(global_max, data.max())
    if len(all_data) < 2:
        print(f"  ⚠️ 有效年份不足 ({len(all_data)}), 跳过")
        return output_path
    global_min *= 0.9; global_max *= 1.1
    x = np.linspace(global_min, global_max, 500)
    plt.figure(figsize=(10, 6))
    years_sorted = sorted(all_data.keys())
    for year in years_sorted:
        data = all_data[year]
        pdf = kde_fit(data, x)
        color = YEAR_COLORS.get(year, 'green')
        ls = YEAR_LINESTYLES.get(year, '-')
        mu, sigma = data.mean(), data.std()
        plt.plot(x, pdf, ls, color=color, linewidth=2.5,
                 label=f"{year} (μ={mu:.2f}, σ={sigma:.2f})")
    plt.legend(loc="upper right", fontsize=11)
    if not title:
        title = f"{month_cn} {variable} ({', '.join(str(y) for y in years_sorted)})"
    plt.title(title, fontsize=15, fontweight="bold")
    plt.xlabel(xlabel or variable, fontsize=13)
    plt.ylabel("Probability Density", fontsize=13)
    plt.grid(False); plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  ✅ PDF → {output_path}")
    return output_path


# ============================================================
# 数据源配置
# ============================================================

PDF_SOURCE_CONFIGS = {
    "cmaq": {
        "variables": ["O3", "PM2.5"],
        "file_pattern": "{year}_Emission[{year}met]_{month}",
        "clean_range": (0, 500),
    },
    "mcip": {
        "variables": ["TA_mean", "SOL_RAD_mean", "PBLH_mean"],
        "file_pattern": "{year}_mcipout_{month}",
        "clean_range": (0, 1000),
    },
    "emission": {
        "variables": ["PM2.5"],
        "file_pattern": "EM_{year}{month}_PM2.5",
        "clean_range": (0, 500),
    },
}

REGION_CONFIGS = {
    "raw":       {"folder_suffix": "",      "file_suffix": "",        "label": "全区域"},
    "GuangDong": {"folder_suffix": "_GuangDong", "file_suffix": "_GuangDong", "label": "广东"},
    "HuiZhou":   {"folder_suffix": "_HuiZhou",   "file_suffix": "_HuiZhou",   "label": "惠州"},
    "Land":      {"folder_suffix": "_land",       "file_suffix": "_land",       "label": "陆地"},
}


# ============================================================
# 管道函数
# ============================================================

def run_pdf_pipeline(
    data_dir: str,
    output_dir: str,
    data_source: str = "cmaq",
    reference_year: int = 2023,
    compare_years: Optional[List[int]] = None,
    months: Optional[List[str]] = None,
    variables: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
) -> List[str]:
    """PDF 概率密度分布图管道。

    对每个 variable × month × region，将 compare_years 与 reference_year
    进行 KDE 分布对比。

    Args:
        data_dir:       CSV 数据根目录（不含区域子目录）
        output_dir:     图片输出目录
        data_source:    'cmaq' | 'mcip' | 'emission'
        reference_year: 基准年（默认 2023）
        compare_years:  对比年份列表，默认 [2000, 2030, 2060]
        months:         月份列表，默认 ['01', '07']
        variables:      变量列表，默认使用 PDF_SOURCE_CONFIGS 配置
        regions:        区域列表，默认 ['GuangDong', 'HuiZhou', 'Land']

    Returns:
        生成的文件路径列表
    """
    cfg = PDF_SOURCE_CONFIGS.get(data_source)
    if cfg is None:
        raise ValueError(f"未知数据源: {data_source}，可选: {list(PDF_SOURCE_CONFIGS.keys())}")

    if compare_years is None:
        compare_years = [2000, 2030, 2060]
    if months is None:
        months = ["01", "07"]
    if variables is None:
        variables = cfg["variables"]

    # 默认区域: 仅对已存在的数据目录启用
    available_regions = []
    for rkey in (regions or ["GuangDong", "HuiZhou", "Land"]):
        rcfg = REGION_CONFIGS.get(rkey)
        if rcfg is None:
            continue
        region_data_dir = os.path.join(data_dir, f"{data_dir.rstrip('/')}{rcfg['folder_suffix']}")
        if os.path.isdir(region_data_dir):
            available_regions.append(rkey)
        elif rkey == "raw" or rcfg["file_suffix"] == "":
            available_regions.append(rkey)
    if not available_regions:
        print(f"  ⚠️ 未找到任何区域数据目录")
        return []

    print(f"\n{'='*60}")
    print(f"Run PDF Pipeline — {data_source}")
    print(f"  Data: {data_dir}")
    print(f"  Reference: {reference_year}")
    print(f"  Compare: {compare_years}")
    print(f"  Months: {months}")
    print(f"  Variables: {variables}")
    print(f"  Regions: {available_regions}")
    print(f"{'='*60}")

    outputs = []
    for var in variables:
        for month in months:
            month_str = str(month).zfill(2)
            for rkey in available_regions:
                rcfg = REGION_CONFIGS.get(rkey, REGION_CONFIGS["raw"])
                fsuffix = rcfg["file_suffix"]
                label = rcfg["label"]

                # 构建文件路径映射
                csv_paths: Dict[int, str] = {}
                for year in [reference_year] + compare_years:
                    fname = cfg["file_pattern"].format(year=year, month=month_str) + f"{fsuffix}.csv"
                    fpath = os.path.join(data_dir, fname)
                    if os.path.exists(fpath):
                        csv_paths[year] = fpath

                if reference_year not in csv_paths or len(csv_paths) < 2:
                    continue

                # 输出路径
                out_name = f"{var}_{reference_year}vs{'_'.join(str(y) for y in compare_years)}_{month_str}_{rkey}.png"
                out_path = os.path.join(output_dir, out_name)

                title = f"{MONTH_NAMES_CN.get(month_str, month_str)} {var}（{label}）"
                plot_kde_comparison(
                    csv_paths=csv_paths,
                    variable=var,
                    output_path=out_path,
                    month=month_str,
                    title=title,
                    clean_range=cfg["clean_range"],
                )
                outputs.append(out_path)

    print(f"\n  ✅ 完成: {len(outputs)} 张 PDF 图")
    return outputs
