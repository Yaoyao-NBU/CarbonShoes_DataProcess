import numpy as np
from scipy.signal import butter, filtfilt
import pandas as pd
from io import StringIO
import os
import csv
import re
from scipy.ndimage import gaussian_filter1d
######################################滤波器#######################################################
def butter_lowpass_filter(data, cutoff, fs, order=4):
    """
    Butterworth 低通滤波器
    data : 输入序列
    cutoff : 截止频率 (Hz)
    fs : 采样频率 (Hz)
    """
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

def gaussian_filter_stance_cop(data, window_size=7, sigma=None):
    """
    高斯滤波器，用于消除COP初期和结束的高频震荡
    只用于COP的stance阶段滤波

    参数:
        data : 输入序列（numpy array）
        window_size : 高斯窗口大小（默认7）
        sigma : 高斯核标准差，若为None则自动计算为 window_size/3

    返回:
        滤波后的序列

    原理:
        高斯滤波通过加权平均相邻数据点，权重呈高斯分布
        窗口大小为7时，有效消除短周期简谐振动成分
        相比低通滤波，高斯滤波在保持信号平滑性的同时
        能更好地保留COP的整体趋势特征
    """
    if sigma is None:
        sigma = window_size / 3.0

    # 使用零填充模式进行边界滤波
    # mode='nearest' 使用边界值填充，避免端点震荡
    filtered_data = gaussian_filter1d(data, sigma=sigma, mode='nearest', truncate=3.0)

    return filtered_data

#######################################文件处理滤波##############################################
def filter_trc(input_path, output_path, cutoff=6, fs=200):
    """
    对 TRC 文件进行低通滤波处理
    保留前 6 行标题结构（包括第 6 行的空行）
    数据部分无额外空行
    """

    # --- 读取前 6 行 header（含空行） ---
    header_lines = []
    with open(input_path, "r") as f:
        for _ in range(6):
            header_lines.append(next(f))

    # --- 正确读取数据：使用正则匹配空格和tab ---
    df = pd.read_csv(input_path, sep=r"\s+", engine="python", skiprows=6)

    # 确保路径存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    frame_col = df.columns[0]
    time_col = df.columns[1]

    data = df.copy()

    # --- 对所有 X,Y,Z 列滤波 ---
    for col in df.columns[2:]:
        if any(axis in col for axis in ["X", "Y", "Z"]):
            data[col] = butter_lowpass_filter(df[col].values, cutoff, fs)

    # --- 写回 ---
    with open(output_path, "w", newline="") as f:
        f.writelines(header_lines)
        data.to_csv(f, sep="\t", index=False)

    print(f"[OK] TRC filtered → {output_path}")
    return output_path

########################################Mot文件滤波#########################################
def filter_mot(input_path, output_path, cutoff=50, fs=1000):
    """
    对 OpenSim MOT/STO 文件进行巴特沃斯低通滤波
    保留前 8 行标题
    cutoff: 关节角 IK 6–8 Hz / GRF 30–50 Hz
    """

    # ---- 读取前 8 行标题 ----
    with open(input_path, 'r') as f:
        header_lines = [next(f) for _ in range(8)]

    # ---- 读取数据部分 ----
    #df = pd.read_csv(input_path, sep="\t", skiprows=8)  #Mot文件就使用这个
    df = pd.read_csv(input_path, sep="\t", skiprows=8)   #Sto文件使用这个！

    # 输出路径保证存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 第一列通常是 time
    time_col = df.columns[0]

    data = df.copy()

    # ---- 对数据列滤波 ----
    for col in df.columns:
        if col.lower() != time_col.lower():   # 不处理 time 列
            data[col] = butter_lowpass_filter(df[col].values, cutoff, fs)

    # ---- 写回文件：先写 header，再写数据 ----
    with open(output_path, "w", newline="") as f:   # ★关键修复，不要丢！
        # 写回前 8 行标题
        for line in header_lines:
            f.write(line)

        # 写回滤波后的数据
        data.to_csv(f, sep="\t", index=False)

    print(f"[OK] MOT filtered → {output_path}")
    return  output_path

