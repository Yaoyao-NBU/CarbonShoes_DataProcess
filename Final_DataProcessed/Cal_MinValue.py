"""
================================================================================
Cal_MinValue.py
================================================================================
功能: 批量计算CSV数据文件中各列的最小值，并按人群和刚度分类汇总
作者: [Your Name]
日期: 2026-04-13

使用方法:
    直接运行: python Cal_MinValue.py
    或按F5运行（如果在IDE中打开）

================================================================================
"""

import os           # 用于文件和目录操作（如遍历文件夹、创建目录）
import pandas as pd # 数据处理核心库，用于读取CSV和数据分析
import re           # 正则表达式，用于从字符串中提取特定模式


# ================================================================================
# 第1部分: 配置参数 - 根据实际情况修改这些路径
# ================================================================================

# 输入目录: 存放原始CSV数据的根文件夹
# 该文件夹下应包含按"人群/刚度"组织的子文件夹结构
INPUT_ROOT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO-Data_Processed\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Result_Average_UnInterpolte'

# 输出目录: 存放计算结果的文件夹
OUTPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO-Data_Processed\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Summary_Statistics_UnInterpolte\MinValue'

# 人群分类列表 - 脚本会查找路径中包含这些关键字的文件夹
GROUPS = ['Amateur_Runner',   # 业余跑者
          'Elite_Runner']     # 精英跑者

# 刚度等级列表 - 脚本会查找路径中包含这些关键字的文件夹
STIFFNESSES = ['T1',   # 刚度等级1 (通常最软)
               'T2',   # 刚度等级2 (中等)
               'T3']   # 刚度等级3 (通常最硬)


# ================================================================================
# 第2部分: 功能函数定义
# ================================================================================

def get_subject_id(col_name):
    """
    从列名中提取受试者ID

    参数:
        col_name (str): 列名字符串，例如 'S1T1V1'、'S10_Angle' 等

    返回:
        str: 提取的受试者ID，例如 'S1'、'S10'；如果没有匹配到则返回原字符串

    示例:
        >>> get_subject_id('S1T1V1')
        'S1'
        >>> get_subject_id('S10_Angle')
        'S10'
        >>> get_subject_id('Unknown_Column')
        'Unknown_Column'
    """
    # 使用正则表达式匹配以 'S' 开头、后跟一个或多个数字的模式
    match = re.match(r'(S\d+)', col_name)
    # 如果匹配成功，返回匹配到的受试者ID；否则返回原列名
    return match.group(1) if match else col_name


def scan_and_group_files(root_dir):
    """
    扫描指定目录下的所有CSV文件，并按文件名进行分组归类

    参数:
        root_dir (str): 要扫描的根目录路径

    返回:
        dict: 文件分组字典，结构为：
              {
                  '文件名.csv': [
                      {'path': '文件完整路径', 'group': '人群', 'stiffness': '刚度'},
                      ...
                  ],
                  ...
              }

    说明:
        该函数会递归遍历 root_dir 下的所有子目录，根据路径中是否包含
        GROUPS 和 STIFFNESSES 中定义的关键字来识别文件所属的人群和刚度类别
    """
    file_map = {}  # 用于存储文件分组的字典
    print("🔍 正在扫描文件结构...")

    # 遍历根目录下的所有子目录和文件
    for dirpath, _, filenames in os.walk(root_dir):

        # 检查当前路径中包含的人群分类（取第一个匹配的）
        # next() 函数返回迭代器中第一个符合条件的元素，如果没有则返回 None
        current_group = next((g for g in GROUPS if g in dirpath), None)

        # 检查当前路径中包含的刚度等级（取第一个匹配的）
        current_stiffness = next((s for s in STIFFNESSES if s in dirpath), None)

        # 如果当前路径没有匹配到人群或刚度，跳过该目录
        if not current_group or not current_stiffness:
            continue

        # 遍历当前目录下的所有文件
        for file in filenames:
            # 只处理CSV文件
            if file.endswith('.csv'):
                # 如果该文件名第一次出现，初始化一个空列表
                if file not in file_map:
                    file_map[file] = []

                # 添加文件信息到映射中
                file_map[file].append({
                    'path': os.path.join(dirpath, file),   # 文件的完整路径
                    'group': current_group,                # 所属人群分类
                    'stiffness': current_stiffness         # 所属刚度等级
                })

    return file_map


