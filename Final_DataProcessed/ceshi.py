from concurrent.futures import ProcessPoolExecutor
import time
import os
import pandas as pd
from scipy.interpolate import interp1d
import numpy as np


def interpolate_single_file_simple(
        input_path,
        output_path,
        num_frames=101,
        interp_method='linear'
):
    """
    对只有【标题行 + 数据行】的文件进行时间归一化插值
    第一列默认是 time
    """

    # ========= 1. 读取数据（第一行即标题） =========
    df = pd.read_csv(input_path, header=0)
    headers = df.columns.tolist()

    # ========= 2. 时间列 =========
    time_original = df.iloc[:, 0].values
    time_uniform = np.linspace(
        time_original[0],
        time_original[-1],
        num_frames
    )

    # ========= 3. 插值 =========
    interpolated_data = []

    for col in headers[1:]:
        y = df[col].values

        f = interp1d(
            time_original,
            y,
            kind=interp_method,
            fill_value="extrapolate"
        )

        y_interp = f(time_uniform)
        interpolated_data.append(y_interp)

    # ========= 4. 合并结果 =========
    result = np.column_stack([time_uniform] + interpolated_data)
    result_df = pd.DataFrame(result, columns=headers)

    # ========= 5. 保存 =========
    result_df.to_csv(output_path, index=False)

    print(f"\n✅ 插值完成：{output_path}")















def main():
    InputBase = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Raw_Data'
    OutputBase = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\WorkAndPower\Raw_data_Interpalte'


    tasks = []
    for root, dirs, files in os.walk(InputBase):
        for file in files:
            if file.lower().endswith(".csv"):

                input_file = os.path.join(root, file)
                rel_path = os.path.relpath(root, InputBase)
                output_dir = os.path.join(OutputBase, rel_path)
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, file)
                # 将参数打包成元组
                tasks.append((input_file, output_file))

    print(f"扫描完毕：共找到 {len(tasks)} 个待处理文件。")
    print(f" 正在启动并行处理（使用所有 CPU 核心,进行并行计算）")
    start_time = time.time()

    with ProcessPoolExecutor() as executor:#并行处理算法

        futures = [executor.submit(interpolate_single_file_simple, t[0], t[1]) for t in tasks]

        for count, future in enumerate(futures, 1):
            res = future.result()
            if count % 10 == 0:
                print(f"进度: {count}/{len(tasks)} | {res}")

    end_time = time.time()
    print(f"\n 全部任务处理完成！")
    print(f" 总耗时: {end_time - start_time:.2f} 秒")



if __name__ == "__main__":
    main()