##################################################去除不必要的点#####################################################################
def remove_marker_prefix_trc(input_path, output_path, header_lines_count=6, encoding="utf-8"):
    """
    读取 TRC 文件，去掉第 4 行（index=3）中每个 marker 名称冒号前的前缀（如 Pre_test_run:LSHO -> LSHO）,
    保留前 header_lines_count 行原样（包含空行），其余数据区保持不变。

    参数:
        input_path (str): 原始 trc 路径
        output_path (str): 输出 trc 路径（会自动创建父目录）
        header_lines_count (int): TRC 前几行为 header（默认 6）
        encoding (str): 文件编码（默认 utf-8）
    """
    # 读所有行
    with open(input_path, "r", encoding=encoding) as f:
        lines = f.readlines()

    if len(lines) < header_lines_count:
        raise ValueError(f"文件行数少于 header_lines_count={header_lines_count}，无法处理: {input_path}")

    # 保留 header 原样（列表）
    header_lines = lines[:header_lines_count]

    # 第4 行（index=3）是 marker 名称行（注意 header_lines_count 必须 >=4）
    marker_line = header_lines[3].rstrip("\n")

    # 自动检测分隔符（优先 tab、逗号），若 Sniffer 失败回退到 tab
    delimiter = "\t"
    try:
        dialect = csv.Sniffer().sniff(marker_line, delimiters="\t,; ")
        delimiter = dialect.delimiter
    except Exception:
        # 保守策略：优先检测 tab，再逗号，否则用 tab
        if "\t" in marker_line:
            delimiter = "\t"
        elif "," in marker_line:
            delimiter = ","
        else:
            delimiter = "\t"

    # 用检测到的 delimiter 切分
    cols = marker_line.split(delimiter)

    # 对每个列项去掉冒号前缀（但 Frame#/Time 一般没有冒号，也会被安全处理）
    cleaned_cols = []
    for item in cols:
        # 如果项为空（比如连续分隔），保留原样
        if item is None or item == "":
            cleaned_cols.append(item)
            continue
        # 删除前缀直到最后一个冒号（如 a:b:cNAME -> NAME）
        if ":" in item:
            cleaned_cols.append(item.split(":")[-1])
        else:
            cleaned_cols.append(item)

    # 恢复第 4 行（保留原分隔符）
    header_lines[3] = delimiter.join(cleaned_cols) + "\n"

    # 确保输出路径存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 写回：前 header_lines_count 行原样（含修改后的第4行），其余行按原样追加
    # 使用 newline="" 以避免跨平台多余空行问题
    with open(output_path, "w", encoding=encoding, newline="") as f:
        f.writelines(header_lines)
        # 将剩余的行（从 header_lines_count 开始）原样写出，不做任何改变
        f.writelines(lines[header_lines_count:])

    print(f"[OK] Marker 前缀已移除并保存：{output_path}")
    return output_path

####################################################力台基线归零###########################################################
def remove_baseline_force_sto(sto_path, output_path, threshold=20):
    """
    对 STO 文件去除 ground_force_vx/vy/vz 基线漂移
    保留前 8 行 header，不产生空行，不重复列名
    兼容旧版本 pandas
    """
    # --- Step1: 读取前 8 行 header ---
    with open(sto_path, "r", encoding="utf-8") as f:
        header_lines = [next(f) for _ in range(8)]
        label_line = header_lines[7].strip()
        labels = re.split(r'\s+', label_line)

    # --- Step2: 读取数据区 ---
    df = pd.read_csv(sto_path, sep=r'\s+', engine='python', skiprows=8, names=labels, header=None)

    # --- Step3: 找需要基线处理的列 ---
    force_cols = [c for c in labels if re.match(r".*_ground_force_v[xyz]$", c)]
    if not force_cols:
        print("[WARNING] 未找到 ground_force_vx/vy/vz 列，跳过处理")
    else:
        baseline_mask = (df[force_cols].abs().max(axis=1) < threshold)
        if baseline_mask.sum() < 5:
            print("[WARNING] 基线区域太少，可能没有空台阶段 → 跳过基线矫正")
        else:
            baseline_mean = df.loc[baseline_mask, force_cols].mean()
            df[force_cols] = df[force_cols] - baseline_mean
            print("基线均值：", baseline_mean)

    # --- Step4: 写回文件 ---
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        # 写 header
        for line in header_lines:
            f.write(line if line.endswith("\n") else line + "\n")
        # 写数据行
        for i, row in df.iterrows():
            f.write("\t".join(f"{v:.6f}" if isinstance(v, float) else str(v) for v in row.values) + "\n")

    print(f"[OK] 基线去除完成 → {output_path}")
    return output_path

#####################################################帧数拓展#############################################################
def expand_trc_single_frame(input_path, output_path, duration_sec=4):
    """
    将单帧 TRC 数据扩充为指定时间长度
    Frame 和 Time 列按顺序递增，其余列复制原始数据
    同时修改第三行的第3列(C3)和第8列(H3)为扩展后的总帧数
    """
    # --- 读取 header ---
    with open(input_path, "r") as f:
        header_lines = [next(f) for _ in range(6)]

    # --- 获取采样频率 ---
    # TRC 第三行通常包含“DataRate = xxx”，提取数字即可
    match = re.search(r'(\d+\.?\d*)', header_lines[2])
    if match:
        sample_rate = float(match.group(1))
    else:
        sample_rate = 100.0  # 默认 100Hz

    # --- 读取数据行，使用正则分隔空格 ---
    with open(input_path, "r") as f:
        all_lines = f.readlines()[6:]  # 第7行开始是数据

    data_rows = []
    for line in all_lines:
        line = line.strip()
        if line:  # 非空行
            # 按任意空格分列
            data_rows.append(re.split(r'\s+', line))

    if not data_rows:
        raise ValueError("读取数据为空，请检查TRC文件格式和分隔符！")

    # 转成 DataFrame
    df = pd.DataFrame(data_rows)

    # --- 扩充数据 ---
    total_frames = int(duration_sec * sample_rate)
    single_row = df.iloc[0].copy()

    expanded_rows = []
    for i in range(total_frames):
        new_row = single_row.copy()
        new_row[0] = str(i + 1)          # Frame 列
        new_row[1] = str(i / sample_rate)  # Time 列
        expanded_rows.append(new_row)

    expanded_df = pd.DataFrame(expanded_rows)

    # --- 修改 header 第3行的第3列(C3)和第8列(H3) ---
    line3_parts = re.split(r'\s+', header_lines[2].strip())
    if len(line3_parts) >= 8:
        line3_parts[2] = str(total_frames)  # C3
        line3_parts[7] = str(total_frames)  # H3
    header_lines[2] = "\t".join(line3_parts) + "\n"

    # --- 写回 TRC ---
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        # 写 header
        for line in header_lines:
            f.write(line if line.endswith("\n") else line + "\n")
        # 写数据行
        for i, row in expanded_df.iterrows():
            f.write("\t".join(row) + "\n")

    print(f"[OK] TRC 扩充完成 → {output_path}")
    return output_path

