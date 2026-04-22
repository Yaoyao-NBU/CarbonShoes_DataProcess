"""
Stance力学数据截取 + COP线性趋势异常值填补 + 绘图工具 (2号力台)

处理流程:
  1. Peak检测获取stance时间段
  2. 截取STO文件（补充帧归零）
  3. 对COPx/COPz异常值用线性趋势填补（非中值替换）
  4. 写回截取后的STO文件
  5. 绘制对比图（原始 vs 填补后）和组合图
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import Data_ProcessFunction as DPF
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
import re

# ==========================================
# 配置参数
# ==========================================
source_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\input'
output_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\output\output_plots_linear'
output_cut_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\output\output_cut_sto_linear'

fs_sto = 200                     # 采样频率 (Hz)
threshold = 30                   # 力阈值 (N)
fz_pattern = r".*_ground_force_v[yz]$"
padding_frames = 20
padding_time = padding_frames / fs_sto

# COP异常值检测与填补参数
distance_threshold = 0.08        # 距离中位数阈值（米），超过则视为异常值
jump_threshold = 0.03            # 帧间跳变阈值（米），相邻帧变化超过此值视为异常

# 图像参数
dpi = 600

# ==========================================
# 全局样式
# ==========================================
rcParams['font.family'] = 'Arial'
rcParams['font.size'] = 10
rcParams['lines.linewidth'] = 1.0
rcParams['figure.dpi'] = dpi
rcParams['savefig.dpi'] = dpi
rcParams['savefig.bbox'] = 'tight'
rcParams['savefig.pad_inches'] = 0.1

# ==========================================
# 辅助函数
# ==========================================
def read_sto_header(sto_path):
    """读取STO文件前8行header和列名"""
    with open(sto_path, "r", encoding="utf-8") as f:
        header_lines = [next(f) for _ in range(8)]
    labels = header_lines[7].strip().split()
    return header_lines, labels


def read_sto_data(sto_path, labels):
    """读取STO文件数据部分"""
    return pd.read_csv(sto_path, sep='\t', skiprows=8, names=labels, header=None)


def extract_force_plate_2(df, labels):
    """提取2号力台的Fy/COPx/COPz数据"""
    n = len(df)
    data_dict = {'time': df[labels[0]].values}
    for key, col in [('Fy', '2_ground_force_vy'), ('COPx', '2_ground_force_px'),
                     ('COPy', '2_ground_force_py'), ('COPz', '2_ground_force_pz')]:
        data_dict[key] = df[col].values if col in df.columns else np.zeros(n)
    data_dict['name'] = ''
    return data_dict


def write_sto(output_path, header_lines, df):
    """将DataFrame写回STO文件（保留原header）"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for line in header_lines:
            f.write(line if line.endswith("\n") else line + "\n")
        for _, row in df.iterrows():
            f.write("\t".join(
                f"{v:.6f}" if isinstance(v, (float, int, np.floating)) else str(v)
                for v in row.values
            ) + "\n")


def plot_single_file(file_data, output_dir):
    """为单个文件绘制 Fy/COPx/COPz 三子图组合图"""
    configs = [
        ('Fy', 'Mediolateral Force (Fy)', 'Force (N)'),
        ('COPx', 'Anteroposterior COPx (Linear Filled)', 'Position (m)'),
        ('COPz', 'Vertical COPz (Linear Filled)', 'Position (m)')
    ]

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f"{file_data['name']} — Force Plate 2 (Linear Trend Fill)",
                 fontsize=14, fontweight='bold')

    for idx, (var, title, ylabel) in enumerate(configs):
        ax = axes[idx]
        ax.plot(file_data['time'], file_data[var], linewidth=1.2, color='blue', alpha=0.9)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12, loc='left')
        ax.grid(True, linestyle='--', alpha=0.6)

    axes[-1].set_xlabel('Time (s)', fontsize=12)
    plt.tight_layout()

    path = os.path.join(output_dir, f"{file_data['name']}_combined.png")
    plt.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close()
    return path


def plot_trial_overlay(trial_name, files_data, output_dir):
    """为同一个trial的所有文件绘制叠加折线图（Fy/COPx/COPz 各一张）"""
    configs = [
        ('Fy', 'Ground Reaction Force - Fy', 'Force (N)'),
        ('COPx', 'Center of Pressure - COPx (Linear Filled)', 'Position (m)'),
        ('COPz', 'Center of Pressure - COPz (Linear Filled)', 'Position (m)')
    ]

    saved = []
    for var, title, ylabel in configs:
        fig, ax = plt.subplots(figsize=(12, 6.75))
        for i, fd in enumerate(files_data):
            ax.plot(fd['time'], fd[var], label=fd['name'],
                    color=plt.cm.tab10(i % 10), linewidth=0.8, alpha=0.8)
        ax.set_title(f"{trial_name} — {title} (Force Plate 2)", fontsize=14, fontweight='bold')
        ax.set_xlabel('Time (s)', fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=8, framealpha=0.8)
        plt.tight_layout()

        path = os.path.join(output_dir, f'{trial_name}_{var}.png')
        plt.savefig(path, dpi=dpi, bbox_inches='tight')
        plt.close()
        saved.append(path)
    return saved


