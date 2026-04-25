import os
import pandas as pd
import re

# ===================== 1. 基础配置区域 (Configuration) =====================
# 输入路径：存放所有未插值平均结果的根目录
# 程序会自动递归查找这个目录下的所有子文件夹
INPUT_ROOT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\uninterpolte\uninterpolte_average_data_normalization'

# 输出路径：最终生成的汇总表格存放位置
OUTPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\uninterpolte\Characteristic_Value\Load_JointAngle_Value'

# 定义受试者人群 (Groups) 和 刚度条件 (Stiffness)
# 程序会根据路径中是否包含这些关键词来判断文件属于哪一组
GROUPS = ['Amateur_Runner', 'Elite_Runner']
STIFFNESSES = ['T1', 'T2', 'T3']


# ===================== 2. 核心工具函数 (Helper Functions) =====================

def get_subject_id(col_name):
    """
    功能：从列名字符串中提取受试者编号
    例如：输入 'S1T1V1' -> 输出 'S1'
    """
    # 使用正则表达式查找 'S' 开头后面跟数字的模式
    match = re.match(r'(S\d+)', col_name)
    # 如果找到了就返回 S1，没找到就返回原名
    return match.group(1) if match else col_name


def scan_and_group_files(root_dir):
    """
    功能：扫描文件夹，把所有同名的特征文件（比如 IK_knee_angle.csv）归类。
    原理：有些文件在 T1 文件夹下，有些在 T2 下，这个函数把它们按文件名关联起来。
    返回：一个字典，Key是文件名，Value是该文件所在的所有路径信息列表。
    """
    file_map = {}  # 初始化字典用于存储结果

    print("🔍 正在扫描文件结构...")
    # os.walk 会遍历目录树下的每一个角落
    for dirpath, _, filenames in os.walk(root_dir):

        # 核心逻辑：检查当前文件夹路径里，是否包含我们定义的人群(Amateur/Elite)和刚度(T1/T2/T3)
        # next() 函数会返回列表中第一个匹配到的元素
        current_group = next((g for g in GROUPS if g in dirpath), None)
        current_stiffness = next((s for s in STIFFNESSES if s in dirpath), None)

        # 如果当前文件夹路径里没有包含特定的人群或刚度信息，就跳过不处理
        if not current_group or not current_stiffness:
            continue

        # 遍历当前文件夹下的所有文件
        for file in filenames:
            if file.endswith('.csv'):  # 只处理 csv 文件
                if file not in file_map:
                    file_map[file] = []  # 如果字典里还没有这个文件名，先初始化一个空列表

                # 将文件的具体路径、所属人群、所属刚度记录下来
                file_map[file].append({
                    'path': os.path.join(dirpath, file),  # 完整绝对路径
                    'group': current_group,  # 例如: Amateur_Runner
                    'stiffness': current_stiffness  # 例如: T1
                })
    return file_map


