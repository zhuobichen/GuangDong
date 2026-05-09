#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import gaussian_kde

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
plt.rcParams['font.family'] = 'sans-serif'

# 确保所有元素都使用中文字体
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# ============================
# 统一设置
# ============================
YEARS_TO_COMPARE = [2060]  # 只与 2023 对比的年份
MONTHS = ["01", "07"]
REGIONS = ["normal"]  # 只画广东整体，不单独画惠州
OUTPUT_DIR = "Emission_Comparison_Plots_PDF_CN"
TARGET_BIN_COUNT = 20
XTICK_EVERY_N_BINS = 2

# ============================
# 变量配置
# ============================
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

VARIABLE_CONFIGS = {
    'PM2.5': {
        'column': 'PM2.5',
        'unit': 'μg/m³',
        'title': 'PM2.5',
        'is_count_data': False
    },
    # 'O3_Days': {
    #     'column': 'O3_Days',
    #     'unit': 'days',
    #     'title': 'O3 Exceedance Days',
    #     'color_2023': 'darkviolet',
    #     'color_compare': 'darkgreen',
    #     'is_count_data': True
    # },
    # 'PM2.5_Days': {
    #     'column': 'PM2.5_Days',
    #     'unit': 'days',
    #     'title': 'PM2.5 Exceedance Days',
    #     'color_2023': 'darkviolet',
    #     'color_compare': 'darkgreen',
    #     'is_count_data': True
    # }
}

# ============================
# 统一路径生成
# ============================
def get_filepath(year, month, region, var):
    base = Path(__file__).parent
    if region == "normal":
        return base / f"cmaqout_processed/{year}_Emission[{year}met]_{month}.csv"
    else:
        return base / f"cmaqout_processed_HuiZhou/{year}_Emission[{year}met]_{month}_HuiZhou.csv"

# ============================
# KDE 拟合
# ============================
def kde_fit(data, x):
    kde = gaussian_kde(data)
    pdf = kde(x)
    area = np.trapz(pdf, x)
    if area > 1e-10:
        pdf /= area
    return pdf

# ============================
# 绘制单张图
# ============================
def plot_comparison(var_name, cfg, year, month, region):
    print(f"📌 {var_name} — {year} vs 2023, 月份 {month}, 地区 {region}")

    file_2023 = get_filepath(2023, month, region, var_name)
    file_other = get_filepath(year, month, region, var_name)

    if not file_2023.exists() or not file_other.exists():
        print(f"❌ 缺少文件: {file_2023} 或 {file_other}")
        return

    df2023 = pd.read_csv(file_2023)
    df_other = pd.read_csv(file_other)

    col = cfg['column']
    data23 = df2023[col].dropna().values
    dataO = df_other[col].dropna().values

    # 清洗
    if cfg['is_count_data']:
        data23 = data23[(data23 >= 0) & (data23 <= 31)]
        dataO = dataO[(dataO >= 0) & (dataO <= 31)]
    else:
        data23 = data23[(data23 >= 0) & (data23 <= 500)]
        dataO = dataO[(dataO >= 0) & (dataO <= 500)]

    if len(data23) == 0 or len(dataO) == 0:
        print("⚠ 数据为空，跳过")
        return

    # x 范围
    min_val = min(data23.min(), dataO.min())
    # max_val = max(data23.max(), dataO.max())
    max_val = 22
    min_val *= 0.9
    max_val *= 1.1
    x = np.linspace(min_val, max_val, 500)
    # 直方图分箱（同时用于 x 轴刻度）
    bins = np.linspace(min_val, max_val, TARGET_BIN_COUNT + 1)

    # KDE
    pdf23 = kde_fit(data23, x)
    pdfO = kde_fit(dataO, x)

    # 统计量
    m23, s23 = data23.mean(), data23.std()
    mO, sO = dataO.mean(), dataO.std()

    # 绘图
    plt.figure(figsize=(10, 6))

    # 使用统一的颜色和线型
    color_2023 = YEAR_COLORS[2023]
    linestyle_2023 = YEAR_LINESTYLES[2023]
    color_year = YEAR_COLORS.get(year, 'green')  # 默认绿色
    linestyle_year = YEAR_LINESTYLES.get(year, '--')  # 默认虚线

    # 先画直方图作为背景：2023 半透明实心柱，对比年份空心柱
    plt.hist(data23, bins=bins, density=True,
             alpha=0.25, color=color_2023,
             edgecolor=color_2023, linewidth=0.5)
    plt.hist(dataO, bins=bins, density=True,
             alpha=1.0, facecolor='none',
             edgecolor=color_year, linewidth=1.5)

    # 再叠加 KDE 曲线
    plt.plot(x, pdf23, linestyle_2023, color=color_2023, linewidth=2.5)
    plt.plot(x, pdfO, linestyle_year, color=color_year, linewidth=2.5)

    # 图例（左上角，专业）
    plt.plot([], [], linestyle_2023, color=color_2023,
             label=f"2023 (μ={m23:.2f}, σ={s23:.2f})")
    plt.plot([], [], linestyle_year, color=color_year,
             label=f"{year} (μ={mO:.2f}, σ={sO:.2f})")

    plt.legend(loc="upper right", fontsize=12)

    # 标题 & 标签
    region_name = "HuiZhou" if region == "huizhou" else "GuangDong"
    month_names_cn = {"01": "1月", "07": "7月"}

    # 使用中文标题格式：月份 变量名 (年份1, 年份2, 年份3)
    plt.title(f"{month_names_cn[month]} {cfg['title']} ({year}, 2023) ({region_name})",
              fontsize=15, fontweight="bold")
    plt.xlabel(f"{cfg['title']} ({cfg['unit']})",fontsize=13)
    plt.ylabel("Probability Density",fontsize=13)
    plt.grid(True, alpha=0.3)

    # x tick
    xticks = bins[::XTICK_EVERY_N_BINS]
    plt.xticks(xticks, [f"{v:.1f}" for v in xticks])

    plt.tight_layout()

    # 输出路径
    outdir = Path(__file__).parent / OUTPUT_DIR
    outdir.mkdir(exist_ok=True)
    suffix = "" if region == "normal" else "_HuiZhou"
    outfile = outdir / f"{var_name}_{year}vs2023_{month}{suffix}.png"

    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✔ 保存: {outfile}")

# ============================
# 主函数
# ============================
def main():
    print("=" * 70)
    print("CMAQ 多年份 KDE 分布对比（优化版）")
    print("=" * 70)

    for var_name, cfg in VARIABLE_CONFIGS.items():
        print(f"\n📌 开始变量：{var_name}")
        for year in YEARS_TO_COMPARE:
            for month in MONTHS:
                for region in REGIONS:
                    plot_comparison(var_name, cfg, year, month, region)

    print("\n🎉 全部处理完成！")
    print(f"📁 输出目录: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
