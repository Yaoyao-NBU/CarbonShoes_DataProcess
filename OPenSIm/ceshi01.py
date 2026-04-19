import pandas as pd
import os

def mirror_grf_plate2_only(input_path, output_path):
    """
    专门针对数据落在 2 号力台的 STO 文件进行镜像处理。
    镜像逻辑：Z轴力取反, Z轴作用点取反, X/Y轴力矩取反。
    """
    # 1. 提取并保留 OpenSim 必需的 7 行文件头
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            header_lines = [f.readline() for _ in range(7)]
    except UnicodeDecodeError:
        # 如果有特殊字符，尝试其他编码
        with open(input_path, 'r', encoding='gbk') as f:
            header_lines = [f.readline() for _ in range(7)]

    # 2. 读取数据部分 (从第 8 行开始)
    # 你的文件后缀是 .sto.csv，通常使用逗号分隔
    df = pd.read_csv(input_path, skiprows=7, sep=',')

    # 3. 定义镜像翻转的列 (仅针对 2 号力台)
    # 根据生物力学镜像原理：
    # vz (Z向力): 取反
    # pz (Z向压力中心): 取反
    # torque_x & torque_y (横向力矩): 取反 (基于右手定则)
    cols_to_mirror = [
        '2_ground_force_vz',
        '2_ground_force_pz',
        '2_ground_torque_x',
        '2_ground_torque_y'
    ]

    # 检查列是否存在并执行取反
    for col in cols_to_mirror:
        if col in df.columns:
            df[col] = df[col] * -1
        else:
            print(f"警告: 未在文件中找到列 {col}")

    # 4. 保存文件，恢复头信息
    # 使用 lineterminator='\n' 确保跨平台格式一致性
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(header_lines)
        df.to_csv(f, index=False, sep=',', lineterminator='\n')

    print("-" * 30)
    print(f"处理完成！")
    print(f"原始文件: {os.path.basename(input_path)}")
    print(f"镜像文件: {os.path.basename(output_path)}")
    print("-" * 30)

# ================= 配置区 =================
# 请确保路径正确，或者将脚本放在文件同目录下
input_file = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\S20T2V31.sto'
output_file = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\S20T2V31_Mirrored_GRF.sto'

if __name__ == "__main__":
    if os.path.exists(input_file):
        mirror_grf_plate2_only(input_file, output_file)
    else:
        print(f"错误: 找不到输入文件 {input_file}")