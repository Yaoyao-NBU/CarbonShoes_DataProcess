import os
import Data_ProcessFunction as DPF
source_dir = r'G:\Carbon_Plate_Shoes_Data\New_Opensim_Transform\3_try\C3D_File\rename'
target_dir = r'G:\Carbon_Plate_Shoes_Data\New_Opensim_Transform\3_try\C3D_File\filter_File'

"""
遍历 source_dir 下的所有子文件夹，
对 .trc 或 .mot 进行处理，
并将结果写入 target_dir 保持原文件夹结构。
 """

for root, dirs, files in os.walk(source_dir):

     for file in files:
        src_path = os.path.join(root, file)

        # ========== 计算相对路径并生成输出路径 ==========
        relative_path = os.path.relpath(src_path, source_dir)
        dst_path = os.path.join(target_dir, relative_path)

        # ========== 判断文件类型 ==========
        if file.lower().endswith(".trc"):
            dst_path = dst_path.replace(".trc", "_filtered.trc")
            print("Processing TRC:", src_path)
            DPF.filter_trc(src_path, dst_path,cutoff=6, fs=200)##单个滤波函数用于trc
            DPF.remove_marker_prefix_trc(dst_path, dst_path,header_lines_count=6)

        elif file.lower().endswith(".sto"):
            dst_path = dst_path.replace(".sto", "_filtered.sto")
            print("Processing STO:", src_path)
            DPF.filter_mot(src_path, dst_path,cutoff=50, fs=200)##单个滤波函数用于Mot

        else:
                # 其他文件跳过
            continue

            # 自动创建输出文件夹
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

print("DONE!")
###########################################################################################################
