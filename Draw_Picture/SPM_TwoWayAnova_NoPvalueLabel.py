"""
SPM双因素方差分析信号图绘制脚本（无p值标注版本）
=================================================

功能说明：
-----------
本脚本用于对二维步态数据进行SPM（Statistical Parametric Mapping，统计参数映射）
双因素方差分析，并绘制包含以下内容的综合性结果图：
    - 各组均值曲线（带标准差填充区域）
    - 主效应和交互效应的显著性区间标注（仅色带，不显示p值文字）
    - 显著性区间范围和p值导出至CSV表格（供后续手动标注使用）

与原版的区别：
-----------
- 移除了图上直接显示的 p值文字标注（避免多个相邻显著区间时文字重叠）
- 显著性区间信息（起止位置、p值）完整导出到CSV表格中
- 图表更干净，适合后续用画图软件手动添加标注

数据格式要求：
---------------
输入数据为CSV文件，每行代表一个样本的完整步态周期数据，每列代表一个时间点。
数据应按以下组别顺序排列：
    - Group 1: 业余跑者 (Amateur) - T1, T2, T3
    - Group 2: 精英跑者 (Elite) - T1, T2, T3

作者：Yaoyao_Lin
日期：2026-05-13
"""
import spm1d
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


def spm_plot_no_pvalue(file_list, factor_A_levels, factor_B_levels,
                       factor_A_name="Group", factor_B_name="Stiffness",
                       alpha=0.05, save_path="SPM_Integrated_Result.png",
                       plot_title="", x_label="Stance (%)", y_label="Angle (°)"):
    """
    绘制SPM双因素方差分析结果图（无p值文字标注）

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
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['axes.unicode_minus'] = False

    # ============================================================
    # 模块 2: 数据加载与预处理
    # ============================================================
    raw_data_groups = []

    for file in file_list:
        if not os.path.exists(file):
            raise FileNotFoundError(f"找不到文件，请检查绝对路径: {file}")
        data = pd.read_csv(file, header=0).T
        raw_data_groups.append(data.values)

    # --- 数据平衡处理 ---
    min_n = min([d.shape[0] for d in raw_data_groups])
    balanced_groups = [d[:min_n, :] for d in raw_data_groups]
    Y = np.vstack(balanced_groups)

    # ============================================================
    # 模块 3: SPM统计计算
    # ============================================================
    FACTOR_A = np.repeat(np.arange(factor_A_levels), factor_B_levels * min_n)
    FACTOR_B = np.tile(np.repeat(np.arange(factor_B_levels), min_n), factor_A_levels)

    s = spm1d.stats.anova2(Y, FACTOR_A, FACTOR_B, equal_var=True)
    si = s.inference(alpha)

    # ============================================================
    # 模块 4: 画布初始化与均值曲线绘制
    # ============================================================
    fig, ax = plt.subplots(figsize=(12, 9), dpi=600)

    # --- 配色方案 ---
    line_colors = ['#FF9999', '#FF3333', '#990000',  # Group1: AM-LS, AM-MS, AM-Hs
                   '#99FF99', '#33CC33', '#006600']  # Group2: ET-LS, ET-MS, ET-HS

    labels = ["AM-LS", "AM-MS", "AM-HS", "ET-LS", "ET-MS", "ET-HS"]

    # --- 绘制均值曲线和标准差填充 ---
    x = np.linspace(0, 100, Y.shape[1])

    for i, data in enumerate(balanced_groups):
        mean = np.mean(data, axis=0)
        std = np.std(data, axis=0)
        ax.fill_between(x, mean - std, mean + std, color=line_colors[i],
                        alpha=0.1, edgecolor='none', zorder=2)
        ax.plot(x, mean, color=line_colors[i], lw=3, label=labels[i], zorder=3)

    # ============================================================
    # 模块 5: 显著性条带绘制（仅色带，无p值文字）
    # ============================================================
    data_ymin, data_ymax = ax.get_ylim()
    y_range = data_ymax - data_ymin

    bar_h = y_range * 0.05
    gap = y_range * 0.03
    base_y = data_ymin - (y_range * 0.15)

    effects = [
        (si[0], f"Main Effect: {factor_A_name}", "#000000"),
        (si[1], f"Main Effect: {factor_B_name}", "#000000"),
        (si[2], "Interaction Effect", "#000000")
    ]

    sig_stats_data = []

    for i, (si_effect, name, color) in enumerate(effects):
        top = base_y - i * (bar_h + gap)
        bottom = top - bar_h

        # 背景条带
        ax.fill_between([0, 100], bottom, top, color='#F2F2F2',
                        zorder=1, clip_on=False, alpha=0.8)

        # 显著性区间条带（仅色带，不添加p值文字）
        for cluster in si_effect.clusters:
            if cluster.P < alpha:
                ax.fill_between([cluster.endpoints[0], cluster.endpoints[1]],
                                bottom, top, color='#4A90E2',
                                zorder=2, clip_on=False, alpha=0.2)

                # 收集统计数据用于CSV导出
                sig_stats_data.append({
                    "Effect_Type": name,
                    "Start_Phase_(%)": round(cluster.endpoints[0], 2),
                    "End_Phase_(%)": round(cluster.endpoints[1], 2),
                    "Duration_(%)": round(cluster.endpoints[1] - cluster.endpoints[0], 2),
                    "P_Value": round(cluster.P, 4)
                })

        # 条带左侧效应类型标签
        ax.text(-2, (top + bottom) / 2, name, ha='right', va='center',
                fontsize=20, fontweight='bold', color=color)

    # ============================================================
    # 模块 6: 视觉美化与导出
    # ============================================================
    if plot_title:
        ax.set_title(plot_title, fontsize=20, pad=30, fontweight='bold')

    ax.set_xlabel(x_label, fontsize=20, fontweight='bold')
    ax.set_ylabel(y_label, fontsize=20, fontweight='bold')

    ax.set_xlim(0, 100)
    ax.set_ylim(data_ymin, data_ymax)

    # ==================== 【图例控制开关 开始】 ====================
    # 如果不需要图例，把下面三行注释掉即可
    # leg = ax.legend(loc='upper right', frameon=False, fontsize=16)
    # for text in leg.get_texts():
        # text.set_fontweight('bold')
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
    print(f"绘图成功！图片已保存至: {save_path}")

    # ============================================================
    # 模块 7: 导出显著性区间摘要 CSV
    # ============================================================
    df_sig = pd.DataFrame(sig_stats_data)
    csv_save_path = save_path.replace(".png", "_SPM_Stats_Summary.csv")

    if df_sig.empty:
        df_sig = pd.DataFrame([{
            "Effect_Type": "No significant effects found",
            "Start_Phase_(%)": "-", "End_Phase_(%)": "-", "Duration_(%)": "-", "P_Value": "-"
        }])
    df_sig.to_csv(csv_save_path, index=False, encoding='utf-8-sig')
    print(f"显著性区间摘要已导出至: {csv_save_path}")

    # ============================================================
    # 模块 8: 导出 F值曲线数据 CSV
    # ============================================================
    df_curves = pd.DataFrame({
        "Stance_(%)": x,
        f"F_Value_Main_{factor_A_name}": si[0].z,
        f"Threshold_Main_{factor_A_name}": si[0].zstar,
        f"F_Value_Main_{factor_B_name}": si[1].z,
        f"Threshold_Main_{factor_B_name}": si[1].zstar,
        "F_Value_Interaction": si[2].z,
        "Threshold_Interaction": si[2].zstar
    })
    curves_csv_path = save_path.replace(".png", "_SPM_Curves_Full.csv")
    df_curves.to_csv(curves_csv_path, index=False, encoding='utf-8-sig')
    print(f"连续F值统计曲线数据已导出至: {curves_csv_path}")


# ================= 执行入口 =================
if __name__ == "__main__":
    print("\n>>>> 正在处理单张图表（无p值标注版本）<<<<")

    # 🎯 1. 设置根目录和想要分析的指标名
    BASE_DIR = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data\Interpolte_Average"
    DATA_TYPE_FOLDER = "Joint_angle"
    METRIC_NAME = "IK_knee_angle_r"

    # 🎯 2. 定义图片保存位置和名称
    SAVE_FILE_PATH = os.path.join(
        r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data\SPM_Picture\new_picture\Joint_angle",
        f"{METRIC_NAME}.png"
    )

    # 🎯 3. 定义标题和坐标轴名称
    MY_PLOT_TITLE = ""
    MY_X_LABEL = "Stance (%)"
    MY_Y_LABEL = "Right Knee Sagit.Angle(°)"  # 根据实际指标调整单位和名称

    # 🎯 4. 自动拼接 6 个文件的绝对路径
    MY_FILE_LIST = [
        os.path.join(BASE_DIR, r"Amateur_Runner\T1", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Amateur_Runner\T2", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Amateur_Runner\T3", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Elite_Runner\T1", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Elite_Runner\T2", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Elite_Runner\T3", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv")
    ]

    try:
        spm_plot_no_pvalue(
            file_list=MY_FILE_LIST,
            factor_A_levels=2,
            factor_B_levels=3,
            factor_A_name="Group",
            factor_B_name="Stiffness",
            save_path=SAVE_FILE_PATH,
            plot_title=MY_PLOT_TITLE,
            x_label=MY_X_LABEL,
            y_label=MY_Y_LABEL
        )
    except Exception as e:
        print(f"!!! 绘图或导出失败，错误信息: {e}")
