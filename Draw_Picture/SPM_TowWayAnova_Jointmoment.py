import spm1d
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


# ================= 核心绘图函数（已修改） =================
def spm_integrated_plot(file_list, factor_A_levels, factor_B_levels,
                        factor_A_name="Group", factor_B_name="Stiffness",
                        alpha=0.05, save_path="SPM_Integrated_Result.png",
                        plot_title="Joint Angle"):  # <-- 修改1：增加接收参数位
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
    fig, ax = plt.subplots(figsize=(16, 9), dpi=300)

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
    模块 5: 显著性标识标注
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

    for i, (si_effect, name, color) in enumerate(effects):
        top = base_y - i * (bar_h + gap)
        bottom = top - bar_h
        ax.fill_between([0, 100], bottom, top, color='#F2F2F2',
                        zorder=1, clip_on=False, alpha=0.8)
        for cluster in si_effect.clusters:
            if cluster.P < alpha:
                ax.fill_between([cluster.endpoints[0], cluster.endpoints[1]],
                                bottom, top, color='#4A90E2',
                                zorder=2, clip_on=False, alpha=0.2)
                ax.text((cluster.endpoints[0] + cluster.endpoints[1]) / 2, bottom,
                        f'p={cluster.P:.3f}', ha='center', va='top',
                        fontsize=14, color='#E35B5B', fontweight='bold')
        ax.text(-2, (top + bottom) / 2, name, ha='right', va='center',
                fontsize=14, fontweight='bold', color=color)

    """
    模块 6: 视觉美化与导出
    """
    # 修改2：将固定标题改为传入的 plot_title
    ax.set_title(plot_title, fontsize=16, pad=35, fontweight='bold')

    ax.set_xlabel("Stance (%)", fontsize=16, fontweight='bold')
    ax.set_ylabel("BW (%)", fontsize=16, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.set_ylim(data_ymin, data_ymax)

    leg = ax.legend(loc='upper right', bbox_to_anchor=(1.18, 1.0), frameon=False, fontsize=10)
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
    plt.close()  # 批量处理时建议关闭画布，节省内存
    print(f"--- 绘图成功: {plot_title}")


# ================= 执行入口：批量处理逻辑 =================
if __name__ == "__main__":
    # 1. 路径设置
    base_dir = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data\Interpolte_Average"
    save_dir = r"G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_data\SPM_Picture\Test_picture\joint_moment"

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 2. 待处理指标列表
    target_metrics = [
        "ID_mtp_angle_r_moment", "ID_ankle_angle_r_moment", "ID_knee_angle_r_moment", "ID_hip_adduction_r_moment",
        "ID_hip_flexion_r_moment", "ID_hip_rotation_r_moment", "ID_subtalar_angle_r_moment",
         "ID_lumbar_bending_moment",
        "ID_lumbar_extension_moment", "ID_lumbar_rotation_moment", "ID_pelvis_list_moment",
        "ID_pelvis_rotation_moment", "ID_pelvis_tilt_moment", "ID_pelvis_tx_force", "ID_pelvis_ty_force", "ID_pelvis_tz_force"
    ]

    for metric in target_metrics:
        print(f"\n>>>> 正在开始处理指标: {metric} <<<<")

        # 3. 动态拼接 6 个组的文件路径
        current_files = [
            os.path.join(base_dir, r"Amateur_Runner\T1\Joint_moment", f"{metric}.csv"),
            os.path.join(base_dir, r"Amateur_Runner\T2\Joint_moment", f"{metric}.csv"),
            os.path.join(base_dir, r"Amateur_Runner\T3\Joint_moment", f"{metric}.csv"),
            os.path.join(base_dir, f"Elite_Runner\T1\Joint_moment", f"{metric}.csv"),
            os.path.join(base_dir, f"Elite_Runner\T2\Joint_moment", f"{metric}.csv"),
            os.path.join(base_dir, f"Elite_Runner\T3\Joint_moment", f"{metric}.csv"),
        ]

        # 4. 文件检查
        missing_files = [f for f in current_files if not os.path.exists(f)]
        if missing_files:
            print(f"[跳过] {metric} 缺少 {len(missing_files)} 个数据文件")
            continue

        # 5. 生成动态路径和标题
        current_save_path = os.path.join(save_dir, f"{metric}.png")
        display_title = metric.replace("_", " ").title()

        # 6. 调用函数
        try:
            spm_integrated_plot(
                file_list=current_files,
                factor_A_levels=2,
                factor_B_levels=3,
                factor_A_name="Group",
                factor_B_name="Stiffness",
                save_path=current_save_path,
                plot_title=display_title  # 传入动态标题
            )
        except Exception as e:
            print(f"[错误] {metric} 绘图失败: {e}")

    print("\n" + "=" * 30)
    print("所有批量画图任务已完成！")
    print("=" * 30)