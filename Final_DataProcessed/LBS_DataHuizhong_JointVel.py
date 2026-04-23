import os
import pandas as pd
import fnmatch

# ===================== 配置区域 (修改这里) =====================
# 1. 基础路径 (Raw_Data 文件夹路径)
BASE_INPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data'
# 输出路径 (保存汇总后的速度文件)
BASE_OUTPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_huizhong_data'

# 2. 批量处理列表
RUNNER_TYPES = ['Amateur_Runner', 'Elite_Runner']
STIFFNESS_LIST = ['T1', 'T2', 'T3']

# 3. 目标文件特征 (OpenSim输出的状态文件)
# 通常长这样: S1T1V1_StatesReporter_states.csv
TARGET_FILE_PATTERN = '*_StatesReporter_states.csv'

# 4. 我们要提取的目标关节 (简写名)
# 程序会自动去寻找对应的 /speed 列
TARGET_COLUMNS = [
    'hip_flexion_r', 'hip_adduction_r', 'hip_rotation_r',
    'knee_angle_r', 'ankle_angle_r', 'subtalar_angle_r', 'mtp_angle_r',
    'pelvis_tilt', 'pelvis_list', 'pelvis_rotation',
    'pelvis_tx', 'pelvis_ty', 'pelvis_tz',
    'lumbar_extension', 'lumbar_bending', 'lumbar_rotation'
]


# ===================== 核心汇总函数 =====================
def summarize_velocity_csv(root_dir, target_stiffness, target_file_pattern, target_columns):
    # 临时存储: { 'knee_angle_r': [Series_S1, Series_S2...], ... }
    temp_storage = {col: [] for col in target_columns}
    total_files = 0

    if not os.path.exists(root_dir):
        print(f"❌ 路径不存在，跳过: {root_dir}")
        return {}

    # 遍历受试者 (S1, S2...)
    for subject in sorted(os.listdir(root_dir)):
        subject_path = os.path.join(root_dir, subject)
        if not os.path.isdir(subject_path): continue

        # 遍历刚度 (T1, T2...)
        for stiffness in os.listdir(subject_path):
            if stiffness != target_stiffness: continue

            stiffness_path = os.path.join(subject_path, stiffness)

            # 遍历 Trial (S1T1V1, S1T1V2...)
            for trial in sorted(os.listdir(stiffness_path)):
                trial_path = os.path.join(stiffness_path, trial)
                if not os.path.isdir(trial_path): continue

                # 搜索目标文件
                for dirpath, _, filenames in os.walk(trial_path):
                    matched_files = [f for f in filenames if fnmatch.fnmatch(f, target_file_pattern)]

                    for file in matched_files:
                        file_path = os.path.join(dirpath, file)
                        try:
                            # 读取 CSV
                            df = pd.read_csv(file_path)

                            # === 关键修改：智能匹配 /speed 列 ===
                            for col_simple in target_columns:
                                # 构造后缀，例如: /knee_angle_r/speed
                                # OpenSim 输出通常是: /jointset/walker_knee_r/knee_angle_r/speed
                                search_suffix = f"/{col_simple}/speed"

                                # 在 DataFrame 的所有列中寻找结尾匹配的列
                                found_col = None
                                for df_col in df.columns:
                                    if df_col.endswith(search_suffix):
                                        found_col = df_col
                                        break

                                if found_col:
                                    # 提取数据，重命名为 Trial 名 (如 S1T1V1)
                                    data_series = df[found_col].reset_index(drop=True)
                                    data_series.name = trial
                                    temp_storage[col_simple].append(data_series)

                            total_files += 1
                        except Exception as e:
                            print(f"  ⚠️ 读取错误 {file}: {e}")

    # 合并数据
    result = {}
    for col, col_list in temp_storage.items():
        if col_list:
            result[col] = pd.concat(col_list, axis=1)
        else:
            result[col] = pd.DataFrame()

    print(f'✅ 本组汇总完成，共处理 {total_files} 个文件')
    return result


# ===================== 保存函数 =====================
def save_results(result, output_dir):
    if not result: return

    os.makedirs(output_dir, exist_ok=True)

    for col, df in result.items():
        if df.empty: continue

        # 保存为 Velocity_knee_angle_r.csv
        save_path = os.path.join(output_dir, f'Velocity_{col}.csv')
        df.to_csv(save_path, index=False)

    print(f'💾 数据已保存至: {output_dir}')


# ===================== 主程序 =====================
if __name__ == '__main__':
    print("🚀 开始批量提取关节角速度 (StatesReporter)...\n")
    print("⚠️ 注意：OpenSim StatesReporter 输出的单位通常是 [rad/s] (弧度/秒)")
    print("   这非常适合直接计算功率 (Power = Moment * AngularVelocity_rad)\n")

    for runner_type in RUNNER_TYPES:
        for stiffness in STIFFNESS_LIST:
            # 输入路径
            current_input_dir = os.path.join(BASE_INPUT_DIR, runner_type)

            # 输出路径 (例如: .../WorkAndPower/Moment_AngleVel/Amateur_Runner/T1/Joint_Velocity)
            # 这里我把最后加了一层 Joint_Velocity 文件夹，方便区分
            current_output_dir = os.path.join(BASE_OUTPUT_DIR, runner_type, stiffness, 'Joint_Velocity')

            print(f"--------------------------------------------------")
            print(f"正在处理: [{runner_type}] - [{stiffness}]")

            # 汇总
            result_data = summarize_velocity_csv(current_input_dir, stiffness, TARGET_FILE_PATTERN, TARGET_COLUMNS)

            # 保存
            save_results(result_data, current_output_dir)

    print("\n🎉 所有速度数据提取完成！")