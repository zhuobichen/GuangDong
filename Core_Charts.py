#!/usr/bin/env python3
"""
Core_Charts.py — 柱状图/箱线图核心模块

提供 CASE 对比的柱状图（超标面积×天数）和箱线图绘制函数。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# 字体
plt.rcParams["font.family"] = ['Times New Roman', 'Noto Serif CJK JP', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['text.usetex'] = False

# ============================================================
# CASE 定义 (所有图表脚本共用)
# ============================================================

CASE_DEFINITIONS = {
    'CASE1': ('2000', '2000', '2000e2000m'),
    'CASE2': ('2000', '2023', '2000e2023m'),
    'CASE3': ('2023', '2023', '2023e2023m'),
    'CASE4': ('2023', '2000', '2023e2000m'),
    'CASE5': ('2060', '2060', '2060e2060m'),
    'CASE6': ('2030', '2030', '2030e2030m'),
}

CASE_COLORS = {
    'CASE1': '#E3A018', 'CASE2': '#6F2DA8', 'CASE3': '#1B8248',
    'CASE4': '#D73027', 'CASE5': '#9C27B0', 'CASE6': '#FFB703',
}

MONTH_MAPPING_CN = {f"{i:02d}": f"{i}月" for i in range(1, 13)}
GRID_AREA_KM2 = 3.0 * 3.0  # 3km × 3km


# ============================================================
# 文件查找
# ============================================================

def find_case_file(
    case_id: str,
    month_code: str,
    data_dir: Path,
    file_suffix: str = "",
) -> Optional[Path]:
    """根据 CASE 定义和月份查找 CSV 文件。"""
    if case_id not in CASE_DEFINITIONS:
        raise ValueError(f"Unknown CASE: {case_id}")

    emission_year, met_year, case_key = CASE_DEFINITIONS[case_id]

    patterns = [
        f"{emission_year}_Emission[{met_year}met]_{month_code}{file_suffix}.csv",
        f"{case_key}_{month_code}{file_suffix}.csv",
        f"{case_id}_{month_code}{file_suffix}.csv",
        f"{emission_year}e{met_year}m_{month_code}{file_suffix}.csv",
        f"{emission_year}_Emission_{month_code}{file_suffix}.csv",
    ]
    for pattern in patterns:
        fp = data_dir / pattern
        if fp.exists():
            return fp
    return None


def load_case_data(case_id: str, month_code: str, column: str, data_dir: Path,
                   file_suffix: str = "") -> np.ndarray:
    """加载单个 CASE 的数据列 (dropna)。"""
    fp = find_case_file(case_id, month_code, data_dir, file_suffix)
    if fp is None:
        raise FileNotFoundError(f"CASE {case_id} 文件未找到: {data_dir}/{month_code}")
    df = pd.read_csv(fp)
    if column not in df.columns:
        raise ValueError(f"列 '{column}' 不存在于 {fp}")
    return pd.to_numeric(df[column], errors='coerce').dropna().to_numpy(dtype=float)


# ============================================================
# 超标面积×天数柱状图
# ============================================================

def plot_area_days_barchart(
    cases: List[str],
    var_name: str,
    var_column: str,
    var_title: str,
    var_ylabel: str,
    month_code: str,
    data_dir: Path,
    file_suffix: str = "",
    output_dir: Optional[Path] = None,
) -> str:
    """绘制 CASE 超标面积×天数柱状图。

    Args:
        cases:       CASE 列表，如 ['CASE1', 'CASE2', 'CASE3', 'CASE4']
        var_name:    变量名（用于输出文件名），如 'O3' 或 'PM2.5'
        var_column:  CSV 列名，如 'O3_Days' 或 'PM2.5_Days'
        var_title:   图表标题
        var_ylabel:  y 轴标签
        month_code:  月份代码 '01' / '07'
        data_dir:    数据目录
        file_suffix: 文件后缀，如 '_GuangDong'
        output_dir:  输出目录（默认 data_dir 的父目录/BarCharts_Output_CaseComparison）

    Returns:
        输出文件路径
    """
    if output_dir is None:
        output_dir = data_dir.parent / "BarCharts_Output_CaseComparison"

    month_cn = MONTH_MAPPING_CN.get(month_code, f"Month {month_code}")
    values: Dict[str, float] = {}
    for cid in cases:
        try:
            data = load_case_data(cid, month_code, var_column, data_dir, file_suffix)
            values[cid] = float(np.nansum(data) * GRID_AREA_KM2)
        except Exception as e:
            print(f"  ❌ {cid}: {e}")
            values[cid] = np.nan

    x_labels = cases
    y = [values.get(c, np.nan) for c in x_labels]
    colors = [CASE_COLORS.get(c, '#4C78A8') for c in x_labels]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(x_labels, y, color=colors, edgecolor="black", linewidth=0.8)

    plt.title(f"{var_title}（{month_cn}）", fontsize=18, fontweight='bold')
    plt.ylabel(var_ylabel, fontsize=16, fontweight='bold')
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)

    for rect, val in zip(bars, y):
        if np.isfinite(val):
            plt.text(rect.get_x() + rect.get_width() / 2, rect.get_height(),
                     f"{val:.0f}", ha='center', va='bottom', fontsize=12, fontweight='bold')

    y_arr = np.array(y, dtype=float)
    if np.isfinite(y_arr).any():
        plt.ylim(0, np.nanmax(y_arr) * 1.1)

    handles = [Patch(facecolor=CASE_COLORS.get(c, '#4C78A8'), edgecolor='black', label=c)
               for c in x_labels]
    plt.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, -0.08),
               ncol=len(x_labels), frameon=False, fontsize=14)

    os.makedirs(str(output_dir), exist_ok=True)
    out = output_dir / f"{var_name}_AreaDays_{month_cn}.png"
    plt.tight_layout()
    plt.savefig(str(out), dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✅ Bar chart → {out}")
    return str(out)


# ============================================================
# 箱线图
# ============================================================

REGION_CONFIGS = {
    'GuangDong': {'name': 'GuangDong', 'suffix': '',      'color': '#1f77b4', 'box_color': '#aec7e8'},
    'HuiZhou':   {'name': 'HuiZhou',   'suffix': '_HuiZhou', 'color': '#ff7f0e', 'box_color': '#ffbb78'},
}


def plot_case_boxplot(
    cases: List[str],
    var_name: str,
    var_column: str,
    var_title: str,
    var_ylabel: str,
    month_code: str,
    data_dir: Path,
    regions: Optional[List[str]] = None,
    output_dir: Optional[Path] = None,
) -> str:
    """绘制多 CASE 多区域组合箱线图。

    Args:
        cases:       CASE 列表
        var_name:    变量名
        var_column:  CSV 列名
        var_title:   图表标题
        var_ylabel:  y 轴标签
        month_code:  月份代码
        data_dir:    基础数据目录（不含 region suffix）
        regions:     区域列表，如 ['GuangDong', 'HuiZhou']，默认仅 Guangdong
        output_dir:  输出目录

    Returns:
        输出文件路径
    """
    if regions is None:
        regions = ['GuangDong']
    if output_dir is None:
        output_dir = data_dir.parent / "Boxplots_Output_CaseComparison"

    enabled_regions = [r for r in regions if r in REGION_CONFIGS]
    month_en = {'01': 'January', '07': 'July'}.get(month_code, f"Month{month_code}")

    # 收集数据
    all_data, labels, positions, box_colors = [], [], [], []
    pos = 1
    for cid in cases:
        offset_idx = 0
        for rkey in enabled_regions:
            rcfg = REGION_CONFIGS[rkey]
            try:
                region_dir = data_dir.parent / f"{data_dir.name}{rcfg['suffix']}"
                data_arr = load_case_data(cid, month_code, var_column, region_dir, rcfg['suffix'])
                if isinstance(data_arr, list) and len(data_arr) == 0:
                    raise ValueError("empty")
            except Exception:
                data_arr = np.array([])

            if len(data_arr) > 0:
                all_data.append(data_arr)
                labels.append(f'{cid}\n{rcfg["name"]}')
                positions.append(pos + 0.3 * offset_idx)
                box_colors.append(rcfg['box_color'])
                offset_idx += 1
        pos += 1.5

    if not all_data:
        print("  ❌ 无有效数据")
        return ""

    # 绘图
    plt.figure(figsize=(16, 8))
    bp = plt.boxplot(all_data, positions=positions, labels=labels,
                     patch_artist=True, widths=0.3, showfliers=True,
                     flierprops={'marker': 'o', 'markerfacecolor': 'red', 'markeredgecolor': 'black',
                                 'markersize': 6, 'alpha': 0.7},
                     medianprops={'color': 'black', 'linewidth': 2})

    for i, box in enumerate(bp['boxes']):
        box.set(facecolor=box_colors[i], alpha=0.8)

    plt.title(f'{var_title} Comparison ({month_en})', fontsize=18, fontweight='bold', pad=20)
    plt.ylabel(var_ylabel, fontsize=14, fontweight='bold')
    plt.xlabel('Case and Region', fontsize=14, fontweight='bold')

    all_vals = np.concatenate([d for d in all_data if len(d) > 0])
    plt.ylim(0, np.max(all_vals) * 1.1)
    plt.grid(True, alpha=0.3, axis='y')
    plt.gca().set_facecolor('#f8f9fa')

    legend_elements = [Patch(facecolor=REGION_CONFIGS[r]['box_color'], edgecolor='black',
                             label=REGION_CONFIGS[r]['name']) for r in enabled_regions]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=12)

    os.makedirs(str(output_dir), exist_ok=True)
    out = output_dir / f"{var_name}_CaseComparison_{month_en}.png"
    plt.tight_layout()
    plt.savefig(str(out), dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✅ Boxplot → {out}")
    return str(out)
