import os
import pandas as pd
import re


# ================= 功能函数 =================
def batch_normalize_by_weight(data_path, weight_info_path, output_path, gravity=1.0):
    try:
        weight_df = pd.read_csv(weight_info_path)
        weight_df['people'] = weight_df['people'].astype(str).str.strip()
        weight_lookup = weight_df.set_index('people')['weight'].to_dict()

        data_df = pd.read_csv(data_path)
        normalized_df = data_df.copy()

        success_count = 0
        for col in data_df.columns:
            match = re.match(r'([sS]\d+)', col)
            if match:
                subject_id = match.group(1).upper()
                if subject_id in weight_lookup:
                    weight = weight_lookup[subject_id]
                    # Power标准化: W / (kg * gravity)
                    # gravity=1.0 -> W/kg; gravity=9.81 -> BW
                    normalized_df[col] = data_df[col] / (weight * gravity)
                    success_count += 1

        if success_count > 0:
            normalized_df.to_csv(output_path, index=False)
            print(f"  ✅ 成功标准化 ({success_count} 列)")
        else:
            print(f"  ⚠️ 未找到匹配的受试者ID，跳过保存")

    except Exception as e:
        print(f"  ❌ 处理出错: {e}")


# ================= 配置区 =================
input_root = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data\interpolte_huizhong_noemalization"
output_root = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data\interpolte_huizhong_noemalization"
weight_file = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\baseline_01.csv"

RUNNER_TYPES = ['Amateur_Runner', 'Elite_Runner']
STIFFNESS_LIST = ['T1', 'T2', 'T3']

# 需要标准化的关节Power文件 (髋膝踝)
POWER_KEYWORDS = {
    'Hip': 'hip_flexion_r',
    'Knee': 'knee_angle_r',
    'Ankle': 'ankle_angle_r',
}

# 需要处理的文件类型前缀
FILE_PREFIXES = ['Time_Series_Power', 'Raw_Positive_Work', 'Raw_Negative_Work',
                 'Raw_Net_Work', 'Raw_Peak_Power']

print(f"开始任务：批量标准化Power数据 (W/kg)...\n")

total_processed = 0

for runner in RUNNER_TYPES:
    for stiff in STIFFNESS_LIST:
        joint_power_dir = os.path.join(input_root, runner, stiff, 'Joint_Power')

        if not os.path.exists(joint_power_dir):
            print(f"⚠️ 跳过: {runner}/{stiff} - 找不到 Joint_Power 文件夹")
            continue

        print(f"📂 处理分组: [{runner}] - [{stiff}]")

        # 构建输出目录
        out_dir = os.path.join(output_root, runner, stiff, 'Joint_Power')
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        for prefix in FILE_PREFIXES:
            for joint_key, keyword in POWER_KEYWORDS.items():
                filename = f"{prefix}_{keyword}.csv"
                file_path = os.path.join(joint_power_dir, filename)

                if not os.path.exists(file_path):
                    print(f"  ⚠️ 文件不存在: {filename}")
                    continue

                save_path = os.path.join(out_dir, filename)

                # Power/Work文件用 gravity=1.0 -> W/kg
                print(f"  [正在处理] {filename:<50} | 模式: W/kg")
                batch_normalize_by_weight(
                    data_path=file_path,
                    weight_info_path=weight_file,
                    output_path=save_path,
                    gravity=1.0
                )
                total_processed += 1

print("\n" + "=" * 50)
print(f"任务完成！共处理了 {total_processed} 个文件。")
print(f"结果已保存在: {output_root}")
print("=" * 50)