#####################################################获取力台数据中的Stance时间#############################################
def get_stance_time_from_sto(sto_path, fs=200, fz_pattern=r".*_ground_force_v[yz]$", threshold=20):
    """
    从 STO 力台数据中自动识别 stance 时间段
    返回 t_start, t_end, frame_start, frame_end
    frame_start/frame_end 通过采样频率计算，Frame 从1开始
    """
    import re, pandas as pd

    # --- 读取 header ---
    with open(sto_path, "r", encoding="utf-8") as f:
        header_lines = [next(f) for _ in range(8)]
        label_line = header_lines[7].strip()
        labels = re.split(r'\s+', label_line)

    # --- 读取数据 ---
    df = pd.read_csv(
        sto_path,
        sep=r'\s+',
        engine='python',
        skiprows=8,
        names=labels,
        header=None
    )

    time_col = labels[0]   # 第一列通常是 time
    force_cols = [c for c in labels if re.match(fz_pattern, c)]
    if not force_cols:
        raise ValueError("❌ 未找到垂直方向 ground_force_v 列")

    # --- 强制列转为数值，非数字置 NaN ---
    for col in force_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- stance 判断 ---
    fz = df[force_cols].abs().max(axis=1)
    contact = fz > threshold
    if contact.sum() == 0:
        raise ValueError("❌ 未检测到 stance（Fz 全部低于阈值）")

    # --- 获取实际 stance 时间（不含补偿） ---
    t_stance_start = df.loc[contact.idxmax(), time_col]
    t_stance_end = df.loc[contact[::-1].idxmax(), time_col]

    # --- 获取包含补偿的时间 ---
    t_start = t_stance_start - 0.1  # 预留前0.1秒补偿
    t_end = t_stance_end + 0.1      # 预留后0.1秒补偿

    # --- 通过采样频率计算帧数 ---
    frame_start = int(t_start * fs) + 1
    frame_end = int(t_end * fs) + 1

    print(f"[OK] Stance detected: {t_start:.4f} – {t_end:.4f}, frames: {frame_start} – {frame_end}")
    return t_start, t_end, frame_start, frame_end, t_stance_start, t_stance_end

#####################################################截取力台文件#########################################################
def cut_sto_by_time(sto_path, output_path, t_start, t_end, fs=None, t_stance_start=None, t_stance_end=None):
    """
    按时间截取 STO 文件，并可选重新生成时间列（与 TRC 对齐）

    支持将补充帧（t_stance_start之前、t_stance_end之后）的力台数据（Fx-Fz, Copx-Copz, torque）归零

    sto_path : 原始 STO 文件路径
    output_path : 输出截取后的 STO 文件路径
    t_start, t_end : 截取时间范围（秒，含补偿）
    fs : 可选，采样频率。如果提供，会按等间隔生成时间列
    t_stance_start, t_stance_end : 实际 stance 时间范围（不含补偿），用于确定哪些帧需要归零
    """
    import os, numpy as np, pandas as pd, re

    # --- Step1: 读取前8行 header ---
    with open(sto_path, "r", encoding="utf-8") as f:
        header_lines = [next(f) for _ in range(8)]
        label_line = header_lines[7].strip()
        labels = re.split(r'\s+', label_line)

    # --- Step2: 读取数据 ---
    df = pd.read_csv(
        sto_path,
        sep=r'\s+',
        engine='python',
        skiprows=8,
        names=labels,
        header=None
    )

    time_col = labels[0]

    # --- Step3: 按时间截取 ---（补偿时间）
    df_cut = df[(df[time_col] >= t_start) & (df[time_col] <= t_end )].reset_index(drop=True)

    # --- Step4: 尝试将所有列转为数值 ---
    for col in df_cut.columns:
        if df_cut[col].dtype == object:
            try:
                df_cut[col] = pd.to_numeric(df_cut[col])
            except ValueError:
                pass

    # --- Step5: 将补充帧的力数据（Fx-Fz, Copx-Copz, torque）归零 ---
    if t_stance_start is not None and t_stance_end is not None:
        # 找到力相关的列：ground_force_vx, ground_force_vy, ground_force_vz, ground_force_px, ground_force_py, ground_force_pz, ground_force_torque
        force_cols = [c for c in labels if re.match(r".*ground_force_v[xyz]$", c)]  # Fx-Fz
        cop_cols = [c for c in labels if re.match(r".*ground_force_p[xyz]$", c)]   # Copx-Copz
        torque_cols = [c for c in labels if "torque" in c.lower()]  # torque

        zero_cols = force_cols + cop_cols + torque_cols

        # 将 t_stance_start 之前的补充帧归零（包括t_stance_start这一帧）
        padding_mask = (df_cut[time_col] <= t_stance_start)
        for col in zero_cols:
            if col in df_cut.columns:
                df_cut.loc[padding_mask, col] = 0

        # 将 t_stance_end 之后的补充帧归零
        padding_mask = (df_cut[time_col] > t_stance_end)
        for col in zero_cols:
            if col in df_cut.columns:
                df_cut.loc[padding_mask, col] = 0

        print(f"[OK] 已将补充帧的力台数据归零（时间范围: {t_start:.4f}-{t_stance_start:.4f} 和 {t_stance_end:.4f}-{t_end:.4f}）")

    # --- Step6: 可选按 fs 重建时间列 ---
    n = len(df_cut)
    if fs is not None and n > 0:
        df_cut[time_col] = np.arange(n) / fs  # 从0开始等间隔生成时间列

    # --- Step7: 写回文件 ---
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        # 写 header
        for line in header_lines:
            f.write(line if line.endswith("\n") else line + "\n")
        # 写数据
        for _, row in df_cut.iterrows():
            f.write(
                "\t".join(
                    f"{v:.6f}" if isinstance(v, (float, int, np.floating)) else str(v)
                    for v in row.values
                ) + "\n"
            )

    print(f"[OK] STO 截取完成 → {output_path}")
    return output_path

