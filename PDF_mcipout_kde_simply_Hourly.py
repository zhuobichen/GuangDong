#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCIP 气象变量 KDE 分布对比脚本（极简 + 自动化 + 高性能）
自动处理：
- 变量（TA_mean、SOL_RAD_mean、PBLH_mean 等）
- 年份（2000/2030/2060 vs 2023）
- 月份（01 / 07）
- 地区（normal / huizhou）
自动生成路径，不需要手写 file_XXXX_YYY。
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
plt.rcParams['font.family'] = 'sans-serif'

# 确保所有元素都使用中文字体
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# =========================================================
# 基础配置
# =========================================================
BASE = Path(__file__).parent
OUTPUT_DIR = BASE / "Mcip_Comparison_Plots_PDF_CN"
OUTPUT_DIR.mkdir(exist_ok=True)

COMPARE_YEARS = [2000]
MONTHS = ["07"]
REGIONS = ["normal", "huizhou"]

# 统一变量配置
VARIABLES = {
    # "TA_mean":  {"col": "TA_mean",  "unit": "°C",   "title": "TEMP"},
    # "SOL_RAD_mean": {"col": "SOL_RAD_mean", "unit": "W/m²", "title": "SOL_RAD"},
    # "PBLH_mean": {"col": "PBLH_mean", "unit": "m", "title": "PBLH"},
    "Heatwave Days": {"col": "Heatwave_Days_Coverage", "unit": "Days", "title": "Heatwave Days (Coverage, ≥35°)"},
}

# 统一的颜色和线型配置
YEAR_COLORS = {
    2000: 'orange',
    2023: 'purple',
    2030: 'blue',
    2060: 'red'
}

YEAR_LINESTYLES = {
    2000: '-',
    2023: '--',
    2030: '-.',
    2060: ':'
}


# =========================================================
# 自动生成文件路径
# =========================================================
def get_filepath(year: int, month: str, region: str):
    """自动生成 MCIP 文件路径"""
    folder = "mcipout_processed_hourly_HuiZhou" if region == "huizhou" else "mcipout_processed_hourly"
    suffix = f"{year}_mcipout_{month}"
    if region == "huizhou":
        suffix += "_HuiZhou"
    return BASE / folder / (suffix + ".csv")


# =========================================================
# KDE 拟合
# =========================================================
def kde_fit(data, x):
    kde = gaussian_kde(data)
    pdf = kde(x)
    area = np.trapz(pdf, x)
    if area > 0:
        pdf *= 1 / area
    return pdf


# =========================================================
# 绘制单张对比图
# =========================================================
def plot_kde_comparison(var_name, var_cfg, compare_year, month, region):
    col = var_cfg["col"]
    unit = var_cfg["unit"]
    title = var_cfg["title"]

    # 自动生成文件路径
    f2023 = get_filepath(2023, month, region)
    fcmp = get_filepath(compare_year, month, region)

    if not f2023.exists() or not fcmp.exists():
        print(f"⚠️ 文件不存在，跳过: {f2023} 或 {fcmp}")
        return

    # 加载数据
    d1 = pd.read_csv(f2023)[col].dropna().values
    d2 = pd.read_csv(fcmp)[col].dropna().values

    if len(d1) == 0 or len(d2) == 0:
        print(f"⚠️ 数据为空，跳过变量 {var_name}")
        return

    m1, s1 = d1.mean(), d1.std()
    m2, s2 = d2.mean(), d2.std()

    # x 轴范围自动
    x_min = min(d1.min(), d2.min()) * 0.95
    x_max = max(d1.max(), d2.max()) * 1.05
    x = np.linspace(x_min, x_max, 500)

    # KDE
    pdf1 = kde_fit(d1, x)
    pdf2 = kde_fit(d2, x)

    # 绘图
    plt.figure(figsize=(10, 6))

    # 使用统一的颜色和线型
    color_2023 = YEAR_COLORS[2023]
    linestyle_2023 = YEAR_LINESTYLES[2023]
    color_compare = YEAR_COLORS.get(compare_year, 'green')
    linestyle_compare = YEAR_LINESTYLES.get(compare_year, '--')

    plt.plot(x, pdf1, linestyle_2023, color=color_2023, linewidth=2.5,
             label=f"2023  (μ={m1:.2f}, σ={s1:.2f})")
    plt.plot(x, pdf2, linestyle_compare, color=color_compare, linewidth=2.5,
             label=f"{compare_year}  (μ={m2:.2f}, σ={s2:.2f})")

    region_name = "HuiZhou" if region == "huizhou" else "GuangDong"
    month_names_cn = {"01": "1月", "07": "7月"}

    # 使用中文标题格式：月份 变量名 (年份1, 年份2, 年份3)
    plt.title(f"{month_names_cn[month]} {title} ({compare_year}, 2023) ({region_name})",
              fontsize=15, fontweight="bold")
    # plt.xlabel(f"{title} ({unit})", fontsize=13)
    plt.xlabel(f"{title}", fontsize=13)
    plt.ylabel("Probability Density", fontsize=13)

    plt.legend(loc="upper left", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # 保存文件
    out_name = f"{var_name}_{compare_year}vs2023_{month}_{region_name}.png"
    out_path = OUTPUT_DIR / out_name
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✅ 保存: {out_path}")


# =========================================================
# 主流程
# =========================================================
def main():
    print("\n📌 MCIP KDE 分布自动对比开始...\n")

    for var_name, cfg in VARIABLES.items():
        print(f"\n=== 处理变量：{var_name} ===")

        for year in COMPARE_YEARS:
            for month in MONTHS:
                for region in REGIONS:
                    plot_kde_comparison(var_name, cfg, year, month, region)

    print("\n🎉 所有任务完成！图像已生成在：", OUTPUT_DIR)


if __name__ == "__main__":
    main()
