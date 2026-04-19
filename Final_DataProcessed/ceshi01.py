import os
import pandas as pd
import re


# ================= 你的功能函数 =================
def batch_normalize_by_weight(data_path, weight_info_path, output_path, gravity=9.81):
    # ... (这里保持你提供的函数内容不变) ...
    weight_df = pd.read_csv(weight_info_path)
    weight_df['People'] = weight_df['People'].astype(str).str.strip()
    weight_lookup = weight_df.set_index('People')['Weight'].to_dict()
    data_df = pd.read_csv(data_path)
    normalized_df = data_df.copy()

    success_count = 0
    for col in data_df.columns:
        match = re.match(r'([sS]\d+)', col)
        if match:
            subject_id = match.group(1).upper()
            if subject_id in weight_lookup:
                weight = weight_lookup[subject_id]
                normalized_df[col] = data_df[col] / (weight * gravity)
                success_count += 1

    normalized_df.to_csv(output_path, index=False)
    return normalized_df


# ================= 配置区 =================
input_root = r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\ceshi\cehsi"  # 原始数据根目录
output_root = r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\ceshi\out"  # 标准化后保存的根目录
weight_file = r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\ceshi\BodayWeight.csv"  # 体重信息表路径
target_filename = "AT_Total_Force_r.csv"  # 指定要处理的文件名
# ==========================================

print(f"开始任务：仅处理名为 {target_filename} 的文件...")

# 历遍目标文件夹
for root, dirs, files in os.walk(input_root):
    for file in files:
        # 只处理指定文件名的文件
        if file == target_filename:
            # 1. 确定原始文件路径
            original_file_path = os.path.join(root, file)

            # 2. 计算相对路径并保持结构
            rel_path = os.path.relpath(root, input_root)
            target_dir = os.path.join(output_root, rel_path)

            # 3. 自动创建目标文件夹结构
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            # 4. 确定输出文件路径
            save_file_path = os.path.join(target_dir, file)

            # 5. 调用你的标准化处理函数
            print(f"\n[正在调度] 源文件: {original_file_path}")
            batch_normalize_by_weight(
                data_path=original_file_path,
                weight_info_path=weight_file,
                output_path=save_file_path,
                gravity=9.81
            )

print("\n" + "=" * 30)
print("所有目标文件已按照原始目录结构完成标准化处理！")
print("=" * 30)