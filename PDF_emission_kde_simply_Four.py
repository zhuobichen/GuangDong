#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import gaussian_kde
import re
import os

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']  # 支持中文显示
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
plt.rcParams['font.family'] = 'sans-serif'

# 确保所有元素都使用中文字体
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# ============================
# CASE映射配置（Case1到Case4）
# ============================
CASE_DEFINITIONS = {
    'CASE1': ('2000', '2000', '2000e2000m', '2000排放+2000气象'),  # 基准Case
    'CASE2': ('2000', '2023', '2000e2023m', '2000排放+2023气象'),  # 气象变化
    'CASE3': ('2023', '2023', '2023e2023m', '2023排放+2023气象'),  # 排放+气象变化
    'CASE4': ('2023', '2000', '2023e2000m', '2023排放+2000气象'),  # 排放变化
}

CASE_COLORS = {
    'CASE1': 'orange',    # 基准Case（实线）
    'CASE2': 'purple',    # 气象变化（虚线）
    'CASE3': 'green',     # 排放+气象变化（点划线）
    'CASE4': 'red',       # 排放变化（点线）
}

CASE_LINESTYLES = {
    'CASE1': '-',         # 实线
    'CASE2': '--',        # 虚线
    'CASE3': '-.',        # 点划线
    'CASE4': ':',         # 点线
}

CASE_DISPLAY_NAMES = {
    'CASE1': 'Case1',
    'CASE2': 'Case2', 
    'CASE3': 'Case3',
    'CASE4': 'Case4',
}

# ============================
# 直接指定配置参数
# ============================
INPUT_CASES = ['CASE1', 'CASE2', 'CASE3', 'CASE4']  # 直接指定Case1到Case4
SELECTED_VARIABLES = ['O3', 'PM2.5']  # 直接指定要分析的变量
SELECTED_MONTHS = ["01", "07"]  # 直接指定月份
SELECTED_REGIONS = None  # 区域由数据变体控制

BASE_DATA_DIR = Path(__file__).parent / "cmaqout_processed"  # 默认，不直接使用
OUTPUT_DIR = "Emission_Comparison_Plots_PDF_CN"
TARGET_BIN_COUNT = 20
XTICK_EVERY_N_BINS = 2

# ============================
# 数据变体选择：raw / land / GuangDong / HuiZhou
# ============================
DATA_VARIANT = "GuangDong"  # 默认用陆地掩膜版本
VARIANT_CONFIG = {
    "raw": {
        "folder": "cmaqout_processed",
        "suffix": "",
        "region_label": "原始",
        "outfile_tag": "Raw"
    },
    "land": {
        "folder": "cmaqout_processed_land",
        "suffix": "_land",
        "region_label": "陆地",
        "outfile_tag": "Land"
    },
    "GuangDong": {
        "folder": "cmaqout_processed_GuangDong",
        "suffix": "_GuangDong",
        "region_label": "广东",
        "outfile_tag": "GuangDong"
    },
    "HuiZhou": {
        "folder": "cmaqout_processed_HuiZhou",
        "suffix": "_HuiZhou",
        "region_label": "惠州",
        "outfile_tag": "HuiZhou"
    }
}

# ============================
# 变量配置
# ============================
VARIABLE_CONFIGS = {
    'O3': {
        'column': 'O3',
        'unit': 'ppbv',
        'title': 'O3',
        'is_count_data': False
    },
    'PM2.5': {
        'column': 'PM2.5',
        'unit': 'μg/m³',
        'title': 'PM2.5',
        'is_count_data': False
    },
    'O3_Days': {
        'column': 'O3_Days',
        'unit': 'days',
        'title': 'O3≥80ppb Days',
        'is_count_data': True
    },
    'PM2.5_Days': {
        'column': 'PM2.5_Days',
        'unit': 'days',
        'title': 'PM2.5≥75μg/m³ Days',
        'is_count_data': True
    }
}

