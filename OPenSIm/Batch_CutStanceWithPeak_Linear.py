"""
Stance力学数据截取 + COP线性趋势异常值填补工具

处理流程:
  1. Peak检测获取stance时间段
  2. 截取STO文件（补充帧归零 + 时间列重建）
  3. 修正COP单位（mm → m）
  4. 对COPx/COPz异常值用线性趋势填补（非中值替换）
  5. 写回处理后的STO文件
  6. 截取对应TRC文件
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import Data_ProcessFunction as DPF
import pandas as pd
import numpy as np

# ==========================================
# 配置参数
# ==========================================
source_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\input'
target_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\output_linear'
CSVFilename = 'Cut_Records_Peak_Linear.csv'

fs_trc = 200                     # TRC采样频率 (Hz)
fs_sto = 200                     # STO采样频率 (Hz)

# Stance检测参数
threshold = 30                   # 力阈值 (N)
fz_pattern = r".*_ground_force_v[yz]$"
padding_frames = 20
padding_time = padding_frames / fs_sto

# COP异常值检测与线性趋势填补参数
distance_threshold = 0.08        # 距中位数阈值（米），超过则视为异常值
jump_threshold = 0.03            # 帧间跳变阈值（米），相邻帧变化超过此值视为异常

# ==========================================
# 主处理逻辑
# ==========================================
records = []
processed_count = 0
error_count = 0

print("=" * 60)
print("Stance截取工具（Peak检测 + COP线性趋势填补）")
print("=" * 60)
print(f"源目录:     {source_dir}")
print(f"输出目录:   {target_dir}")
print(f"力阈值:     {threshold}N")
print(f"补偿帧数:   {padding_frames} 帧 = {padding_time:.4f}s")
print(f"异常值阈值: {distance_threshold}m (中位数距离)")
print(f"跳变阈值:   {jump_threshold*1000:.0f}mm (帧间跳变)")
print("=" * 60)

for root, dirs, files in os.walk(source_dir):
    sto_files = [f for f in files if f.lower().endswith(".sto")]
    if not sto_files:
        continue

    for sto_file in sto_files:
        sto_path = os.path.join(root, sto_file)
        name, _ = os.path.splitext(sto_file)

        try:
            # Step 1: Peak检测获取stance时间
            t_start, t_end, frame_stance_start, frame_stance_end, \
                padding_frames_start, padding_frames_end, \
                t_stance_start, t_stance_end, peak_idx, peak_value = \
                DPF.get_stance_time_from_sto_with_peak(
                    sto_path, fs=fs_sto, fz_pattern=fz_pattern,
                    threshold=threshold, padding_frames=padding_frames)

            print(f"\n处理文件: {name}")
            print(f"  Peak: {peak_value:.2f}N (索引{peak_idx})")
            print(f"  Stance: {t_stance_start:.4f}s - {t_stance_end:.4f}s")

            # Step 2: 截取STO文件（补充帧归零 + 时间列重建）
            relative_path = os.path.relpath(sto_path, source_dir)
            dst_path_sto = os.path.join(target_dir, relative_path)
            os.makedirs(os.path.dirname(dst_path_sto), exist_ok=True)

            DPF.cut_sto_by_time(
                sto_path, dst_path_sto, t_start, t_end,
                fs=fs_sto, t_stance_start=t_stance_start, t_stance_end=t_stance_end)

            # Step 3: 修正COP单位（mm → m）
            DPF.fix_sto_ground_force_units(dst_path_sto, dst_path_sto)

            # Step 4: 读取截取后数据，用线性趋势填补COP异常值
            with open(dst_path_sto, "r", encoding="utf-8") as f:
                header_lines = [next(f) for _ in range(8)]
                label_line = header_lines[7].strip()
                labels = label_line.split()

            df_cut = pd.read_csv(dst_path_sto, sep='\t', skiprows=8, names=labels, header=None)

            # 构建2号力台数据字典，调用DPF统一处理函数
            time_col = labels[0]
            n = len(df_cut)
            data_dict = {'name': name, 'time': df_cut[time_col].values}
            for key, col in [('Fy', '2_ground_force_vy'), ('COPx', '2_ground_force_px'),
                             ('COPy', '2_ground_force_py'), ('COPz', '2_ground_force_pz')]:
                data_dict[key] = df_cut[col].values if col in df_cut.columns else np.zeros(n)

            rel_t_start = padding_time
            rel_t_end = (t_end - t_start) - padding_time

            processed_dict, _ = DPF.process_cop_outliers_linear(
                data_dict, distance_threshold=distance_threshold,
                jump_threshold=jump_threshold,
                t_stance_start=rel_t_start, t_stance_end=rel_t_end)

            # 将处理后的COPx/COPz写回DataFrame
            for col, key in [('2_ground_force_px', 'COPx'), ('2_ground_force_pz', 'COPz')]:
                if col in df_cut.columns:
                    df_cut[col] = processed_dict[key]

            # 写回STO文件
            with open(dst_path_sto, "w", encoding="utf-8") as f:
                for line in header_lines:
                    f.write(line if line.endswith("\n") else line + "\n")
                for _, row in df_cut.iterrows():
                    f.write("\t".join(
                        f"{v:.6f}" if isinstance(v, (float, int, np.floating)) else str(v)
                        for v in row.values
                    ) + "\n")

            print(f"  STO文件已处理（线性趋势填补）")

            # Step 5: 截取对应TRC文件
            trc_path = os.path.join(root, name + ".trc")
            if os.path.exists(trc_path):
                dst_path_trc = os.path.join(target_dir, os.path.relpath(trc_path, source_dir))
                os.makedirs(os.path.dirname(dst_path_trc), exist_ok=True)
                DPF.cut_trc_by_time(trc_path, dst_path_trc, t_start, t_end, fs=fs_trc)
                print(f"  TRC文件已处理")
            else:
                print(f"  [WARNING] 对应TRC文件不存在")

            # Step 6: 记录处理信息
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
            print(f"\n  [ERROR] {name}: {e}")
            continue

# ==========================================
# 保存处理记录
# ==========================================
if records:
    records_path = os.path.join(target_dir, CSVFilename)
    pd.DataFrame(records).to_csv(records_path, index=False)
    print(f"\n处理记录已保存: {records_path}")

# ==========================================
# 总结
# ==========================================
print(f"\n{'=' * 60}")
print("处理完成!")
print(f"成功: {processed_count} 个文件, 失败: {error_count} 个文件")
print(f"{'=' * 60}")
