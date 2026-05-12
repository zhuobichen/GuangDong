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
YEARS_TO_COMPARE = [2000, 2023, 2030, 2060]  # 修改：绘制2000、2023、2030、2060四年
MONTHS = ["01", "07"]
REGIONS = ["normal", "huizhou"]
OUTPUT_DIR = "Emission_Comparison_Plots_PDF_CN"
TARGET_BIN_COUNT = 20
XTICK_EVERY_N_BINS = 2

# ============================
# 变量配置
# ============================
VARIABLE_CONFIGS = {
    'O3': {
        'column': 'O3',
        'unit': 'ppbv',
        'title': 'O3',
        'color_2000': 'orange',
        'color_2023': 'purple',
        'color_2030': 'blue',
        'color_2060': 'red',
        'is_count_data': False
    },
    'PM2.5': {
        'column': 'PM2.5',
        'unit': 'μg/m³',
        'title': 'PM2.5',
        'color_2000': 'orange',
        'color_2023': 'purple',
        'color_2030': 'blue',
        'color_2060': 'red',
        'is_count_data': False
    }
}

# ============================
# 文件路径生成
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
# 绘制四年份叠加图
# ============================
def plot_four_years_overlay(var_name, cfg, month, region):
    print(f"📊 {var_name} — 2000, 2023, 2030, 2060 四年叠加, 月份 {month}, 区域 {region}")

    years_to_load = [2000, 2023, 2030, 2060]
    colors = ['orange', 'purple', 'blue', 'red']
    linestyles = ['-', '--', '-.', ':']

    data_dict = {}

    # 读取所有年份的数据
    for i, year in enumerate(years_to_load):
        file_path = get_filepath(year, month, region, var_name)
        if not file_path.exists():
            print(f"❌ 缺少文件: {file_path}")
            continue  # 跳过这个年份，继续处理其他年份

        df = pd.read_csv(file_path)
        col = cfg['column']
        data = df[col].dropna().values

        # 清洗数据
        if cfg['is_count_data']:
            data = data[(data >= 0) & (data <= 31)]
        else:
            data = data[(data >= 0) & (data <= 500)]

        if len(data) == 0:
            print(f"⚠️ {year}年数据为空，跳过")
            continue  # 跳过这个年份，继续处理其他年份

        data_dict[year] = data

    # 检查是否至少有两年份数据
    if len(data_dict) < 2:
        print(f"⚠️ 有效数据年份不足2个，跳过变量 {var_name}")
        return

    # 确定x范围
    all_data = np.concatenate([data_dict[year] for year in data_dict.keys()])
    min_val = all_data.min() * 0.9
    max_val = all_data.max() * 1.1
    x = np.linspace(min_val, max_val, 500)

    # 绘图
    plt.figure(figsize=(14, 8))

    # 为每个年份绘制KDE曲线
    available_years = list(data_dict.keys())
    for i, year in enumerate(available_years):
        # 获取对应的颜色和线型
        year_index = years_to_load.index(year)
        color = colors[year_index]
        linestyle = linestyles[year_index]

        pdf = kde_fit(data_dict[year], x)
        m_year, s_year = data_dict[year].mean(), data_dict[year].std()
        plt.plot(x, pdf, linestyle=linestyle, color=color, linewidth=2.5,
                label=f"{year} (μ={m_year:.2f}, σ={s_year:.2f})")

    plt.legend(loc="upper right", fontsize=12)

    # 标题 & 标签
    region_name = "HuiZhou" if region == "huizhou" else "GuangDong"
    month_names_cn = {"01": "1月", "07": "7月"}

    # 使用中文标题格式：月份 变量名 (年份1, 年份2, 年份3, 年份4)
    plt.title(f"{month_names_cn[month]} {cfg['title']} (2000, 2023, 2030, 2060) ({region_name})",
              fontsize=16, fontweight="bold")
    plt.xlabel(f"{cfg['title']} ({cfg['unit']})", fontsize=14)
    plt.ylabel("Probability Density", fontsize=14)
    plt.grid(True, alpha=0.3)

    # x ticks
    bins = np.linspace(min_val, max_val, TARGET_BIN_COUNT + 1)
    xticks = bins[::XTICK_EVERY_N_BINS]
    plt.xticks(xticks, [f"{v:.1f}" for v in xticks])

    plt.tight_layout()

    # 输出路径
    outdir = Path(__file__).parent / OUTPUT_DIR
    outdir.mkdir(exist_ok=True)
    suffix = "" if region == "normal" else "_HuiZhou"
    outfile = outdir / f"{var_name}_FourYears_{month}{suffix}.png"

    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✔ 保存: {outfile}")

# ============================
# 主函数
# ============================
def main():
    print("=" * 80)
    print("       CMAQ 四年份 KDE 分布叠加（2000, 2023, 2030, 2060版）")
    print("=" * 80)

    for var_name, cfg in VARIABLE_CONFIGS.items():
        print(f"\n📊 开始变量: {var_name}")
        for month in MONTHS:
            for region in REGIONS:
                plot_four_years_overlay(var_name, cfg, month, region)

    print("\n🎉 全部处理完成！")
    print(f"📁 输出目录: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()