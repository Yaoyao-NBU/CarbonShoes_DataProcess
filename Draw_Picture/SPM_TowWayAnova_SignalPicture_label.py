"""
SPM双因素方差分析信号图绘制脚本
=====================================

功能说明：
-----------
本脚本用于对二维步态数据进行SPM（Statistical Parametric Mapping，统计参数映射）
双因素方差分析，并绘制包含以下内容的综合性结果图：
    - 各组均值曲线（带标准差填充区域）
    - 主效应和交互效应的显著性区间标注
    - SPM统计检验的p值标注

数据格式要求：
---------------
输入数据为CSV文件，每行代表一个样本的完整步态周期数据，每列代表一个时间点。
数据应按以下组别顺序排列：
    - Group 1: 业余跑者 (Amateur) - T1, T2, T3
    - Group 2: 精英跑者 (Elite) - T1, T2, T3

作者：[Your Name]
日期：2026-04-13
"""

# 导入必要的库
import spm1d  # SPM统计库，用于方差分析
import pandas as pd  # 数据处理
import numpy as np  # 数值计算
import matplotlib.pyplot as plt  # 绘图
import os  # 文件路径处理


# ================= 核心绘图函数 =================
def spm_integrated_plot(file_list, factor_A_levels, factor_B_levels,
                        factor_A_name="Group", factor_B_name="Stiffness",
                        alpha=0.05, save_path="SPM_Integrated_Result.png",
                        plot_title="",  # 默认设为空表示不显示主标题
                        x_label="Stance (%)", y_label="Angle (°)"):
    """
    绘制SPM双因素方差分析综合结果图

    参数说明：
    -----------
    file_list : list
        包含6个CSV文件路径的列表，按Group A(T1,T2,T3), Group B(T1,T2,T3)顺序排列
    factor_A_levels : int
        因素A的水平数（如2组：业余vs精英）
    factor_B_levels : int
        因素B的水平数（如3种刚度：T1,T2,T3）
    factor_A_name : str, 默认 "Group"
        因素A的名称（用于图表标注）
    factor_B_name : str, 默认 "Stiffness"
        因素B的名称（用于图表标注）
    alpha : float, 默认 0.05
        显著性水平阈值
    save_path : str
        图片保存的完整路径
    plot_title : str, 默认 ""
        图表主标题（空字符串则不显示）
    x_label : str, 默认 "Stance (%)"
        X轴标签
    y_label : str, 默认 "Angle (°)"
        Y轴标签
    """

    # ============================================================
    # 模块 1: 全局绘图环境配置
    # ============================================================
    # 设置全局字体为Times New Roman（符合学术论文标准）
    plt.rcParams['font.family'] = 'Times New Roman'
    # 解决负号显示问题（确保负号正确渲染）
    plt.rcParams['axes.unicode_minus'] = False

    # ============================================================
    # 模块 2: 数据加载与预处理
    # ============================================================
    raw_data_groups = []  # 存储原始数据的列表

    # 遍历所有输入文件，加载数据
    for file in file_list:
        # 检查文件是否存在，避免后续错误
        if not os.path.exists(file):
            raise FileNotFoundError(f"找不到文件，请检查绝对路径: {file}")

        # 读取CSV文件，header=0表示第一行为列名
        # .T 进行转置：使每行代表一个样本，每列代表一个时间点
        data = pd.read_csv(file, header=0).T
        raw_data_groups.append(data.values)

    # --- 数据平衡处理 ---
    # 找出所有组中最小的样本数，确保各组样本数相同（SPM要求平衡设计）

    min_n = min([d.shape[0] for d in raw_data_groups])
    # 截断各组数据至相同样本数，创建平衡数据集
    balanced_groups = [d[:min_n, :] for d in raw_data_groups]
    # 垂直堆叠所有组数据，形成SPM输入矩阵Y (形状: 总样本数 × 时间点数)
    Y = np.vstack(balanced_groups)

    # ============================================================
    # 模块 3: SPM统计计算 (核心分析)
    # ============================================================
    # --- 创建因素编码向量 ---
    # FACTOR_A: 组间因素 (如 Amateur vs Elite)
    # 使用np.repeat重复编码，例如 [0,0,0,0,0,0, 1,1,1,1,1,1]
    FACTOR_A = np.repeat(np.arange(factor_A_levels), factor_B_levels * min_n)

    # FACTOR_B: 组内因素 (如 T1, T2, T3 刚度)
    # 使用np.tile和np.repeat组合编码，例如 [0,0,0, 1,1,1, 2,2,2, 0,0,0, 1,1,1, 2,2,2]
    FACTOR_B = np.tile(np.repeat(np.arange(factor_B_levels), min_n), factor_A_levels)

    # --- 执行双因素方差分析 ---
    # spm1d.stats.anova2: 双因素方差分析
    # equal_var=True: 假设方差齐性
    s = spm1d.stats.anova2(Y, FACTOR_A, FACTOR_B, equal_var=True)

    # --- 统计推断 ---
    # inference(alpha): 基于随机场理论进行多重比较校正
    # alpha: 显著性水平（默认0.05）
    si = s.inference(alpha)

    # ============================================================
    # 模块 4: 画布初始化与均值曲线绘制
    # ============================================================
    # --- 创建画布 ---
    # figsize=(12, 9): 画布尺寸（英寸），适合论文插图
    # dpi=600: 高分辨率，满足期刊投稿要求
    fig, ax = plt.subplots(figsize=(12, 9), dpi=600)

    # --- 定义配色方案 ---
    # 使用渐变色区分不同刚度水平：浅→深
    # Group1 (Amateur): 红色系渐变
    # Group2 (Elite): 绿色系渐变
    line_colors = ['#FF9999', '#FF3333', '#990000',  # Group1: AM-LS, AM-MS, AM-HS
                   '#99FF99', '#33CC33', '#006600']  # Group2: ET-LS, ET-MS, ET-HS

    # 【图例说明】：此处定义的labels用于图例显示
    # AM = Amateur (业余), ET = Elite (精英)
    # LS = Low Stiffness (低刚度), Ms = Medium (中), Hs = High (高)
    labels = ["AM-LS", "AM-MS", "AM-HS", "ET-LS", "ET-MS", "ET-HS"]

    # --- 绘制均值曲线和标准差填充 ---
    # x轴：步态周期百分比（0-100%）
    x = np.linspace(0, 100, Y.shape[1])

    for i, data in enumerate(balanced_groups):
        # 计算均值和标准差（沿样本维度axis=0）
        mean = np.mean(data, axis=0)
        std = np.std(data, axis=0)

        # 绘制标准差填充区域（半透明）
        # zorder=2: 图层顺序，确保填充在底层
        ax.fill_between(x, mean - std, mean + std, color=line_colors[i],
                        alpha=0.1, edgecolor='none', zorder=2)

        # 绘制均值曲线（实线）
        # label=labels[i]: 绑定图例标签
        # lw=3: 线宽3像素
        # zorder=3: 确保曲线在填充区域之上
        ax.plot(x, mean, color=line_colors[i], lw=3, label=labels[i], zorder=3)
    
    # ============================================================
    # 模块 5: 显著性标识标注 & 收集统计数据
    # ============================================================
    # 获取当前Y轴范围，用于计算显著性标注条带的位置
    data_ymin, data_ymax = ax.get_ylim()
    y_range = data_ymax - data_ymin

    # 计算显著性条带的尺寸参数
    bar_h = y_range * 0.05    # 每个条带的高度（占Y轴范围的5%）
    gap = y_range * 0.03      # 条带之间的间隙（占Y轴范围的3%）
    base_y = data_ymin - (y_range * 0.15)  # 基准线位置（数据区域下方15%处）

    # 定义要绘制的三种效应类型：主效应A、主效应B、交互效应
    # si[0]=主效应A, si[1]=主效应B, si[2]=交互效应
    effects = [
        (si[0], f"Main Effect: {factor_A_name}", "#000000"),  # 因素A主效应（黑色标签）
        (si[1], f"Main Effect: {factor_B_name}", "#000000"),  # 因素B主效应（黑色标签）
        (si[2], "Interaction Effect", "#000000")             # 交互效应（黑色标签）
    ]

    # 存储显著性区间的统计数据，用于后续导出CSV报告
    sig_stats_data = []

    # 遍历每种效应类型，绘制显著性条带
    for i, (si_effect, name, color) in enumerate(effects):
        # 计算当前条带的顶部和底部位置
        top = base_y - i * (bar_h + gap)
        bottom = top - bar_h

        # 绘制背景条带（浅灰色，表示整个时间范围0-100%）
        ax.fill_between([0, 100], bottom, top, color='#F2F2F2',
                        zorder=1, clip_on=False, alpha=0.8)

        # 遍历所有显著性簇（clusters），绘制显著区间
        for cluster in si_effect.clusters:
            # 只处理p值小于显著性阈值的簇
            if cluster.P < alpha:
                # --- 绘制显著性区间条带（蓝色高亮）---
                ax.fill_between([cluster.endpoints[0], cluster.endpoints[1]],
                                bottom, top, color='#4A90E2',
                                zorder=2, clip_on=False, alpha=0.2)

                # --- 添加p值标注 ---
                # 计算文本位置（区间中点），显示p值（保留3位小数）
                ax.text((cluster.endpoints[0] + cluster.endpoints[1]) / 2, bottom,
                        f'p={cluster.P:.3f}', ha='center', va='top',
                        fontsize=20, color='#E35B5B', fontweight='bold')

                # --- 收集统计数据用于CSV导出 ---
                sig_stats_data.append({
                    "Effect_Type": name,                                    # 效应类型名称
                    "Start_Phase_(%)": round(cluster.endpoints[0], 2),       # 显著区间起始点
                    "End_Phase_(%)": round(cluster.endpoints[1], 2),         # 显著区间结束点
                    "Duration_(%)": round(cluster.endpoints[1] - cluster.endpoints[0], 2),  # 持续时长
                    "P_Value": round(cluster.P, 4)                          # p值（保留4位小数）
                })

        # --- 在条带左侧添加效应类型标签 ---
        ax.text(-2, (top + bottom) / 2, name, ha='right', va='center',
                fontsize=20, fontweight='bold', color=color)

    # ============================================================
    # 模块 6: 视觉美化与导出
    # ============================================================
    # 说明：本模块负责设置图表标题、坐标轴标签、图例、样式等视觉元素
    if plot_title:  # 如果大标题为空，则不添加
        ax.set_title(plot_title, fontsize=20, pad=30, fontweight='bold')

    ax.set_xlabel(x_label, fontsize=20, fontweight='bold')
    ax.set_ylabel(y_label, fontsize=20, fontweight='bold')

    ax.set_xlim(0, 100)
    ax.set_ylim(data_ymin, data_ymax)

    # ==================== 【图例控制开关 开始】 ====================
    # 功能说明：如果你不需要画图例，请把下面这三行代码全部注释掉（在前面加 #）。
    # 需要图例时，再把 # 删掉即可。
    
    # 1. 绘制图例：loc='upper right'为右上角，frameon=False去掉边框，fontsize设置字号
    leg = ax.legend(loc='upper right', frameon=False, fontsize=16)
    # 2. 遍历图例中的文字，将其设置为加粗
    for text in leg.get_texts():
        text.set_fontweight('bold')
        
    # ==================== 【图例控制开关 结束】 ====================

    axis_linewidth = 2.0
    ax.spines['left'].set_linewidth(axis_linewidth)
    ax.spines['bottom'].set_linewidth(axis_linewidth)
    ax.tick_params(axis='both', which='major', width=axis_linewidth, length=6, direction='out', labelsize=20)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()
    print(f"🎉 绘图成功！图片已保存至: {save_path}")

    # ============================================================
    # 模块 7: 导出 SPM 统计显著性报告 (区间摘要 CSV)
    # ============================================================
    # 将显著性统计数据转换为DataFrame
    df_sig = pd.DataFrame(sig_stats_data)
    # 生成CSV文件路径（将.png替换为_SPM_Stats_Summary.csv）
    csv_save_path = save_path.replace(".png", "_SPM_Stats_Summary.csv")

    if df_sig.empty:
        df_sig = pd.DataFrame([{
            "Effect_Type": "No significant effects found",
            "Start_Phase_(%)": "-", "End_Phase_(%)": "-", "Duration_(%)": "-", "P_Value": "-"
        }])
    df_sig.to_csv(csv_save_path, index=False, encoding='utf-8-sig')
    print(f"📄 显著性区间摘要已导出至: {csv_save_path}")

    # ============================================================
    # 模块 8: 导出 SPM 全过程 F值曲线数据 (详细数据 CSV)
    # ============================================================
    # 获取每一帧的 F/Z 统计值和对应的临界阈值 (zstar)
    # si[0]=主效应A, si[1]=主效应B, si[2]=交互效应
    # .z 属性包含每个时间点的F统计量（或Z统计量）
    # .zstar 属性包含临界阈值（超过此值表示显著）
    df_curves = pd.DataFrame({
        "Stance_(%)": x,                                     # 步态周期百分比
        f"F_Value_Main_{factor_A_name}": si[0].z,            # 因素A主效应的F值曲线
        f"Threshold_Main_{factor_A_name}": si[0].zstar,    # 因素A主效应的临界阈值
        f"F_Value_Main_{factor_B_name}": si[1].z,          # 因素B主效应的F值曲线
        f"Threshold_Main_{factor_B_name}": si[1].zstar,    # 因素B主效应的临界阈值
        "F_Value_Interaction": si[2].z,                      # 交互效应的F值曲线
        "Threshold_Interaction": si[2].zstar               # 交互效应的临界阈值
    })
    # 生成CSV文件路径（将.png替换为_SPM_Curves_Full.csv）
    curves_csv_path = save_path.replace(".png", "_SPM_Curves_Full.csv")
    # 导出为CSV文件
    df_curves.to_csv(curves_csv_path, index=False, encoding='utf-8-sig')
    print(f"📈 连续F值统计曲线数据已导出至: {curves_csv_path}")


