#!/usr/bin/env python3
"""
Core_Extract.py — CMAQ NC 数据提取核心模块

从 CMAQ Daily COMBINE ACONC NetCDF 文件中提取网格化时间序列，
计算月均值/极值/超标天数，输出 ROW,COL 格式 CSV。

核心流程:
  NC file → 逐日逐网格读取 → 按月过滤 → 计算统计量 → CSV

支持两种提取模式:
  - emission: O3_MDA8 + PM25_TOT + 超标天数
  - meteo:    SFC_TMP + SOL_RAD + PBLH + 高温超标天数
  - pollutant: 多污染物 (PM25_TOT, NOX, VOC, SO2, NH3, O3 + MDA8)
"""

from __future__ import annotations

import datetime as dt
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import netCDF4 as nc
import numpy as np
import pandas as pd

# ============================================================
# 文件名解析
# ============================================================

def parse_dates_from_filename(filename: str) -> Tuple[dt.datetime, dt.datetime]:
    """从 CMAQ 标准文件名中提取起止日期。

    文件名格式: ..._YYYY-MM-DD_YYYY-MM-DD_...
    """
    pattern = r'(\d{4})-(\d{2})-(\d{2})_(\d{4})-(\d{2})-(\d{2})'
    matches = re.findall(pattern, os.path.basename(filename))
    if matches:
        sy, sm, sd, ey, em, ed = matches[0]
        return dt.datetime(int(sy), int(sm), int(sd)), dt.datetime(int(ey), int(em), int(ed))
    raise ValueError(f"无法从文件名中解析日期: {filename}")


# ============================================================
# 数据存储结构
# ============================================================

def _init_grid_dict(n_rows: int, n_cols: int, var_defs: List[dict]) -> Dict:
    """创建网格字典: {(row,col): {field: []}}。"""
    grid: Dict = {}
    for r in range(1, n_rows + 1):
        for c in range(1, n_cols + 1):
            entry: Dict[str, List] = {}
            for vd in var_defs:
                if vd.get("counter", False):
                    entry[vd["name"]] = 0
                else:
                    entry[vd["name"]] = []
            grid[(r, c)] = entry
    return grid


# ============================================================
# NC 数据提取
# ============================================================

