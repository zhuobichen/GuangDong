#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core_NationStationValidation.py — 国家监测站 MCIP 气象校验核心模块

与中国环境监测总站逐小时 xlsx 数据对接，区别于 NOAA ISD 版本
(Core_WeatherValidation.py)。

差异:
  - 输入:   xlsx 格式（直接数值） vs ISD CSV（编码字段）
  - 时间:   中国时区 UTC+8 → 需转 UTC 匹配 MCIP
  - 分辨率: 逐小时 (24条/天) vs 3小时 (8条/天)
  - 站点:   "S"+数字 编号 vs 11位 USGS 编号
  - 网格:   支持 KDTree 或预计算 CSV 查找
  - 缺测:   -9999.0 vs ISD 编码 9999

包含功能:
  1. xlsx 监测数据 → 标准校验表 CSV 转换
  2. MCIP 网格匹配（KDTree / CSV 查找）
  3. MCIP 模型数据提取（含 UTC+8→UTC）
  4. 观测 vs 模型时间序列对比图
  5. 校验结果报表 (xlsx)

所有函数为纯函数，路径/参数通过函数签名传入。
"""

import os
import re
import math
import numpy as np
import pandas as pd
from netCDF4 import Dataset
from datetime import datetime, timedelta
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties

# ============================================================
#  中文字体设置
# ============================================================
plt.rcParams["font.sans-serif"] = ["Noto Serif CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
#  公共常量
# ============================================================
VARIABLE_INFO = {
    "Temperature":   ("温度", "°C"),
    "Humidity":      ("相对湿度", "%"),
    "AirPress":      ("气压", "hPa"),
    "WindSpeed":     ("风速", "m/s"),
    "WindDirection": ("风向", "°"),
}

POLLUTANT_COLS = ["SO2", "NO2", "PM10", "PM25", "O3", "CO", "O3_8H_averange"]

NATION_MISSING = -9999.0  # 国家监测站缺测标记


# ============================================================
#  私有工具函数
# ============================================================

def _latlon_to_xyz(lat, lon):
    """经纬度 → 3D 笛卡尔坐标 (km)。"""
    R = 6371.0
    lat_r, lon_r = np.radians(lat), np.radians(lon)
    return (R * np.cos(lat_r) * np.cos(lon_r),
            R * np.cos(lat_r) * np.sin(lon_r),
            R * np.sin(lat_r))


def _get_grid_kdtree(lat, lon, griddot_file):
    """KDTree 球面距离最近邻 → (ROW, COL) 1-based。"""
    with Dataset(griddot_file) as nc:
        grid_lat = nc.variables["LATD"][0, 0, :, :]
        grid_lon = nc.variables["LOND"][0, 0, :, :]
        nr, nc_cols = grid_lat.shape
        nrows, ncols = nr - 1, nc_cols - 1

        glat = (grid_lat[:-1, :-1] + grid_lat[:-1, 1:] +
                grid_lat[1:, :-1] + grid_lat[1:, 1:]) / 4.0
        glon = (grid_lon[:-1, :-1] + grid_lon[:-1, 1:] +
                grid_lon[1:, :-1] + grid_lon[1:, 1:]) / 4.0

        sx, sy, sz = _latlon_to_xyz(lat, lon)
        gx, gy, gz = _latlon_to_xyz(glat, glon)
        gcoords = np.column_stack([gx.flatten(), gy.flatten(), gz.flatten()])
        tree = cKDTree(gcoords)
        dist, idx = tree.query([sx, sy, sz])
        ri = idx // ncols
        ci = idx % ncols
        print(f"    KDTree: ({lat:.4f},{lon:.4f}) → ROW={ri+1}, COL={ci+1}, dist={dist:.2f}km")
        return ri + 1, ci + 1


def _get_grid_csv(station_id, site_info_df, grid_df):
    """从预计算 CSV 查找网格 (ROW, COL)。

    网格 CSV 行序与站点 CSV 一一对应（均无 header 的 grid_df 行号 = site_info_df 数据行号 - 1）。
    station_id 为纯数字（不带 S 前缀）。
    """
    site_id_s = f"S{station_id}"
    matches = site_info_df[site_info_df["site_name"] == site_id_s]
    if matches.empty:
        print(f"    ⚠ 站点 {site_id_s} 未在站点信息表中找到")
        return None, None
    site_idx = matches.index[0]
    grid_idx = site_idx - 1  # site_info 第0行是表头
    if grid_idx < 0 or grid_idx >= len(grid_df):
        print(f"    ⚠ 网格索引越界: {grid_idx}")
        return None, None
    row = int(grid_df.iloc[grid_idx, 0])
    col = int(grid_df.iloc[grid_idx, 1])
    print(f"    CSV网格: station_id={station_id} → ROW={row}, COL={col}")
    return row, col


def _calc_rh_q2(temp_c, q2, prsfc_pa):
    """从 MCIP Q2 (混合比) 计算相对湿度(%)。"""
    try:
        eps = 0.622
        prsfc_hpa = prsfc_pa / 100.0
        e = (q2 * prsfc_hpa) / (eps + q2)
        es = 6.112 * np.exp(17.67 * temp_c / (temp_c + 243.5))
        return np.clip(100.0 * e / es, 0, 100)
    except Exception:
        return np.nan


def _wind_dir_uv(u, v):
    """U/V → 风向(°) 气象学定义 (风从哪来)。"""
    return (270.0 - np.degrees(np.arctan2(v, u))) % 360.0


def _wind_spd_uv(u, v):
    """U/V → 风速 (m/s)。"""
    return np.sqrt(u * u + v * v)


def _read_metcro2d(filepath):
    """读取单个 METCRO2D 文件。

    返回: {times_utc, TEMP2, Q2, PRSFC, WSPD10, WDIR10, U10, V10}
    """
    data = {}
    with Dataset(filepath) as nc:
        tflag = nc.variables["TFLAG"][:, 0, :]
        times = []
        for i in range(tflag.shape[0]):
            yyyyddd = int(tflag[i, 0])
            hhmmss = int(tflag[i, 1])
            y = yyyyddd // 1000
            doy = yyyyddd % 1000
            base = datetime(y, 1, 1) + timedelta(days=doy - 1)
            h = hhmmss // 10000
            m = (hhmmss % 10000) // 100
            if h == 24:
                base += timedelta(days=1)
                h = 0
            times.append(base + timedelta(hours=h, minutes=m))
        data["times_utc"] = np.array(times, dtype="datetime64[s]")
        data["TEMP2"] = nc.variables["TEMP2"][:, 0, :, :]
        data["Q2"] = nc.variables["Q2"][:, 0, :, :]
        data["PRSFC"] = nc.variables["PRSFC"][:, 0, :, :]

        for vn in ["WSPD10", "WDIR10"]:
            data[vn] = nc.variables[vn][:, 0, :, :] if vn in nc.variables else None

        for cu, cv in [("U10", "V10"), ("UWIND10", "VWIND10")]:
            if cu in nc.variables and cv in nc.variables:
                data["U10"] = nc.variables[cu][:, 0, :, :]
                data["V10"] = nc.variables[cv][:, 0, :, :]
                break
        else:
            data["U10"] = data["V10"] = None
    return data


def _sanitize_val(v):
    """将 -9999 (int/float) 转为 NaN。"""
    if v is None:
        return np.nan
    try:
        if isinstance(v, (int, float)) and np.isclose(float(v), NATION_MISSING):
            return np.nan
    except (ValueError, TypeError):
        pass
    return v


# ============================================================
#  1. xlsx → 标准校验表转换
# ============================================================

def convert_nation_xlsx_to_table(xlsx_dir, site_info_csv, output_dir,
                                 year, months=None, station_ids=None):
    """读取国家监测站 xlsx 文件，转为标准校验表 CSV。

    参数:
        xlsx_dir:     xlsx 文件所在目录
        site_info_csv: GD_125nation_site_v01.csv 路径
        output_dir:   校验表 CSV 输出目录
        year:         目标年份
        months:       要保留的月份列表，None=全部
        station_ids:  要处理的站点 ID 列表，None=目录下所有 xlsx

    返回:
        list[str]: 输出 CSV 文件路径列表
    """
    os.makedirs(output_dir, exist_ok=True)

    # 读取站点信息
    site_info = pd.read_csv(site_info_csv)  # columns: site_name, lon, lat

    xlsx_files = sorted([f for f in os.listdir(xlsx_dir)
                         if f.endswith(".xlsx") and not f.startswith("~")])
    outputs = []
    print(f"找到 {len(xlsx_files)} 个 xlsx 文件")

    for xf in xlsx_files:
        # 文件名格式: 序号_StationID_站点名.xlsx
        stem = xf.replace(".xlsx", "")
        parts = stem.split("_", 2)
        if len(parts) < 2:
            print(f"  ⚠ 文件名格式不符, 跳过: {xf}")
            continue
        station_id = parts[1]
        station_name = parts[2] if len(parts) > 2 else station_id

        if station_ids and station_id not in station_ids:
            continue

        # 查找站点经纬度
        sid_s = f"S{station_id}"
        srow = site_info[site_info["site_name"] == sid_s]
        if srow.empty:
            print(f"  ⚠ 站点 {sid_s} 不在站点信息表中, 跳过")
            continue
        slat = float(srow.iloc[0]["lat"])
        slon = float(srow.iloc[0]["lon"])

        # 读取 xlsx
        xlsx_path = os.path.join(xlsx_dir, xf)
        try:
            df = pd.read_excel(xlsx_path)
        except Exception as e:
            print(f"  ✗ 读取失败 {xf}: {e}")
            continue

        if "timePoint" not in df.columns:
            print(f"  ✗ {xf}: 缺少 timePoint 列")
            continue

        result = pd.DataFrame()
        result["Date"] = pd.to_datetime(df["timePoint"]).dt.strftime(
            "%Y-%m-%d %H:%M:%S")
        result["Lat"] = slat
        result["Lon"] = slon

        # 气象变量
        for col in ["Temperature", "Humidity", "AirPress",
                     "WindSpeed", "WindDirection"]:
            if col in df.columns:
                result[f"Obs_{col}"] = df[col].apply(_sanitize_val)
            else:
                result[f"Obs_{col}"] = np.nan

        # 污染物变量（保留，后续扩展用）
        for col in POLLUTANT_COLS:
            if col in df.columns:
                result[col] = df[col].apply(_sanitize_val)

        # 筛选年份
        result["_yr"] = pd.to_datetime(result["Date"]).dt.year
        result = result[result["_yr"] == year].drop(columns=["_yr"])

        # 筛选月份
        if months:
            result["_mo"] = pd.to_datetime(result["Date"]).dt.month
            result = result[result["_mo"].isin(months)].drop(columns=["_mo"])

        out_path = os.path.join(output_dir, f"{station_id}_{station_name}_校验表.csv")
        result.to_csv(out_path, index=False, float_format="%.2f")
        outputs.append(out_path)
        print(f"  ✓ {station_id} ({station_name}): {len(result)} 条 → {os.path.basename(out_path)}")

    return outputs


# ============================================================
#  2. 网格匹配
# ============================================================

def match_stations_to_grid(site_info_csv, griddot_file=None,
                           grid_csv=None, station_ids=None):
    """为国家监测站匹配 MCIP 网格坐标。

    参数:
        site_info_csv: GD_125nation_site_v01.csv 路径
        griddot_file:  GRIDDOT2D NC 文件路径 (KDTree 方法)
        grid_csv:      GD_125nation_grid_v01.csv 路径 (CSV 方法)
        station_ids:   要匹配的站点 ID 列表，None=全部

    返回:
        dict: {station_id: {"row": int, "col": int, "name": str, "lat": float, "lon": float}}
    """
    site_info = pd.read_csv(site_info_csv)

    if grid_csv and os.path.exists(grid_csv):
        grid_df = pd.read_csv(grid_csv, header=None)
        method = "csv"
    elif griddot_file and os.path.exists(griddot_file):
        method = "kdtree"
    else:
        raise ValueError("必须提供 grid_csv 或 griddot_file")

    print(f"网格匹配方法: {method}")

    station_grids = {}
    for _, row in site_info.iterrows():
        sid_s = str(row["site_name"])
        if not sid_s.startswith("S"):
            continue
        sid = sid_s[1:]  # 去掉 S 前缀
        if station_ids and sid not in station_ids:
            continue

        lat = float(row["lat"])
        lon = float(row["lon"])

        if method == "kdtree":
            r, c = _get_grid_kdtree(lat, lon, griddot_file)
        else:
            r, c = _get_grid_csv(sid, site_info, grid_df)

        if r is not None and c is not None:
            station_grids[sid] = {"row": r, "col": c, "name": sid,
                                  "lat": lat, "lon": lon}

    print(f"匹配完成: {len(station_grids)} 个站点")
    return station_grids


# ============================================================
#  3. MCIP 模型数据提取
# ============================================================

def extract_mcip_for_nation_stations(processed_dir, output_dir, mcip_dir,
                                     year, station_grids, months=None):
    """从 METCRO2D 提取国家监测站点对应网格的气象数据。

    国家监测站时间是中国时区 (UTC+8)，需减去 8 小时对齐 MCIP 的 UTC 时间。

    参数:
        processed_dir: Data/Station/Nation/Processed/ (校验表目录)
        output_dir:    Data/Station/Nation/Validation/
        mcip_dir:      mcipout/{year}/
        year:          目标年份
        station_grids: match_stations_to_grid() 返回值
        months:        要处理的月份，None=全部

    返回:
        list[str]: 含 MCIP 数据的 CSV 路径列表
    """
    os.makedirs(output_dir, exist_ok=True)

    # 查找 GRIDDOT2D（仅用于确认网格信息）
    griddot_files = sorted([f for f in os.listdir(mcip_dir)
                            if f.startswith("GRIDDOT2D_")])
    if not griddot_files:
        raise FileNotFoundError(f"MCIP 目录中无 GRIDDOT2D: {mcip_dir}")

    outputs = []
    mcip_cache = {}
    current_date_key = None
    merged_data = None

    # 找出所有校验表文件
    csv_files = sorted([f for f in os.listdir(processed_dir)
                        if f.endswith("_校验表.csv")])

    for cf in csv_files:
        # 从文件名提取 station_id
        sid = cf.split("_")[0]
        if sid not in station_grids:
            print(f"  ⚠ {sid} 无网格信息, 跳过")
            continue

        sg = station_grids[sid]
        sname = sg["name"]
        grid_row = sg["row"]
        grid_col = sg["col"]

        print(f"\n{'='*60}")
        print(f"处理: {sname} ({sid})  ROW={grid_row}, COL={grid_col}")

        vf = os.path.join(processed_dir, cf)
        df = pd.read_csv(vf)
        print(f"  读取 {len(df)} 条记录")

        # 筛选月份
        if months:
            df["_mo"] = pd.to_datetime(df["Date"]).dt.month
            df = df[df["_mo"].isin(months)].drop(columns=["_mo"]).copy()

        if len(df) == 0:
            print(f"  无数据, 跳过")
            continue

        # 初始化网格数据列
        for c in ["Grid_ROW", "Grid_COL", "Grid_Temperature", "Grid_Humidity",
                   "Grid_AirPress", "Grid_WindSpeed", "Grid_WindDirection"]:
            df[c] = np.nan
        df["Grid_ROW"] = grid_row
        df["Grid_COL"] = grid_col

        success = 0
        fail = 0
        total = len(df)
        mcip_cache.clear()
        current_date_key = None
        merged_data = None

        for idx, csv_row in df.iterrows():
            dt_str = str(csv_row["Date"])
            try:
                # 监测数据是中国时区 → 转 UTC
                dt_cn = pd.to_datetime(dt_str)
                dt_utc = dt_cn - timedelta(hours=8)

                doy = dt_utc.timetuple().tm_yday
                dkey = f"{dt_utc.year}{doy:03d}"

                if dkey != current_date_key:
                    prev = dt_utc.date() - timedelta(days=1)
                    pkey = f"{prev.year}{prev.timetuple().tm_yday:03d}"

                    all_t = []
                    all_d = {"TEMP2": [], "Q2": [], "PRSFC": [],
                             "WSPD10": [], "WDIR10": [], "U10": [], "V10": []}

                    for k in [pkey, dkey]:
                        fp = os.path.join(mcip_dir, f"METCRO2D_{k}")
                        if not os.path.exists(fp):
                            continue
                        if k not in mcip_cache:
                            mcip_cache[k] = _read_metcro2d(fp)
                        d = mcip_cache[k]
                        all_t.extend(pd.to_datetime(d["times_utc"]))
                        for vn in all_d:
                            if d.get(vn) is not None:
                                all_d[vn].append(d[vn])

                    if all_t:
                        merged_data = {
                            "times_utc": pd.DatetimeIndex(all_t),
                            "TEMP2":  np.concatenate(all_d["TEMP2"]),
                            "Q2":     np.concatenate(all_d["Q2"]),
                            "PRSFC":  np.concatenate(all_d["PRSFC"]),
                            "WSPD10": np.concatenate(all_d["WSPD10"]) if all_d["WSPD10"] else None,
                            "WDIR10": np.concatenate(all_d["WDIR10"]) if all_d["WDIR10"] else None,
                            "U10":    np.concatenate(all_d["U10"]) if all_d["U10"] else None,
                            "V10":    np.concatenate(all_d["V10"]) if all_d["V10"] else None,
                        }
                        current_date_key = dkey
                        if len(mcip_cache) > 3:
                            del mcip_cache[min(mcip_cache.keys())]

                if merged_data is None or merged_data["TEMP2"] is None:
                    fail += 1
                    continue

                diffs = np.abs((merged_data["times_utc"] - dt_utc).total_seconds())
                mi = np.argmin(diffs)
                if diffs[mi] > 7200:  # ±2 小时容差
                    fail += 1
                    continue

                ri, ci = grid_row - 1, grid_col - 1
                t2k = merged_data["TEMP2"][mi, ri, ci]
                q2v = merged_data["Q2"][mi, ri, ci]
                psv = merged_data["PRSFC"][mi, ri, ci]

                wspd = merged_data.get("WSPD10")
                wdir = merged_data.get("WDIR10")
                u10 = merged_data.get("U10")
                v10 = merged_data.get("V10")

                if wspd is not None:
                    ws = float(wspd[mi, ri, ci])
                elif u10 is not None and v10 is not None:
                    ws = _wind_spd_uv(float(u10[mi, ri, ci]),
                                      float(v10[mi, ri, ci]))
                else:
                    ws = np.nan

                if wdir is not None:
                    wd = float(wdir[mi, ri, ci])
                elif u10 is not None and v10 is not None:
                    wd = _wind_dir_uv(float(u10[mi, ri, ci]),
                                      float(v10[mi, ri, ci]))
                else:
                    wd = np.nan

                t2c = float(t2k - 273.15)
                rh = _calc_rh_q2(t2c, float(q2v), float(psv))
                ph = float(psv) / 100.0

                df.loc[idx, "Grid_Temperature"] = round(t2c, 2)
                df.loc[idx, "Grid_Humidity"] = round(rh, 2)
                df.loc[idx, "Grid_AirPress"] = round(ph, 2)
                df.loc[idx, "Grid_WindSpeed"] = (round(ws, 2)
                                                  if not np.isnan(ws) else np.nan)
                df.loc[idx, "Grid_WindDirection"] = (round(wd, 1)
                                                      if not np.isnan(wd) else np.nan)
                success += 1

                if (success + fail) % 500 == 0:
                    pct = (success + fail) / total * 100
                    print(f"  进度: {success+fail}/{total} ({pct:.0f}%) 成功={success}")

            except Exception:
                fail += 1
                continue

        out_path = os.path.join(output_dir, f"{sid}_校验表_含MCIP模型数据.csv")
        df.to_csv(out_path, index=False)
        outputs.append(out_path)
        rate = success / (success + fail) * 100 if (success + fail) > 0 else 0
        print(f"  ✅ 成功={success} 失败={fail} ({rate:.1f}%) → {os.path.basename(out_path)}")

    return outputs


# ============================================================
#  4. 时间序列对比图
# ============================================================

def plot_nation_timeseries(validation_dir, picture_dir, year, stations,
                           variables=None, periods=None):
    """绘制国家监测站观测 vs CMAQ 时间序列对比图。

    参数:
        validation_dir: Data/Station/Nation/Validation/
        picture_dir:    Picture/Station/Nation/Timeseries/
        year:           目标年份
        stations:       {站点ID: 站点名} 字典
        variables:      要绘制的变量列表
        periods:        时段配置 dict, 默认 1月+7月

    返回:
        list[str]: 输出 PNG 路径列表
    """
    if variables is None:
        variables = ["Temperature", "Humidity", "AirPress", "WindSpeed"]
    if periods is None:
        periods = {
            "jan": ("1月", 1),
            "jul": ("7月", 7),
        }

    os.makedirs(picture_dir, exist_ok=True)
    outputs = []
    times_font = FontProperties(family="DejaVu Sans", size=13, weight="bold")
    tick_font = FontProperties(family="DejaVu Sans", size=18)

    for pkey, (pname, month_filter) in periods.items():
        for sid, sname in stations.items():
            # 查找校验表文件
            candidates = [f for f in os.listdir(validation_dir)
                          if f.startswith(sid) and f.endswith("含MCIP模型数据.csv")]
            if not candidates:
                print(f"  ⚠ 未找到 {sid} 的校验表")
                continue
            vf = os.path.join(validation_dir, candidates[0])
            if not os.path.exists(vf):
                continue

            df = pd.read_csv(vf)
            df["Date"] = pd.to_datetime(df["Date"])
            df = df[df["Date"].dt.month == month_filter]

            nv = len(variables)
            ncols = 2
            nrows = max(1, math.ceil(nv / ncols))
            fig, axes = plt.subplots(nrows, ncols, figsize=(16, 6 * nrows))
            axes = np.atleast_1d(axes).flatten()

            for i, var_en in enumerate(variables):
                ax = axes[i]
                var_cn, unit = VARIABLE_INFO[var_en]
                gvar = f"Grid_{var_en}"
                ocol = f"Obs_{var_en}"

                if ocol not in df.columns:
                    ocol = var_en

                valid = df.dropna(subset=[ocol, gvar])
                if len(valid) > 0:
                    obs = valid[ocol].values
                    model = valid[gvar].values
                    r = np.corrcoef(obs, model)[0, 1]
                    rmse = np.sqrt(np.mean((model - obs) ** 2))
                    mb = np.mean(model - obs)

                    ax.plot(valid["Date"], obs, "k-", lw=0.7, label="Obs")
                    ax.plot(valid["Date"], model, "r--", lw=0.7, label="CMAQ")
                    ax.set_title(f"{sname} - {var_cn}", fontsize=22,
                                 fontweight="bold", pad=25)
                    ax.text(0.5, 1.01, f"R={r:.3f}  RMSE={rmse:.2f}  MB={mb:.2f}",
                            transform=ax.transAxes, fontsize=13,
                            va="bottom", ha="center", fontproperties=times_font)
                    ax.set_xlabel("日期", fontsize=19)
                    ax.set_ylabel(f"{var_cn} ({unit})", fontsize=19)
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d日"))
                    ax.tick_params(axis="both", labelsize=18)
                    for lbl in ax.get_yticklabels():
                        lbl.set_fontproperties(tick_font)
                    for lbl in ax.get_xticklabels():
                        lbl.set_fontsize(18)
                    lfont = FontProperties(family="DejaVu Sans", size=14)
                    ax.legend(fontsize=14, loc="upper left", frameon=False,
                              prop=lfont)
                    ax.grid(True, alpha=0.3)
                else:
                    ax.text(0.5, 0.5, "无有效数据", transform=ax.transAxes,
                            fontsize=20, ha="center", va="center")

            for j in range(nv, len(axes)):
                axes[j].axis("off")

            plt.tight_layout()
            out = os.path.join(picture_dir,
                               f"{sid}_{sname}_时间序列对比_{pname}.png")
            plt.savefig(out, dpi=150, bbox_inches="tight")
            plt.close()
            outputs.append(out)
            print(f"  ✓ {out}")

    print("✅ 国家站时间序列图绘制完成")
    return outputs


# ============================================================
#  5. 校验结果报表
# ============================================================

def _calc_metrics(obs, model, metrics=("R", "RMSE", "MB")):
    """计算统计指标。"""
    mask = ~np.isnan(obs) & ~np.isnan(model)
    o, m = obs[mask], model[mask]
    if len(o) < 2:
        return {}
    result = {}
    if "R" in metrics:
        result["R"] = np.corrcoef(o, m)[0, 1]
    if "RMSE" in metrics:
        result["RMSE"] = np.sqrt(np.mean((m - o) ** 2))
    if "MB" in metrics:
        result["MB"] = np.mean(m - o)
    if "NMB" in metrics:
        denom = np.sum(o)
        result["NMB"] = np.nan if np.isclose(denom, 0) else 100.0 * np.sum(m - o) / denom
    return result


def generate_nation_report(validation_dir, output_file, year, stations,
                           variables=None, months=(1, 7),
                           metrics=("R", "RMSE", "MB")):
    """生成国家监测站校验结果数据表 (xlsx)。

    参数:
        validation_dir: Data/Station/Nation/Validation/
        output_file:    输出 xlsx 路径
        year:           目标年份
        stations:       {站点ID: 站点名}
        variables:      变量英文名列表
        months:         统计月份
        metrics:        统计指标

    返回:
        str: 输出文件路径
    """
    if variables is None:
        variables = ["Temperature", "Humidity", "WindSpeed"]

    results = []
    for sid, sname in stations.items():
        candidates = [f for f in os.listdir(validation_dir)
                      if f.startswith(sid) and f.endswith("含MCIP模型数据.csv")]
        if not candidates:
            continue
        vf = os.path.join(validation_dir, candidates[0])
        if not os.path.exists(vf):
            continue

        df = pd.read_csv(vf)
        df["Date"] = pd.to_datetime(df["Date"])
        df["Month"] = df["Date"].dt.month

        for month in months:
            mdf = df[df["Month"] == month]
            row = {"站点": sname, "月份": f"{month}月"}
            for var_en in variables:
                var_cn = VARIABLE_INFO[var_en][0]
                gvar = f"Grid_{var_en}"
                ocol = f"Obs_{var_en}" if f"Obs_{var_en}" in df.columns else var_en
                valid = mdf.dropna(subset=[ocol, gvar])
                if len(valid) > 0:
                    mr = _calc_metrics(valid[ocol].values, valid[gvar].values,
                                       metrics)
                    for mk, mv in mr.items():
                        key = f"{var_cn}_{mk}" if mk != "NMB" else f"{var_cn}_{mk}(%)"
                        row[key] = mv
                else:
                    for mk in metrics:
                        key = f"{var_cn}_{mk}" if mk != "NMB" else f"{var_cn}_{mk}(%)"
                        row[key] = np.nan
            results.append(row)

    df_out = pd.DataFrame(results).round(3)
    print(df_out.to_string(index=False))
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file)
                else ".", exist_ok=True)
    df_out.to_excel(output_file, index=False, engine="openpyxl")
    print(f"✅ 报表已保存: {output_file}")
    return output_file
