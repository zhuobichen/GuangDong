#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core_WeatherValidation.py — 气象站点 MCIP 校验核心模块

包含功能:
  1. ISD 数据完整性检查
  2. ISD 原始数据 → 标准校验表格式转换
  3. MCIP 网格匹配与模型数据提取
  4. 观测 vs 模型时间序列对比图绘制
  5. 校验结果报表生成

所有函数为纯函数，路径/参数通过函数签名传入。
"""

import os
import re
import math
import shutil
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
    "Temperature":  ("温度", "°C"),
    "Humidity":     ("相对湿度", "%"),
    "AirPress":     ("气压", "hPa"),
    "WindSpeed":    ("风速", "m/s"),
    "WindDirection":("风向", "°"),
}

# ============================================================
#  ISD 字段解析 (私有)
# ============================================================
def _parse_isd_tmp(tmp_str):
    """解析 ISD TMP/DEW 字段，返回 °C。缺测返回 NaN。"""
    if pd.isna(tmp_str) or str(tmp_str).strip() == "":
        return np.nan
    try:
        val = int(str(tmp_str).split(",")[0])
        if abs(val) >= 9999:
            return np.nan
        return val / 10.0
    except Exception:
        return np.nan


def _parse_isd_slp(slp_str):
    """解析 ISD SLP 字段，返回 hPa。缺测返回 NaN。"""
    if pd.isna(slp_str) or str(slp_str).strip() == "":
        return np.nan
    try:
        val = int(str(slp_str).split(",")[0])
        if val >= 99999:
            return np.nan
        return val / 10.0
    except Exception:
        return np.nan


def _parse_isd_wnd(wnd_str):
    """解析 ISD WND 字段，返回 (风向_度, 风速_m/s)。"""
    if pd.isna(wnd_str) or str(wnd_str).strip() == "":
        return np.nan, np.nan
    try:
        parts = str(wnd_str).split(",")
        if len(parts) < 4:
            return np.nan, np.nan
        wdir = int(parts[0])
        wspd_raw = int(parts[3])
        if wdir == 999:
            wdir = np.nan
        if wspd_raw == 9999:
            wspd = np.nan
        else:
            wspd = wspd_raw / 10.0
        return wdir, wspd
    except Exception:
        return np.nan, np.nan


def _extract_rem_pressure(rem_str):
    """从 ISD REM 字段提取 Q#### 气压 (hPa)。"""
    if pd.isna(rem_str) or str(rem_str).strip() == "":
        return np.nan
    m = re.search(r"Q(\d{4})", str(rem_str))
    if m:
        return float(m.group(1))
    return np.nan


def _calc_rh_dewpoint(temp_c, dewpoint_c):
    """Magnus 公式：温度+露点 → 相对湿度(%)。"""
    if np.isnan(temp_c) or np.isnan(dewpoint_c):
        return np.nan
    try:
        a, b = 17.625, 243.04
        rh = 100.0 * np.exp((a * dewpoint_c) / (b + dewpoint_c)
                            - (a * temp_c) / (b + temp_c))
        return round(float(rh), 2)
    except Exception:
        return np.nan


# ============================================================
#  1. ISD 数据完整性检查
# ============================================================
def check_data_completeness(raw_dir, output_dir, year):
    """筛选覆盖全年(1-12月)的站点CSV，复制到 output_dir。

    参数:
        raw_dir:   ISD 原始 CSV 所在目录
        output_dir: 完整数据输出目录
        year:      目标年份 (int)
    返回:
        list[str]: 完整站点文件名列表
    """
    os.makedirs(output_dir, exist_ok=True)
    csv_files = sorted([f for f in os.listdir(raw_dir) if f.endswith(".csv")])
    full_year = []

    print(f"检查 {raw_dir} 中 {len(csv_files)} 个站点 ...")
    for fname in csv_files:
        path = os.path.join(raw_dir, fname)
        try:
            df = pd.read_csv(path)
            if "DATE" not in df.columns:
                continue
            df["DATE"] = pd.to_datetime(df["DATE"])
            df_y = df[df["DATE"].dt.year == year]
            if len(df_y) == 0:
                continue
            months = set(df_y["DATE"].dt.month)
            if 1 in months and 12 in months:
                full_year.append(fname)
                shutil.copy2(path, os.path.join(output_dir, fname))
                print(f"  ✓ {fname}")
        except Exception as e:
            print(f"  ✗ {fname}: {e}")

    print(f"完整站点: {len(full_year)}/{len(csv_files)}")
    return full_year


