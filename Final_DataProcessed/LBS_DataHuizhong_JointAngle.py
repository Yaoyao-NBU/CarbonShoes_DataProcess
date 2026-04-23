import os
import pandas as pd
import fnmatch

# ===================== 配置区域 (修改这里) =====================
# 1. 基础路径 (去掉具体的人群文件夹，只保留共同的父目录)
BASE_INPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data'
BASE_OUTPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_huizhong_data'

# 2. 批量处理列表
RUNNER_TYPES = ['Amateur_Runner', 'Elite_Runner']  # 受试者人群
STIFFNESS_LIST = ['T1', 'T2', 'T3']  # 刚度条件

# 3. 文件匹配模式与列名 (保持不变)
TARGET_FILE_PATTERN = '*_IK.csv'
TARGET_COLUMNS = [
    'hip_flexion_r', 'hip_adduction_r', 'hip_rotation_r',
    'knee_angle_r', 'ankle_angle_r', 'subtalar_angle_r', 'mtp_angle_r',
    'pelvis_tilt', 'pelvis_list', 'pelvis_rotation',
    'pelvis_tx', 'pelvis_ty', 'pelvis_tz',
    'lumbar_extension', 'lumbar_bending', 'lumbar_rotation'
]


# ===================== 核心汇总 (保持原样) =====================
def summarize_csv(root_dir, target_stiffness, target_file_pattern, target_columns):
    # 用临时存储避免碎片化
    temp_storage = {col: [] for col in target_columns}
    total_files = 0  # 计数处理的文件数量

    # 检查输入目录是否存在，不存在则直接返回
    if not os.path.exists(root_dir):
        print(f"❌ 路径不存在，跳过: {root_dir}")
        return {}

    for subject in sorted(os.listdir(root_dir)):
        subject_path = os.path.join(root_dir, subject)
        if not os.path.isdir(subject_path):
            continue
        # print(f'正在处理被试: {subject}') # 可以注释掉减少刷屏

        for stiffness in os.listdir(subject_path):
            if stiffness != target_stiffness:
                continue
            stiffness_path = os.path.join(subject_path, stiffness)
            # print(f'  筛选刚度: {stiffness}')

            for trial in sorted(os.listdir(stiffness_path)):
                trial_path = os.path.join(stiffness_path, trial)
                if not os.path.isdir(trial_path):
                    continue
                # print(f'    处理 trial: {trial}')

                # 遍历 Trial 下所有子文件夹
                for dirpath, dirnames, filenames in os.walk(trial_path):
                    matched_files = [f for f in filenames if fnmatch.fnmatch(f, target_file_pattern)]

                    for file in matched_files:
                        file_path = os.path.join(dirpath, file)
                        # print(f'      读取文件: {file}')

                        df = pd.read_csv(file_path)
                        col_name = f'{trial}'

                        for col in target_columns:
                            if col in df.columns:
                                temp_storage[col].append(df[col].reset_index(drop=True).rename(col_name))

                        total_files += 1

    # 一次性合并，减少碎片化
    result = {}
    for col, col_list in temp_storage.items():
        if col_list:
            result[col] = pd.concat(col_list, axis=1)
            result[col] = result[col].copy()  # 再次消除碎片化
        else:
            result[col] = pd.DataFrame()  # 空数据保持一致

    print(f'✅ 本组汇总完成，共处理 {total_files} 个文件')
    return result


# ===================== 保存为 CSV (保持原样) =====================
def save_results(result, output_dir, stiffness):
    if not result:
        print("⚠️ 结果为空，跳过保存")
        return

    os.makedirs(output_dir, exist_ok=True)

    for col, df in result.items():
        if df.empty:
            # print(f'⚠️ 列 "{col}" 没有数据，跳过保存')
            continue
        save_path = os.path.join(output_dir, f'IK_{col}.csv')
        df.to_csv(save_path, index=False)

    print(f'💾 数据已保存至: {output_dir}')


# ===================== 主程序 (修改为双层循环) =====================
if __name__ == '__main__':
    print("🚀 开始批量处理任务...\n")

    # 外层循环：受试者类型 (Amateur vs Elite)
    for runner_type in RUNNER_TYPES:
        # 内层循环：刚度条件 (T1, T2, T3)
        for stiffness in STIFFNESS_LIST:
            # 1. 动态构建输入路径
            # 例如: ...\High_Speed\Interpolte\Amateur_Runner
            current_input_dir = os.path.join(BASE_INPUT_DIR, runner_type)

            # 2. 动态构建输出路径
            # 例如: ...\huizongFile_Interpolte\Amateur_Runner\T1\Joint_angle
            current_output_dir = os.path.join(BASE_OUTPUT_DIR, runner_type, stiffness, 'Joint_angle')

            print(f"--------------------------------------------------")
            print(f"正在处理: [{runner_type}] - [{stiffness}]")
            print(f"📂 输入源: {current_input_dir}")
            print(f"📂 输出地: {current_output_dir}")

            # 3. 调用核心函数
            result_data = summarize_csv(current_input_dir, stiffness, TARGET_FILE_PATTERN, TARGET_COLUMNS)

            # 4. 保存结果
            save_results(result_data, current_output_dir, stiffness)

    print("\n🎉 所有批处理任务全部完成！")