# ============================
# 根据Case自动查找对应文件
# ============================
def find_case_file(case_id, month):
    """根据Case ID自动查找对应的文件"""
    if case_id not in CASE_DEFINITIONS:
        raise ValueError(f"不支持的Case ID: {case_id}，仅支持CASE1到CASE4")
    
    emission_year, met_year, case_key, desc = CASE_DEFINITIONS[case_id]
    
    # 构建可能的文件路径模式
    file_patterns = [
        f"{emission_year}_Emission[{met_year}met]_{month}.csv",
        f"{emission_year}e{met_year}m_{month}.csv",
        f"CASE{case_id[-1]}_{month}.csv",
        f"{case_key}_{month}.csv"
    ]
    
    # 根据数据变体选择目录与后缀
    cfg = VARIANT_CONFIG[DATA_VARIANT]
    data_dir = Path(__file__).parent / cfg["folder"]
    suffix = cfg["suffix"]
    file_patterns = [f"{os.path.splitext(p)[0]}{suffix}.csv" for p in file_patterns]
    
    # 查找匹配的文件
    for pattern in file_patterns:
        file_path = data_dir / pattern
        if file_path.exists():
            print(f"✅ {case_id} 文件找到: {file_path.name}")
            return file_path
        
        # 检查子目录
        for subdir in data_dir.glob("*"):
            if subdir.is_dir():
                subdir_file = subdir / pattern
                if subdir_file.exists():
                    print(f"✅ {case_id} 文件找到: {subdir_file}")
                    return subdir_file
    
    # 如果找不到，尝试模糊匹配
    for file in data_dir.glob(f"*{emission_year}*_{month}{suffix}.csv"):
        if str(met_year) in file.name:
            print(f"✅ {case_id} 文件找到（模糊匹配）: {file.name}")
            return file
    
    print(f"❌ {case_id} 文件未找到！尝试的模式: {file_patterns}")
    return None

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
# 绘制Case对比图
# ============================
def plot_case_comparison(var_name, cfg, month):
    region_label = VARIANT_CONFIG[DATA_VARIANT]["region_label"]
    print(f"\n📊 {cfg['title']} — Case1~Case4对比分析, 月份 {month}, 变体 {DATA_VARIANT}（{region_label}）")
    
    data_dict = {}
    
    # 为每个Case加载数据
    for case_id in INPUT_CASES:
        file_path = find_case_file(case_id, month)
        if not file_path or not file_path.exists():
            print(f"⚠️ {case_id} 文件缺失，跳过")
            continue
        
        try:
            df = pd.read_csv(file_path)
            
            # 检查列是否存在
            if cfg['column'] not in df.columns:
                print(f"⚠️ {case_id} 文件中缺少列: {cfg['column']}")
                continue
            
            data = df[cfg['column']].dropna().values
            
            # 数据清洗
            if cfg['is_count_data']:
                data = data[(data >= 0) & (data <= 31)]  # 超标天数限制
            else:
                if cfg['unit'] == 'ppbv':
                    data = data[(data >= 0) & (data <= 200)]  # O3浓度范围
                else:
                    data = data[(data >= 0) & (data <= 200)]  # PM2.5浓度范围
            
            if len(data) > 0:
                data_dict[case_id] = {
                    'data': data,
                    'mean': np.mean(data),
                    'std': np.std(data),
                    'count': len(data)
                }
                print(f"📈 {case_id}: 样本数={len(data)}, 均值={np.mean(data):.2f}, 标准差={np.std(data):.2f}")
            else:
                print(f"⚠️ {case_id} 有效数据为空")
                
        except Exception as e:
            print(f"❌ {case_id} 数据加载失败: {str(e)}")
            continue
    
    # 检查有效数据
    if len(data_dict) < 2:
        print(f"⚠️ 有效Case数据不足2个，跳过")
        return
    
    # 准备绘图数据
    all_data = []
    for case_data in data_dict.values():
        all_data.extend(case_data['data'])
    
    all_data = np.array(all_data)
    min_val = max(0, all_data.min() * 0.9)
    max_val = all_data.max() * 1.1
    x = np.linspace(min_val, max_val, 500)
    
    # 创建图形
    plt.figure(figsize=(14, 8))
    
    # 绘制每个Case的KDE曲线
    for case_id in data_dict:
        case_info = data_dict[case_id]
        color = CASE_COLORS.get(case_id, 'gray')
        linestyle = CASE_LINESTYLES.get(case_id, '-')
        
        pdf = kde_fit(case_info['data'], x)
        
        # 图例标签：只保留Case标识和统计信息（原样）
        label = f"{CASE_DISPLAY_NAMES[case_id]} (μ={case_info['mean']:.2f}, σ={case_info['std']:.2f})"
        
        plt.plot(x, pdf, linestyle=linestyle, color=color, linewidth=2.5,
                label=label, alpha=0.8)
    
    # 添加图例和标签（右上角保留原样）
    plt.legend(loc="upper right", fontsize=12)
    
    # 设置标题：年份换成Case，保持原有样式
    region_name = region_label
    month_names_cn = {"01": "1月", "07": "7月"}
    
    # 标题格式：月份 指标 (Case1, Case2, Case3, Case4) (区域)
    plt.title(f"{month_names_cn[month]} {cfg['title']} (Case1, Case2, Case3, Case4)（{region_name}）",
              fontsize=16, fontweight="bold")
    
    plt.xlabel(f"{cfg['title']} ({cfg['unit']})", fontsize=14)
    plt.ylabel("Probability Density", fontsize=14)
    plt.grid(False)
    
    # x ticks
    bins = np.linspace(min_val, max_val, TARGET_BIN_COUNT + 1)
    xticks = bins[::XTICK_EVERY_N_BINS]
    plt.xticks(xticks, [f"{v:.1f}" for v in xticks])
    
    # 移除左上角的标注
    
    plt.tight_layout()
    
    # 输出路径
    outdir = Path(OUTPUT_DIR)
    outdir.mkdir(exist_ok=True)
    outfile_tag = VARIANT_CONFIG[DATA_VARIANT]["outfile_tag"]
    outfile = outdir / f"{var_name}_CaseComparison_{month}_{outfile_tag}.png"
    
    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close()
    
    print(f"✔ 保存: {outfile}")
    
    # 返回统计摘要
    return data_dict

