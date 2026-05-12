#!/usr/bin/env python3
"""
Core_Map.py — 地图绘图核心模块

提供单图 (single) 和差值图 (diff) 两种模式的地图绘制函数。
依赖 esil (map_helper, rsm_helper) 和 cmaps。
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from esil.rsm_helper.model_property import model_attribute
from esil.map_helper import get_multiple_data, show_maps
import cmaps

plt.rcParams['font.sans-serif'] = ['Noto Serif CJK JP', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'

CASE_DEFINITIONS = {
    'CASE1': ('2000', '2000', '2000e2000m'), 'CASE2': ('2000', '2023', '2000e2023m'),
    'CASE3': ('2023', '2023', '2023e2023m'), 'CASE4': ('2023', '2000', '2023e2000m'),
    'CASE5': ('2060', '2060', '2060e2060m'), 'CASE6': ('2030', '2030', '2030e2030m'),
}
CASE_MAPPING = {desc: case for case, (_, _, desc) in CASE_DEFINITIONS.items()}

MONTH_NAMES_CN = {1:'1月',2:'2月',3:'3月',4:'4月',5:'5月',6:'6月',7:'7月',8:'8月',9:'9月',10:'10月',11:'11月',12:'12月'}

def get_case_from_filename(filename: str) -> Optional[str]:
    basename = os.path.basename(filename)
    m = re.search(r'(\d{4})_Emission\[(\d{4})met\]', basename)
    if m:
        key = f"{m.group(1)}e{m.group(2)}m"
        return CASE_MAPPING.get(key, key)
    return None

def get_case_number(case_str: Optional[str]) -> str:
    if case_str is None: return "?"
    m = re.search(r'CASE(\d+)', case_str)
    return m.group(1) if m else case_str

def get_month_from_filename(filename: str) -> Optional[int]:
    m = re.search(r'_(\d{2})\.csv$', os.path.basename(filename))
    return int(m.group(1)) if m else None

_grid_cache: Dict[str, Any] = {}

def load_model_grid(model_file: str) -> Dict[str, Any]:
    if model_file not in _grid_cache:
        mp = model_attribute(model_file)
        _grid_cache[model_file] = {"projection": mp.projection, "lons": mp.lons,
                                    "lats": mp.lats, "shape": mp.lons.shape}
    return _grid_cache[model_file]

def plot_single_map(csv_path: str, variable: str, model_file: str, output_dir: str,
                    boundary_json: Optional[str] = None, cmap=cmaps.WhiteBlueGreenYellowRed,
                    value_range: Optional[Tuple[float, float]] = None, unit: str = "μg/m³",
                    title_prefix: str = "") -> Optional[str]:
    grid = load_model_grid(model_file)
    proj, lons, lats, shape = grid["projection"], grid["lons"], grid["lats"], grid["shape"]
    df = pd.read_csv(csv_path)
    if variable not in df.columns or len(df) != shape[0] * shape[1]:
        return None
    df_s = df.sort_values(["ROW", "COL"])
    data = df_s[variable].values.reshape(shape)
    case = get_case_from_filename(csv_path) or ""
    case_num = get_case_number(case)
    month = get_month_from_filename(csv_path) or 1
    month_cn = MONTH_NAMES_CN.get(month, f"{month}月")
    title = f"{title_prefix}{month_cn} {variable} (Case{case_num})"
    if value_range is None:
        valid = data[~np.isnan(data)]
        if len(valid) > 0:
            is_d = "_Days" in variable
            vmin = np.nanmin(valid) if is_d else np.nanpercentile(valid, 1.5)
            vmax = np.nanmax(valid) if is_d else np.nanpercentile(valid, 98.5)
        else: vmin, vmax = 0, 1
    else: vmin, vmax = value_range
    is_days = "_Days" in variable
    cbar_fmt = '.0f' if is_days else '.1f'
    map_unit = 'days' if is_days else unit
    map_data = {}
    get_multiple_data(map_data, dataset_name=title, variable_name="",
                      grid_x=lons, grid_y=lats, grid_concentration=data)
    fig = show_maps(map_data, unit=map_unit, cmap=cmap, show_lonlat=True, projection=proj,
                    is_wrf_out_data=True, boundary_file=boundary_json, show_original_grid=True,
                    title_fontsize=14, xy_title_fontsize=12, show_dependenct_colorbar=True,
                    value_range=(vmin, vmax), show_domain_mean=True, show_grid_line=True,
                    colorbar_format=cbar_fmt)
    os.makedirs(output_dir, exist_ok=True)
    filename = f"Case{case_num}_{month:02d}_{variable}.png"
    out_path = os.path.join(output_dir, filename)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path

CMAP_DELTA = cmaps.ViBlGrWhYeOrRe

def plot_diff_map(csv1: str, csv2: str, variable: str, model_file: str, output_dir: str,
                  boundary_json: Optional[str] = None,
                  value_range: Optional[Tuple[float, float]] = None,
                  output_suffix: str = "") -> Optional[str]:
    grid = load_model_grid(model_file)
    proj, lons, lats, shape = grid["projection"], grid["lons"], grid["lats"], grid["shape"]
    df1, df2 = pd.read_csv(csv1), pd.read_csv(csv2)
    if variable not in df1.columns or variable not in df2.columns:
        return None
    df1_s = df1.sort_values(["ROW", "COL"])
    df2_s = df2.sort_values(["ROW", "COL"])
    diff = df1_s[variable].values.reshape(shape) - df2_s[variable].values.reshape(shape)
    case1, case2 = get_case_from_filename(csv1), get_case_from_filename(csv2)
    month = get_month_from_filename(csv1) or get_month_from_filename(csv2) or 1
    month_cn = MONTH_NAMES_CN.get(month, f"{month}月")
    suffix = output_suffix or f"Case{get_case_number(case1)}-Case{get_case_number(case2)}"
    title = f"{month_cn} {variable} ({suffix.replace('_', ' ')})"
    if value_range is None:
        vmin, vmax = np.nanpercentile(diff, 0.5), np.nanpercentile(diff, 99.5)
    else: vmin, vmax = value_range
    is_days = "_Days" in variable
    cbar_fmt = '.0f' if is_days else '.1f'
    unit = 'days' if is_days else ('μg/m³' if 'PM' in variable else 'ppb')
    map_data = {}
    get_multiple_data(map_data, dataset_name=title, variable_name="",
                      grid_x=lons, grid_y=lats, grid_concentration=diff,
                      is_delta=True, cmap=CMAP_DELTA)
    fig = show_maps(map_data, unit=unit, cmap=CMAP_DELTA, show_lonlat=True, projection=proj,
                    is_wrf_out_data=True, boundary_file=boundary_json, show_original_grid=True,
                    title_fontsize=14, xy_title_fontsize=12, show_dependenct_colorbar=True,
                    show_domain_mean=True, show_domain_max=True,
                    delta_map_settings={"cmap": CMAP_DELTA, "value_range": (vmin, vmax),
                                        "colorbar_ticks_value_format": cbar_fmt,
                                        "value_format": cbar_fmt})
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{variable}_{suffix}.png"
    out_path = os.path.join(output_dir, filename)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


# ============================================================
# 数据源配置
# ============================================================

DATA_SOURCE_CONFIGS = {
    "cmaq": {
        "variables": ["O3", "PM2.5", "O3_Days", "PM2.5_Days"],
        "variable_units": {"O3": "ppb", "PM2.5": "μg/m³", "O3_Days": "days", "PM2.5_Days": "days"},
        "file_pattern": "{year}_Emission[{year}met]_{month}",
    },
    "mcip": {
        "variables": ["TA_mean", "TA_max", "SOL_RAD_mean", "SOL_RAD_max", "PBLH_mean", "PBLH_max"],
        "variable_units": {"TA_mean": "°C", "TA_max": "°C", "SOL_RAD_mean": "W/m²",
                          "SOL_RAD_max": "W/m²", "PBLH_mean": "m", "PBLH_max": "m"},
        "file_pattern": "{year}_mcipout_{month}",
    },
    "emission": {
        "variables": ["PM2.5"],
        "variable_units": {"PM2.5": "g/s"},
        "file_pattern": "EM_{year}{month}_PM2.5",
    },
}


# ============================================================
# 文件查找辅助
# ============================================================

def _find_csv_files(
    data_dir: str,
    years: List[str],
    months: List[str],
    file_pattern: str,
    region_suffix: str = "",
) -> List[Tuple[str, str, str]]:
    """扫描目录，按年份/月份/区域后缀匹配 CSV 文件。

    Returns:
        List of (file_path, year, month)
    """
    results = []
    for year in years:
        for month in months:
            month_str = str(month).zfill(2)
            fname = file_pattern.format(year=year, month=month_str) + f"{region_suffix}.csv"
            fpath = os.path.join(data_dir, fname)
            if os.path.exists(fpath):
                results.append((fpath, year, month_str))
            else:
                for f in sorted(os.listdir(data_dir)):
                    if not f.endswith(f"{region_suffix}.csv"):
                        continue
                    if year in f and f"_{month_str}" in f:
                        results.append((os.path.join(data_dir, f), year, month_str))
                        break
    return results


# ============================================================
# 管道函数
# ============================================================

def run_single_map_pipeline(
    data_dir: str,
    output_dir: str,
    model_file: str,
    boundary_json: str,
    data_source: str = "cmaq",
    years: Optional[List[str]] = None,
    months: Optional[List[str]] = None,
    variables: Optional[List[str]] = None,
    region_suffix: str = "",
    unified_legend: bool = False,
    value_range: Optional[Tuple[float, float]] = None,
) -> List[str]:
    """单独空间分布图管道。

    扫描 data_dir 中符合年份/月份模式的 CSV，批量绘制单张空间分布图。
    """
    cfg = DATA_SOURCE_CONFIGS.get(data_source)
    if cfg is None:
        raise ValueError(f"未知数据源: {data_source}，可选: {list(DATA_SOURCE_CONFIGS.keys())}")

    if years is None:
        years = ["2000", "2023"]
    if months is None:
        months = ["01", "07"]
    if variables is None:
        variables = cfg["variables"]

    files = _find_csv_files(data_dir, years, months, cfg["file_pattern"], region_suffix)
    if not files:
        print(f"  ⚠️ 未找到匹配的 CSV 文件 (dir={data_dir}, pattern={cfg['file_pattern']})")
        return []

    print(f"\n{'='*60}")
    print(f"Run Single Map Pipeline — {data_source}")
    print(f"  Data: {data_dir} ({len(files)} files)")
    print(f"  Output: {output_dir}")
    print(f"  Variables: {variables}")
    print(f"{'='*60}")

    load_model_grid(model_file)

    outputs = []
    for csv_path, year, month in files:
        year_output_dir = os.path.join(output_dir, year)
        for var in variables:
            unit = cfg["variable_units"].get(var, "")
            out = plot_single_map(
                csv_path=csv_path,
                variable=var,
                model_file=model_file,
                output_dir=year_output_dir,
                boundary_json=boundary_json,
                unit=unit,
                value_range=value_range if unified_legend else None,
            )
            if out:
                outputs.append(out)

    print(f"\n  ✅ 完成: {len(outputs)} 张地图")
    return outputs


def run_diff_map_pipeline(
    data_dir: str,
    output_dir: str,
    model_file: str,
    boundary_json: str,
    data_source: str = "cmaq",
    variables: Optional[List[str]] = None,
    comparison_pairs: Optional[List[Tuple[str, str, str]]] = None,
) -> List[str]:
    """差异对比地图管道。

    Args:
        data_dir:         CSV 数据目录
        output_dir:       图片输出目录
        model_file:       IOAPI 网格文件路径
        boundary_json:    边界 GeoJSON 路径
        data_source:      'cmaq' | 'mcip' | 'emission'
        variables:        变量列表
        comparison_pairs: 对比对列表 [(文件1, 文件2, 输出后缀), ...]
    """
    cfg = DATA_SOURCE_CONFIGS.get(data_source)
    if cfg is None:
        raise ValueError(f"未知数据源: {data_source}，可选: {list(DATA_SOURCE_CONFIGS.keys())}")

    if variables is None:
        variables = cfg["variables"]
    if comparison_pairs is None:
        raise ValueError("comparison_pairs 不能为空")

    print(f"\n{'='*60}")
    print(f"Run Diff Map Pipeline — {data_source}")
    print(f"  Data: {data_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Pairs: {len(comparison_pairs)}")
    print(f"  Variables: {variables}")
    print(f"{'='*60}")

    load_model_grid(model_file)

    outputs = []
    for f1_name, f2_name, suffix in comparison_pairs:
        csv1 = f1_name if os.path.isabs(f1_name) else os.path.join(data_dir, f1_name)
        csv2 = f2_name if os.path.isabs(f2_name) else os.path.join(data_dir, f2_name)

        if not os.path.exists(csv1):
            print(f"  ⚠️ 文件不存在，跳过: {csv1}")
            continue
        if not os.path.exists(csv2):
            print(f"  ⚠️ 文件不存在，跳过: {csv2}")
            continue

        for var in variables:
            out = plot_diff_map(
                csv1=csv1, csv2=csv2, variable=var,
                model_file=model_file, output_dir=output_dir,
                boundary_json=boundary_json, output_suffix=suffix,
            )
            if out:
                outputs.append(out)

    print(f"\n  ✅ 完成: {len(outputs)} 张差值地图")
    return outputs
