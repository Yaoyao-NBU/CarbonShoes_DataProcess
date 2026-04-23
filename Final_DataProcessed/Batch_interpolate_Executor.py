import os
from concurrent.futures import ProcessPoolExecutor
import Function_FinalProcessed as FTP
import time


def main():
    InputBase = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Raw_data'
    OutputBase = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data'


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

        futures = [executor.submit(FTP.interpolate_single_file_simple, t[0], t[1]) for t in tasks]

        for count, future in enumerate(futures, 1):
            res = future.result()
            if count % 10 == 0:
                print(f"进度: {count}/{len(tasks)} | {res}")

    end_time = time.time()
    print(f"\n 全部任务处理完成！")
    print(f" 总耗时: {end_time - start_time:.2f} 秒")



if __name__ == "__main__":
    main()