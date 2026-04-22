import os
import sys

# 添加 OPenSIm 目录到 Python 路径
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
output_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\output\output_plots_with_median02'  # 绘图输出目录
output_cut_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\output\output_cut_sto_with_median02'  # 截取并滤波后的STO文件输出目录

fs_sto = 200

# Stance 检测参数
threshold = 30                # 力阈值 (N)
fz_pattern = r".*_ground_force_v[yz]$"  # 垂直力列名匹配模式
padding_frames = 20           # 前后各补充 20 帧
padding_time = padding_frames / fs_sto  # 补偿时间（秒）

# COPx异常值处理参数
distance_threshold = 0.1   # COPx距离中位数的绝对距离阈值（米）

# COP高斯滤波参数
gaussian_window_size = 7   # 高斯滤波窗口大小

# 图像参数
dpi = 600                     # 图像分辨率
aspect_ratio = 16 / 9         # 宽高比

# ==========================================
# 设置图像清晰度和全局样式
# ==========================================
rcParams['font.family'] = 'Arial'
rcParams['font.size'] = 10
rcParams['lines.linewidth'] = 1.0
rcParams['figure.dpi'] = dpi
rcParams['savefig.dpi'] = dpi
rcParams['savefig.bbox'] = 'tight'
rcParams['savefig.pad_inches'] = 0.1

# ==========================================
# 主处理逻辑
# ==========================================
processed_count = 0
error_count = 0

# 创建输出目录
os.makedirs(output_dir, exist_ok=True)
os.makedirs(output_cut_dir, exist_ok=True)

print("=" * 60)
print("Stance 力学数据截取、异常值处理、高斯滤波与绘制工具 (2号力台)")
print("=" * 60)
print(f"源目录: {source_dir}")
print(f"输出图像目录: {output_dir}")
print(f"输出截取文件目录: {output_cut_dir}")
print(f"力阈值: {threshold}N")
print(f"补偿帧数: {padding_frames} 帧 = {padding_time:.4f}s")
print(f"COPx距离中位数阈值: {distance_threshold} 米")
print(f"COP高斯滤波窗口: {gaussian_window_size}")
print(f"图像分辨率: {dpi} dpi")
print("=" * 60)

# 遍历三层目录，收集所有sto文件并按trial分组
trial_data = {}  # 按trial分组存储数据

for root, dirs, files in os.walk(source_dir):
    sto_files = [f for f in files if f.lower().endswith(".sto")]
    if not sto_files:
        continue

    # 从路径中提取trial名称（如T1, T2, T3）
    relative_path = os.path.relpath(root, source_dir)
    parts = relative_path.split(os.sep)

    trial_name = None
    for part in parts:
        if re.match(r'^T\d+$', part):  # 匹配T1, T2, T3等
            trial_name = part
            break

    if trial_name is None:
        print(f"[WARNING] 路径 {relative_path} 中未找到trial名称，跳过")
        continue

    for sto_file in sto_files:
        sto_path = os.path.join(root, sto_file)
        file_name, _ = os.path.splitext(sto_file)

        if trial_name not in trial_data:
            trial_data[trial_name] = []

        trial_data[trial_name].append({
            'path': sto_path,
            'name': file_name,
            'trial': trial_name
        })

print(f"\n找到 {len(trial_data)} 个trial")
for trial, files in trial_data.items():
    print(f"  {trial}: {len(files)} 个文件")

# ==========================================
# 处理每个trial的数据
# ==========================================
all_trials_processed = {}

