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
# 把您想处理的完整文件名写在列表里，例如 ['AT_Total_Force_r.csv']
# 如果想处理多个文件，可以用逗号隔开：['AT_Total_Force_r.csv', 'Knee_moment_r.csv']
# 如果把这个列表留空 []，它就会按原来的逻辑处理所有 Force/moment/Power 文件。
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
    处理单个特征文件，剔除 NaN 并计算积分，整理为宽格式
    """
    records = []

    # 遍历该特征(如 AT_Total_Force_r.csv)下找到的所有文件
    for info in file_info_list:
        try:
            df = pd.read_csv(info['path'])
            if df.empty: continue

            # =========================================================
            # 🔥 核心修复点：按列单独剔除空白 (NaN) 后再积分！
            # =========================================================
            for col in df.columns:
                # 剔除空白帧，保留真实数据
                valid_data = df[col].dropna().values

                if len(valid_data) < 2:
                    continue  # 数据太短无法积分

                # 使用梯形法则计算这一列的冲量
                impulse_val = trapezoid(valid_data, dx=DT)

                # 提取受试者ID
                subj_id = get_subject_id(col)

                # 存入列表
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

    # --- 后续整理为 SPSS/JASP 宽格式 ---
    df_records = pd.DataFrame(records)

    # 自动对同受试者、同组别、同鞋况下的多次测试(V1, V2)取平均
    df_agg = df_records.groupby(['Subject', 'Group', 'Stiffness'])['Impulse'].mean().reset_index()

    # 转换为宽格式: 行是受试者，列是 T1, T2, T3
    df_wide = df_agg.pivot(index=['Subject', 'Group'], columns='Stiffness', values='Impulse').reset_index()

    # 按照受试者ID排序 (让 S1, S2, S10 能够正确排序)
    df_wide['Sub_Num'] = df_wide['Subject'].str.extract(r'(\d+)').astype(int)
    df_wide = df_wide.sort_values(['Group', 'Sub_Num']).drop(columns=['Sub_Num'])

    # 保存文件
    save_file = os.path.join(output_path, f"SPSS_Ready_Impulse_{filename}")
    df_wide.to_csv(save_file, index=False)
    print(f"  ✅ 已生成统计用汇总表: SPSS_Ready_Impulse_{filename}")


# ===================== 3. 主程序入口 =====================
if __name__ == '__main__':
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 创建输出目录: {OUTPUT_DIR}")

    files_dict = scan_and_group_files(INPUT_ROOT_DIR)

    print(f"📊 共找到 {len(files_dict)} 种特征文件。开始提取 Impulse (冲量积分)...")

    # 核心判断逻辑修改
    for filename, info_list in files_dict.items():
        # 1. 如果用户指定了具体的文件列表，则只处理列表里的文件
        if TARGET_FILES:
            if filename in TARGET_FILES:
                process_for_statistics(filename, info_list, OUTPUT_DIR)
        # 2. 如果用户没有指定文件(列表为空)，采用原来的默认策略
        else:
            if "Force" in filename or "moment" in filename or "Power" in filename:
                process_for_statistics(filename, info_list, OUTPUT_DIR)
            else:
                pass # 静默跳过，避免打印太多

    print("\n🎉 指定文件的处理全部完毕！")