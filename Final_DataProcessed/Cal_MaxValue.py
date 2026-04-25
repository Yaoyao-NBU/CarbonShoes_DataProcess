import os
import pandas as pd
import re

# ===================== 1. 基础配置区域 =====================
INPUT_ROOT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\uninterpolte\Characteristic_Value\power_work'
OUTPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\uninterpolte\Characteristic_Value\Max_Value'

GROUPS = ['Amateur_Runner', 'Elite_Runner']
STIFFNESSES = ['T1', 'T2', 'T3']


# ===================== 2. 核心工具函数 =====================

def get_subject_id(col_name):
    """从列名中提取受试者ID (例如 'S1T1V1' -> 'S1')"""
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


def process_single_feature(filename, file_info_list, output_path):
    """
    处理单个特征文件，计算最大值，并按宽格式汇总（无Subject列）。
    """
    group_dfs_list = []

    # --- 第一层循环：分人群 (Amateur / Elite) ---
    for target_group in GROUPS:

        # 临时表：存放当前人群 T1-T3 的数据
        current_group_df = pd.DataFrame()

        # --- 第二层循环：分刚度 (T1 / T2 / T3) ---
        for target_stiffness in STIFFNESSES:

            matched_info = next(
                (info for info in file_info_list
                 if info['group'] == target_group and info['stiffness'] == target_stiffness),
                None
            )

            if matched_info:
                file_path = matched_info['path']
                col_header = f"{target_group}_{target_stiffness}"

                try:
                    df = pd.read_csv(file_path)
                    if df.empty: continue

                    # =======================================================
                    # 🔥 修改点：这里改为计算每一列的最大值 (Max)
                    # =======================================================
                    # df.max() 会返回一个 Series，索引是列名，值是该列的最大值
                    feature_series = df.max()

                    # 提取ID
                    subjects = [get_subject_id(col) for col in feature_series.index]
                    values = feature_series.values

                    # 构建 DataFrame
                    temp_df = pd.DataFrame(data=values, index=subjects, columns=[col_header])
                    temp_df.index.name = 'Subject'

                    # 同ID取平均
                    temp_df = temp_df.groupby('Subject').mean()

                    # 合并
                    if current_group_df.empty:
                        current_group_df = temp_df
                    else:
                        current_group_df = current_group_df.merge(temp_df, left_index=True, right_index=True,
                                                                  how='outer')

                except Exception as e:
                    print(f"  ⚠️ 读取 {file_path} 出错: {e}")

        # --- 去头去尾：删除 Subject 索引 ---
        if not current_group_df.empty:
            current_group_df.reset_index(drop=True, inplace=True)
            group_dfs_list.append(current_group_df)

    # --- 横向拼接 ---
    if group_dfs_list:
        master_df = pd.concat(group_dfs_list, axis=1)

        # 保存文件，前缀改为 Summary_Max_
        save_file = os.path.join(output_path, f"Summary_Max_{filename}")
        master_df.to_csv(save_file, index=False)
        print(f"  ✅ 已生成最大值汇总表: {save_file}")
    else:
        print(f"  ⚠️ 未找到数据: {filename}")


# ===================== 3. 主程序入口 =====================
if __name__ == '__main__':
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 创建输出目录: {OUTPUT_DIR}")

    files_dict = scan_and_group_files(INPUT_ROOT_DIR)

    print(f"📊 共找到 {len(files_dict)} 种特征文件。开始提取最大值...")

    for filename, info_list in files_dict.items():
        process_single_feature(filename, info_list, OUTPUT_DIR)

    print("\n🎉 全部完成！最大值已提取。")