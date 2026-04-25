import os
import pandas as pd
import re


# ================= 你的功能函数 (保持不变) =================
def batch_normalize_by_weight(data_path, weight_info_path, output_path, gravity=9.81):
    try:
        weight_df = pd.read_csv(weight_info_path)
        # 确保体重表ID是字符串且无空格
        weight_df['people'] = weight_df['people'].astype(str).str.strip()
        # 生成体重查询字典
        weight_lookup = weight_df.set_index('people')['weight'].to_dict()

        data_df = pd.read_csv(data_path)
        normalized_df = data_df.copy()

        success_count = 0
        for col in data_df.columns:
            # 匹配受试者ID (例如 S1T1V1 -> S1)
            match = re.match(r'([sS]\d+)', col)
            if match:
                subject_id = match.group(1).upper()
                if subject_id in weight_lookup:
                    weight = weight_lookup[subject_id]
                    # 核心公式: 原始值 / (体重kg * gravity)
                    # 如果 gravity=1, 则是 W/kg; 如果 gravity=9.81, 则是 BW
                    normalized_df[col] = data_df[col] / (weight * gravity)
                    success_count += 1

        # 只在成功处理了数据的情况下保存
        if success_count > 0:
            normalized_df.to_csv(output_path, index=False)
            print(f"  ✅ 成功标准化 ({success_count} 列)")
        else:
            print(f"  ⚠️ 未找到匹配的受试者ID，跳过保存")

    except Exception as e:
        print(f"  ❌ 处理出错: {e}")


# ================= 配置区 =================
input_root = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\uninterpolte\uninterpolte_huizhong_data_normalization"
output_root = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\uninterpolte\uninterpolte_huizhong_data_normalization"  # 建议输出到新文件夹
weight_file = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\baseline_01.csv"

# --- 修改点1：在列表中加入功率文件 ---
target_filenames = [
    # 原有力矩/力文件 (BW)
    "AT_gasmed_r.csv", "AT_gaslat_r.csv", "AT_soleus_r.csv",
    'ID_hip_flexion_r_moment.csv', 'ID_hip_adduction_r_moment.csv', 'ID_hip_rotation_r_moment.csv',
    'ID_knee_angle_r_moment.csv', 'ID_ankle_angle_r_moment.csv', 'ID_subtalar_angle_r_moment.csv',
    'ID_mtp_angle_r_moment.csv',
    'ID_pelvis_tilt_moment.csv', 'ID_pelvis_list_moment.csv', 'ID_pelvis_rotation_moment.csv',
    'ID_pelvis_tx_force.csv', 'ID_pelvis_ty_force.csv', 'ID_pelvis_tz_force.csv',
    'ID_lumbar_extension_moment.csv', 'ID_lumbar_bending_moment.csv', 'ID_lumbar_rotation_moment.csv',

    # 新增功率文件 (W/kg)
    # "AT_Total_Force_r.csv",
    # "ID_knee_angle_l_moment.csv",
]
# ==========================================

print(f"开始任务：准备批量处理 {len(target_filenames)} 个文件...")

total_processed = 0

# 遍历目标文件夹
for root, dirs, files in os.walk(input_root):
    for file in files:
        if file in target_filenames:
            # 1. 确定路径
            original_file_path = os.path.join(root, file)
            rel_path = os.path.relpath(root, input_root)
            target_dir = os.path.join(output_root, rel_path)

            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            save_file_path = os.path.join(target_dir, file)

            # --- 修改点2：智能判断是否为功率文件 ---
            # 默认 gravity = 9.81 (用于力/力矩 -> BW)
            current_gravity = 9.81
            unit_info = "BW (除以 Weight*9.81)"

            # 如果文件名包含 Power 或 Work，改为 gravity = 1.0 (用于功率 -> W/kg)
            if "Power" in file or "Work" in file:
                current_gravity = 1.0
                unit_info = "W/kg (除以 Weight)"

            # 5. 调用函数
            print(f"[正在处理] {file:<40} | 模式: {unit_info}")

            batch_normalize_by_weight(
                data_path=original_file_path,
                weight_info_path=weight_file,
                output_path=save_file_path,
                gravity=current_gravity  # 传入动态调整后的 gravity
            )
            total_processed += 1

print("\n" + "=" * 50)
print(f"任务完成！共处理了 {total_processed} 个文件。")
print(f"结果已保存在: {output_root}")
print("=" * 50)