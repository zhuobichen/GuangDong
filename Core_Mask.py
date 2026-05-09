#!/usr/bin/env python3
"""
Core_Mask.py — Guangdong 项目掩膜核心模块

提供网格空间掩膜功能，支持三种掩膜类型：
  - guangdong: 广东省行政边界 (adcode=440000)
  - huizhou:    惠州市 (预生成的 Flag NC 文件)
  - land:       中国陆地 (china.json 多边形)

原则：
  - 所有函数接受参数，不依赖于全局路径
  - 不依赖任何 Run_* 脚本
  - 可被多个 Run_* 脚本共享
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xarray as xr
from pyproj import CRS, Transformer
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep


# ============================================================
# 几何体加载
# ============================================================

def load_land_geometry(china_json_path: str):
    """从 china.json 加载中国陆地多边形 (unary_union)。"""
    with open(china_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    polygons = []
    for feat in data.get("features", []):
        geom_def = feat.get("geometry")
        if not geom_def:
            continue
        geom = shape(geom_def)
        if not geom.is_valid:
            geom = geom.buffer(0)
        if geom.is_empty:
            continue
        polygons.append(geom)
    if not polygons:
        raise ValueError("未在 china.json 中找到任何多边形")
    return unary_union(polygons)


def load_guangdong_boundary(provinces_json_path: str):
    """从 China_provinces.json 提取广东省边界 (adcode=440000)。"""
    with open(provinces_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feat in data.get("features", []):
        props = feat.get("properties", {})
        if props.get("adcode") == 440000:
            geom = shape(feat.get("geometry"))
            if not geom.is_valid:
                geom = geom.buffer(0)
            if not geom.is_empty:
                return geom
    raise ValueError("未在 China_provinces.json 中找到广东省边界 (adcode=440000)")


# ============================================================
# 网格信息提取
# ============================================================

def get_grid_xy_from_ioapi(nc_file: str) -> Tuple[np.ndarray, np.ndarray, int, int, dict]:
    """从 IOAPI 网格文件提取 LCC 坐标网格。

    Returns:
        x_2d, y_2d (2D arrays), nrows, ncols, attrs (dict)
    """
    with xr.open_dataset(nc_file) as ds:
        # 尝试多种方式获取行列数
        rows = int(len(ds["ROW"])) if "ROW" in ds.coords else int(ds.dims.get("ROW", 0))
        cols = int(len(ds["COL"])) if "COL" in ds.coords else int(ds.dims.get("COL", 0))
        if rows <= 0 or cols <= 0:
            rows = int(ds.attrs.get("NROWS"))
            cols = int(ds.attrs.get("NCOLS"))

        xorig = float(ds.attrs.get("XORIG", 0.0))
        yorig = float(ds.attrs.get("YORIG", 0.0))
        xcell = float(ds.attrs.get("XCELL", 1.0))
        ycell = float(ds.attrs.get("YCELL", 1.0))

        x_coords = xorig + (np.arange(cols) + 0.5) * xcell
        y_coords = yorig + (np.arange(rows) + 0.5) * ycell
        x_2d, y_2d = np.meshgrid(x_coords, y_coords)

        return x_2d, y_2d, rows, cols, dict(ds.attrs)


def build_transformer_from_ioapi_attrs(attrs: dict) -> Transformer:
    """从 IOAPI 全局属性构建 LCC→WGS84 坐标转换器。"""
    required = ["P_ALP", "P_BET", "P_GAM", "XCENT", "YCENT"]
    missing = [k for k in required if k not in attrs]
    if missing:
        raise ValueError(f"网格文件缺少投影属性: {missing}")

    proj_lcc = CRS.from_string(
        ("+proj=lcc +lat_1={lat1} +lat_2={lat2} "
         "+lat_0={lat0} +lon_0={lon0} "
         "+x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs").format(
            lat1=float(attrs["P_ALP"]),
            lat2=float(attrs["P_BET"]),
            lat0=float(attrs["YCENT"]),
            lon0=float(attrs["P_GAM"]),
        )
    )
    proj_wgs84 = CRS.from_epsg(4326)
    return Transformer.from_crs(proj_lcc, proj_wgs84, always_xy=True)


# ============================================================
# 掩膜构建
# ============================================================

def _build_geometry_mask(
    grid_file: str,
    geometry,
    attrs: Optional[dict] = None,
) -> np.ndarray:
    """基于 shapely 几何体构建布尔掩膜 (True=在几何体内)。

    Args:
        grid_file: IOAPI 网格文件路径
        geometry: shapely 几何体对象
        attrs:   已缓存的网格属性 (避免重复读取网格)

    Returns:
        bool ndarray, shape=(nrows, ncols)
    """
    if attrs is None:
        _, _, _, _, attrs = get_grid_xy_from_ioapi(grid_file)

    x_2d, y_2d, rows, cols, _ = get_grid_xy_from_ioapi(grid_file)
    transformer = build_transformer_from_ioapi_attrs(attrs)
    lon, lat = transformer.transform(x_2d, y_2d)

    geo_prep = prep(geometry)
    mask = np.zeros((rows, cols), dtype=bool)
    lon_f = lon.ravel()
    lat_f = lat.ravel()
    inside = np.zeros(lon_f.shape[0], dtype=bool)
    for idx in range(lon_f.shape[0]):
        inside[idx] = geo_prep.contains(Point(float(lon_f[idx]), float(lat_f[idx])))
    mask[:, :] = inside.reshape((rows, cols))
    return mask


def create_guangdong_mask(
    grid_file: str,
    provinces_json: str,
    attrs: Optional[dict] = None,
) -> np.ndarray:
    """构建广东省掩膜。"""
    gd_geom = load_guangdong_boundary(provinces_json)
    return _build_geometry_mask(grid_file, gd_geom, attrs)


def create_land_mask(
    grid_file: str,
    china_json: str,
    attrs: Optional[dict] = None,
) -> np.ndarray:
    """构建陆地区域掩膜。"""
    land_geom = load_land_geometry(china_json)
    return _build_geometry_mask(grid_file, land_geom, attrs)


def create_huizhou_mask(flag_nc_file: str) -> np.ndarray:
    """从预生成的 Flag NC 文件加载惠州市掩膜。

    掩膜中值==1 的网格属于惠州市。
    """
    with xr.open_dataset(flag_nc_file) as ds:
        flag = ds["Flag"].values.astype(bool)
    return flag


# ============================================================
# 掩膜应用
# ============================================================

def mask_dataframe(
    df: pd.DataFrame,
    mask: np.ndarray,
    numeric_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """对 DataFrame 按掩膜设置 NaN。

    Args:
        df:          含 ROW, COL 列的数据
        mask:        布尔掩膜，True=保留
        numeric_cols: 数值列名列表。为 None 时自动检测

    Returns:
        掩膜后的 DataFrame (copy)
    """
    if "ROW" not in df.columns or "COL" not in df.columns:
        raise ValueError("DataFrame 缺少 ROW/COL 列")

    rows_n, cols_n = mask.shape
    df_sorted = df.sort_values(["ROW", "COL"]).reset_index(drop=True)
    expected = rows_n * cols_n
    if len(df_sorted) != expected:
        raise ValueError(
            f"行数({len(df_sorted)})与网格({rows_n}x{cols_n}={expected})不匹配"
        )

    if numeric_cols is None:
        numeric_cols = [
            c for c in df_sorted.columns
            if c not in ("ROW", "COL") and pd.api.types.is_numeric_dtype(df_sorted[c])
        ]

    masked = df_sorted.copy()
    for col_name in numeric_cols:
        grid = masked[col_name].to_numpy().reshape((rows_n, cols_n))
        masked[col_name] = np.where(mask, grid, np.nan).reshape(-1)

    return masked


# ============================================================
# 文件扫描
# ============================================================

def list_input_csvs(input_dir: Path) -> List[Path]:
    """列出目录中可处理的 CSV，排除已掩膜文件。"""
    files = sorted(input_dir.glob("*.csv"))
    out: List[Path] = []
    for p in files:
        name = p.name
        if any(token in name for token in ("_land", "_GuangDong", "_HuiZhou")):
            continue
        if "RegionalAverage" in name:
            continue
        out.append(p)
    return out


def list_input_csvs_filtered(
    input_dir: Path,
    target_files: Optional[List[str]] = None,
) -> List[Path]:
    """列出 CSV 文件，可选按文件名过滤。"""
    if target_files is not None:
        return [input_dir / f for f in target_files if (input_dir / f).exists()]
    return list_input_csvs(input_dir)


# ============================================================
# 批量掩膜流水线
# ============================================================

# 掩膜类型 → (创建函数, 输出后缀, 网格参数)
MASK_REGISTRY: Dict[str, Tuple[Callable, str, dict]] = {}


def _register():
    """注册所有掩膜类型。"""
    MASK_REGISTRY["guangdong"] = (
        lambda grid_file, **kw: create_guangdong_mask(
            grid_file, str(kw["provinces_json"])
        ),
        "_GuangDong",
        {"provinces_json"},
    )
    MASK_REGISTRY["land"] = (
        lambda grid_file, **kw: create_land_mask(
            grid_file, str(kw["china_json"])
        ),
        "_land",
        {"china_json"},
    )
    MASK_REGISTRY["huizhou"] = (
        lambda grid_file, **kw: create_huizhou_mask(str(kw["flag_nc"])),
        "_HuiZhou",
        {"flag_nc"},
    )


_register()


def run_masks(
    input_dir: Path,
    output_dirs: Dict[str, Path],
    mask_types: List[str],
    grid_file: str,
    extra_params: Optional[Dict[str, str]] = None,
    file_limit: Optional[int] = None,
    target_files: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, int]:
    """一站式批量掩膜流水线。

    对 input_dir 下所有 CSV，依次应用指定的 mask_types，
    输出到对应的 output_dirs。

    Args:
        input_dir:   输入 CSV 目录
        output_dirs: {mask_type: output_dir_path}
        mask_types:  要应用的掩膜类型列表，如 ["land", "guangdong"]
        grid_file:   IOAPI 网格文件路径
        extra_params: 额外参数，如 {"china_json": ..., "provinces_json": ..., "flag_nc": ...}
        file_limit:  限制处理文件数 (调试用)
        target_files: 指定文件名列表 (为 None 时处理全部)
        progress_callback: 可选进度回调 (csv_name, status)

    Returns:
        {mask_type: ok_count}
    """
    params = extra_params or {}
    csv_files = list_input_csvs_filtered(input_dir, target_files)
    if file_limit is not None:
        csv_files = csv_files[:file_limit]

    if not csv_files:
        print(f"  No eligible CSVs found in {input_dir}")
        return {mt: 0 for mt in mask_types}

    # 预先读取网格属性（避免每个掩膜重复读）
    _, _, _, _, attrs = get_grid_xy_from_ioapi(grid_file)
    params["attrs"] = attrs

    # 预先构建所有掩膜
    masks: Dict[str, np.ndarray] = {}
    for mt in mask_types:
        factory, suffix, _ = MASK_REGISTRY[mt]
        masks[mt] = factory(grid_file, **params)
        print(f"  [{mt}] mask built: {int(masks[mt].sum())} / {masks[mt].size} cells")

    # 确保输出目录存在
    for mt in mask_types:
        output_dirs[mt].mkdir(parents=True, exist_ok=True)

    # 逐文件处理
    ok_counts = {mt: 0 for mt in mask_types}
    print(f"  Processing {len(csv_files)} CSV files from {input_dir}...")

    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path)
            if "ROW" not in df.columns or "COL" not in df.columns:
                if progress_callback:
                    progress_callback(csv_path.name, "SKIP (no ROW/COL)")
                continue

            df_sorted = df.sort_values(["ROW", "COL"]).reset_index(drop=True)
            first_mask = list(masks.values())[0]
            expected = first_mask.shape[0] * first_mask.shape[1]
            if len(df_sorted) != expected:
                raise ValueError(
                    f"行数({len(df_sorted)})与网格不匹配 (expected={expected})"
                )

            numeric_cols = [
                c for c in df_sorted.columns
                if c not in ("ROW", "COL") and pd.api.types.is_numeric_dtype(df_sorted[c])
            ]

            for mt in mask_types:
                _, suffix, _ = MASK_REGISTRY[mt]
                masked_df = mask_dataframe(df_sorted, masks[mt], numeric_cols)
                out_name = f"{csv_path.stem}{suffix}.csv"
                out_path = output_dirs[mt] / out_name
                masked_df.to_csv(out_path, index=False, encoding="utf-8-sig")
                ok_counts[mt] += 1

            if progress_callback:
                progress_callback(csv_path.name, "OK")

        except Exception as exc:
            if progress_callback:
                progress_callback(csv_path.name, f"FAIL: {exc}")

    return ok_counts