def extract_grid_data(
    nc_file: str,
    variable_specs: List[dict],
    target_month: int,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Dict:
    """从 CMAQ NC 文件提取指定月份网格数据。

    Args:
        nc_file: CMAQ Daily COMBINE ACONC NetCDF 文件路径
        variable_specs: 变量规格列表，每项包含:
            - name:     内部字段名
            - nc_var:   NetCDF 变量名 (如 'PM25_TOT', 'SFC_TMP')
            - counter:  是否为计数器 (bool, 默认 False)
            - threshold: 超标阈值 (可选，float)
        target_month: 目标月份 (1-12)
        progress_callback: 可选进度回调 (current_day, total_days)

    Returns:
        grid_data: {(row, col): {field_name: list_or_int}}
    """
    start_date, end_date = parse_dates_from_filename(nc_file)
    print(f"  日期范围: {start_date.date()} ~ {end_date.date()}, 目标月份={target_month}")

    ds = nc.Dataset(nc_file)

    # 读取变量
    arrays: Dict[str, np.ndarray] = {}
    for vd in variable_specs:
        try:
            arrays[vd["name"]] = ds.variables[vd["nc_var"]][:, 0, :, :]
        except KeyError:
            print(f"  警告: 未找到变量 {vd['nc_var']}，用零值填充")
            ref = ds.variables.get('PM25_TOT')
            if ref is None:
                # 尝试其他已知变量
                for test_var in ds.variables:
                    if len(ds.variables[test_var].shape) == 4:
                        ref = ds.variables[test_var]
                        break
            if ref is None:
                raise RuntimeError(f"无法找到参考变量用于填充: {nc_file}")
            arrays[vd["name"]] = np.zeros_like(ref[:, 0, :, :])

    n_t, n_row, n_col = list(arrays.values())[0].shape
    print(f"  数据维度: {n_t}天 × {n_row}行 × {n_col}列")

    # 初始化网格字典
    grid_data = _init_grid_dict(n_row, n_col, variable_specs)

    # 逐日处理
    valid_days = 0
    for t in range(n_t):
        date = start_date + dt.timedelta(days=t)
        if date.month != target_month:
            continue
        valid_days += 1

        if progress_callback:
            progress_callback(valid_days, n_t)

        for r in range(n_row):
            for c in range(n_col):
                key = (r + 1, c + 1)
                for vd in variable_specs:
                    val = float(arrays[vd["name"]][t, r, c])
                    if vd.get("counter", False):
                        # 计数器模式: 检查是否超标
                        threshold = vd.get("threshold")
                        if threshold is not None and val > threshold:
                            grid_data[key][vd["name"]] += 1
                    else:
                        # 列表模式: 累积值
                        grid_data[key][vd["name"]].append(val)

    ds.close()
    print(f"  处理完成: {valid_days}天 ({target_month}月)")
    return grid_data


# ============================================================
# 网格字典 → DataFrame
# ============================================================

def grid_data_to_dataframe(
    grid_data: Dict,
    output_specs: List[dict],
) -> pd.DataFrame:
    """将网格字典转换为 DataFrame。

    Args:
        grid_data: extract_grid_data() 的输出
        output_specs: 输出列规格，每项包含:
            - col_name: DataFrame 列名
            - source_field: 网格字典字段名
            - agg: 聚合方式 ('mean', 'max', 'identity')
                   identity 表示原样取值 (用于计数器)

    Returns:
        含 ROW, COL 列的 DataFrame
    """
    rows = []
    for (r, c), data in grid_data.items():
        row = {"ROW": r, "COL": c}
        for spec in output_specs:
            field = spec["source_field"]
            agg = spec.get("agg", "mean")
            values = data.get(field, [])

            if agg == "identity":
                row[spec["col_name"]] = values
            elif agg == "max":
                row[spec["col_name"]] = float(np.max(values)) if len(values) > 0 else np.nan
            else:  # mean
                row[spec["col_name"]] = float(np.mean(values)) if len(values) > 0 else np.nan
        rows.append(row)

    return pd.DataFrame(rows)


def output_csv(df: pd.DataFrame, output_path: str, verbose: bool = True) -> str:
    """保存 DataFrame 为 CSV 并打印统计信息。"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    if verbose:
        print(f"  ✅ 已保存 → {output_path}  ({len(df)}行 × {len(df.columns)}列)")
        for col in df.columns:
            if col in ("ROW", "COL"):
                continue
            valid = df[col].dropna()
            if len(valid) > 0:
                print(f"     {col}: {valid.min():.3f} ~ {valid.max():.3f} "
                      f"(mean={valid.mean():.3f}, valid={len(valid)}/{len(df)})")
    return output_path


# ============================================================
# 预定义变量规格
# ============================================================

EMISSION_VARIABLE_SPECS = [
    {"name": "o3_values",   "nc_var": "O3_MDA8"},
    {"name": "pm25_values", "nc_var": "PM25_TOT"},
    {"name": "o3_days",     "nc_var": "O3_MDA8",   "counter": True, "threshold": 80.0},
    {"name": "pm25_days",   "nc_var": "PM25_TOT",  "counter": True, "threshold": 75.0},
]

METEO_VARIABLE_SPECS = [
    {"name": "ta_values",      "nc_var": "SFC_TMP"},
    {"name": "sol_rad_values", "nc_var": "SOL_RAD"},
    {"name": "pblh_values",    "nc_var": "PBLH"},
    {"name": "ta_max_values",  "nc_var": "SFC_TMP"},
    {"name": "sol_rad_max",    "nc_var": "SOL_RAD"},
    {"name": "pblh_max_val",   "nc_var": "PBLH"},
    {"name": "temp_days_35C",  "nc_var": "SFC_TMP", "counter": True, "threshold": 35.0},
]

EMISSION_OUTPUT_SPECS = [
    {"col_name": "O3",           "source_field": "o3_values",   "agg": "mean"},
    {"col_name": "PM2.5",        "source_field": "pm25_values", "agg": "mean"},
    {"col_name": "O3_Days",      "source_field": "o3_days",     "agg": "identity"},
    {"col_name": "PM2.5_Days",   "source_field": "pm25_days",   "agg": "identity"},
]

METEO_OUTPUT_SPECS = [
    {"col_name": "TA_mean",      "source_field": "ta_values",      "agg": "mean"},
    {"col_name": "SOL_RAD_mean", "source_field": "sol_rad_values", "agg": "mean"},
    {"col_name": "PBLH_mean",    "source_field": "pblh_values",    "agg": "mean"},
    {"col_name": "TA_max",       "source_field": "ta_max_values",  "agg": "max"},
    {"col_name": "SOL_RAD_max",  "source_field": "sol_rad_max",    "agg": "max"},
    {"col_name": "PBLH_max",     "source_field": "pblh_max_val",   "agg": "max"},
    {"col_name": "Temp_Days_35C","source_field": "temp_days_35C",  "agg": "identity"},
]


# ============================================================
# 便捷流水线
# ============================================================

def extract_and_output(
    nc_file: str,
    target_month: int,
    mode: str,
    output_dir: str,
    output_name: str,
) -> List[str]:
    """一站式提取: NC → CSV。

    Args:
        nc_file:      输入 NC 文件路径
        target_month: 目标月份
        mode:         'emission' | 'meteo' | 'both'
        output_dir:   输出目录
        output_name:  输出文件名 (不含扩展名)

    Returns:
        生成的 CSV 文件路径列表
    """
    os.makedirs(output_dir, exist_ok=True)
    outputs = []

    if mode in ("emission", "both"):
        grid = extract_grid_data(nc_file, EMISSION_VARIABLE_SPECS, target_month)
        df = grid_data_to_dataframe(grid, EMISSION_OUTPUT_SPECS)
        out_path = os.path.join(output_dir, f"{output_name}.csv")
        output_csv(df, out_path)
        outputs.append(out_path)

    if mode in ("meteo", "both"):
        grid = extract_grid_data(nc_file, METEO_VARIABLE_SPECS, target_month)
        df = grid_data_to_dataframe(grid, METEO_OUTPUT_SPECS)
        out_path = os.path.join(output_dir, f"{output_name}.csv")
        output_csv(df, out_path)
        outputs.append(out_path)

    return outputs