#####################################################截取Marker文件#######################################################
def cut_trc_by_time(trc_path, output_path, t_start, t_end, fs=None):
    """
    按时间截取 TRC 文件，只处理第7行开始的数据。
    前6行 header 保留原样。
    fs : 可选，TRC采样频率，如果提供，会重新生成Time列
    截取后自动修改第3行第3列(C3)和第8列(H3)为总帧数
    """
    import os
    import pandas as pd

    # --- 读取前6行 header ---
    with open(trc_path, "r") as f:
        header_lines = [next(f) for _ in range(6)]

    # --- 读取第7行及之后的数据 ---
    df = pd.read_csv(trc_path, sep=r"\s+", engine="python", skiprows=6, header=None)

    # 第一列 Frame，第二列 Time
    frame_col = 0
    time_col = 1

    # 转 Time 列为数值
    df[time_col] = pd.to_numeric(df[time_col], errors='coerce')

    # 按时间截取
    df_cut = df[(df[time_col] >= t_start ) & (df[time_col] <= t_end )].reset_index(drop=True)

    # 重建 Frame / Time
    n = len(df_cut)
    df_cut[frame_col] = range(1, n + 1)
    if fs is not None:
        df_cut[time_col] = [i/fs for i in range(n)]

    # --- 修改 header 第3行第3列(C3)和第8列(H3)为总帧数 ---
    if n > 0:
        line3_parts = header_lines[2].rstrip("\n").split()
        if len(line3_parts) >= 8:
            line3_parts[2] = str(n)  # 第3列 C3
            line3_parts[7] = str(n)  # 第8列 H3
            header_lines[2] = "\t".join(line3_parts) + "\n"

    # --- 写回 TRC 文件 ---
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="") as f:
        # 写前6行 header
        f.writelines(header_lines)
        # 写数据
        df_cut.to_csv(f, sep="\t", index=False, header=False)

    print(f"[OK] TRC 截取完成 → {output_path}")
    return output_path

