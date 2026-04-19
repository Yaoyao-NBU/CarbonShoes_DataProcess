import pandas as pd
import numpy as np


def mirror_trc_in_place_by_body_center(input_path, output_path):
    # 1. 读取 TRC 文件头 (前 5 行)
    with open(input_path, 'r') as f:
        header_lines = [f.readline() for _ in range(5)]

    # 2. 读取坐标数据
    data = pd.read_csv(input_path, skiprows=5, sep='\t', header=None)
    labels = header_lines[3].strip().split('\t')

    # 3. 自动计算镜像中心 (z_center)
    # 我们寻找一个位于身体中线的标记点，比如 'SACR'
    # 如果找不到 SACR，就用所有标记点的 Z 轴平均值作为中心
    z_center = 0
    sacr_idx = -1
    for i, label in enumerate(labels):
        if label == 'SACR':
            sacr_idx = i
            break

    if sacr_idx != -1:
        # SACR 的 Z 坐标通常在第 i+2 列 (X=i, Y=i+1, Z=i+2)
        # 我们取整个动作周期内 SACR 的 Z 轴平均位置作为跑道中心
        z_center = data.iloc[:, sacr_idx + 2].mean()
        print(f"检测到中线标记点 'SACR'，原地镜像中心 Z = {z_center:.2f}")
    else:
        # 如果没有 SACR，计算所有标记点的平均 Z 坐标
        z_cols = range(4, data.shape[1], 3)
        z_center = data.iloc[:, z_cols].mean().mean()
        print(f"未找到 SACR，使用全局平均值作为镜像中心 Z = {z_center:.2f}")

    # 4. 左右标签名对换 (L <-> R)
    new_labels = []
    for label in labels:
        if label.startswith('L'):
            new_labels.append('R' + label[1:])
        elif label.startswith('R'):
            new_labels.append('L' + label[1:])
        else:
            new_labels.append(label)
    header_lines[3] = '\t'.join(new_labels) + '\n'

    # 5. 执行原地镜像计算
    # 公式：Z_new = 2 * z_center - Z_old
    # 这个公式可以实现绕 z_center 轴翻转，从而保持在原位
    mirrored_data = data.copy()
    for col_idx in range(4, mirrored_data.shape[1], 3):
        z_old = mirrored_data.iloc[:, col_idx]
        mirrored_data.iloc[:, col_idx] = 2 * z_center - z_old

    # 6. 数据列重排 (确保数据内容与新的左右标签匹配)
    marker_to_idx = {label: i for i, label in enumerate(labels) if label and label not in ['Frame#', 'Time']}
    final_data = mirrored_data.copy()

    for i, nl in enumerate(new_labels):
        if nl in marker_to_idx:
            old_side = ('L' + nl[1:] if nl.startswith('R') else ('R' + nl[1:] if nl.startswith('L') else nl))
            if old_side in marker_to_idx:
                old_start = marker_to_idx[old_side]
                # 将原地镜像后的 X, Y, Z 数据移动到新标签对应的列
                final_data.iloc[:, i:i + 3] = mirrored_data.iloc[:, old_start:old_start + 3]

    # 7. 保存文件
    with open(output_path, 'w') as f:
        f.writelines(header_lines)
        final_data.to_csv(f, sep='\t', index=False, header=False, lineterminator='\n')

    print(f"✅ TRC 原地镜像完成！镜像文件已保存至: {output_path}")


# --- 执行 ---
input_trc = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\S20T2V31.trc'
output_trc = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\S20T2V31_Mirrored.trc'

mirror_trc_in_place_by_body_center(input_trc, output_trc)