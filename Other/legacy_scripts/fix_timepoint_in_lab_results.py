#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清洗 实验室站点结果 目录下 CSV 文件的 timePoint 列格式。

做的事情：
- 在目录 "臭氧颗粒物站点校验/实验室站点结果" 下寻找所有 .csv 文件；
- 若存在列名为 "timePoint"（大小写不敏感），则：
  * 用 pandas.to_datetime 解析为时间；
  * 统一格式化输出为 "YYYY-MM-DD HH:MM:SS" 字符串；
  * 其他列保持不变；
  * 覆盖原 CSV 前，会先备份为 原名 + ".bak"。

这样可以纠正混乱的时间格式（例如 - / / 混用，带时区等），而不会更改实际时间值。
"""

import shutil
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
# 实际目录名为“实验室广东站点结果”
ROOT = BASE / "臭氧颗粒物站点校验" / "实验室广东站点结果"


def normalize_timepoint_column(df: pd.DataFrame) -> pd.DataFrame:
    # 找到名为 timePoint 的列（不区分大小写）
    time_cols = [c for c in df.columns if c.lower() == "timepoint"]
    if not time_cols:
        return df

    col = time_cols[0]
    print(f"  - 发现时间列: {col}")

    # 解析为 datetime
    dt = pd.to_datetime(df[col], errors="coerce")
    # 保留原有无法解析的值，用于排查
    bad_mask = dt.isna() & df[col].notna()
    if bad_mask.any():
        print(f"    * 有 {bad_mask.sum()} 条记录无法解析，将保留原字符串。")
        # 对能解析的写新格式，不能解析的保留原值
        formatted = dt.dt.strftime("%Y-%m-%d %H:%M:%S")
        df[col] = df[col].where(bad_mask, formatted)
    else:
        # 全部解析成功
        df[col] = dt.dt.strftime("%Y-%m-%d %H:%M:%S")

    return df


def process_csv_file(csv_path: Path):
    print(f"处理文件: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"  ! 读取失败，跳过: {e}")
        return

    if not any(c.lower() == "timepoint" for c in df.columns):
        print("  - 不含 timePoint 列，跳过。")
        return

    df_new = normalize_timepoint_column(df)

    # 备份原文件
    backup = csv_path.with_suffix(csv_path.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(csv_path, backup)
        print(f"  - 已备份原文件到: {backup}")

    # 覆盖写回
    df_new.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print("  - 已写回修正后的 CSV。")


def main():
    print("=== 修正 实验室站点结果 下 CSV 的 timePoint 列 ===")
    print(f"目标目录: {ROOT}")

    if not ROOT.exists():
        print("目录不存在，退出。")
        return

    csv_files = sorted(ROOT.glob("*.csv"))
    if not csv_files:
        print("未找到 CSV 文件。")
        return

    print(f"共发现 {len(csv_files)} 个 CSV 文件。")

    for csv_path in csv_files:
        process_csv_file(csv_path)

    print("\n完成。")


if __name__ == "__main__":
    main()
