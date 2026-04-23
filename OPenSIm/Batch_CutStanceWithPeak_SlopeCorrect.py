"""
Stance数据截取 + COP斜率纠正 + TRC/STO文件批量处理

处理流程:
  1. Peak检测获取stance时间段
  2. 截取STO文件（补充帧归零 + 时间列重建）
  3. 修正COP单位（mm -> m）
  4. 用中间部分斜率纠正COPx/COPz异常值
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
source_dir = r'G:\Carbon_Plate_Shoes_Data\New_Opensim_Transform\4_try\rename_Final'
target_dir = r'G:\Carbon_Plate_Shoes_Data\New_Opensim_Transform\4_try\output_Cut_Peak_SlopeCorrect'
CSVFilename = 'Cut_Records_Peak_SlopeCorrect.csv'

fs_trc = 200                     # TRC采样频率 (Hz)
fs_sto = 200                     # STO采样频率 (Hz)

# Stance检测参数
threshold = 30                   # 力阈值 (N)
fz_pattern = r".*_ground_force_v[yz]$"
padding_frames = 20
padding_time = padding_frames / fs_sto

# COP斜率纠正参数
middle_ratio = 0.3               # 中间部分占比（默认0.3，即取30%~70%区间）
rate_multiplier = 2.0            # 变化率异常倍数（超过通用斜率2倍为异常）

# ==========================================
# 辅助函数：读取STO文件
# ==========================================
def read_sto(sto_path):
    """读取STO文件，返回(header_lines, labels, df)"""
    with open(sto_path, "r", encoding="utf-8") as f:
        header_lines = [next(f) for _ in range(8)]
    labels = header_lines[7].strip().split()
    df = pd.read_csv(sto_path, sep='\t', skiprows=8, names=labels, header=None)
    return header_lines, labels, df


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


def build_data_dict(df, labels, name=''):
    """构建2号力台数据字典"""
    n = len(df)
    data_dict = {
        'name': name,
        'time': df[labels[0]].values,
        'Fy':   df['2_ground_force_vy'].values if '2_ground_force_vy' in df.columns else np.zeros(n),
        'COPx': df['2_ground_force_px'].values if '2_ground_force_px' in df.columns else np.zeros(n),
        'COPy': df['2_ground_force_py'].values if '2_ground_force_py' in df.columns else np.zeros(n),
        'COPz': df['2_ground_force_pz'].values if '2_ground_force_pz' in df.columns else np.zeros(n),
    }
    return data_dict


# ==========================================
# 主处理逻辑
# ==========================================
records = []
processed_count = 0
error_count = 0

print("=" * 60)
print("Stance截取工具（Peak检测 + COP斜率纠正）")
print("=" * 60)
print(f"源目录:       {source_dir}")
print(f"输出目录:     {target_dir}")
print(f"力阈值:       {threshold}N")
print(f"补偿帧数:     {padding_frames} 帧 = {padding_time:.4f}s")
print(f"中间区间比:   {middle_ratio} (取中间{middle_ratio*100:.0f}%~{100-middle_ratio*100:.0f}%)")
print(f"异常倍数:     {rate_multiplier}x (变化率超过通用斜率{rate_multiplier}倍为异常)")
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

            # Step 3: 修正COP单位（mm -> m）
            DPF.fix_sto_ground_force_units(dst_path_sto, dst_path_sto)

            # Step 4: 读取截取后数据，用斜率纠正COP异常值
            header_lines, labels, df_cut = read_sto(dst_path_sto)
            data_dict = build_data_dict(df_cut, labels, name)

            rel_t_start = padding_time
            rel_t_end = (t_end - t_start) - padding_time

            processed_dict, slope_info = DPF.process_cop_outliers_slope(
                data_dict, middle_ratio=middle_ratio,
                rate_multiplier=rate_multiplier,
                t_stance_start=rel_t_start, t_stance_end=rel_t_end)

            # 将处理后的COPx/COPz写回DataFrame
            for col, key in [('2_ground_force_px', 'COPx'), ('2_ground_force_pz', 'COPz')]:
                if col in df_cut.columns:
                    df_cut[col] = processed_dict[key]

            # 写回STO文件
            write_sto(dst_path_sto, header_lines, df_cut)
            print(f"  STO文件已处理（斜率纠正: COPx纠正{slope_info['copx_outlier_count']}帧, "
                  f"COPz纠正{slope_info['copz_outlier_count']}帧）")

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
                "Stance End Frame": frame_stance_end,
                "COPx Slope": slope_info['copx_slope'],
                "COPz Slope": slope_info['copz_slope'],
                "COPx Outlier Count": slope_info['copx_outlier_count'],
                "COPz Outlier Count": slope_info['copz_outlier_count'],
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