#####################################################截取并滤波STO文件中的COP数据#########################################################
def cut_sto_with_gaussian_filter_cop(sto_path, output_path, t_start, t_end, t_stance_start, t_stance_end,
                                     fs=200, window_size=7, sigma=None):
    """
    截取STO文件并对COP数据在stance阶段应用高斯滤波
    补充帧的力台数据（Fx-Fz, Copx-Copz, torque）归零

    参数:
        sto_path: 原始STO文件路径
        output_path: 输出路径
        t_start, t_end: 截取时间范围（含补偿，秒）
        t_stance_start, t_stance_end: 实际stance时间范围（不含补偿，秒）
        fs: 采样频率
        window_size: 高斯滤波窗口大小
        sigma: 高斯核标准差

    返回:
        output_path
    """
    import os, pandas as pd, re

    # --- 读取header ---
    with open(sto_path, "r", encoding="utf-8") as f:
        header_lines = [next(f) for _ in range(8)]
        label_line = header_lines[7].strip()
        labels = re.split(r'\s+', label_line)

    # --- 读取数据 ---
    df = pd.read_csv(
        sto_path,
        sep=r'\s+',
        engine='python',
        skiprows=8,
        names=labels,
        header=None
    )

    time_col = labels[0]

    # --- 按时间截取 ---
    df_cut = df[(df[time_col] >= t_start) & (df[time_col] <= t_end)].reset_index(drop=True)

    # --- 转为数值 ---
    for col in df_cut.columns:
        if df_cut[col].dtype == object:
            try:
                df_cut[col] = pd.to_numeric(df_cut[col])
            except ValueError:
                pass

    # --- 识别力台相关列 ---
    force_cols = [c for c in labels if re.match(r".*ground_force_v[xyz]$", c)]
    cop_cols = [c for c in labels if re.match(r".*ground_force_p[xyz]$", c)]
    torque_cols = [c for c in labels if "torque" in c.lower()]
    zero_cols = force_cols + cop_cols + torque_cols

    # --- 将补充帧的力台数据归零 ---
    # t_stance_start之前
    padding_mask = (df_cut[time_col] < t_stance_start)
    for col in zero_cols:
        if col in df_cut.columns:
            df_cut.loc[padding_mask, col] = 0

    # t_stance_end之后
    padding_mask = (df_cut[time_col] > t_stance_end)
    for col in zero_cols:
        if col in df_cut.columns:
            df_cut.loc[padding_mask, col] = 0

    # --- 对stance阶段的COP数据应用高斯滤波 ---
    stance_mask = (df_cut[time_col] >= t_stance_start) & (df_cut[time_col] <= t_stance_end)

    for col in cop_cols:
        if col in df_cut.columns:
            # 提取stance阶段的数据
            stance_data = df_cut.loc[stance_mask, col].values

            if len(stance_data) >= window_size:
                # 应用高斯滤波
                filtered_stance = gaussian_filter_stance_cop(stance_data, window_size=window_size, sigma=sigma)

                # 将滤波后的数据写回原DataFrame
                df_cut.loc[stance_mask, col] = filtered_stance

    print(f"[OK] 已对COP数据应用高斯滤波（窗口大小: {window_size}）")
    print(f"[OK] 已将补充帧的力台数据归零")

    # --- 重建时间列 ---
    n = len(df_cut)
    df_cut[time_col] = np.arange(n) / fs

    # --- 写回文件 ---
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf") as f:
        for line in header_lines:
            f.write(line if line.endswith("\n") else line + "\n")

        for _, row in df_cut.iterrows():
            f.write(
                "\t".join(
                    f"{v:.6f}" if isinstance(v, (float, int, np.floating)) else str(v)
                    for v in row.values
                ) + "\n"
            )

    print(f"[OK] STO 截取并滤波完成 → {output_path}")
    return output_path

#####################################################COPx异常值处理函数#############################################################
def process_copx_outliers(data_dict, distance_threshold=0.1, t_stance_start=None, t_stance_end=None):
    """
    对stance阶段的COPx和COPz数据进行异常值处理：距离中位数超过阈值的点替换为中位数
    只处理真实stance阶段的数据，padding_frames保持归零状态

    参数:
        data_dict : 包含COPx和COPz数据的字典，应包含以下键：
            - 'time': 时间序列
            - 'COPx': COPx位置序列
            - 'COPy': COPy位置序列（可选）
            - 'COPz': COPz位置序列
        distance_threshold : 距离中位数的绝对距离阈值（默认0.1米）
        t_stance_start : 真实stance开始时间（不含补偿）
        t_stance_end : 真实stance结束时间（不含补偿）

    返回:
        处理后的数据字典

    原理:
        1. 根据时间范围识别真实stance阶段的数据点
        2. 分别计算真实stance阶段COPx和COPz的中位数
        3. 计算stance阶段每个点到各自中位数的绝对距离
        4. 将距离超过阈值（0.3米）的点标记为异常值
        5. 将异常值替换为各自的中位数
        6. padding_frames区域保持归零状态不变

    注意:
        - 只对真实stance阶段的COPx和COPz数据进行异常值处理
        - 如果stance阶段值距离各自中位数超过0.3米，则该点替换为中位数
        - padding_frames区域的COPx和COPz数据保持归零不变
        - 其他数据（Fy, COPy）保持不变
    """
    # 创建输出字典的深拷贝
    import copy
    result = copy.deepcopy(data_dict)

    # 提取时间、COPx和COPz数据
    time_data = result['time'].copy()
    copx_data = result['COPx'].copy()
    copz_data = result['COPz'].copy()

    # 识别真实stance阶段的数据点
    if t_stance_start is not None and t_stance_end is not None:
        stance_mask = (time_data >= t_stance_start) & (time_data <= t_stance_end)
    else:
        # 如果没有提供stance时间范围，处理全部数据
        stance_mask = np.ones(len(time_data), dtype=bool)

    # 提取真实stance阶段的数据
    copx_stance = copx_data[stance_mask]
    copz_stance = copz_data[stance_mask]

    if len(copx_stance) == 0:
        print("[WARNING] 警告：真实stance阶段没有数据，跳过异常值处理")
        return result, {
            'copx_median': 0,
            'copz_median': 0,
            'outlier_count': 0,
            'outlier_ratio': 0
        }

    # Step 1: 计算真实stance阶段COPx和COPz的中位数
    copx_median = np.median(copx_stance)
    copz_median = np.median(copz_stance)

    # Step 2: 计算stance阶段每个点到各自中位数的绝对距离
    copx_distance_to_median = np.abs(copx_stance - copx_median) #这里的情况没有考虑Cop为负值的情况！
    copz_distance_to_median = np.abs(copz_stance - copz_median)

    # Step 3: 识别异常值：距离超过阈值（0.3米）的点（仅在stance阶段内）
    copx_stance_outlier_mask = (copx_distance_to_median > distance_threshold)
    copz_stance_outlier_mask = (copz_distance_to_median > distance_threshold)

    # Step 4: 创建完整的outlier_mask（默认为False）
    copx_outlier_mask = np.zeros(len(time_data), dtype=bool)
    copz_outlier_mask = np.zeros(len(time_data), dtype=bool)

    # 将stance阶段的outlier_mask设置为识别到的异常值
    copx_outlier_mask[stance_mask] = copx_stance_outlier_mask
    copz_outlier_mask[stance_mask] = copz_stance_outlier_mask

    # Step 5: 将异常值替换为中位数（仅在stance阶段内）
    result['COPx'][copx_outlier_mask] = copx_median
    result['COPz'][copz_outlier_mask] = copz_median

    # 统计信息
    copx_outlier_count = np.sum(copx_stance_outlier_mask)
    copz_outlier_count = np.sum(copz_stance_outlier_mask)
    total_stance_count = len(copx_stance)
    copx_outlier_ratio = copx_outlier_count / total_stance_count * 100 if total_stance_count > 0 else 0
    copz_outlier_ratio = copz_outlier_count / total_stance_count * 100 if total_stance_count > 0 else 0

    return result, {
        'copx_median': copx_median,
        'copz_median': copz_median,
        'outlier_count': copx_outlier_count + copz_outlier_count,
        'outlier_ratio': (copx_outlier_ratio + copz_outlier_ratio) / 2
    }

