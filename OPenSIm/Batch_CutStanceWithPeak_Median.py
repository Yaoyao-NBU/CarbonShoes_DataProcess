import os
import sys

# 添加 OPenSIm 目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import Data_ProcessFunction as DPF
import pandas as pd
import numpy as np
import re

# ==========================================
# 配置参数
# ==========================================
source_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\input'
target_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\output'
CSVFilename = 'Cut_Records_Peak_Median.csv'

# 采样频率
fs_trc = 200   # TRC 采样频率 (Hz)
fs_sto = 200   # STO 采样频率 (Hz)

# Stance 检测参数 —— 基于2号力台垂直力
threshold = 30                            # 力阈值 (N)
fz_pattern = r".*_ground_force_v[yz]$"    # 垂直力列名匹配模式
padding_frames = 20                       # 前后各补充帧数
padding_time = padding_frames / fs_sto    # 补偿时间（秒）

# COP异常值中值补偿参数
distance_threshold = 0.1   # COPx/COPz距离各自中位数的阈值（米），超过则替换为中位数

# ==========================================
# 主处理逻辑
# ==========================================
records = []
processed_count = 0
error_count = 0

print("=" * 60)
print("Stance 截取工具（Peak检测 + COP中值补偿）")
print("=" * 60)
print(f"源目录: {source_dir}")
print(f"输出目录: {target_dir}")
print(f"力阈值: {threshold}N")
print(f"补偿帧数: {padding_frames} 帧 = {padding_time:.4f}s")
print(f"COP异常值阈值: {distance_threshold}m")
print("=" * 60)

