import os
import Function_FinalProcessed as DPF
from concurrent.futures import ProcessPoolExecutor, as_completed


def process_single_file(root, fname, source_dir, csv_output_dir):
    """
    单个文件处理逻辑，封装成函数供进程池调用
    """
    file_path = os.path.join(root, fname)

    # 复刻目录结构
    rel_dir = os.path.relpath(root, source_dir)
    csv_save_dir = os.path.join(csv_output_dir, rel_dir)

    # 确保子目录存在（多进程下建议在此检查）
    os.makedirs(csv_save_dir, exist_ok=True)

    try:
        DPF.sto_mot_to_csv_single(
            file_path=file_path,
            output_root=csv_save_dir
        )
        return f"Successfully processed: {fname}"
    except Exception as e:
        return f"Error processing {fname}: {str(e)}"


def main():
    source_dir = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Redo_DataSto_V4_ForPython_transform"
    csv_output_dir = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Redo_DataSto_V4_ForPython_transform_CSV"

    # 1. 收集所有待处理的任务清单
    tasks = []
    for root, _, files in os.walk(source_dir):
        sto_mot_files = [f for f in files if f.lower().endswith((".sto", ".mot"))]
        for fname in sto_mot_files:
            tasks.append((root, fname, source_dir, csv_output_dir))

    print(f"找到 {len(tasks)} 个文件，准备开始并行处理...")

    # 2. 使用进程池执行任务
    # max_workers 默认通常为 CPU 核心数
    with ProcessPoolExecutor() as executor:
        # 提交所有任务
        futures = [executor.submit(process_single_file, *task) for task in tasks]

        # 实时打印进度
        completed_count = 0
        for future in as_completed(futures):
            completed_count += 1
            result = future.result()
            if "Error" in result:
                print(result)
            if completed_count % 10 == 0:  # 每完成10个打印一次进度
                print(f"进度: {completed_count}/{len(tasks)}")

    print("✓ 所有 STO / MOT 文件已批量并行转换为 CSV")


if __name__ == '__main__':
    # 在 Windows 上使用多进程必须放在 if __name__ == '__main__': 之下
    main()