#####################################################COPx/COPz线性趋势异常值填补函数##################################################
def process_cop_outliers_linear(data_dict, distance_threshold=0.08, jump_threshold=0.03,
                                 t_stance_start=None, t_stance_end=None):
    """
    对stance阶段的COPx和COPz进行异常值检测与线性趋势填补

    双重检测机制:
      1. 中位数距离检测 — 值偏离中位数超过 distance_threshold 的点
      2. 帧间跳变检测 — 相邻帧变化超过 jump_threshold 的点
         （正常COP帧间变化约1-3mm，异常跳变通常>30mm）

    填补策略: 用正常点拟合线性趋势 y = k*t + b，异常点按趋势值填补

    参数:
        data_dict       : 包含 'time', 'COPx', 'COPz' 键的数据字典
        distance_threshold : 距中位数的绝对距离阈值（米，默认0.08）
        jump_threshold  : 帧间跳变阈值（米，默认0.03，即30mm）
        t_stance_start  : 真实stance开始时间（不含补偿）
        t_stance_end    : 真实stance结束时间（不含补偿）

    返回:
        (result_dict, info_dict)
    """
    import copy
    result = copy.deepcopy(data_dict)

    time_data = result['time'].copy()
    copx_data = result['COPx'].copy()
    copz_data = result['COPz'].copy()

    # 识别真实stance阶段
    if t_stance_start is not None and t_stance_end is not None:
        stance_mask = (time_data >= t_stance_start) & (time_data <= t_stance_end)
    else:
        stance_mask = np.ones(len(time_data), dtype=bool)

    copx_stance = copx_data[stance_mask]
    copz_stance = copz_data[stance_mask]

    if len(copx_stance) == 0:
        print("[WARNING] 真实stance阶段没有数据，跳过异常值处理")
        return result, {'copx_outlier_count': 0, 'copz_outlier_count': 0}

    t_stance = time_data[stance_mask]

    for col_name, stance_vals in [('COPx', copx_stance), ('COPz', copz_stance)]:
        # --- 检测1: 中位数距离检测 ---
        median_val = np.median(stance_vals)
        dist_outlier = np.abs(stance_vals - median_val) > distance_threshold

        # --- 检测2: 帧间跳变检测 ---
        # 计算相邻帧的绝对差值，两端各补False保证长度一致
        diffs = np.abs(np.diff(stance_vals))
        jump_outlier = np.zeros(len(stance_vals), dtype=bool)
        jump_outlier[1:] |= diffs > jump_threshold      # 后帧跳变
        jump_outlier[:-1] |= diffs > jump_threshold      # 前帧跳变（两端都标记）

        # 合并两种检测结果
        outlier_mask = dist_outlier | jump_outlier
        outlier_count = np.sum(outlier_mask)
        dist_only = np.sum(dist_outlier)
        jump_only = outlier_count - dist_only  # 仅被跳变检测捕获的数量

        if outlier_count == 0:
            print(f"  {col_name}: 无异常值")
            continue

        print(f"  {col_name}: 检测到 {outlier_count} 帧异常"
              f"（中位数距离: {dist_only}帧, 帧间跳变额外: {jump_only}帧）")

        # --- 用正常点拟合线性趋势 y = k*t + b ---
        normal_mask = ~outlier_mask
        if np.sum(normal_mask) < 2:
            # 正常点不足，退化为中值替换
            result[col_name][stance_mask] = np.where(outlier_mask, median_val, stance_vals)
            print(f"  {col_name}: 正常点不足2个，退化为中值替换")
            continue

        k, b = np.polyfit(t_stance[normal_mask], stance_vals[normal_mask], 1)
        linear_vals = k * t_stance + b

        # 按线性趋势填补异常值
        filled_vals = np.where(outlier_mask, linear_vals, stance_vals)
        result[col_name][stance_mask] = filled_vals

        print(f"  {col_name}: 线性趋势 k={k:.4f}m/s, b={b:.4f}m, 填补 {outlier_count}帧")

    return result, {
        'copx_outlier_count': int(np.sum(copx_data[stance_mask] != result['COPx'][stance_mask])),
        'copz_outlier_count': int(np.sum(copz_data[stance_mask] != result['COPz'][stance_mask]))
    }

