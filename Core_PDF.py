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
