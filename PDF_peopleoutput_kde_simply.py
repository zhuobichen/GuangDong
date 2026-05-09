#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

# ================================
# 配置
# ================================
VARIABLE_NAME = "PM2.5"
COLUMN_NAME = "PM2.5"
UNIT = "g/s"
TITLE = r"$PM_{2.5}$ Emissions"

COLOR_2023 = "purple"
COLOR_OTHER = "green"

YEARS_TO_COMPARE = [2000, 2030, 2060]
MONTHS = ["01", "07"]
REGIONS = ["normal", "huizhou"]

OUTPUT_DIR = "PeopleEmission_Plots_PDF"
TARGET_BIN_COUNT = 20
XTICK_EVERY_N_BINS = 2


# ================================
# 读取数据文件路径
# ================================
def get_filepath(year: int, month: str, region: str) -> Path:
    """
    根据年份、月份、地区生成文件路径。
    """
    base = Path(__file__).parent

    if region == "normal":
        return base / f"emissionlist/EM_{year}{month}_PM2.5.csv"
    else:
        return base / f"emissionlist_HuiZhou/EM_{year}{month}_PM2.5_HuiZhou.csv"


# ================================
# KDE 拟合
# ================================
def kde_fit(data: np.ndarray, x_range: np.ndarray):
    kde = gaussian_kde(data)
    pdf = kde(x_range)
    area = np.trapz(pdf, x_range)
    if area > 1e-10:
        pdf *= 1.0 / area
    return pdf


# ================================
# 绘制单张图
# ================================
def plot_comparison(year, month, region):
    """
    绘制某年 vs 2023（某地区 & 某月份）排放分布图
    """
    print(f"📌 绘制: {year} vs 2023 - {region}, 月份 {month}")

    base = Path(__file__).parent

    # 文件路径
    file_2023 = get_filepath(2023, month, region)
    file_other = get_filepath(year, month, region)

    if not file_2023.exists() or not file_other.exists():
        print(f"❌ 文件缺失，跳过: {file_2023}, {file_other}")
        return

    # 读取数据
    df2023 = pd.read_csv(file_2023)
    df_other = pd.read_csv(file_other)

    data2023 = df2023[COLUMN_NAME].dropna().values
    data_other = df_other[COLUMN_NAME].dropna().values

    data2023 = data2023[data2023 >= 0]
    data_other = data_other[data_other >= 0]

    if len(data2023) == 0 or len(data_other) == 0:
        print("❌ 数据为空，跳过。")
        return

    # === 截断极端尾部（p99.5） ===
    p99_23 = np.percentile(data2023, 98.5)
    p99_cmp = np.percentile(data_other, 98.5)

    min_val = min(data2023.min(), data_other.min())
    max_val = min(p99_23, p99_cmp)
    margin_min = 0.9
    margin_max = 1.1

    if min_val > 0:
        min_val *= margin_min
    else:
        min_val *= margin_max
    max_val *= margin_max

    x_cont = np.linspace(min_val, max_val, 500)

    # KDE
    pdf_2023 = kde_fit(data2023, x_cont)
    pdf_other = kde_fit(data_other, x_cont)

    # 均值和标准差
    mean23, std23 = data2023.mean(), data2023.std()
    meanO, stdO = data_other.mean(), data_other.std()

    # 绘图
    plt.figure(figsize=(10, 6))

    plt.plot(x_cont, pdf_2023, "-", color=COLOR_2023, linewidth=2.5)
    plt.plot(x_cont, pdf_other, "--", color=COLOR_OTHER, linewidth=2.5)

    # 图例（左上角）
    plt.plot([], [], "-", color=COLOR_2023,
             label=f"2023  (μ={mean23:.2f}, σ={std23:.2f})")
    plt.plot([], [], "--", color=COLOR_OTHER,
             label=f"{year}  (μ={meanO:.2f}, σ={stdO:.2f})")

    plt.legend(loc="upper right", fontsize=12, frameon=True)

    # 标题与轴标签
    region_name = "HuiZhou" if region == "huizhou" else "GuangDong"
    month_name = "January" if month == "01" else "July"

    plt.title(f"{TITLE} Distribution ({region_name}, {month_name})",
              fontsize=15, fontstyle="italic")
    plt.xlabel(f"{TITLE} ({UNIT})", fontsize=13)
    plt.ylabel("Probability Density", fontsize=13)

    # x 轴刻度
    bins = np.linspace(min_val, max_val, TARGET_BIN_COUNT + 1)
    xticks = bins[::XTICK_EVERY_N_BINS]
    plt.xticks(xticks, [f"{x:.2f}" for x in xticks])

    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # 输出路径
    suffix = "" if region == "normal" else "_HuiZhou"
    outname = f"{VARIABLE_NAME}_{year}vs2023_{month}{suffix}.png"
    output_dir = base / OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)
    outfile = output_dir / outname

    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✔ 保存成功: {outfile}")


# ================================
# 主函数
# ================================
def main():
    print("\n🚀 开始绘制 PM2.5 多年份 KDE 分布图...\n")

    for year in YEARS_TO_COMPARE:
        for month in MONTHS:
            for region in REGIONS:
                plot_comparison(year, month, region)

    print("\n🎉 所有图像生成完成！")
    print(f"📂 输出目录: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