#####################################################修改力台单位参数#############################################################
def fix_sto_ground_force_units(sto_path, output_path):
    """
    修改 STO 文件中的 ground_force_p 单位参数
    将 ground_force_p=mm 改为 ground_force_p=m

    参数:
        sto_path (str): 原始 STO 文件路径
        output_path (str): 输出 STO 文件路径
    """
    # 读取所有行
    with open(sto_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 查找并修改 ground_force_p=mm 为 ground_force_p=m
    modified = False
    for i, line in enumerate(lines):
        if "ground_force_p=mm" in line:
            lines[i] = line.replace("ground_force_p=mm", "ground_force_p=m")
            modified = True
            print(f"[OK] 第{i+1}行: ground_force_p=mm → ground_force_p=m")

    if not modified:
        print("[WARNING] 未找到 ground_force_p=mm，文件可能已正确")
    else:
        # 写回文件
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)

        print(f"[OK] 单位修正完成 → {output_path}")

    return output_path

#####################################################基于Peak检测Stance时间#############################################
def get_stance_time_from_sto_with_peak(sto_path, fs=200, fz_pattern=r".*_ground_force_v[yz]$", threshold=20, padding_frames=0):
    """
    从 STO 力台数据中通过 Peak 检测 stance 时间段
    先找到中间的 Peak 值，然后向两边找阈值

    参数:
        sto_path: STO 文件路径
        fs: 采样频率
        fz_pattern: 垂直力列名匹配模式
        threshold: 阈值
        padding_frames: 补偿帧数（前后各补充）

    返回:
        t_start, t_end, frame_start, frame_end, t_stance_start, t_stance_end
    """
    import re, pandas as pd

    # --- 读取 header ---
    with open(sto_path, "r", encoding="utf-8") as f:
        header_lines = [next(f) for _ in range(8)]
        label_line = header_lines[7].strip()
        labels = re.split(r'\s+', label_line)

    # --- 读取数据 ---
    df = pd.read_csv(
        sto_path,
        sep=r'\s+',
        engine='python',
        skiprows=8,
        names=labels,
        header=None
    )

    time_col = labels[0]
    force_cols = [c for c in labels if re.match(fz_pattern, c)]
    if not force_cols:
        raise ValueError("❌ 未找到垂直方向 ground_force_v 列")

    # --- 强制列转为数值 ---
    for col in force_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- 计算垂直力 ---
    fz = df[force_cols].abs().max(axis=1)

    # --- 找到 Peak 位置（最大值索引）---
    peak_idx = fz.idxmax()
    peak_value = fz[peak_idx]

    if peak_value <= threshold:
        raise ValueError("❌ Peak 值低于阈值，无法检测 stance")

    # --- 从 Peak 向左搜索第一个小于阈值的点 ---
    left_idx = peak_idx
    for i in range(peak_idx, -1, -1):
        if fz[i] < threshold:
            left_idx = i
            break

    # --- 从 Peak 向右搜索第一个小于阈值的点 ---
    right_idx = peak_idx
    for i in range(peak_idx, len(fz)):
        if fz[i] < threshold:
            right_idx = i
            break

    # --- 获取实际 stance 时间（不含补偿）---
    t_stance_start = df.loc[left_idx, time_col]
    t_stance_end = df.loc[right_idx, time_col]

    # --- 计算补偿时间 ---
    padding_time = padding_frames / fs
    t_start = t_stance_start - padding_time
    t_end = t_stance_end + padding_time

    # --- 通过采样频率计算帧数 ---
    padding_frames_start = int(t_start * fs) + 1
    padding_frames_end = int(t_end * fs) + 1

    # --- 计算补偿帧数 ---
    frame_stance_start= int(t_stance_start * fs)
    frame_stance_end = int(t_stance_end * fs)


    print(f"[OK] Peak detected: idx={peak_idx}, value={peak_value:.2f}N")
    print(f"[OK] Stance detected: {t_start:.4f} - {t_end:.4f}, frames: {frame_stance_start} - {frame_stance_end}")
    print(f"[OK] Actual stance (without padding): {t_stance_start:.4f} - {t_stance_end:.4f}")
    print(f"[OK] Padding: {padding_frames} frames = {padding_time:.4f}s")

    return t_start, t_end, frame_stance_start, frame_stance_end,padding_frames_start,padding_frames_end,t_stance_start, t_stance_end, peak_idx, peak_value

