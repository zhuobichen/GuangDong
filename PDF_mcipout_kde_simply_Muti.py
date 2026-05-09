#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
from tqdm.auto import tqdm
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

# ============================
# 【修改1】优化中文字体配置 - 全平台兼容，中文显示更稳定
# ============================
plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']  # 适配全平台中文
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
plt.rcParams['font.family'] = 'sans-serif'

# 图表全局字号配置
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# ============================
# 统一设置
# ============================
YEARS_TO_COMPARE = [2030, 2060, 2023]  # 只绘制2030、2060、2023年
MONTHS = ["01", "07"]
OUTPUT_DIR = "Mcip_Comparison_Plots_PDF_CN_MutiYear"
TARGET_BIN_COUNT = 20
XTICK_EVERY_N_BINS = 2

# 数据变体选择：raw / land / GuangDong / HuiZhou
DATA_VARIANT = "land"  # 默认用陆地掩膜版本

# 变体配置：输入目录、文件名后缀、标题区域名、输出文件名标识
VARIANT_CONFIG = {
    "raw": {
        "folder": "mcipout_processed",
        "suffix": "",
        "region_label": "原始",
        "outfile_tag": "Raw"
    },
    "land": {
        "folder": "mcipout_processed_land",
        "suffix": "_land",
        "region_label": "陆地",
        "outfile_tag": "Land"
    },
    "GuangDong": {
        "folder": "mcipout_processed_GuangDong",
        "suffix": "_GuangDong",
        "region_label": "广东",
        "outfile_tag": "GuangDong"
    },
    "HuiZhou": {
        "folder": "mcipout_processed_HuiZhou",
        "suffix": "_HuiZhou",
        "region_label": "惠州",
        "outfile_tag": "HuiZhou"
    }
}

# ============================
# 变量配置（气象数据）
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

VARIABLES = {
    # "TA_mean": {
    #     "col": "TA_mean",
    #     "unit": "°C",
    #     "title": "TA",
    #     "is_count_data": False
    # },
    "SOL_RAD_mean": {
        "col": "SOL_RAD_mean",
        "unit": "W/m²",
        "title": "SOL_RAD",
        "is_count_data": False
    },
    "PBLH_mean": {
        "col": "PBLH_mean",
        "unit": "m",
        "title": "PBLH",
        "is_count_data": False
    },
}

# ============================
# 文件路径生成（按变体）
# ============================
def get_filepath(year: int, month: str):
    """根据 DATA_VARIANT 生成 MCIP 文件路径"""
    base = Path(__file__).parent
    cfg = VARIANT_CONFIG.get(DATA_VARIANT)
    if cfg is None:
        raise ValueError(f"未知的数据变体 DATA_VARIANT={DATA_VARIANT}，可选：{list(VARIANT_CONFIG.keys())}")
    folder = cfg["folder"]
    suffix = cfg["suffix"]
    return base / f"{folder}/{year}_mcipout_{month}{suffix}.csv"

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
# 绘制三年份叠加图
# ============================
def plot_three_years_overlay(var_name, var_config, month):
    cfg = VARIANT_CONFIG[DATA_VARIANT]
    region_label = cfg["region_label"]
    print(f"📊 {var_name} — 2030, 2060, 2023 三年叠加, 月份 {month}, 变体 {DATA_VARIANT}（{region_label}）")

    years_to_load = YEARS_TO_COMPARE
    data_dict = {}

    # 【修改3】强制按定义顺序读取年份，保证图例顺序正确
    for year in years_to_load:
        file_path = get_filepath(year, month)
        if not file_path.exists():
            print(f"❌ 缺少文件: {file_path}")
            continue  # 跳过这个年份，继续处理其他年份

        df = pd.read_csv(file_path)
        col = var_config["col"]
        data = df[col].dropna().values

        if len(data) == 0:
            print(f"⚠️ {year}年数据为空，跳过")
            continue  # 跳过这个年份，继续处理其他年份

        data_dict[year] = data

    # 检查是否至少有两年份数据
    if len(data_dict) < 2:
        print(f"⚠️ 有效数据年份不足2个，跳过变量 {var_name}")
        return

    # 确定x范围
    all_data = np.concatenate([data_dict[year] for year in years_to_load])
    min_val = all_data.min() * 0.9
    max_val = all_data.max() * 1.1
    x = np.linspace(min_val, max_val, 500)

    # 绘图
    plt.figure(figsize=(12, 7))

    # 按定义顺序绘制每个年份的KDE曲线
    for year in years_to_load:
        if year not in data_dict:  # 跳过没有数据的年份
            continue
        # 获取当前年份的颜色、线型
        color = YEAR_COLORS[year]
        linestyle = YEAR_LINESTYLES[year]
        # 拟合KDE并绘图
        pdf = kde_fit(data_dict[year], x)
        m_year, s_year = data_dict[year].mean(), data_dict[year].std()
        plt.plot(x, pdf, linestyle=linestyle, color=color, linewidth=2.5,
                label=f"{year} (μ={m_year:.2f}, σ={s_year:.2f})")

    plt.legend(loc="upper right", fontsize=12)

    # 标题 & 标签
    region_name = region_label
    month_names_cn = {"01": "1月", "07": "7月"}

    # 使用中文标题格式：月份 变量名 (年份1, 年份2, 年份3)
    plt.title(f"{month_names_cn[month]} {var_config['title']} ({', '.join(map(str, YEARS_TO_COMPARE))})（{region_name}）",
              fontsize=15, fontweight="bold")
    plt.xlabel(f"{var_config['title']} ({var_config['unit']})", fontsize=13)
    plt.ylabel("Probability Density", fontsize=13)
    
    # ============================
    # 【修改2】核心需求：彻底移除所有背景网格线（主+次）
    # ============================
    plt.grid(visible=False)

    # x ticks
    bins = np.linspace(min_val, max_val, TARGET_BIN_COUNT + 1)
    xticks = bins[::XTICK_EVERY_N_BINS]
    plt.xticks(xticks, [f"{v:.1f}" for v in xticks])

    plt.tight_layout()

    # 输出路径
    outdir = Path(__file__).parent / OUTPUT_DIR
    outdir.mkdir(exist_ok=True)
    outfile_tag = cfg["outfile_tag"]
    outfile = outdir / f"{var_name}_ThreeYears_{month}_{outfile_tag}.png"

    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✔ 保存: {outfile}")

# ============================
# 主函数
# ============================
def main():
    print("=" * 70)
    print("       MCIP 气象变量三年份 KDE 分布叠加（2030,2060,2023版）")
    print("=" * 70)

    for var_name, var_config in VARIABLES.items():
        print(f"\n📊 开始变量: {var_name}（变体：{DATA_VARIANT}）")
        for month in MONTHS:
            plot_three_years_overlay(var_name, var_config, month)

    print("\n🎉 全部处理完成！")
    print(f"📁 输出目录: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()