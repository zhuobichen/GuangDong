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
