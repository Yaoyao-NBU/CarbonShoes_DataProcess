import os
import pandas as pd
import numpy as np
import re
from scipy.integrate import trapezoid

# ===================== 1. 基础配置区域 =====================
INPUT_ROOT_DIR = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Result_Average_UnInterpolte'
OUTPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Summary_Statistics_UnInterpolte\Impulse_Value'

GROUPS = ['Amateur_Runner', 'Elite_Runner']
STIFFNESSES = ['T1', 'T2', 'T3']

# 🔥🔥🔥 [重要]: 确保这个采样率是您真实的频率！
SAMPLING_RATE = 200.0
DT = 1.0 / SAMPLING_RATE

# 🔥🔥🔥 [新增配置]: 指定您想要积分的文件名！
TARGET_FILES = ['AT_Total_Force_r.csv']


# ===================== 2. 核心工具函数 =====================

def get_subject_id(col_name):
    """从列名中提取受试者ID (例如 'S1T1V2' -> 'S1')"""
    match = re.match(r'(S\d+)', col_name)
    return match.group(1) if match else col_name


def scan_and_group_files(root_dir):
    """扫描文件夹，归类同名文件"""
    file_map = {}
    print("🔍 正在扫描文件结构...")
    for dirpath, _, filenames in os.walk(root_dir):
        current_group = next((g for g in GROUPS if g in dirpath), None)
        current_stiffness = next((s for s in STIFFNESSES if s in dirpath), None)

        if not current_group or not current_stiffness:
            continue

        for file in filenames:
            if file.endswith('.csv'):
                if file not in file_map: file_map[file] = []
                file_map[file].append({
                    'path': os.path.join(dirpath, file),
                    'group': current_group,
                    'stiffness': current_stiffness
                })
    return file_map


def process_for_statistics(filename, file_info_list, output_path):
    """
    处理单个特征文件，剔除 NaN 并计算积分，还原为您指定的汇总宽表格式
    """
    records = []

    # 1. 抽取所有的有效积分数据
    for info in file_info_list:
        try:
            df = pd.read_csv(info['path'])
            if df.empty: continue

            for col in df.columns:
                # 剔除空白帧，保留真实数据进行积分
                valid_data = df[col].dropna().values
                if len(valid_data) < 2:
                    continue

                impulse_val = trapezoid(valid_data, dx=DT)
                subj_id = get_subject_id(col)

                records.append({
                    'Subject': subj_id,
                    'Group': info['group'],
                    'Stiffness': info['stiffness'],
                    'Impulse': impulse_val
                })

        except Exception as e:
            print(f"  ⚠️ 读取 {info['path']} 出错: {e}")

    if not records:
        print(f"  ⚠️ 未找到有效数据: {filename}")
        return

    # 2. 转换为 DataFrame 并对多次测试(V1, V2)取平均
    df_records = pd.DataFrame(records)
    df_agg = df_records.groupby(['Subject', 'Group', 'Stiffness'])['Impulse'].mean().reset_index()

    # 创造目标列名 (例如: Amateur_Runner_T1)
    df_agg['Col_Name'] = df_agg['Group'] + '_' + df_agg['Stiffness']

    # 3. 按人群分组进行排版还原
    group_dfs = []
    for g in GROUPS:
        df_g = df_agg[df_agg['Group'] == g]
        if df_g.empty: continue

        # 将该组人群数据铺平 (保证同一人的 T1, T2, T3 在同一行)
        wide_g = df_g.pivot(index='Subject', columns='Col_Name', values='Impulse')

        # 内部对受试者按数字大小排序一下，让表格更规整
        wide_g['Sub_Num'] = wide_g.index.str.extract(r'(\d+)').astype(int)
        wide_g = wide_g.sort_values('Sub_Num').drop(columns=['Sub_Num'])

        # 🔥 核心格式还原：抹除 Subject 索引，变成没有任何左侧表头的纯数值表
        wide_g.reset_index(drop=True, inplace=True)

        group_dfs.append(wide_g)

    # 4. 横向拼接所有组别 (Amateur 左边，Elite 右边)
    if group_dfs:
        final_df = pd.concat(group_dfs, axis=1)

        # 保存文件
        save_file = os.path.join(output_path, f"Summary_Impulse_{filename}")
        final_df.to_csv(save_file, index=False)
        print(f"  ✅ 格式已对齐！已生成汇总表: Summary_Impulse_{filename}")


# ===================== 3. 主程序入口 =====================
if __name__ == '__main__':
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 创建输出目录: {OUTPUT_DIR}")

    files_dict = scan_and_group_files(INPUT_ROOT_DIR)

    print(f"📊 共找到 {len(files_dict)} 种特征文件。开始提取 Impulse (冲量积分)...")

    for filename, info_list in files_dict.items():
        if TARGET_FILES:
            if filename in TARGET_FILES:
                process_for_statistics(filename, info_list, OUTPUT_DIR)
        else:
            if "Force" in filename or "moment" in filename or "Power" in filename:
                process_for_statistics(filename, info_list, OUTPUT_DIR)
            else:
                pass

    print("\n🎉 指定文件的处理全部完毕！")