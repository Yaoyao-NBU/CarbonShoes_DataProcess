import os
import shutil
import numpy as np
import ezc3d
from scipy.signal import butter, filtfilt


############################ 处理单个文件夹中的C3D文件 ##################################################################
def process_single_folder(current_folder, remove_str, output_folder):
    """
    处理单个文件夹：对其中的 C3D 文件重命名并复制到指定输出文件夹。
    不递归，不遍历上层文件夹。
    """
    # 创建输出目录
    os.makedirs(output_folder, exist_ok=True)

    # 处理当前文件夹的所有 C3D 文件
    for filename in os.listdir(current_folder):

        if filename.lower().endswith(".c3d"):
            new_name = filename.replace(remove_str, "").lstrip("_- ")

            old_path = os.path.join(current_folder, filename)
            new_path = os.path.join(output_folder, new_name)

            shutil.copy2(old_path, new_path)

            print(f"Processed: {old_path}  →  {new_path}")

############################ 滤波器 ###########################################################
def butter_filter(data, fs, filter_type, cutoff, order=4):
    """
    通用巴特沃斯滤波器
    data:        (N, dim) 数据
    fs:          采样率
    filter_type: 'low', 'high', 'band'
    cutoff:      数字或元组
    order:       滤波器阶数
    """
    nyquist = fs / 2

    if filter_type == 'band':
        Wn = [c / nyquist for c in cutoff]
    else:
        Wn = cutoff / nyquist

    b, a = butter(order, Wn, btype=filter_type)
    return filtfilt(b, a, data, axis=0)

############################# 滤波器接口 ################################################################
def filter_c3d_markers(c3d_path, fs, filter_choice, cutoff):
    """
    读取 C3D → 滤波 → 返回滤波后的 marker 数据

    filter_choice:
        1 = low-pass
        2 = high-pass
        3 = band-pass
        4 = no filter

    cutoff:
        low-pass: 一个数字（例如 6）
        high-pass: 一个数字（例如 10）
        band-pass: 一个元组（例如 (10, 50)）
    """

    c3d = ezc3d.c3d(c3d_path)

    markers = c3d['data']['points']       # shape = (4, Nmarkers, Nframes)
    markers = np.transpose(markers[:3], (2, 1, 0))  # → (frames, markers, xyz)

    output = np.zeros_like(markers)

    for i in range(markers.shape[1]):   # 每一个 marker
        marker_data = markers[:, i, :]  # (Nframes, 3)

        if filter_choice == 1:
            filtered = butter_filter(marker_data, fs, 'low', cutoff)

        elif filter_choice == 2:
            filtered = butter_filter(marker_data, fs, 'high', cutoff)

        elif filter_choice == 3:
            filtered = butter_filter(marker_data, fs, 'band', cutoff)

        elif filter_choice == 4:
            filtered = marker_data  # 不滤波

        else:
            raise ValueError("Filter choice must be 1, 2, 3, or 4")

        output[:, i, :] = filtered

    return output  # (frames, markers, 3)