def process_single_feature(filename, file_info_list, output_path):
    """
    处理单个特征文件，计算最小值，并按宽格式汇总输出

    参数:
        filename (str): 当前处理的特征文件名（例如 'Force.csv'）
        file_info_list (list): 该特征在不同条件下的文件信息列表
        output_path (str): 输出结果的保存目录

    返回:
        None: 结果直接保存到文件

    处理流程:
        1. 按人群分组（Amateur_Runner / Elite_Runner）
        2. 在每个群体内，按刚度分组（T1 / T2 / T3）
        3. 对每个文件计算各列的最小值
        4. 合并同一人群的所有刚度数据
        5. 将不同人群的数据横向拼接
        6. 保存结果文件，文件名为 Summary_Min_<filename>

    与 Cal_MaxValue.py 的区别:
        本函数使用 df.min() 计算最小值
        Cal_MaxValue.py 使用 df.max() 计算最大值
    """
    group_dfs_list = []  # 用于存储每个人群处理后的DataFrame

    # ===========================================================
    # 第一层循环：按人群分组处理 (Amateur_Runner / Elite_Runner)
    # ===========================================================
    for target_group in GROUPS:

        # 创建一个空的DataFrame，用于存放当前人群在所有刚度下的数据
        current_group_df = pd.DataFrame()

        # ===========================================================
        # 第二层循环：按刚度分组处理 (T1 / T2 / T3)
        # ===========================================================
        for target_stiffness in STIFFNESSES:

            # -------------------------------------------------------
            # 步骤1：在文件信息列表中查找匹配当前人群和刚度的文件
            # -------------------------------------------------------
            matched_info = next(
                (info for info in file_info_list
                 if info['group'] == target_group and info['stiffness'] == target_stiffness),
                None
            )

            # -------------------------------------------------------
            # 步骤2：如果找到匹配文件，读取并处理数据
            # -------------------------------------------------------
            if matched_info:
                file_path = matched_info['path']
                # 构建列标题，格式为：人群_刚度（如 Amateur_Runner_T1）
                col_header = f"{target_group}_{target_stiffness}"

                try:
                    # 使用pandas读取CSV文件
                    df = pd.read_csv(file_path)
                    # 如果文件为空，跳过处理
                    if df.empty:
                        continue

                    # =======================================================
                    # 🔥 核心修改点：计算每一列的最小值 (Min)
                    # 与 Cal_MaxValue.py 的唯一区别：
                    # Cal_MaxValue.py 使用 df.max() 计算最大值
                    # 本文件使用 df.min() 计算最小值
                    # =======================================================
                    # df.min() 会返回一个 Series，索引是列名，值是该列的最小值
                    feature_series = df.min()

                    # -------------------------------------------------------
                    # 步骤3：从列名中提取受试者ID并构建DataFrame
                    # -------------------------------------------------------
                    # 遍历所有列名，提取受试者ID（如 S1T1V1 -> S1）
                    subjects = [get_subject_id(col) for col in feature_series.index]
                    # 获取每列的最小值作为数值
                    values = feature_series.values

                    # 构建临时DataFrame：索引是受试者ID，列标题是 人群_刚度
                    temp_df = pd.DataFrame(data=values, index=subjects, columns=[col_header])
                    temp_df.index.name = 'Subject'

                    # -------------------------------------------------------
                    # 步骤4：对同一受试者的多个值取平均
                    # -------------------------------------------------------
                    # 如果一个受试者有多个测量值，计算平均值
                    temp_df = temp_df.groupby('Subject').mean()

                    # -------------------------------------------------------
                    # 步骤5：将当前刚度的数据合并到当前人群的数据表中
                    # -------------------------------------------------------
                    if current_group_df.empty:
                        # 如果是第一个刚度数据，直接赋值
                        current_group_df = temp_df
                    else:
                        # 否则，按索引合并（横向拼接），使用 outer join 保留所有受试者
                        current_group_df = current_group_df.merge(temp_df, left_index=True, right_index=True,
                                                                  how='outer')

                except Exception as e:
                    # 如果读取或处理文件时出错，打印警告信息但继续处理其他文件
                    print(f"  ⚠️ 读取 {file_path} 出错: {e}")

        # -----------------------------------------------------------
        # 步骤6：移除Subject索引，准备横向拼接
        # -----------------------------------------------------------
        if not current_group_df.empty:
            # reset_index(drop=True) 移除索引，drop=True 表示不保留原索引作为列
            current_group_df.reset_index(drop=True, inplace=True)
            # 将当前人群的数据表加入列表，等待横向拼接
            group_dfs_list.append(current_group_df)

    # ===============================================================
    # 步骤7：横向拼接所有人群的数据并保存
    # ===============================================================
    if group_dfs_list:
        # 使用 pd.concat 横向拼接所有人群的数据表
        # axis=1 表示横向拼接（增加列），axis=0 表示纵向拼接（增加行）
        master_df = pd.concat(group_dfs_list, axis=1)

        # 构建输出文件路径，文件名前缀为 Summary_Min_
        save_file = os.path.join(output_path, f"Summary_Min_{filename}")
        # 保存为CSV文件，不包含索引
        master_df.to_csv(save_file, index=False)
        print(f"  ✅ 已生成最小值汇总表: {save_file}")
    else:
        # 如果没有找到任何数据，打印警告信息
        print(f"  ⚠️ 未找到数据: {filename}")


# ================================================================================
# 第3部分: 主程序入口
# ================================================================================

if __name__ == '__main__':
    """
    程序入口点
    执行流程:
        1. 检查并创建输出目录
        2. 扫描输入目录获取所有CSV文件的组织信息
        3. 遍历处理每个特征文件，计算最小值并保存结果
        4. 输出完成提示
    """

    # ---------------------------------------------------------------
    # 步骤1：检查并创建输出目录
    # ---------------------------------------------------------------
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 创建输出目录: {OUTPUT_DIR}")

    # ---------------------------------------------------------------
    # 步骤2：扫描输入目录，获取所有CSV文件的组织信息
    # ---------------------------------------------------------------
    files_dict = scan_and_group_files(INPUT_ROOT_DIR)

    # ---------------------------------------------------------------
    # 步骤3：遍历处理每个特征文件
    # ---------------------------------------------------------------
    print(f"📊 共找到 {len(files_dict)} 种特征文件。开始提取最小值...")

    for filename, info_list in files_dict.items():
        # 调用处理函数，计算最小值并保存结果
        process_single_feature(filename, info_list, OUTPUT_DIR)

    # ---------------------------------------------------------------
    # 步骤4：处理完成，输出提示信息
    # ---------------------------------------------------------------
    print("\n🎉 全部完成！最小值已提取。")
