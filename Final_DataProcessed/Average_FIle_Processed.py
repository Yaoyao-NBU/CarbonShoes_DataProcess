import pandas as pd
import os


def process_csv(file_path, output_path):
    """处理单个 CSV 逻辑"""
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return

        # 分组逻辑：按列名去掉最后一位数字分组
        groups = {}
        for col in df.columns:
            prefix = col[:-1]
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(col)

        df_averaged = pd.DataFrame()
        for prefix, columns in groups.items():
            # 仅对数值列求平均，避免报错
            numeric_cols = df[columns].select_dtypes(include=['number']).columns
            if not numeric_cols.empty:
                df_averaged[prefix] = df[numeric_cols].mean(axis=1)
            else:
                df_averaged[prefix] = df[columns[0]]

        df_averaged.to_csv(output_path, index=False)
    except Exception as e:
        print(f"处理出错 {file_path}: {e}")


def batch_process_with_walk(input_root, output_root):
    """使用 os.walk 遍历所有层级"""
    print(f"正在扫描目录: {input_root}")

    # root: 当前正在遍历的目录路径
    # dirs: 当前路径下的子目录列表
    # files: 当前路径下的文件列表
    for root, dirs, files in os.walk(input_root):
        for file in files:
            if file.endswith('.csv'):
                # 1. 构造完整输入路径
                input_file_path = os.path.join(root, file)

                # 2. 构造对应的输出路径（保持子文件夹结构）
                # 计算当前文件相对于输入根目录的相对路径
                relative_path = os.path.relpath(root, input_root)
                target_dir = os.path.join(output_root, relative_path)

                # 如果目标子文件夹不存在，则创建
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                output_file_path = os.path.join(target_dir, f"{file}")

                # 3. 执行处理
                process_csv(input_file_path, output_file_path)
                print(f"成功: {output_file_path}")

    print("\n✅ 所有子文件夹中的 CSV 已处理完毕！")


# --- 使用设置 ---
input_path = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data\interpolte_huizhong_noemalization'  # 替换为你的源数据路径
output_path = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data\Interpolte_Average'  # 替换为你的输出路径

batch_process_with_walk(input_path, output_path)