# ============================================================
#  2. ISD → 标准校验表格式转换
# ============================================================
def convert_to_validation_table(input_dir, output_dir, year, station_ids=None):
    """将 ISD 原始 CSV 转为标准校验表。

    输出列: Date, Lat, Lon, Obs_Temperature, Obs_Humidity,
            Obs_AirPress, Obs_WindSpeed, Obs_WindDirection

    参数:
        input_dir:   ISD CSV 所在目录
        output_dir:  校验表输出目录
        year:        目标年份
        station_ids: 可选, {id: name} 字典, 为空则处理全部CSV
    返回:
        list[str]: 输出文件路径列表
    """
    os.makedirs(output_dir, exist_ok=True)
    all_csv = sorted([f for f in os.listdir(input_dir) if f.endswith(".csv")])

    if station_ids:
        target = [f"{sid}.csv" for sid in station_ids]
        all_csv = [f for f in all_csv if f in target]

    outputs = []
    print(f"转换 {len(all_csv)} 个站点 → 校验表格式 ({year}年) ...")

    for fname in all_csv:
        path = os.path.join(input_dir, fname)
        try:
            df = pd.read_csv(path)
            out = pd.DataFrame()
            out["Date"] = pd.to_datetime(df["DATE"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            out["Lat"] = df["LATITUDE"].astype(float)
            out["Lon"] = df["LONGITUDE"].astype(float)

            # 温度 & 湿度
            temp = df["TMP"].apply(_parse_isd_tmp)
            dew = df.get("DEW", pd.Series(dtype=float))
            if not dew.empty:
                dew = dew.apply(_parse_isd_tmp)
            else:
                dew = pd.Series([np.nan] * len(df))
            out["Obs_Temperature"] = temp
            out["Obs_Humidity"] = [
                _calc_rh_dewpoint(t, d) for t, d in zip(temp, dew)
            ]

            # 气压
            out["Obs_AirPress"] = df["SLP"].apply(_parse_isd_slp)
            if "REM" in df.columns:
                rem_p = df["REM"].apply(_extract_rem_pressure)
                out["Obs_AirPress"] = out["Obs_AirPress"].fillna(rem_p)

            # 风速/风向
            wd_ws = df["WND"].apply(lambda x: pd.Series(_parse_isd_wnd(x)))
            out["Obs_WindDirection"] = wd_ws[0]
            out["Obs_WindSpeed"] = wd_ws[1]

            # 过滤年份
            out["_year"] = pd.to_datetime(out["Date"]).dt.year
            out = out[out["_year"] == year].drop(columns=["_year"]).copy()

            sid = fname.replace(".csv", "")
            out_path = os.path.join(output_dir, f"{sid}_校验表.csv")
            out.to_csv(out_path, index=False, float_format="%.2f")
            outputs.append(out_path)
            print(f"  ✓ {fname} → {len(out)} 行")
        except Exception as e:
            print(f"  ✗ {fname}: {e}")

    return outputs


# ============================================================
#  3. MCIP 网格匹配与数据提取
# ============================================================

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
    """U/V → 气象风向 (0-360, 风从哪来)。"""
    return (270.0 - np.degrees(np.arctan2(v, u))) % 360.0


def _wind_spd_uv(u, v):
    """U/V → 风速 (m/s)。"""
    return np.sqrt(u * u + v * v)


def _get_grid_from_latlon(lat, lon, griddot_file):
    """经纬度 → (ROW, COL) (1-based), 基于 KD-Tree 球面距离。"""
    with Dataset(griddot_file) as nc:
        grid_lat = nc.variables["LATD"][0, 0, :, :]
        grid_lon = nc.variables["LOND"][0, 0, :, :]
        nrows_dot, ncols_dot = grid_lat.shape
        nrows, ncols = nrows_dot - 1, ncols_dot - 1

        # cell center = 4 dot 平均
        glat = (grid_lat[:-1, :-1] + grid_lat[:-1, 1:] +
                grid_lat[1:, :-1] + grid_lat[1:, 1:]) / 4.0
        glon = (grid_lon[:-1, :-1] + grid_lon[:-1, 1:] +
                grid_lon[1:, :-1] + grid_lon[1:, 1:]) / 4.0

        # 3D 笛卡尔坐标
        R = 6371.0
        lat_r, lon_r = np.radians(lat), np.radians(lon)
        sx = R * np.cos(lat_r) * np.cos(lon_r)
        sy = R * np.cos(lat_r) * np.sin(lon_r)
        sz = R * np.sin(lat_r)

        glat_r, glon_r = np.radians(glat), np.radians(glon)
        gx = R * np.cos(glat_r) * np.cos(glon_r)
        gy = R * np.cos(glat_r) * np.sin(glon_r)
        gz = R * np.sin(glat_r)

        gcoords = np.column_stack([gx.flatten(), gy.flatten(), gz.flatten()])
        tree = cKDTree(gcoords)
        dist, idx = tree.query([sx, sy, sz])
        row_idx = idx // ncols
        col_idx = idx % ncols

        print(f"  网格匹配: ({lat:.4f},{lon:.4f}) → ROW={row_idx+1}, COL={col_idx+1}, dist={dist:.2f}km")
        return row_idx + 1, col_idx + 1


def _read_metcro2d(filepath):
    """读取单个 METCRO2D NC 文件，返回 {times_utc, TEMP2, Q2, PRSFC, WSPD10, WDIR10, U10, V10}。"""
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


def extract_mcip_data(mcip_dir, processed_dir, output_dir, year, stations):
    """从 METCRO2D 提取站点对应网格的气象数据，输出含模型数据的校验表。

    参数:
        mcip_dir:      mcipout/{year}/ 目录 (含 METCRO2D_* 和 GRIDDOT2D_*)
        processed_dir: Data/Station/Processed/{year}/ (标准校验表)
        output_dir:    Data/Station/Validation/{year}/ (输出)
        year:          目标年份 (int)
        stations:      {站点ID: 站点名} 字典
    返回:
        list[str]: 输出文件路径列表
    """
    os.makedirs(output_dir, exist_ok=True)

    # 查找 GRIDDOT2D 文件
    griddot_files = sorted([f for f in os.listdir(mcip_dir)
                            if f.startswith("GRIDDOT2D_")])
    if not griddot_files:
        raise FileNotFoundError(f"MCIP目录中未找到 GRIDDOT2D 文件: {mcip_dir}")
    griddot_path = os.path.join(mcip_dir, griddot_files[0])

    outputs = []

    for sid, sname in stations.items():
        print(f"\n{'='*60}\n处理站点: {sname} ({sid})")
        vf = os.path.join(processed_dir, f"{sid}_校验表.csv")
        if not os.path.exists(vf):
            print(f"  ❌ 校验表不存在: {vf}")
            continue

        df = pd.read_csv(vf)
        print(f"  读取 {len(df)} 条记录")

        # 从校验表读取经纬度
        if "Lat" not in df.columns or "Lon" not in df.columns:
            print(f"  ❌ 缺少 Lat/Lon 列")
            continue
        slat = float(df["Lat"].dropna().iloc[0])
        slon = float(df["Lon"].dropna().iloc[0])
        print(f"  经纬度: ({slat:.4f}, {slon:.4f})")

        row, col = _get_grid_from_latlon(slat, slon, griddot_path)

        # 初始化模型数据列
        for c in ["Grid_ROW", "Grid_COL", "Grid_Temperature", "Grid_Humidity",
                   "Grid_AirPress", "Grid_WindSpeed", "Grid_WindDirection"]:
            df[c] = np.nan
        df["Grid_ROW"] = row
        df["Grid_COL"] = col

        # 逐行提取模型数据
        cache = {}
        success = 0
        fail = 0
        current_key = None
        merged = None

        for idx, csv_row in df.iterrows():
            dt = pd.to_datetime(str(csv_row["Date"]))
            doy = dt.timetuple().tm_yday
            dkey = f"{dt.year}{doy:03d}"

            if dkey != current_key:
                prev = dt.date() - timedelta(days=1)
                pkey = f"{prev.year}{prev.timetuple().tm_yday:03d}"
                all_t = []; all_d = {"TEMP2":[],"Q2":[],"PRSFC":[],"WSPD10":[],"WDIR10":[],"U10":[],"V10":[]}

                for k in [pkey, dkey]:
                    fp = os.path.join(mcip_dir, f"METCRO2D_{k}")
                    if not os.path.exists(fp):
                        continue
                    if k not in cache:
                        cache[k] = _read_metcro2d(fp)
                    d = cache[k]
                    all_t.extend(pd.to_datetime(d["times_utc"]))
                    for vn in all_d:
                        if d.get(vn) is not None:
                            all_d[vn].append(d[vn])

                if all_t:
                    merged = {
                        "times_utc": pd.DatetimeIndex(all_t),
                        "TEMP2": np.concatenate(all_d["TEMP2"]),
                        "Q2":    np.concatenate(all_d["Q2"]),
                        "PRSFC": np.concatenate(all_d["PRSFC"]),
                        "WSPD10": np.concatenate(all_d["WSPD10"]) if all_d["WSPD10"] else None,
                        "WDIR10": np.concatenate(all_d["WDIR10"]) if all_d["WDIR10"] else None,
                        "U10": np.concatenate(all_d["U10"]) if all_d["U10"] else None,
                        "V10": np.concatenate(all_d["V10"]) if all_d["V10"] else None,
                    }
                    current_key = dkey
                    if len(cache) > 3:
                        del cache[min(cache.keys())]

            if merged is None or merged["TEMP2"] is None:
                fail += 1
                continue

            diffs = np.abs((merged["times_utc"] - dt).total_seconds())
            mi = np.argmin(diffs)
            if diffs[mi] > 7200:
                fail += 1
                continue

            ri, ci = row - 1, col - 1
            t2k = merged["TEMP2"][mi, ri, ci]
            q2v = merged["Q2"][mi, ri, ci]
            psv = merged["PRSFC"][mi, ri, ci]

            wspd = merged.get("WSPD10")
            wdir = merged.get("WDIR10")
            u10 = merged.get("U10")
            v10 = merged.get("V10")

            if wspd is not None:
                ws = float(wspd[mi, ri, ci])
            elif u10 is not None and v10 is not None:
                ws = _wind_spd_uv(float(u10[mi, ri, ci]), float(v10[mi, ri, ci]))
            else:
                ws = np.nan

            if wdir is not None:
                wd = float(wdir[mi, ri, ci])
            elif u10 is not None and v10 is not None:
                wd = _wind_dir_uv(float(u10[mi, ri, ci]), float(v10[mi, ri, ci]))
            else:
                wd = np.nan

            t2c = float(t2k - 273.15)
            rh = _calc_rh_q2(t2c, float(q2v), float(psv))
            ph = float(psv) / 100.0

            df.loc[idx, "Grid_Temperature"] = round(t2c, 2)
            df.loc[idx, "Grid_Humidity"] = round(rh, 2)
            df.loc[idx, "Grid_AirPress"] = round(ph, 2)
            df.loc[idx, "Grid_WindSpeed"] = round(ws, 2) if not np.isnan(ws) else np.nan
            df.loc[idx, "Grid_WindDirection"] = round(wd, 1) if not np.isnan(wd) else np.nan
            success += 1

            if (success + fail) % 500 == 0:
                pct = (success + fail) / len(df) * 100
                print(f"  进度: {success+fail}/{len(df)} ({pct:.0f}%) 成功={success}")

        out_path = os.path.join(output_dir, f"{sid}_校验表_含MCIP模型数据.csv")
        df.to_csv(out_path, index=False)
        outputs.append(out_path)
        print(f"  ✅ 成功={success} 失败={fail} ({(success/(success+fail)*100):.1f}%) → {out_path}")

    return outputs


# ============================================================
#  4. 时间序列对比图绘制
# ============================================================
def plot_timeseries_comparison(validation_dir, picture_dir, year, stations,
                               variables=None, periods=None, all_label=None):
    """绘制观测 vs CMAQ 时间序列对比图。

    参数:
        validation_dir: Data/Station/Validation/{year}/
        picture_dir:    Picture/Station/Timeseries/{year}/
        year:           目标年份
        stations:       {站点ID: 站点名}
        variables:      要绘制的变量列表, 默认全部
        periods:        时段配置 dict, 默认 {'all':('全年',None),'jan':('1月',1),'jul':('7月',7)}
        all_label:      全年时段的图注标签, 如 '1-11月' 或 '1-12月'
    返回:
        list[str]: 输出图片路径列表
    """
    if variables is None:
        variables = ["Temperature", "Humidity", "AirPress", "WindSpeed"]
    if periods is None:
        if all_label is None:
            all_label = f"1-12月"
        periods = {
            "all": (all_label, None),
            "jan": ("1月", 1),
            "jul": ("7月", 7),
        }

    os.makedirs(picture_dir, exist_ok=True)
    outputs = []
    times_font = FontProperties(family="DejaVu Sans", size=13, weight="bold")

    for pkey, (pname, month_filter) in periods.items():
        for sid, sname in stations.items():
            vf = os.path.join(validation_dir, f"{sid}_校验表_含MCIP模型数据.csv")
            if not os.path.exists(vf):
                print(f"  ⚠ 文件不存在: {vf}")
                continue

            df = pd.read_csv(vf)
            df["Date"] = pd.to_datetime(df["Date"])
            if month_filter is not None:
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

                # 优先找 Obs_{var_en}，否则用 {var_en}
                if f"Obs_{var_en}" in df.columns:
                    ocol = f"Obs_{var_en}"
                else:
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
                    ax.set_title(f"{sname} - {var_cn}", fontsize=22, fontweight="bold", pad=25)
                    ax.text(0.5, 1.01, f"R={r:.3f}  RMSE={rmse:.2f}  MB={mb:.2f}",
                            transform=ax.transAxes, fontsize=13,
                            va="bottom", ha="center", fontproperties=times_font)
                    ax.set_xlabel("日期", fontsize=19)
                    ax.set_ylabel(f"{var_cn} ({unit})", fontsize=19)
                    if month_filter is None:
                        ax.xaxis.set_major_locator(mdates.MonthLocator())
                        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m月"))
                    else:
                        ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
                        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d日"))
                    ax.tick_params(axis="both", labelsize=18)
                    for lbl in ax.get_yticklabels():
                        lbl.set_fontproperties(FontProperties(family="DejaVu Sans", size=18))
                    for lbl in ax.get_xticklabels():
                        lbl.set_fontsize(18)
                    lfont = FontProperties(family="DejaVu Sans", size=14)
                    ax.legend(fontsize=14, loc="upper left", frameon=False, prop=lfont)
                    ax.grid(True, alpha=0.3)
                else:
                    ax.text(0.5, 0.5, "无有效数据", transform=ax.transAxes,
                            fontsize=20, ha="center", va="center")

            for j in range(nv, len(axes)):
                axes[j].axis("off")

            plt.tight_layout()
            safe_name = pname.replace("-", "_")
            out = os.path.join(picture_dir, f"{sid}_{sname}_时间序列对比_{safe_name}.png")
            plt.savefig(out, dpi=150, bbox_inches="tight")
            plt.close()
            outputs.append(out)
            print(f"  ✓ {out}")

    print("✅ 时间序列图绘制完成")
    return outputs


# ============================================================
#  5. 校验结果报表生成
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


def generate_validation_report(validation_dir, output_file, year, stations,
                               variables=None, months=(1, 4, 7, 10),
                               metrics=("R", "RMSE", "MB")):
    """生成校验结果数据表 (xlsx)。

    参数:
        validation_dir: Data/Station/Validation/{year}/
        output_file:    输出 xlsx 文件路径
        year:           目标年份
        stations:       {站点ID: 站点名}
        variables:      变量英文名列表, 默认 ["Temperature","Humidity","WindSpeed"]
        months:         统计月份元组
        metrics:        统计指标元组, 默认 ("R","RMSE","MB")
    返回:
        str: 输出文件路径
    """
    if variables is None:
        variables = ["Temperature", "Humidity", "WindSpeed"]

    results = []
    for sid, sname in stations.items():
        vf = os.path.join(validation_dir, f"{sid}_校验表_含MCIP模型数据.csv")
        if not os.path.exists(vf):
            print(f"  ⚠ 跳过 {sname}: 文件不存在")
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
                    mr = _calc_metrics(valid[ocol].values, valid[gvar].values, metrics)
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
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    df_out.to_excel(output_file, index=False, engine="openpyxl")
    print(f"✅ 报表已保存: {output_file}")
    return output_file