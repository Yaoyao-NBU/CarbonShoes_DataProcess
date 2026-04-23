import pandas as pd
import numpy as np
import os


def mirror_trc_in_place_by_body_center(input_path, output_path):
    """
    核心处理函数：
    1. 绕身体中心(SACR)进行 Z 轴原地镜像。
    2. 交换左右标签及其对应的数据列。
    """
    with open(input_path, 'r') as f:
        header_lines = [f.readline() for _ in range(5)]

    # 读取坐标数据
    data = pd.read_csv(input_path, skiprows=5, sep='\t', header=None)
    labels = header_lines[3].strip().split('\t')

    # 1. 自动计算镜像中心 (z_center)
    z_center = 0
    sacr_idx = -1
    for i, label in enumerate(labels):
        if label == 'SACR':
            sacr_idx = i
            break

    if sacr_idx != -1:
        # 取整个动作周期内 SACR 的 Z 轴平均位置作为镜像轴
        z_center = data.iloc[:, sacr_idx + 2].mean()
    else:
        # 如果找不到 SACR，取所有 Marker 的 Z 轴平均值
        z_cols = range(4, data.shape[1], 3)
        z_center = data.iloc[:, z_cols].mean().mean()

    # 2. 左右标签名对换 (L <-> R)
    new_labels = []
    for label in labels:
        if label.startswith('L'):
            new_labels.append('R' + label[1:])
        elif label.startswith('R'):
            new_labels.append('L' + label[1:])
        else:
            new_labels.append(label)
    header_lines[3] = '\t'.join(new_labels) + '\n'

    # 3. 执行原地镜像计算 (公式：Z_new = 2 * z_center - Z_old)
    mirrored_data = data.copy()
    for col_idx in range(4, mirrored_data.shape[1], 3):
        z_old = mirrored_data.iloc[:, col_idx]
        mirrored_data.iloc[:, col_idx] = 2 * z_center - z_old

    # 4. 数据列重排 (确保数据内容与新的左右标签匹配)
    marker_to_idx = {label: i for i, label in enumerate(labels) if label and label not in ['Frame#', 'Time']}
    final_data = mirrored_data.copy()

    for i, nl in enumerate(new_labels):
        if nl in marker_to_idx:
            old_side = ('L' + nl[1:] if nl.startswith('R') else ('R' + nl[1:] if nl.startswith('L') else nl))
            if old_side in marker_to_idx:
                old_start = marker_to_idx[old_side]
                final_data.iloc[:, i:i + 3] = mirrored_data.iloc[:, old_start:old_start + 3]

    # 5. 保存结果
    with open(output_path, 'w') as f:
        f.writelines(header_lines)
        final_data.to_csv(f, sep='\t', index=False, header=False, lineterminator='\n')


# ================= 递归遍历与覆盖框架 =================

# 1. 设置目标根目录路径（脚本会搜索此目录下所有的子文件夹）
root_folder = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\test'

print(f"开始递归处理目录: {root_folder}")
print("-" * 50)

processed_count = 0
error_count = 0

# 使用 os.walk 遍历所有层级的子文件夹
for dirpath, dirnames, filenames in os.walk(root_folder):
    for filename in filenames:
        # 检查是否为 .trc 文件（忽略大小写）
        if filename.lower().endswith(".trc"):
            file_path = os.path.join(dirpath, filename)
            temp_output = file_path + ".temp"

            try:
                print(f"正在处理: {file_path} ...", end=" ")

                # 调用镜像函数
                mirror_trc_in_place_by_body_center(file_path, temp_output)

                # 处理成功后覆盖原文件
                if os.path.exists(temp_output):
                    os.remove(file_path)  # 删除原文件
                    os.rename(temp_output, file_path)  # 重命名临时文件为原文件名
                    print("✅ 成功并覆盖")
                    processed_count += 1

            except Exception as e:
                print(f"❌ 失败！错误原因: {e}")
                error_count += 1
                # 出错时尝试清理临时文件
                if os.path.exists(temp_output):
                    os.remove(temp_output)

print("-" * 50)
print(f"任务完成！")
print(f"总计成功处理并覆盖: {processed_count} 个文件")
if error_count > 0:
    print(f"跳过失败文件: {error_count} 个")