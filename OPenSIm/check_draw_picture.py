import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from OPenSIm.Data_ProcessFunction import butter_lowpass_filter


def read_mot_sto_file(file_path):
    """
    读取 MOT/STO 文件（OpenSim 输出格式）
    保留前 8 行 header，数据部分从第 9 行开始
    """
    # 读取前 8 行 header
    with open(file_path, 'r') as f:
        header_lines = [next(f) for _ in range(8)]

    # 读取数据部分（第 9 行开始）
    df = pd.read_csv(file_path, sep="\t", skiprows=8)

    return df, header_lines


def extract_and_process_at_force(data_dir, muscle_names, output_dir, cutoff=50, fs=1000):
    """
    从指定目录遍历取出肌肉力数据，进行滤波处理，并绘制图片

    Parameters:
        data_dir: 数据根目录
        muscle_names: 需要提取的肌肉名称列表（将相加）
        output_dir: 图片输出目录
        cutoff: 滤波截止频率（Hz），默认 50Hz
        fs: 采样频率（Hz），默认 1000Hz
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    print(f"开始扫描目录: {data_dir}")
    print(f"目标肌肉: {muscle_names}")

    # 遍历目录
    for subdir, dirs, files in os.walk(data_dir):
        # 检查当前文件夹是否包含所有目标文件
        target_files = [f"{name}.sto" for name in muscle_names] + [f"{name}.mot" for name in muscle_names]

        # 查找存在的文件
        found_files = {}
        for name in muscle_names:
            for ext in ['.sto', '.mot']:
                file_path = os.path.join(subdir, f"{name}{ext}")
                if os.path.exists(file_path):
                    found_files[name] = file_path
                    break

        # 如果找到所有目标文件
        if len(found_files) == len(muscle_names):
            print(f"\n正在处理: {subdir}")

            # 读取并提取数据
            all_data = []
            time_data = None

            for name in muscle_names:
                file_path = found_files[name]
                print(f"  读取文件: {os.path.basename(file_path)}")

                df, _ = read_mot_sto_file(file_path)

                # 获取时间列
                if time_data is None:
                    time_data = df.iloc[:, 0].values

                # 提取肌肉力数据（假设第二列是数据列）
                force_data = df.iloc[:, 1].values
                all_data.append(force_data)

            # 计算三块肌肉的总力
            total_force = np.sum(all_data, axis=0)

            # 四阶巴特沃斯低通滤波
            filtered_force = butter_lowpass_filter(total_force, cutoff, fs, order=4)
            print(f"  已完成 {cutoff}Hz 低通滤波（4阶巴特沃斯）")

            # 绘制图片
            plot_at_force(
                time_data,
                total_force,
                filtered_force,
                subdir,
                output_dir
            )

    print(f"\n所有处理完成！图片保存至: {output_dir}")


def plot_at_force(time, raw_force, filtered_force, subdir, output_dir):
    """
    绘制跟腱力图片（滤波前后对比）

    Parameters:
        time: 时间序列
        raw_force: 原始力数据
        filtered_force: 滤波后力数据
        subdir: 数据源目录（用于生成文件名）
        output_dir: 输出目录
    """
    plt.figure(figsize=(12, 6), dpi=150)

    # 绘制原始数据
    plt.plot(time, raw_force, 'b--', alpha=0.5, linewidth=1, label='Raw Force')

    # 绘制滤波后数据
    plt.plot(time, filtered_force, 'r-', linewidth=2, label='Filtered Force (50Hz LP)')

    # 设置图表样式
    plt.xlabel('Time (s)', fontsize=14, fontweight='bold')
    plt.ylabel('Force (N)', fontsize=14, fontweight='bold')
    plt.title('Achilles Tendon Total Force', fontsize=16, fontweight='bold')
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)

    # 生成文件名（使用目录名称）
    dir_name = os.path.basename(subdir)
    save_path = os.path.join(output_dir, f"{dir_name}_AT_Force.png")

    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

    print(f"  图片已保存: {save_path}")


def plot_single_at_force(file_path, muscle_names, output_dir, cutoff=50, fs=1000):
    """
    从单个文件中提取并绘制跟腱力（用于测试单个文件）

    Parameters:
        file_path: MOT/STO 文件路径
        muscle_names: 需要提取的肌肉名称列表
        output_dir: 输出目录
        cutoff: 滤波截止频率（Hz）
        fs: 采样频率（Hz）
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"处理单个文件: {file_path}")

    # 读取数据
    df, _ = read_mot_sto_file(file_path)
    time_data = df.iloc[:, 0].values

    # 提取指定列的数据（假设列名包含肌肉名称）
    all_force = []
    for name in muscle_names:
        # 尝试匹配列名
        matching_cols = [col for col in df.columns if name in col]
        if matching_cols:
            force_data = df[matching_cols[0]].values
            all_force.append(force_data)
            print(f"  找到列: {matching_cols[0]}")
        else:
            print(f"  警告: 未找到列 {name}")

    if all_force:
        # 计算总力
        total_force = np.sum(all_force, axis=0)

        # 滤波
        filtered_force = butter_lowpass_filter(total_force, cutoff, fs, order=4)

        # 绘图
        plot_at_force(time_data, total_force, filtered_force, os.path.dirname(file_path), output_dir)


# ================= 执行入口 =================
if __name__ == "__main__":
    # 配置参数
    DATA_DIR = r"G:\Carbon_Plate_Shoes_Data\STO-Data_Processed\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\huizongFile_Interpolte"
    OUTPUT_DIR = r"E:\Python_Learn\CarbonShoes_DataProcess\Draw_Picture\Check_Pictures"

    # 需要提取的三块肌肉（跟腱）
    MUSCLE_NAMES = ["AT_gasmed_r", "AT_gaslat_r", "AT_soleus_r"]

    # 滤波参数
    CUTOFF_FREQ = 50  # 截止频率 50Hz
    SAMPLE_FREQ = 1000  # 采样频率 1000Hz

    # 模式选择
    MODE = "batch"  # "batch" 批量处理， "single" 单个文件测试

    if MODE == "batch":
        # 批量处理
        extract_and_process_at_force(
            data_dir=DATA_DIR,
            muscle_names=MUSCLE_NAMES,
            output_dir=OUTPUT_DIR,
            cutoff=CUTOFF_FREQ,
            fs=SAMPLE_FREQ
        )
    elif MODE == "single":
        # 单个文件测试
        TEST_FILE = r"G:\Carbon_Plate_Shoes_Data\STO-Data_Processed\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\huizongFile_Interpolte\Amateur_Runner\T1\01\IK_results.sto"
        plot_single_at_force(
            file_path=TEST_FILE,
            muscle_names=MUSCLE_NAMES,
            output_dir=OUTPUT_DIR,
            cutoff=CUTOFF_FREQ,
            fs=SAMPLE_FREQ
        )