# ==========================================
# 主处理逻辑
# ==========================================
os.makedirs(output_dir, exist_ok=True)
os.makedirs(output_cut_dir, exist_ok=True)

print("=" * 60)
print("Stance数据截取 + COP线性趋势异常值填补 + 绘图")
print("=" * 60)
print(f"源目录:       {source_dir}")
print(f"输出图像目录: {output_dir}")
print(f"输出截取目录: {output_cut_dir}")
print(f"力阈值:       {threshold}N")
print(f"补偿帧数:     {padding_frames} 帧 = {padding_time:.4f}s")
print(f"异常值阈值:   {distance_threshold}m (中位数距离)")
print(f"跳变阈值:     {jump_threshold*1000:.0f}mm (帧间跳变)")
print("=" * 60)

# --- 收集sto文件并按trial分组 ---
trial_data = {}
for root, dirs, files in os.walk(source_dir):
    sto_files = [f for f in files if f.lower().endswith(".sto")]
    if not sto_files:
        continue

    # 提取trial名称（T1, T2, ...）
    parts = os.path.relpath(root, source_dir).split(os.sep)
    trial_name = next((p for p in parts if re.match(r'^T\d+$', p)), None)
    if trial_name is None:
        continue

    for sto_file in sto_files:
        name, _ = os.path.splitext(sto_file)
        trial_data.setdefault(trial_name, []).append({
            'path': os.path.join(root, sto_file), 'name': name, 'trial': trial_name
        })

print(f"\n找到 {len(trial_data)} 个trial")
for t, flist in trial_data.items():
    print(f"  {t}: {len(flist)} 个文件")

# --- 处理每个trial ---
all_trials_processed = {}
processed_count = 0
error_count = 0

for trial_name, files in trial_data.items():
    print(f"\n处理 {trial_name}...")
    trial_files_data = []

    for file_info in files:
        sto_path = file_info['path']
        file_name = file_info['name']

        try:
            # 1) Peak检测获取stance时间
            t_start, t_end, _, _, _, _, t_stance_start, t_stance_end, peak_idx, peak_value = \
                DPF.get_stance_time_from_sto_with_peak(
                    sto_path, fs=fs_sto, fz_pattern=fz_pattern,
                    threshold=threshold, padding_frames=padding_frames)

            # 2) 截取STO文件（补充帧归零 + 时间列重建）
            output_sto_path = os.path.join(output_cut_dir, trial_name, file_name + '_cut.sto')
            DPF.cut_sto_by_time(sto_path, output_sto_path,
                                t_start=t_start, t_end=t_end, fs=fs_sto,
                                t_stance_start=t_stance_start, t_stance_end=t_stance_end)

            # 3) 读取截取后数据，提取2号力台数据
            header_lines, labels = read_sto_header(output_sto_path)
            df_cut = read_sto_data(output_sto_path, labels)
            data_dict = extract_force_plate_2(df_cut, labels)
            data_dict['name'] = file_name

            # 4) 线性趋势异常值填补
            relative_t_stance_start = padding_time
            relative_t_stance_end = (t_end - t_start) - padding_time

            print(f"\n  {file_name}  Peak={peak_value:.1f}N  Stance=[{t_stance_start:.4f}, {t_stance_end:.4f}]s")
            processed_dict, outlier_info = DPF.process_cop_outliers_linear(
                data_dict, distance_threshold=distance_threshold,
                jump_threshold=jump_threshold,
                t_stance_start=relative_t_stance_start,
                t_stance_end=relative_t_stance_end)

            # 5) 写回处理后的STO文件
            df_final = df_cut.copy()
            for col, key in [('2_ground_force_px', 'COPx'), ('2_ground_force_pz', 'COPz')]:
                if col in df_final.columns:
                    df_final[col] = processed_dict[key]
            write_sto(output_sto_path, header_lines, df_final)
            print(f"  [OK] 已保存: {output_sto_path}")

            trial_files_data.append(processed_dict)
            processed_count += 1

        except Exception as e:
            error_count += 1
            print(f"  [ERROR] {file_name}: {e}")
            continue

    all_trials_processed[trial_name] = trial_files_data

print(f"\n数据处理完成! 成功: {processed_count}, 失败: {error_count}")

if processed_count == 0:
    print("[WARNING] 无可用数据，退出")
    sys.exit(1)

# ==========================================
# 绘图
# ==========================================
print("\n开始绘图...")

# 按trial叠加折线图
for trial_name, files_data in all_trials_processed.items():
    if not files_data:
        continue
    paths = plot_trial_overlay(trial_name, files_data, output_dir)
    for p in paths:
        print(f"  [OK] {p}")

# 单文件组合图
for trial_name, files_data in all_trials_processed.items():
    for fd in files_data:
        path = plot_single_file(fd, output_dir)
        print(f"  [OK] {path}")

# ==========================================
# 总结
# ==========================================
print(f"\n{'=' * 60}")
print("处理完成!")
print(f"成功: {processed_count} 个文件, 失败: {error_count} 个文件")
print(f"输出图像目录: {output_dir}")
print(f"输出截取目录: {output_cut_dir}")
print(f"{'=' * 60}")