def process_single_feature(filename, file_info_list, output_path):
    """
    功能：处理某一个具体的特征文件（例如膝关节角度），将所有人、所有刚度的数据汇总。
    特点：先分人群处理，处理完后去掉受试者ID，最后横向拼接。
    """

    # 用于存储处理好的各个人群的 DataFrame 列表
    # 列表里会有两个 DataFrame：一个是 Amateur 的表，一个是 Elite 的表
    group_dfs_list = []

    # --- 第一层循环：分别处理每一个受试者人群 (Amateur / Elite) ---
    for target_group in GROUPS:

        # 创建一个临时表，用于存放当前人群在 T1, T2, T3 三种情况下的数据
        # 此时还需要保留 index 为受试者ID，为了保证同一个人不同刚度的数据能对齐
        current_group_df = pd.DataFrame()

        # --- 第二层循环：遍历三种刚度 (T1, T2, T3) ---
        for target_stiffness in STIFFNESSES:

            # 从文件列表中找到匹配当前 Group 和 Stiffness 的那个文件信息
            matched_info = next(
                (info for info in file_info_list
                 if info['group'] == target_group and info['stiffness'] == target_stiffness),
                None
            )

            # 如果找到了对应的文件，开始读取数据
            if matched_info:
                file_path = matched_info['path']
                # 定义列名，例如: Amateur_Runner_T1
                col_header = f"{target_group}_{target_stiffness}"

                try:
                    # 1. 读取原始 CSV
                    df = pd.read_csv(file_path)
                    if df.empty: continue

                    # 2. 提取特征值：这里取的是第1行（索引0），也就是落地时刻
                    # 这一行通常包含了该次实验所有 Trial 的落地数值
                    touchdown_series = df.iloc[0]

                    # 3. 提取表头中的受试者ID (S1, S2...)
                    subjects = [get_subject_id(col) for col in touchdown_series.index]
                    values = touchdown_series.values

                    # 4. 构建临时 DataFrame
                    # index=subjects: 设定行索引为 S1, S2... 方便后续合并
                    temp_df = pd.DataFrame(data=values, index=subjects, columns=[col_header])
                    temp_df.index.name = 'Subject'

                    # 5. 处理重复 ID (Groupby Mean)
                    # 如果同一个人有多次 Trial (比如有两列都是 S1)，这里取平均值合并成一行
                    temp_df = temp_df.groupby('Subject').mean()

                    # 6. 合并到当前人群的总表中
                    # 使用 merge (Outer Join): 确保即使某人缺了 T1 数据，T2 数据也能保留，不会报错
                    if current_group_df.empty:
                        current_group_df = temp_df
                    else:
                        current_group_df = current_group_df.merge(temp_df, left_index=True, right_index=True,
                                                                  how='outer')

                except Exception as e:
                    print(f"  ⚠️ 读取 {file_path} 出错: {e}")

        # --- 关键步骤：去头去尾 (Reset Index) ---
        # 当某一个人群 (如 Amateur) 的 T1-T3 都找齐合并完后
        # 我们不需要 'S1', 'S2' 这些索引了，因为最终表格要求纯数据紧凑排列
        if not current_group_df.empty:
            # drop=True: 彻底删除 Subject 列，不保留
            # 操作后索引变成 0, 1, 2, 3...
            current_group_df.reset_index(drop=True, inplace=True)

            # 将处理好的干净数据加入列表
            group_dfs_list.append(current_group_df)

    # --- 最后一步：横向拼接 (Concat) ---
    # axis=1: 左右拼接
    # 因为前面都重置了索引为 0,1,2...，所以 Amateur 和 Elite 的数据会并排贴在一起
    # Amateur 的第1行和 Elite 的第1行会在同一水平线上
    if group_dfs_list:
        master_df = pd.concat(group_dfs_list, axis=1)

        # 保存文件
        save_file = os.path.join(output_path, f"Summary_{filename}")
        master_df.to_csv(save_file, index=False)
        print(f"  ✅ 已生成汇总表: {save_file}")
    else:
        print(f"  ⚠️ 未找到任何有效数据: {filename}")


# ===================== 3. 主程序入口 (Main) =====================
if __name__ == '__main__':
    # 检查并创建输出目录
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 创建输出目录: {OUTPUT_DIR}")

    # 第一步：扫描所有文件
    files_dict = scan_and_group_files(INPUT_ROOT_DIR)

    print(f"📊 共找到 {len(files_dict)} 种不同的特征文件。开始汇总...")

    # 第二步：循环处理每一种特征
    for filename, info_list in files_dict.items():
        # filename 例如: 'IK_knee_angle_r.csv'
        # info_list 包含了该文件在各个文件夹下的路径
        process_single_feature(filename, info_list, OUTPUT_DIR)

    print("\n🎉 所有特征值提取与汇总完成！请检查文件夹：Summary_Statistics_UnInterpolte")