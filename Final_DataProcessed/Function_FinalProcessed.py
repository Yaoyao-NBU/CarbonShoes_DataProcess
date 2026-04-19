##################################################导入的库################################################################
import os
import pandas as pd
from io import StringIO
from scipy.interpolate import interp1d
import numpy as np
import glob
import re
########################################################################################################################
##########将STO和Mot数据转换成CSV结构#########################################
#用于将Sto和Mot文件，转化为CSV结构普的文件，通过读取Header所在的行数来定位Header的范围，并去除这个范围！
#
#
def sto_mot_to_csv_single(
    file_path,
    output_root,
    encoding="utf-8-sig"
):
    """
    将单个 OpenSim .sto / .mot 文件转换为 CSV
    """

    print(f"▶ Processing: {file_path}")

    if not (file_path.endswith(".sto") or file_path.endswith(".mot")):
        raise ValueError("文件必须是 .sto 或 .mot")

    # ---- 读取文件 ----
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    print(f"  ✓ 文件加载 ({len(lines)} 行)")

    # ---- 查找 endheader ----因为所有的结果文件是通过怕endhearder来确定前面的标题行有多少
    endheader_index = None
    for i, line in enumerate(lines):
        if 'endheader' in line.lower():
            endheader_index = i    ###找到Endhearder后使用这个标记在第几行
            break

    if endheader_index is None:
        raise RuntimeError(f"❌ 未找到 endheader: {file_path}")

    print(f"  ✓ endheader 在第 {endheader_index + 1}找到了")

    # ---- 提取数据区 ----
    data_str = ''.join(lines[endheader_index + 1:])

    try:
        df = pd.read_csv(
            StringIO(data_str),
            sep=r"\s+",
            engine="python"
        )
    except Exception as e:
        raise RuntimeError(f"❌ 数据区读取失败: {e}")

    print(f"  ✓ 数据矩阵: {df.shape[0]} 行 × {df.shape[1]} 列")

    # ---- 构建输出路径 ----
    os.makedirs(output_root, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    csv_path = os.path.join(output_root, base_name + ".csv")

    # ---- 保存 CSV ----
    df.to_csv(csv_path, index=False, encoding=encoding)

    print(f"  ✓ CSV 保存在 → {csv_path}\n")

    return csv_path

######################用于插值的算法（Single FIle）#####################
#文件要求：第一行为标题行，下面为数据行，第一列为时间列
#
#
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



###############提取目标值和保存函数###########################################
#对单个文件进行处理，会找到你目前的目标列的数据并返回一个DataFrame
#
#
def process_single_csv(file_path, target_columns, col_name=None):
    """
    处理单个 CSV 文件：
        - 读取 CSV
        - 提取 target_columns
        - 返回一个 DataFrame

    参数：
        file_path: CSV 文件路径
        target_columns: 需要提取的列名列表
        col_name: 用作 DataFrame 的列名，如果 None 则用文件名

    返回：
        pd.DataFrame: 提取的列组成的 DataFrame，列名为 col_name
    """

    df = pd.read_csv(file_path)

    # 如果没有指定 col_name，就用文件相对路径或文件名
    if col_name is None:
        col_name = os.path.basename(file_path)

    # 构建新的 DataFrame，只包含 target_columns
    result_df = pd.DataFrame()
    for col in target_columns:
        if col in df.columns:
            result_df[col_name] = df[col].reset_index(drop=True)

    return result_df

########################用于对于文件中的多个Trials进行均值计算################
def process_csv(file_path, output_folder):
    """处理单个 CSV 文件并计算试验平均值"""
    # 读取数据
    df = pd.read_csv(file_path)
    file_name = os.path.basename(file_path)

    # 获取所有列名
    cols = df.columns.tolist()

    # 自动分组逻辑：去掉列名的最后一位数字作为组名
    groups = {}
    for col in cols:
        prefix = col[:-1]  # 例如 S1T1V21 -> S1T1V2
        if prefix not in groups:
            groups[prefix] = []
        groups[prefix].append(col)

    # 创建存放平均值的新 DataFrame
    df_averaged = pd.DataFrame()
    for prefix, columns in groups.items():
        # axis=1 表示按行计算这几列的平均值
        df_averaged[prefix] = df[columns].mean(axis=1)

    # 保存结果
    output_path = os.path.join(output_folder, f"AVG_{file_name}")
    df_averaged.to_csv(output_path, index=False)
    print(f"成功处理并保存: {output_path}")


def batch_process(input_dir, output_dir):
    """批量处理文件夹中的所有 CSV"""
    # 如果输出文件夹不存在则创建
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 查找文件夹下所有的 CSV 文件
    csv_files = glob.glob(os.path.join(input_dir, "*.csv"))

    if not csv_files:
        print("未在文件夹中找到 CSV 文件。")
        return

    for file in csv_files:
        process_csv(file, output_dir)

    print("\n所有文件处理完毕！")
##############################跟腱力的计算##############################
#选取对应文件中的肌肉力量进行相加和汇总
#
def calculate_achilles_total_force(gaslat_path, gasmed_path, soleus_path, output_path):
    """
    计算跟腱总受力：AT_Total = AT_gaslat + AT_gasmed + AT_soleus
    """
    print("正在读取文件...")
    df_gaslat = pd.read_csv(gaslat_path)
    df_gasmed = pd.read_csv(gasmed_path)
    df_soleus = pd.read_csv(soleus_path)

    print("正在合并计算中...")
    df_total = df_gaslat + df_gasmed + df_soleus
    df_total.to_csv(output_path, index=False)
    print(f"计算完成！结果已保存至: {output_path}")
    print("\n结果预览 (前5行):")
    print(df_total.head())
########################动力学数据标准化################################
def batch_normalize_by_weight(data_path, weight_info_path, output_path, gravity=9.81):
    """
    根据表头受试者编号自动匹配体重并进行标准化处理

    参数:
    - data_path: 待标准化的数据CSV路径 (如 AT_Total_Force_r.csv)
    - weight_info_path: 包含受试者体重的CSV路径 (如 BodayWeight.csv)
    - output_path: 标准化后结果的保存路径
    - gravity: 重力加速度，默认9.81 (若CSV里已经是N则设为9.81，若是kg则设为1)
    """

    # 1. 读取受试者信息表
    # 假设 People 列是 S1, S2... Weight 列是体重
    weight_df = pd.read_csv(weight_info_path)
    weight_df['People'] = weight_df['People'].astype(str).str.strip()
    # 将 People 设为索引方便查询
    weight_lookup = weight_df.set_index('People')['Weight'].to_dict()

    # 2. 读取需要标准化的数据文件
    data_df = pd.read_csv(data_path)
    normalized_df = data_df.copy()

    print(f"开始处理文件: {os.path.basename(data_path)}")

    # 3. 遍历列名进行匹配和计算
    success_count = 0
    for col in data_df.columns:
        # 使用正则表达式提取开头的受试者编号 (例如从 S1T1V2 中提取 S1)
        match = re.match(r'([sS]\d+)', col)

        if match:
            subject_id = match.group(1).upper()  # 统一转为大写匹配

            if subject_id in weight_lookup:
                weight = weight_lookup[subject_id]
                # 计算标准化: 原始值 / (体重 * 9.81)
                # 结果单位为 BW (Body Weight)
                normalized_df[col] = data_df[col] / (weight * gravity)
                success_count += 1
            else:
                print(f"警告: 未在体重表中找到受试者 {subject_id} 的信息 (列名: {col})")
        else:
            print(f"跳过: 列名 {col} 格式不符合受试者编号规则")

    # 4. 保存结果
    normalized_df.to_csv(output_path, index=False)
    print(f"--- 处理完成 ---")
    print(f"成功匹配并处理了 {success_count} 个列。")
    print(f"标准化后的数据已保存至: {output_path}")

    return normalized_df
#####################################################################

########################################################################################################################
if __name__ == "__main__":
    # --- 使用设置 ---
    # 存放原始数据的文件夹名称
    input_folder = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\huizongFile_Interpolte'
    # 存放处理后结果的文件夹名称
    output_folder = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Result_Average'
    batch_process(input_folder, output_folder)