# ================= 执行入口：单文件自定义处理 =================
if __name__ == "__main__":
    """
    主执行入口：配置参数并调用绘图函数

    使用说明：
    -----------
    1. 修改 BASE_DIR 指向你的数据根目录
    2. 修改 DATA_TYPE_FOLDER 选择数据类型（Joint_angle / Moment / AT_Force等）
    3. 修改 METRIC_NAME 设置要分析的具体指标名称
    4. 修改 SAVE_FILE_PATH 设置输出图片保存位置
    5. 修改 MY_PLOT_TITLE, MY_X_LABEL, MY_Y_LABEL 自定义图表标签
    6. 运行脚本，自动生成SPM分析图和配套CSV数据文件
    """
    print("\n>>>> 正在处理单张图表 <<<<")

    # 🎯 1. 设置根目录和想要分析的指标名
    # BASE_DIR: 数据文件的根目录路径
    BASE_DIR = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data\Interpolte_Average"
    # DATA_TYPE_FOLDER: 数据类型子文件夹名称
    # 可选值: "Joint_angle"(关节角度), "Moment"(力矩), "AT_Force"(肌腱力), "GRF"(地面反作用力)等
    DATA_TYPE_FOLDER = "AT_Force"
    # METRIC_NAME: 具体的指标名称（对应CSV文件名，不含扩展名）
    # 示例: "IK_ankle_angle_r"(右踝角度), "IK_knee_angle_l"(左膝角度), "AT_Total_Force_r"(右踝总肌腱力)
    METRIC_NAME = "AT_Total_Force_r"

    # 🎯 2. 定义图片保存位置和名称
    # SAVE_FILE_PATH: 输出图片的完整路径（自动使用METRIC_NAME作为文件名）
    SAVE_FILE_PATH = os.path.join(
        r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data\SPM_Picture\AT_Force\Label",
        f"{METRIC_NAME}.png"
    )

    # 🎯 3. 定义您的标题和坐标轴名称！(大标题留空即代表不显示)
    # MY_PLOT_TITLE: 图表主标题（空字符串表示不显示标题）
    MY_PLOT_TITLE = ""
    # MY_X_LABEL: X轴标签（默认"Stance (%)"表示步态周期百分比）
    MY_X_LABEL = "Stance (%)"
    # MY_Y_LABEL: Y轴标签（根据分析指标自定义，需包含单位和方向）
    # 示例: "Right Ankle Angle (°)", "Right Knee Moment (N·m/kg)", "Force (Body Weight, BW)"
    MY_Y_LABEL = "Achilles Tendon Force(BW)"

    # 🎯 4. 自动拼接 6 个文件的绝对路径 (从此不用再手敲了！)
    # 文件路径结构说明：
    # - BASE_DIR/Amateur_Runner/T1/DATA_TYPE_FOLDER/METRIC_NAME.csv (业余-低刚度)
    # - BASE_DIR/Amateur_Runner/T2/DATA_TYPE_FOLDER/METRIC_NAME.csv (业余-中刚度)
    # - BASE_DIR/Amateur_Runner/T3/DATA_TYPE_FOLDER/METRIC_NAME.csv (业余-高刚度)
    # - BASE_DIR/Elite_Runner/T1/DATA_TYPE_FOLDER/METRIC_NAME.csv (精英-低刚度)
    # - BASE_DIR/Elite_Runner/T2/DATA_TYPE_FOLDER/METRIC_NAME.csv (精英-中刚度)
    # - BASE_DIR/Elite_Runner/T3/DATA_TYPE_FOLDER/METRIC_NAME.csv (精英-高刚度)
    MY_FILE_LIST = [
        os.path.join(BASE_DIR, r"Amateur_Runner\T1", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Amateur_Runner\T2", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Amateur_Runner\T3", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Elite_Runner\T1", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Elite_Runner\T2", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Elite_Runner\T3", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv")
    ]

    # 执行绘图函数
    # 使用try-except捕获可能的异常，确保脚本不会崩溃
    try:
        spm_integrated_plot(
            file_list=MY_FILE_LIST,        # 6个CSV文件的完整路径列表
            factor_A_levels=2,              # 因素A（Group）的水平数：2（Amateur, Elite）
            factor_B_levels=3,              # 因素B（Stiffness）的水平数：3（T1, T2, T3）
            factor_A_name="Group",          # 因素A的名称
            factor_B_name="Stiffness",      # 因素B的名称
            save_path=SAVE_FILE_PATH,       # 输出图片保存路径
            plot_title=MY_PLOT_TITLE,       # 图表主标题
            x_label=MY_X_LABEL,             # X轴标签
            y_label=MY_Y_LABEL              # Y轴标签
        )
    except Exception as e:
        # 捕获并打印异常信息，帮助用户排查问题
        print(f"!!! 绘图或导出失败，错误信息: {e}")