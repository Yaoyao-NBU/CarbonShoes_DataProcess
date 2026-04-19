import numpy as np
from scipy.signal import butter, filtfilt
import pandas as pd
from io import StringIO
import os
import csv
import re
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

    print(f"✓ TRC filtered → {output_path}")
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
    df = pd.read_csv(input_path, sep="\t", skiprows=8)

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

    print(f"✓ MOT filtered → {output_path}")
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

    print(f"✓ Marker 前缀已移除并保存：{output_path}")
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
        print("⚠ 未找到 ground_force_vx/vy/vz 列，跳过处理")
    else:
        baseline_mask = (df[force_cols].abs().max(axis=1) < threshold)
        if baseline_mask.sum() < 5:
            print("⚠ 基线区域太少，可能没有空台阶段 → 跳过基线矫正")
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

    print(f"✓ 基线去除完成 → {output_path}")
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

    print(f"✓ TRC 扩充完成 → {output_path}")
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

    # --- 获取时间 ---
    #t_start = df.loc[contact.idxmax(), time_col]
    t_start = df.loc[contact.idxmax(), time_col] - 0.1  # 提前100ms，确保包含接触瞬间
    
    #t_end   = df.loc[contact[::-1].idxmax(), time_col]
    t_end   = df.loc[contact[::-1].idxmax(), time_col] + 0.1  # 延后100ms，确保包含离地瞬间

    # --- 通过采样频率计算帧数 ---
    #frame_start = int(t_start * fs) + 1
    frame_start = int(t_start * fs) + 21


    #frame_end   = int(t_end * fs) + 1
    frame_end   = int(t_end * fs) + 21

    print(f"✓ Stance detected: {t_start:.4f} – {t_end:.4f}, frames: {frame_start} – {frame_end}")
    return t_start, t_end, frame_start, frame_end


#####################################################截取力台文件#########################################################
def cut_sto_by_time(sto_path, output_path, t_start, t_end, fs=None):
    """
    按时间截取 STO 文件，并可选重新生成时间列（与 TRC 对齐）

    sto_path : 原始 STO 文件路径
    output_path : 输出截取后的 STO 文件路径
    t_start, t_end : 截取时间范围（秒）
    fs : 可选，采样频率。如果提供，会按等间隔生成时间列
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

    # --- Step3: 按时间截取 ---
    df_cut = df[(df[time_col] >= t_start) & (df[time_col] <= t_end )].reset_index(drop=True)

    # --- Step4: 尝试将所有列转为数值 ---
    for col in df_cut.columns:
        if df_cut[col].dtype == object:
            try:
                df_cut[col] = pd.to_numeric(df_cut[col])
            except ValueError:
                pass

    # --- Step5: 可选按 fs 重建时间列 ---
    n = len(df_cut)
    if fs is not None and n > 0:
        df_cut[time_col] = np.arange(n) / fs  # 从0开始等间隔生成时间列

    # --- Step6: 写回文件 ---
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

    print(f"✓ STO 截取完成 → {output_path}")
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

    print(f"✓ TRC 截取完成 → {output_path}")
    return output_path


#####################################################???????#############################################################





#####################################################??????#############################################################






#####################################################???????#############################################################





#####################################################???????#############################################################
