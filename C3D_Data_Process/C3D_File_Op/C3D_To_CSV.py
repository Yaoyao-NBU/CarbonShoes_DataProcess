import numpy as np
import ezc3d
import pandas as pd
##############################################################################################################
'''
我们需要知道C3D文件中如何通过二维数据储存的Marker数据！
C3D文件中又三种数据：Marker数据、Analgo数据（肌电等）、Force Plate数据
Marker数据通过ezc3d读取出来的格式是这样[4（数据维度），Point_Lable（数据点名字维度），Frame（帧率或者叫做时间维度）]
最后拼装数据是一排一排的进行拼装
'''
##############################################################################################################
# 读取 C3D 文件
c = ezc3d.c3d(r'C:\Users\admin\Desktop\DeepLearning\S1T1V11.c3d')

# 获取点数据，帧率多少，点的名称多少
points = c['data']['points']  # shape: (4, n_points, n_frames)
n_points = points.shape[1]
n_frames = points.shape[2]

# 获取帧率（用于计算时间）
try:
    point_rate = c['parameters']['POINT']['RATE']['value'][0]
except (KeyError, IndexError):
    point_rate = 100.0  # 默认帧率，避免报错

# 获取 marker 名称（如果有的话）
try:
    point_labels = [label.strip() for label in c['parameters']['POINT']['LABELS']['value']]
    # 确保数量匹配（有些文件可能填充了空标签）
    if len(point_labels) < n_points:
        point_labels += [f"Marker{i+1}" for i in range(len(point_labels), n_points)]
    else:
        point_labels = point_labels[:n_points]
except KeyError:
    point_labels = [f"Marker{i+1}" for i in range(n_points)]

# 构建列名：Frame, Time, Marker1_X, Marker1_Y, Marker1_Z, Marker2_X, ...
columns = ['Frame', 'Time']  # ← 新增 'Time' 列，其余逻辑不变
for label in point_labels:
    columns.extend([f"{label}_X", f"{label}_Y", f"{label}_Z"])

# 准备数据行
rows = []
for frame_idx in range(n_frames):
    row = [frame_idx + 1, frame_idx / point_rate]  # ← Frame 从 1 开始，Time = 帧索引 / 帧率
    for point_idx in range(n_points):
        x, y, z = points[0, point_idx, frame_idx], points[1, point_idx, frame_idx], points[2, point_idx, frame_idx]
        # 可选：如果点无效（第四维接近0），可用 NaN 表示
        if points[3, point_idx, frame_idx] <= 0.5:  # 通常 0 表示无效
            x, y, z = np.nan, np.nan, np.nan
        row.extend([x, y, z])
    rows.append(row)

# 创建 DataFrame 并保存为 CSV
df = pd.DataFrame(rows, columns=columns)
df.to_csv(r'C:\Users\admin\Desktop\DeepLearning\S1T1V11.csv', index=False, na_rep='')

print("✅ Points 已成功保存到 CSV 文件！")