# 遍历三层目录
for root, dirs, files in os.walk(source_dir):
    trc_files = [f for f in files if f.lower().endswith(".trc")]
    sto_files = [f for f in files if f.lower().endswith(".sto")]

    if not sto_files:
        continue

    for sto_file in sto_files:
        sto_path = os.path.join(root, sto_file)
        name, _ = os.path.splitext(sto_file)

        try:
            # ----- Step 1: 用Peak检测获取stance时间 -----
            t_start, t_end, frame_stance_start, frame_stance_end, \
            padding_frames_start, padding_frames_end, \
            t_stance_start, t_stance_end, peak_idx, peak_value = DPF.get_stance_time_from_sto_with_peak(
                sto_path,
                fs=fs_sto,
                fz_pattern=fz_pattern,
                threshold=threshold,
                padding_frames=padding_frames
            )

            print(f"\n处理文件: {name}")
            print(f"  峰值: {peak_value:.2f}N (索引{peak_idx})")
            print(f"  Stance: {t_stance_start:.4f}s - {t_stance_end:.4f}s")
            print(f"  截取: {t_start:.4f}s - {t_end:.4f}s")

            # ----- Step 2: 截取STO文件（padding区域归零 + 时间列重建） -----
            relative_path = os.path.relpath(sto_path, source_dir)
            dst_path_sto = os.path.join(target_dir, relative_path)
            os.makedirs(os.path.dirname(dst_path_sto), exist_ok=True)

            DPF.cut_sto_by_time(
                sto_path,
                dst_path_sto,
                t_start,
                t_end,
                fs=fs_sto,
                t_stance_start=t_stance_start,
                t_stance_end=t_stance_end
            )

            # ----- Step 3: 修正STO文件COP单位（mm → m） -----
            DPF.fix_sto_ground_force_units(dst_path_sto, dst_path_sto)

            # ----- Step 4: 对截取后STO文件的COPx/COPz进行中值补偿 -----
            # 读取截取后的STO文件
            with open(dst_path_sto, "r", encoding="utf-8") as f:
                header_lines = [next(f) for _ in range(8)]
                label_line = header_lines[7].strip()
                labels = label_line.split()

            df_cut = pd.read_csv(dst_path_sto, sep='\t', skiprows=8, names=labels, header=None)
            time_col = labels[0]

            # 截取文件时间从0.0开始，真实stance从padding_time开始
            relative_t_stance_start = padding_time
            relative_t_stance_end = (t_end - t_start) - padding_time

            # 只在有COP列时才做中值补偿
            copx_col = '2_ground_force_px'
            copz_col = '2_ground_force_pz'

            if copx_col in df_cut.columns and copz_col in df_cut.columns:
                # 识别真实stance阶段
                stance_mask = (df_cut[time_col] >= relative_t_stance_start) & \
                              (df_cut[time_col] <= relative_t_stance_end)

                copx_stance = df_cut.loc[stance_mask, copx_col].values
                copz_stance = df_cut.loc[stance_mask, copz_col].values

                if len(copx_stance) > 0:
                    # 计算各自中位数
                    copx_median = np.median(copx_stance)
                    copz_median = np.median(copz_stance)

                    # 计算距离中位数的绝对距离
                    copx_dist = np.abs(copx_stance - copx_median)
                    copz_dist = np.abs(copz_stance - copz_median)

                    # 超过阈值的点替换为中位数
                    copx_outlier_count = np.sum(copx_dist > distance_threshold)
                    copz_outlier_count = np.sum(copz_dist > distance_threshold)

                    # 替换COPx异常值
                    copx_outlier_mask = stance_mask.copy()
                    copx_outlier_mask[stance_mask] = copx_dist > distance_threshold
                    df_cut.loc[copx_outlier_mask, copx_col] = copx_median

                    # 替换COPz异常值
                    copz_outlier_mask = stance_mask.copy()
                    copz_outlier_mask[stance_mask] = copz_dist > distance_threshold
                    df_cut.loc[copz_outlier_mask, copz_col] = copz_median

                    print(f"  COPx中位数: {copx_median:.4f}m, 异常值替换: {copx_outlier_count}帧")
                    print(f"  COPz中位数: {copz_median:.4f}m, 异常值替换: {copz_outlier_count}帧")

                    # 将处理后的数据写回文件
                    with open(dst_path_sto, "w", encoding="utf-8") as f:
                        for line in header_lines:
                            f.write(line if line.endswith("\n") else line + "\n")
                        for _, row in df_cut.iterrows():
                            f.write(
                                "\t".join(
                                    f"{v:.6f}" if isinstance(v, (float, int, np.floating)) else str(v)
                                    for v in row.values
                                ) + "\n"
                            )
            else:
                print(f"  [WARNING] 未找到2号力台COP列，跳过中值补偿")

            print(f"  STO文件已处理（含中值补偿）")

            # ----- Step 5: 截取对应的TRC文件 -----
            trc_path = os.path.join(root, name + ".trc")
            if os.path.exists(trc_path):
                dst_path_trc = os.path.join(
                    target_dir,
                    os.path.relpath(trc_path, source_dir)
                )
                os.makedirs(os.path.dirname(dst_path_trc), exist_ok=True)
                DPF.cut_trc_by_time(trc_path, dst_path_trc, t_start, t_end, fs=fs_trc)
                print(f"  TRC文件已处理")
            else:
                print(f"  [WARNING] 对应TRC文件不存在: {trc_path}")

            # ----- Step 6: 记录处理信息 -----
            records.append({
                "File Name": name,
                "Start Time": t_start,
                "End Time": t_end,
                "Stance Start": t_stance_start,
                "Stance End": t_stance_end,
                "Peak Value": peak_value,
                "Peak Index": peak_idx,
                "Start Frame": padding_frames_start,
                "End Frame": padding_frames_end,
                "Stance Start Frame": frame_stance_start,
                "Stance End Frame": frame_stance_end
            })

            processed_count += 1

        except Exception as e:
            error_count += 1
            print(f"\n  [ERROR] 处理文件 {name} 时出错: {str(e)}")
            continue

# ==========================================
# 保存处理记录
# ==========================================
if records:
    records_path = os.path.join(target_dir, CSVFilename)
    df_records = pd.DataFrame(records)
    df_records.to_csv(records_path, index=False)
    print(f"\n处理记录已保存: {records_path}")

# ==========================================
# 输出总结
# ==========================================
print(f"\n{'=' * 60}")
print("处理完成!")
print(f"成功: {processed_count} 个文件, 失败: {error_count} 个文件")
print(f"{'=' * 60}")
