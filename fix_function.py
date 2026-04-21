import shutil

# 读取原始文件
with open("E:/Python_Learn/CarbonShoes_DataProcess/OPenSIm/Data_ProcessFunction.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到函数开始和结束的行
func_start_line = 621  # process_copx_outliers 函数开始行（622行是def定义，621行是空行）
func_end_line = 717     # 函数结束行（716行是return，717行是空行）

# 新函数内容
new_func = """def process_copx_outliers(data_dict, distance_threshold=0.3, t_stance_start=None, t_stance_end=None):
    \"\"\"
    对stance阶段的COPx和COPz数据进行异常值处理：距离中位数超过阈值的点替换为中位数
    只处理真实stance阶段的数据，padding_frames保持归零状态

    参数:
        data_dict : 包含COPx和COPz数据的字典，应包含以下键：
            - 'time': 时间序列
            - 'COPx': COPx位置序列
            - 'COPy': COPy位置序列（可选）
            - 'COPz': COPz位置序列
        distance_threshold : 距离中位数的绝对距离阈值（默认0.3米）
        t_stance_start : 真实stance开始时间（不含补偿）
        t_stance_end : 真实stance结束时间（不含补偿）

    返回:
        处理后的数据字典

    原理:
        1. 根据时间范围识别真实stance阶段的数据点
        2. 分别计算真实stance阶段COPx和COPz的中位数
        3. 计算stance阶段每个点到各自中位数的绝对距离
        4. 将距离超过阈值（0.3米）的点标记为异常值
        5. 将异常值替换为各自的中位数
        6. padding_frames区域保持归零状态不变

    注意:
        - 只对真实stance阶段的COPx和COPz数据进行异常值处理
        - 如果stance阶段值距离各自中位数超过0.3米，则该点替换为中位数
        - padding_frames区域的COPx和COPz数据保持归零不变
        - 其他数据（Fy, COPy）保持不变
    \"\"\"
    # 创建输出字典的深拷贝
    import copy
    result = copy.deepcopy(data_dict)

    # 提取时间、COPx和COPz数据
    time_data = result['time'].copy()
    copx_data = result['COPx'].copy()
    copz_data = result['COPz'].copy()

    # 识别真实stance阶段的数据点
    if t_stance_start is not None and t_stance_end is not None:
        stance_mask = (time_data >= t_stance_start) & (time_data <= t_stance_end)
    else:
        # 如果没有提供stance时间范围，处理全部数据
        stance_mask = np.ones(len(time_data), dtype=bool)

    # 提取真实stance阶段的数据
    copx_stance = copx_data[stance_mask]
    copz_stance = copz_data[stance_mask]

    if len(copx_stance) == 0:
        print("[WARNING] 警告：真实stance阶段没有数据，跳过异常值处理")
        return result, {
            'copx_median': 0,
            'copz_median': 0,
            'outlier_count': 0,
            'outlier_ratio': 0
        }

    # Step 1: 计算真实stance阶段COPx和COPz的中位数
    copx_median = np.median(copx_stance)
    copz_median = np.median(copz_stance)

    # Step 2: 计算stance阶段每个点到各自中位数的绝对距离
    copx_distance_to_median = np.abs(copx_stance - copx_median)
    copz_distance_to_median = np.abs(copz_stance - copz_median)

    # Step 3: 识别异常值：距离超过阈值（0.3米）的点（仅在stance阶段内）
    copx_stance_outlier_mask = (copx_distance_to_median > distance_threshold)
    copz_stance_outlier_mask = (copz_distance_to_median > distance_threshold)

    # Step 4: 创建完整的outlier_mask（默认为False）
    copx_outlier_mask = np.zeros(len(time_data), dtype=bool)
    copz_outlier_mask = np.zeros(len(time_data), dtype=bool)

    # 将stance阶段的outlier_mask设置为识别到的异常值
    copx_outlier_mask[stance_mask] = copx_stance_outlier_mask
    copz_outlier_mask[stance_mask] = copz_stance_outlier_mask

    # Step 5: 将异常值替换为中位数（仅在stance阶段内）
    result['COPx'][copx_outlier_mask] = copx_median
    result['COPz'][copz_outlier_mask] = copz_median

    # 统计信息
    copx_outlier_count = np.sum(copx_stance_outlier_mask)
    copz_outlier_count = np.sum(copz_stance_outlier_mask)
    total_stance_count = len(copx_stance)
    copx_outlier_ratio = copx_outlier_count / total_stance_count * 100 if total_stance_count > 0 else 0
    copz_outlier_ratio = copz_outlier_count / total_stance_count * 100 if total_stance_count > 0 else 0

    print(f"[OK] COPx和COPz异常值处理完成（仅处理真实stance阶段）:")
    print(f"  - 真实stance时间范围: {t_stance_start:.4f}s - {t_stance_end:.4f}s")
    print(f"  - 真实stance数据点数: {total_stance_count}")
    print(f"  - COPx中位数: {copx_median:.6f} m, 异常值: {copx_outlier_count}/{total_stance_count} ({copx_outlier_ratio:.2f}%)")
    print(f"  - COPz中位数: {copz_median:.6f} m, 异常值: {copz_outlier_count}/{total_stance_count} ({copz_outlier_ratio:.2f}%)")
    print(f"  - 距离阈值: {distance_threshold:.3f} m")
    print(f"  - 异常值处理方式: 替换为中位数")
    print(f"  - padding_frames区域保持归零不变")

    return result, {
        'copx_median': copx_median,
        'copz_median': copz_median,
        'outlier_count': copx_outlier_count + copz_outlier_count,
        'outlier_ratio': (copx_outlier_ratio + copz_outlier_ratio) / 2
    }

"""

# 备份原始文件
shutil.copy("E:/Python_Learn/CarbonShoes_DataProcess/OPenSIm/Data_ProcessFunction.py",
             "E:/Python_Learn/CarbonShoes_DataProcess/OPenSIm/Data_ProcessFunction_backup.py")

# 重新写入文件，替换函数部分
with open("E:/Python_Learn/CarbonShoes_DataProcess/OPenSIm/Data_ProcessFunction.py", "w", encoding="utf-8") as f:
    # 写入原文件开头到函数开始
    f.writelines(lines[:func_start_line])
    # 写入新函数
    f.write(new_func)
    # 写入原文件从函数结束开始的部分
    f.writelines(lines[func_end_line:])

print("函数替换完成！")