for trial_name, files in trial_data.items():
    print(f"\n处理 {trial_name}...")

    # 存储该trial所有文件的数据
    trial_files_data = []

    for file_info in files:
        sto_path = file_info['path']
        file_name = file_info['name']

        try:
            # ----- 读取STO文件 -----
            # 读取前8行header
            with open(sto_path, "r", encoding="utf-8") as f:
                header_lines = [next(f) for _ in range(8)]
                label_line = header_lines[7].strip()
                labels = label_line.split()

            # 读取数据
            df = pd.read_csv(sto_path, sep='\t', skiprows=8, names=labels, header=None)

            # ----- 获取stance时间段（不归零，只用于截取）-----
            t_start, t_end, frame_stance_start, frame_stance_end, \
            padding_frames_frames, padding_frames_end, \
            t_stance_start, t_stance_end, peak_idx, peak_value = DPF.get_stance_time_from_sto_with_peak(
                sto_path,
                fs=fs_sto,
                fz_pattern=fz_pattern,
                threshold=threshold,
                padding_frames=padding_frames
            )

            # ----- 截取stance数据 -----
            # 构建输出路径
            output_sto_path = os.path.join(output_cut_dir, trial_name, file_name + '_cut.sto')

            # 使用原来的截取函数（补充帧的力数据归零）
            DPF.cut_sto_by_time(
                sto_path,
                output_sto_path,
                t_start=t_start,
                t_end=t_end,
                fs=fs_sto,
                t_stance_start=t_stance_start,
                t_stance_end=t_stance_end
            )

            # ----- 读取截取后的数据用于绘图 -----
            with open(output_sto_path, "r", encoding="utf-8") as f:
                header_lines = [next(f) for _ in range(8)]
                label_line = header_lines[7].strip()
                labels = label_line.split()

            df_filtered = pd.read_csv(output_sto_path, sep='\t', skiprows=8, names=labels, header=None)

            # ----- 提取2号力台数据 -----
            # COP单位本身就是M，不需要转换
            data_dict = {
                'name': file_name,
                'time': df_filtered[labels[0]].values,
                'Fy': df_filtered['2_ground_force_vy'].values if '2_ground_force_vy' in df_filtered.columns else np.zeros(len(df_filtered)),
                'COPx': df_filtered['2_ground_force_px'].values if '2_ground_force_px' in df_filtered.columns else np.zeros(len(df_filtered)),
                'COPy': df_filtered['2_ground_force_py'].values if '2_ground_force_py' in df_filtered.columns else np.zeros(len(df_filtered)),
                'COPz': df_filtered['2_ground_force_pz'].values if '2_ground_force_pz' in df_filtered.columns else np.zeros(len(df_filtered))
            }

            # ----- 对COPx进行异常值处理（只处理真实stance阶段）-----
            # 截取后的文件时间从0.0开始，真实stance阶段从padding_time开始
            # t_stance_start在截取文件中的相对时间 = padding_time
            # t_stance_end在截取文件中的相对时间 = (t_end - t_start) - padding_time
            relative_t_stance_start = padding_time
            relative_t_stance_end = (t_end - t_start) - padding_time

            print(f"\n  处理文件: {file_name}")
            processed_data_dict, outlier_info = DPF.process_copx_outliers(
                data_dict,
                distance_threshold=distance_threshold,
                t_stance_start=relative_t_stance_start,
                t_stance_end=relative_t_stance_end
            )

            # ----- 对中值补偿后的COPx/COPz进行高斯滤波 -----
            stance_mask_draw = (processed_data_dict['time'] >= relative_t_stance_start) & \
                               (processed_data_dict['time'] <= relative_t_stance_end)

            copx_stance_vals = processed_data_dict['COPx'][stance_mask_draw]
            copz_stance_vals = processed_data_dict['COPz'][stance_mask_draw]

            if len(copx_stance_vals) >= gaussian_window_size:
                processed_data_dict['COPx'][stance_mask_draw] = DPF.gaussian_filter_stance_cop(
                    copx_stance_vals, window_size=gaussian_window_size)
                processed_data_dict['COPz'][stance_mask_draw] = DPF.gaussian_filter_stance_cop(
                    copz_stance_vals, window_size=gaussian_window_size)
                print(f"  COP高斯滤波完成（窗口: {gaussian_window_size}）")

            # ----- 将处理后的COPx和COPz数据写回文件 -----
            # 重新构建DataFrame
            df_final = df_filtered.copy()

            # 更新COPx和COPz列
            df_final['2_ground_force_px'] = processed_data_dict['COPx']
            df_final['2_ground_force_pz'] = processed_data_dict['COPz']

            # 写回文件
            with open(output_sto_path, "w", encoding="utf-8") as f:
                # 写header
                for line in header_lines:
                    f.write(line if line.endswith("\n") else line + "\n")
                # 写数据
                for _, row in df_final.iterrows():
                    f.write(
                        "\t".join(
                            f"{v:.6f}" if isinstance(v, (float, int, np.floating)) else str(v)
                            for v in row.values
                        ) + "\n"
                    )

            print(f"  [OK] 文件已保存: {output_sto_path}")
            trial_files_data.append(processed_data_dict)
            processed_count += 1

        except Exception as e:
            error_count += 1
            print(f"  [ERROR] 处理文件 {file_name} 时出错: {str(e)}")
            continue

    all_trials_processed[trial_name] = trial_files_data

