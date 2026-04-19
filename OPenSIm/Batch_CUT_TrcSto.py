import os
import Data_ProcessFunction as DPF
import pandas as pd

source_dir = r'G:\Carbon_Plate_Shoes_Data\Data_TrcAndSto\Data_for_Deeplearning\Problem_Data'
target_dir = r'G:\Carbon_Plate_Shoes_Data\Data_TrcAndSto\Data_for_Deeplearning\Problem_Cut_Data'
CSVFilname = 'Cut_Recoeds.csv'

fs_trc = 200
fs_sto = 200
threshold = 40
fz_pattern = r"2_ground_force_vy"
records = []

# 遍历三层目录
for root, dirs, files in os.walk(source_dir):
    # 只处理包含 TRC/STO 文件的目录（第三层刚度文件夹）
    trc_files = [f for f in files if f.lower().endswith(".trc")]
    sto_files = [f for f in files if f.lower().endswith(".sto")]

    if not trc_files and not sto_files:
        continue  # 如果没有 TRC/STO 文件，跳过

    for sto_file in sto_files:
        sto_path = os.path.join(root, sto_file)
        name, _ = os.path.splitext(sto_file)

        # ---------- 获取 stance 时间和帧数 ----------
        t_start, t_end, frame_start, frame_end = DPF.get_stance_time_from_sto(
            sto_path, fs=fs_sto, fz_pattern=fz_pattern, threshold=threshold
        )
        
        # ---------- 截取 STO 文件 ----------
        relative_path = os.path.relpath(sto_path, source_dir)
        dst_path_sto = os.path.join(target_dir, relative_path.replace(".sto", ".sto"))
        os.makedirs(os.path.dirname(dst_path_sto), exist_ok=True)
        DPF.cut_sto_by_time(sto_path, dst_path_sto, t_start, t_end, fs=fs_sto)

        # ---------- 对应 TRC 文件 ----------
        trc_path = os.path.join(root, name + ".trc")
        if os.path.exists(trc_path):
            dst_path_trc = os.path.join(target_dir, os.path.relpath(trc_path, source_dir).replace(".trc", ".trc"))
            os.makedirs(os.path.dirname(dst_path_trc), exist_ok=True)
            DPF.cut_trc_by_time(trc_path, dst_path_trc, t_start, t_end, fs=fs_trc)
        else:
            print(f"⚠ 对应 TRC 文件不存在: {trc_path}")
        records.append({"file Name":name,
                        'Start Time':t_start,
                        'End Time': t_end,
                        'Start Frame': frame_start,
                        'End Frame': frame_end
                        })
Records_OutPath = os.path.join(target_dir,CSVFilname)
df_records = pd.DataFrame(records)
df_records.to_csv(Records_OutPath,index=False)
print("✓ All TRC/STO files processed!")
