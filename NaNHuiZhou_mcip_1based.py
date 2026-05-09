import pandas as pd
import xarray as xr
import numpy as np
import os
import glob

# ========== 用户配置 / User Config ==========
flag_file = "HuiZhou_2000121_GuangDongD3.nc"  # 惠州Flag文件路径
input_dir = "./mcipout_processed/"             # 输入文件夹路径
output_dir = "./mcipout_processed_HuiZhou/"    # 输出文件夹路径

# 指定要处理的文件名列表
target_files = [
    "2060_mcipout_01.csv",
    "2060_mcipout_07.csv",
]

# ========== 1. 读取Flag ==========
flag_ds = xr.open_dataset(flag_file)
flag = flag_ds["Flag"].values  # shape = [nrows, ncols]
flag_ds.close()

# 创建输出目录
os.makedirs(output_dir, exist_ok=True)

print("=" * 60)
print("开始处理CMAQ数据，生成惠州区域过滤后的文件")
print("=" * 60)

# ========== 2. 逐文件处理 ==========
processed_count = 0
for filename in target_files:
    filepath = os.path.join(input_dir, filename)

    if not os.path.exists(filepath):
        print(f"⚠️ 文件未找到: {filepath}")
        continue

    print(f"\n📁 正在处理: {filename}")
    df = pd.read_csv(filepath)

    # 检查必要的列
    if "ROW" not in df.columns or "COL" not in df.columns:
        print(f"⚠️ 跳过 {filepath}：缺少 ROW/COL 列")
        continue

    # 自动识别数值列（除ROW和COL）
    value_cols = [c for c in df.columns if c not in ["ROW", "COL"]]
    if not value_cols:
        print(f"⚠️ 跳过 {filepath}：未找到数值列")
        continue

    print(f"✅ 读取数据成功: {len(df)}行, 数值列: {value_cols}")

    # 注意：输入数据已经是0基索引，不需要减1
    # 保持原始的ROW和COL值不变
    df["ROW"] = df["ROW"].astype(int)-1
    df["COL"] = df["COL"].astype(int)-1
    rows, cols = df["ROW"].values, df["COL"].values

    # 向量化筛选：标记在网格内的点
    mask_inside = (rows >= 0) & (rows < flag.shape[0]) & (cols >= 0) & (cols < flag.shape[1])
    valid_idx = np.where(mask_inside)[0]

    print(f"📊 网格内数据点数: {len(valid_idx)} / {len(df)}")

    # 处理每个变量列 - 只保留惠州区域内的数据
    huizhou_points = 0
    for col_name in value_cols:
        # ⚠️ 强制转为float，防止np.nan写入时报错
        vals = df[col_name].astype(float).values.copy()

        # 对于网格外的点直接设为NaN
        vals[~mask_inside] = np.nan

        # 对于网格内但不在惠州区域的点设为NaN
        for i in valid_idx:
            r, c = rows[i], cols[i]
            if flag[r, c] != 1:
                vals[i] = np.nan
            else:
                huizhou_points += 1

        df[col_name] = vals

    # 输出文件名：添加_HuiZhou后缀
    base_name = os.path.basename(filepath)
    output_filename = base_name.replace(".csv", "_HuiZhou.csv")
    output_path = os.path.join(output_dir, output_filename)

    # 保存处理后的数据
    df.to_csv(output_path, index=False)

    print(f"✅ 已输出：{output_path}")
    print(f"📍 惠州区域有效数据点: {huizhou_points}")
    processed_count += 1

print("\n" + "=" * 60)
print(f"🎯 处理完成！共处理 {processed_count} 个文件")
print(f"📂 输出文件夹: {output_dir}")
print("=" * 60)
