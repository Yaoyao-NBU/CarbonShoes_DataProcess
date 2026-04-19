import spm1d
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


# ================= 核心绘图函数 =================
def spm_integrated_plot(file_list, factor_A_levels, factor_B_levels,
                        factor_A_name="Group", factor_B_name="Stiffness",
                        alpha=0.05, save_path="SPM_Integrated_Result.png",
                        plot_title="",  # 默认设为空
                        x_label="Stance (%)", y_label="Angle (°)"):
    """
    模块 1: 全局环境配置
    """
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['axes.unicode_minus'] = False

    """
    模块 2: 数据加载与预处理
    """
    raw_data_groups = []
    for file in file_list:
        if not os.path.exists(file):
            raise FileNotFoundError(f"找不到文件，请检查绝对路径: {file}")
        data = pd.read_csv(file, header=0).T
        raw_data_groups.append(data.values)

    min_n = min([d.shape[0] for d in raw_data_groups])
    balanced_groups = [d[:min_n, :] for d in raw_data_groups]
    Y = np.vstack(balanced_groups)

    """
    模块 3: 统计计算 (SPM 核心)
    """
    FACTOR_A = np.repeat(np.arange(factor_A_levels), factor_B_levels * min_n)
    FACTOR_B = np.tile(np.repeat(np.arange(factor_B_levels), min_n), factor_A_levels)

    s = spm1d.stats.anova2(Y, FACTOR_A, FACTOR_B, equal_var=True)
    si = s.inference(alpha)

    """
    模块 4: 画布初始化与均值曲线绘制
    """
    fig, ax = plt.subplots(figsize=(12, 9), dpi=300)

    line_colors = ['#FF9999', '#FF3333', '#990000',  # Group1 (Amateur)
                   '#99FF99', '#33CC33', '#006600']  # Group2 (Elite)
    labels = ["AM-LS", "AM-Ms", "AM-Hs", "ET-Ls", "ET-Ms", "ET-Hs"]

    x = np.linspace(0, 100, Y.shape[1])
    for i, data in enumerate(balanced_groups):
        mean = np.mean(data, axis=0)
        std = np.std(data, axis=0)
        ax.fill_between(x, mean - std, mean + std, color=line_colors[i],
                        alpha=0.1, edgecolor='none', zorder=2)
        ax.plot(x, mean, color=line_colors[i], lw=3, label=labels[i], zorder=3)

    """
    模块 5: 显著性标识标注 & 收集统计数据
    """
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

    # 存放区间报告的数据
    sig_stats_data = []

    for i, (si_effect, name, color) in enumerate(effects):
        top = base_y - i * (bar_h + gap)
        bottom = top - bar_h
        ax.fill_between([0, 100], bottom, top, color='#F2F2F2',
                        zorder=1, clip_on=False, alpha=0.8)

        for cluster in si_effect.clusters:
            if cluster.P < alpha:
                # 记录画图
                ax.fill_between([cluster.endpoints[0], cluster.endpoints[1]],
                                bottom, top, color='#4A90E2',
                                zorder=2, clip_on=False, alpha=0.2)
                ax.text((cluster.endpoints[0] + cluster.endpoints[1]) / 2, bottom,
                        f'p={cluster.P:.3f}', ha='center', va='top',
                        fontsize=12, color='#E35B5B', fontweight='bold')

                # 记录显著区间详情
                sig_stats_data.append({
                    "Effect_Type": name,
                    "Start_Phase_(%)": round(cluster.endpoints[0], 2),
                    "End_Phase_(%)": round(cluster.endpoints[1], 2),
                    "Duration_(%)": round(cluster.endpoints[1] - cluster.endpoints[0], 2),
                    "P_Value": round(cluster.P, 4)
                })

        ax.text(-2, (top + bottom) / 2, name, ha='right', va='center',
                fontsize=10, fontweight='bold', color=color)

    """
    模块 6: 视觉美化与导出
    """
    if plot_title:  # 如果大标题为空，则不添加
        ax.set_title(plot_title, fontsize=14, pad=35, fontweight='bold')

    ax.set_xlabel(x_label, fontsize=12, fontweight='bold')
    ax.set_ylabel(y_label, fontsize=12, fontweight='bold')

    ax.set_xlim(0, 100)
    ax.set_ylim(data_ymin, data_ymax)

    leg = ax.legend(loc='upper right', frameon=False, fontsize=10)
    for text in leg.get_texts():
        text.set_fontweight('bold')

    axis_linewidth = 2.0
    ax.spines['left'].set_linewidth(axis_linewidth)
    ax.spines['bottom'].set_linewidth(axis_linewidth)
    ax.tick_params(axis='both', which='major', width=axis_linewidth, length=6, direction='out', labelsize=10)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()
    print(f"🎉 绘图成功！图片已保存至: {save_path}")

    """
    模块 7: 导出 SPM 统计显著性报告 (区间摘要 CSV)
    """
    df_sig = pd.DataFrame(sig_stats_data)
    csv_save_path = save_path.replace(".png", "_SPM_Stats_Summary.csv")

    if df_sig.empty:
        df_sig = pd.DataFrame([{
            "Effect_Type": "No significant effects found",
            "Start_Phase_(%)": "-", "End_Phase_(%)": "-", "Duration_(%)": "-", "P_Value": "-"
        }])
    df_sig.to_csv(csv_save_path, index=False, encoding='utf-8-sig')
    print(f"📄 显著性区间摘要已导出至: {csv_save_path}")

    """
    模块 8: 导出 SPM 全过程 F值曲线数据 (详细数据 CSV)
    """
    # 获取每一帧的 F/Z 统计值和对应的临界阈值 (zstar)
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
    print(f"📈 连续F值统计曲线数据已导出至: {curves_csv_path}")


# ================= 执行入口：单文件自定义处理 =================
if __name__ == "__main__":

    print("\n>>>> 正在处理单张图表 <<<<")

    # 🎯 1. 设置根目录和想要分析的指标名
    BASE_DIR = r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Result_Average"
    DATA_TYPE_FOLDER = "Joint_angle"  # 你的数据存放子文件夹（比如 Joint_angle 或 Moment）
    METRIC_NAME = "IK_hip_adduction_r"  # 想要处理的指标名称

    # 🎯 2. 定义图片保存位置和名称
    SAVE_FILE_PATH = os.path.join(
        r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\Picture_For_Paper",
        f"{METRIC_NAME}.png"
    )

    # 🎯 3. 定义您的标题和坐标轴名称！(大标题留空即代表不显示)
    MY_PLOT_TITLE = ""
    MY_X_LABEL = "Stance (%)"
    MY_Y_LABEL = "Right Hip Adduction Angle(°)"

    # 🎯 4. 自动拼接 6 个文件的绝对路径 (从此不用再手敲了！)
    MY_FILE_LIST = [
        os.path.join(BASE_DIR, r"Amateur_Runner\T1", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Amateur_Runner\T2", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Amateur_Runner\T3", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Elite_Runner\T1", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Elite_Runner\T2", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv"),
        os.path.join(BASE_DIR, r"Elite_Runner\T3", DATA_TYPE_FOLDER, f"{METRIC_NAME}.csv")
    ]

    # 执行绘图函数
    try:
        spm_integrated_plot(
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