# ============================
# 生成统计报告
# ============================
def generate_stat_report(all_results):
    """生成Case对比统计报告"""
    report_file = Path(OUTPUT_DIR) / "Case_Comparison_Report.csv"
    
    # 创建统计摘要
    stats_summary = []
    
    for var_name, var_results in all_results.items():
        for month, month_results in var_results.items():
            for region, region_results in month_results.items():
                for case_id, case_data in region_results.items():
                    stats_summary.append({
                        'Variable': var_name,
                        'Month': month,
                        'Region': region,
                        'Case': case_id,
                        'Description': CASE_DEFINITIONS[case_id][3],
                        'Count': case_data['count'],
                        'Mean': case_data['mean'],
                        'Std': case_data['std'],
                        'Max': np.max(case_data['data']),
                        'Min': np.min(case_data['data']),
                        'Median': np.median(case_data['data'])
                    })
    
    # 保存报告
    df_summary = pd.DataFrame(stats_summary)
    df_summary.to_csv(report_file, index=False)
    print(f"\n📊 统计报告已生成: {report_file}")
    
    # 显示关键对比
    print("\n=== Case1 vs Case3 Change Percentage ===")
    for var_name, var_results in all_results.items():
        for month, month_results in var_results.items():
            for region, region_results in month_results.items():
                if 'CASE1' in region_results and 'CASE3' in region_results:
                    case1_mean = region_results['CASE1']['mean']
                    case3_mean = region_results['CASE3']['mean']
                    change_pct = ((case3_mean - case1_mean) / case1_mean) * 100
                    print(f"{var_name} {month} {region}: {change_pct:+.1f}%")

# ============================
# 主函数
# ============================
def main():
    print("=" * 80)
    print("       CMAQ Case Comparison (Case1, Case2, Case3, Case4)")
    print("=" * 80)
    
    print("\n📋 Case Definitions:")
    for case_id in INPUT_CASES:
        emission, met, key, desc = CASE_DEFINITIONS[case_id]
        print(f"  {case_id}: {desc} ({key})")
    
    cfg = VARIANT_CONFIG[DATA_VARIANT]
    data_dir = Path(__file__).parent / cfg["folder"]
    print(f"\n📁 Data Directory: {data_dir}")
    print(f"📁 Output Directory: {OUTPUT_DIR}")
    
    # 创建输出目录
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    
    # 存储所有结果
    all_results = {}
    
    # 处理直接指定的变量与月份（区域由变体控制）
    for var_name in SELECTED_VARIABLES:
        if var_name not in VARIABLE_CONFIGS:
            print(f"\n⚠️ Variable {var_name} not defined, skipping")
            continue
            
        all_results[var_name] = {}
        cfg = VARIABLE_CONFIGS[var_name]
        
        for month in SELECTED_MONTHS:
            all_results[var_name][month] = {}
            case_results = plot_case_comparison(var_name, cfg, month)
            all_results[var_name][month][DATA_VARIANT] = case_results
    
    # 生成统计报告
    if all_results:
        generate_stat_report(all_results)
    
    print("\n🎉 All analysis completed!")
    print(f"📁 Results saved in: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()