#####################################################基于斜率的COP异常值纠正函数#########################################################
def process_cop_outliers_slope(data_dict, middle_ratio=0.3, rate_multiplier=2.0,
                                t_stance_start=None, t_stance_end=None):
    """
    基于stance中间部分斜率的COPx/COPz异常值纠正

    原理:
      1. 取stance中间部分（如30%~70%），线性拟合得到通用斜率k
      2. 从中间部分向两端遍历，若某帧变化率 > rate_multiplier * k，视为异常
      3. 异常帧用 上一正常值 + k * dt 替换（保持线性趋势连续性）
      4. padding帧不处理

    参数:
        data_dict       : 包含 'time', 'COPx', 'COPz' 键的数据字典
        middle_ratio    : 中间部分占比（默认0.3，即取中间30%~70%区间）
        rate_multiplier : 变化率异常判定倍数（默认2.0，即变化率超过通用斜率2倍为异常）
        t_stance_start  : 真实stance开始时间（不含补偿）
        t_stance_end    : 真实stance结束时间（不含补偿）

    返回:
        (result_dict, info_dict)
        info_dict包含: copx_slope, copz_slope, copx_outlier_count, copz_outlier_count
    """
    import copy
    result = copy.deepcopy(data_dict)

    time_data = result['time'].copy()
    copx_data = result['COPx'].copy()
    copz_data = result['COPz'].copy()

    # 识别真实stance阶段（不含padding）
    if t_stance_start is not None and t_stance_end is not None:
        stance_mask = (time_data >= t_stance_start) & (time_data <= t_stance_end)
    else:
        stance_mask = np.ones(len(time_data), dtype=bool)

    # 获取stance阶段的索引和时间
    stance_indices = np.where(stance_mask)[0]
    t_stance = time_data[stance_mask]
    copx_stance = copx_data[stance_mask].copy()
    copz_stance = copz_data[stance_mask].copy()

    n_stance = len(stance_indices)
    info = {'copx_slope': 0.0, 'copz_slope': 0.0,
            'copx_outlier_count': 0, 'copz_outlier_count': 0}

    if n_stance < 10:
        print("[WARNING] stance帧数过少，跳过斜率纠正")
        return result, info

    # 计算中间部分的范围
    margin = int(n_stance * middle_ratio / 2)
    mid_start = margin
    mid_end = n_stance - margin

    if mid_end - mid_start < 5:
        print("[WARNING] 中间部分帧数不足，跳过斜率纠正")
        return result, info

    # 中间部分索引
    mid_indices = np.arange(mid_start, mid_end)
    t_mid = t_stance[mid_indices]

    # 对COPx和COPz分别处理
    for col_name, stance_vals in [('COPx', copx_stance), ('COPz', copz_stance)]:
        # Step1: 用中间部分拟合线性趋势，获取通用斜率k
        mid_vals = stance_vals[mid_indices]
        k, b = np.polyfit(t_mid, mid_vals, 1)

        print(f"  {col_name}: 中间部分斜率 k={k:.6f} m/s")

        # Step2: 从中间向两端遍历，检测异常值
        corrected = stance_vals.copy()

        # 计算帧间时间间隔（假设等间隔，取中位数）
        dt = np.median(np.diff(t_stance)) if len(t_stance) > 1 else 1.0 / 200
        # 通用帧间变化量
        expected_delta = abs(k * dt)
        # 异常阈值：变化率超过通用斜率的rate_multiplier倍
        outlier_delta = expected_delta * rate_multiplier

        # 向左遍历（从中间部分左边界向stance起始）
        for i in range(mid_start - 1, -1, -1):
            actual_delta = abs(corrected[i] - corrected[i + 1])
            if actual_delta > outlier_delta:
                # 异常帧：用右邻值 - k*dt 修正（向左递推）
                corrected[i] = corrected[i + 1] - k * dt
                info[f'{col_name.lower()}_outlier_count'] += 1

        # 向右遍历（从中间部分右边界向stance结束）
        for i in range(mid_end, n_stance):
            actual_delta = abs(corrected[i] - corrected[i - 1])
            if actual_delta > outlier_delta:
                # 异常帧：用左邻值 + k*dt 修正（向右递推）
                corrected[i] = corrected[i - 1] + k * dt
                info[f'{col_name.lower()}_outlier_count'] += 1

        # Step3: 写回结果
        result[col_name][stance_mask] = corrected
        info[f'{col_name.lower()}_slope'] = k

        count = info[f'{col_name.lower()}_outlier_count']
        print(f"  {col_name}: 纠正 {count} 帧异常值")

    return result, info

#####################################################???????#############################################################
