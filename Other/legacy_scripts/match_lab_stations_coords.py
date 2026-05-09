#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 2023_China 的监测数据，为“实验室站点结果”文件夹中的站点补充经纬度信息。

逻辑：
- 假定 2023_China/2023_HourlyO3Monitor_NA.csv 中包含站点 ID 与经纬度列；
- 自动猜测：
  - 站点ID列：列名中同时包含 'station' 和 ('id' 或 'code')；
  - 经度列：列名中包含 'lon' 或 'lng'；
  - 纬度列：列名中包含 'lat'；
- “实验室站点结果”下的 Excel 文件名格式：序号_站点ID_站点名.xlsx；从中解析站点ID和站点名；
- 生成一个汇总 CSV：LabStations_with_LonLat.csv。
"""

import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
ROOT = BASE / "臭氧颗粒物站点校验"
LAB_DIR = ROOT / "实验室站点结果"
CHINA_DIR = ROOT / "2023_China"
META_FILE = CHINA_DIR / "2023_HourlyO3Monitor_NA.csv"


def guess_columns(df):
    cols = list(df.columns)
    lower = {c: c.lower() for c in cols}

    # 猜测站点ID列
    station_candidates = []
    for c in cols:
        lc = lower[c]
        if "station" in lc and ("id" in lc or "code" in lc):
            station_candidates.append(c)
    station_col = station_candidates[0] if station_candidates else None

    # 特殊情况：如果没找到，但存在名为 "Site" / "site" 的列，则用它
    if station_col is None:
        for c in cols:
            if lower[c] == "site":
                station_col = c
                break

    # 猜测经度列
    lon_candidates = []
    for c in cols:
        lc = lower[c]
        if "lon" in lc or "lng" in lc:
            lon_candidates.append(c)
    lon_col = lon_candidates[0] if lon_candidates else None

    # 猜测纬度列
    lat_candidates = []
    for c in cols:
        lc = lower[c]
        if "lat" in lc:
            lat_candidates.append(c)
    lat_col = lat_candidates[0] if lat_candidates else None

    print("检测到的列名:", cols)
    print(f"猜测站点ID列: {station_col}")
    print(f"猜测经度列: {lon_col}")
    print(f"猜测纬度列: {lat_col}")

    return station_col, lon_col, lat_col


def build_meta_table():
    if not META_FILE.exists():
        raise FileNotFoundError(f"找不到元数据文件: {META_FILE}")

    print(f"读取元数据文件（仅前几行以识别列名）: {META_FILE}")
    df_head = pd.read_csv(META_FILE, nrows=200)

    station_col, lon_col, lat_col = guess_columns(df_head)
    if not station_col or not lon_col or not lat_col:
        raise RuntimeError("无法自动识别站点ID或经纬度列，请手动检查 CSV 列名并修改脚本。")

    # 用全部数据构建去重后的元表
    usecols = [station_col, lon_col, lat_col]
    df = pd.read_csv(META_FILE, usecols=usecols)
    df = df.dropna(subset=[station_col, lon_col, lat_col])
    df_meta = df.drop_duplicates(subset=[station_col]).copy()

    # 统一命名
    df_meta = df_meta.rename(columns={
        station_col: "StationID",
        lon_col: "Lon",
        lat_col: "Lat",
    })

    print(f"元表共 {len(df_meta)} 条唯一站点记录。")
    return df_meta


def collect_lab_stations(df_meta):
    if not LAB_DIR.exists():
        raise FileNotFoundError(f"找不到实验室站点结果目录: {LAB_DIR}")

    records = []
    for xls in sorted(LAB_DIR.glob("*.xlsx")):
        stem = xls.stem
        parts = stem.split("_")
        if len(parts) < 2:
            print(f"文件名无法解析站点ID，跳过: {xls.name}")
            continue

        # 形如 "1_440100051_广雅中学" => idx=1, station_id=440100051, name=广雅中学
        station_id = parts[1]
        station_name = "_".join(parts[2:]) if len(parts) > 2 else ""

        row = df_meta[df_meta["StationID"].astype(str) == station_id]
        if row.empty:
            print(f"⚠ 找不到经纬度: {xls.name} (ID={station_id})")
            records.append({
                "FileName": xls.name,
                "StationID": station_id,
                "StationName": station_name,
                "Lon": None,
                "Lat": None,
            })
            continue

        lon = float(row["Lon"].iloc[0])
        lat = float(row["Lat"].iloc[0])
        print(f"✔ 匹配到经纬度: {xls.name} (ID={station_id}) Lon={lon:.4f}, Lat={lat:.4f}")
        records.append({
            "FileName": xls.name,
            "StationID": station_id,
            "StationName": station_name,
            "Lon": lon,
            "Lat": lat,
        })

    return pd.DataFrame(records)


def main():
    print("=== 实验室站点经纬度匹配脚本 ===")
    print(f"实验室目录: {LAB_DIR}")
    print(f"元数据文件: {META_FILE}")

    df_meta = build_meta_table()
    df_result = collect_lab_stations(df_meta)

    out_file = LAB_DIR / "LabStations_with_LonLat.csv"
    df_result.to_csv(out_file, index=False, encoding="utf-8-sig")
    print(f"\n✅ 已生成汇总文件: {out_file}")


if __name__ == "__main__":
    main()