print(f"\n数据处理完成! 成功: {processed_count}, 失败: {error_count}")

# ==========================================
# 绘制折线图
# ==========================================
if processed_count == 0:
    print("[WARNING] 没有可处理的数据，退出")
    sys.exit(1)

print("\n开始绘制折线图...")

# 定义要绘制的变量及其配置（每个trial生成3个独立图像）
plot_configs = {
    'Fy': {'title': 'Ground Reaction Force - Fy', 'ylabel': 'Mediolateral Force (N)'},
    'COPx': {'title': 'Center of Pressure - COPx (Outlier Removed + Gaussian Filtered)', 'ylabel': 'Anteroposterior Position (m)'},
    'COPy': {'title': 'Center of Pressure - COPy', 'ylabel': 'Mediolateral Position (m)'}
}

# 为每个trial绘制3个独立图像
for trial_name, files_data in all_trials_processed.items():
    if not files_data:
        continue

    # 绘制每个变量（独立图像，不拼子图）
    for var_name, config in plot_configs.items():
        fig, ax = plt.subplots(figsize=(12, 6.75))  # 16:9比例

        # 为该trial中每个文件绘制一条折线
        for i, file_data in enumerate(files_data):
            color = plt.cm.tab10(i % 10)
            ax.plot(file_data['time'], file_data[var_name],
                   label=file_data['name'], color=color, linewidth=0.8, alpha=0.8)

        # 设置标题和标签
        ax.set_title(f"{trial_name} - {config['title']} (Force Plate 2)",
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Time (s)', fontsize=12)
        ax.set_ylabel(config['ylabel'], fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.6)

        # 设置图例（放在右侧外部）
        ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5),
                  fontsize=8, ncol=1, framealpha=0.8)

        # 调整布局
        plt.tight_layout()

        # 保存图像
        output_path = os.path.join(output_dir, f'{trial_name}_{var_name}.png')
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

        print(f"[OK] {trial_name}_{var_name} 图像已保存: {output_path}")

print("\n开始为每个单独的sto文件绘制图像...")

# 为每个单独的sto文件绘制包含Fy、COPx、COPz三个子图的图像
single_file_configs = {
    'Fy': {'title': 'Mediolateral Force (Fy)', 'ylabel': 'Force (N)'},
    'COPx': {'title': 'Anteroposterior Position (COPx)', 'ylabel': 'Position (m)'},
    'COPz': {'title': 'Vertical Position (COPz)', 'ylabel': 'Position (m)'}
}

for trial_name, files_data in all_trials_processed.items():
    if not files_data:
        continue

    # 为该trial的每个单独文件绘制图像
    for file_data in files_data:
        fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
        fig.suptitle(f"{file_data['name']} - Force Plate 2 (Outlier Removed + Gaussian Filtered)", fontsize=16, fontweight='bold')

        # 绘制三个子图：Fy、COPx、COPz
        for idx, (var_name, config) in enumerate(single_file_configs.items()):
            ax = axes[idx]
            ax.plot(file_data['time'], file_data[var_name],
                   linewidth=1.2, color='blue', alpha=0.9)
            ax.set_ylabel(config['ylabel'], fontsize=11)
            ax.set_title(config['title'], fontsize=12, loc='left')
            ax.grid(True, linestyle='--', alpha=0.6)

        axes[-1].set_xlabel('Time (s)', fontsize=12)
        plt.tight_layout()

        # 保存图像
        output_path = os.path.join(output_dir, f"{file_data['name']}_combined.png")
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close()

        print(f"[OK] {file_data['name']}_combined 图像已保存: {output_path}")

# ==========================================
# 输出总结信息
# ==========================================
print(f"\n{'=' * 60}")
print("处理完成!")
print(f"{'=' * 60}")
print(f"成功处理: {processed_count} 个文件")
print(f"处理失败: {error_count} 个文件")
print(f"输出图像目录: {output_dir}")
print(f"输出截取文件目录: {output_cut_dir}")
print(f"每个trial生成3个独立图像: Fy, COPx(去异常值+高斯滤波), COPy")
print(f"每个单独文件生成1个组合图像: Fy, COPx, COPz (子图, 含高斯滤波)")
print(f"{'=' * 60}")
