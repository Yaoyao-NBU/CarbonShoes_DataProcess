import os
import sys

# 添加 OPenSIm 目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import Data_ProcessFunction as DPF
import pandas as pd

# ==========================================
# 配置参数
# ==========================================
source_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\input'
target_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\output01'
CSVFilename = 'Cut_Records_Peak.csv'

# 采样频率
fs_trc = 200
fs_sto = 200

# Stance 检测参数
threshold = 60                # 力阈值 (N)
fz_pattern = r".*_ground_force_v[yz]$"  # 垂直力列名匹配模式
padding_frames = 20           # 前后各补充 20 帧

# ==========================================
# 主处理逻辑
# ==========================================
records = []
processed_count = 0
error_count = 0

print("=" * 60)
print("Stance 截取工具（基于 Peak 检测）")
print("=" * 60)
print(f"源目录: {source_dir}")
print(f"输出目录: {target_dir}")
print(f"阈值: {threshold}N")
print(f"补偿帧数: {padding_frames} 帧")
print("=" * 60)

# 遍历三层目录
for root, dirs, files in os.walk(source_dir):
    # 只处理包含 TRC/STO 文件的目录
    trc_files = [f for f in files if f.lower().endswith(".trc")]
    sto_files = [f for f in files if f.lower().endswith(".sto")]

    if not trc_files and not sto_files:
        continue

    for sto_file in sto_files:
        sto_path = os.path.join(root, sto_file)
        name, _ = os.path.splitext(sto_file)

        try:
            # ---------- 获取 stance 时间和帧数（使用 Peak 检测）----------
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
            print(f"  峰值索引: {peak_idx}, 峰值: {peak_value:.2f}N")
            print(f"  Stance 时间: {t_stance_start:.4f}s - {t_stance_end:.4f}s")
            print(f"  截取时间: {t_start:.4f}s - {t_end:.4f}s")

            # ---------- 截取 STO 文件 ----------
            relative_path = os.path.relpath(sto_path, source_dir)
            dst_path_sto = os.path.join(target_dir, relative_path.replace(".sto", ".sto"))
            os.makedirs(os.path.dirname(dst_path_sto), exist_ok=True)

            # 截取 STO，并将非 stance 阶段的力数据归零
            DPF.cut_sto_by_time(
                sto_path,
                dst_path_sto,
                t_start,
                t_end,
                fs=fs_sto,
                t_stance_start=t_stance_start,
                t_stance_end=t_stance_end
            )

            # ---------- 修正 STO 文件单位 ----------
            DPF.fix_sto_ground_force_units(dst_path_sto, dst_path_sto)
            print(f"  ✓ STO 文件已处理")

            # ---------- 处理对应的 TRC 文件 ----------
            trc_path = os.path.join(root, name + ".trc")
            if os.path.exists(trc_path):
                dst_path_trc = os.path.join(
                    target_dir,
                    os.path.relpath(trc_path, source_dir).replace(".trc", ".trc")
                )
                os.makedirs(os.path.dirname(dst_path_trc), exist_ok=True)
                DPF.cut_trc_by_time(trc_path, dst_path_trc, t_start, t_end, fs=fs_trc)
                print(f"  ✓ TRC 文件已处理")
            else:
                print(f"  ⚠ 对应 TRC 文件不存在: {trc_path}")

            # ---------- 记录处理信息 ----------
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
            print(f"\n❌ 处理文件 {name} 时出错:")
            print(f"   错误信息: {str(e)}")
            continue

# ==========================================
# 保存处理记录
# ==========================================
if records:
    Records_OutPath = os.path.join(target_dir, CSVFilename)
    df_records = pd.DataFrame(records)
    df_records.to_csv(Records_OutPath, index=False)
    print(f"\n{'=' * 60}")
    print(f"处理记录已保存: {Records_OutPath}")
    print(f"{'=' * 60}")

# ==========================================
# 输出总结信息
# ==========================================
print(f"\n{'=' * 60}")
print("处理完成!")
print(f"{'=' * 60}")
print(f"成功处理: {processed_count} 个文件")
print(f"处理失败: {error_count} 个文件")
print(f"总计: {processed_count + error_count} 个文件")
print(f"{'=' * 60}")
