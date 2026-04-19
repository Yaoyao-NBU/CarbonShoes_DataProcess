import spm1d
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


# ================= 辅助函数：格式化标题 =================
def format_power_title(filename):
    """
    把复杂的文件名转换为简洁的标题
    例如: "Time_Series_Power_knee_angle_r" -> "Knee Power"
    """
    # 1. 去掉前缀
    name = filename.replace("Time_Series_Power_", "")
    # 2. 去掉后缀
    name = name.replace("_angle_r", "").replace("_flexion_r", "").replace("_r", "")
    # 3. 首字母大写并加 Power
    return f"{name.title()} Power"


# ================= 核心绘图函数 =================
def spm_integrated_plot(file_list, factor_A_levels, factor_B_levels,
                        factor_A_name="Group", factor_B_name="Stiffness",
                        alpha=0.05, save_path="SPM_Integrated_Result.png",
                        plot_title="Joint Power",
                        y_label="Power (W/kg)"):  # <-- 修改点：增加 y_label 参数
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
        try:
            # 读取数据: 行=时间(101)，列=受试者 -> 转置为 (受试者, 时间)
            data = pd.read_csv(file, header=0).T
            raw_data_groups.append(data.values)
        except Exception as e:
            print(f"读取文件失败: {file}\n错误: {e}")
            return

    # 确保样本量一致 (截断到最小样本量)
    if not raw_data_groups:
        return
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

    # 定义颜色：粉红/红/深红 (Amateur), 浅绿/绿/深绿 (Elite)
    line_colors = ['#FF9999', '#FF3333', '#990000',
                   '#99FF99', '#33CC33', '#006600']
    labels = ["AM-LS", "AM-Ms", "AM-Hs", "ET-Ls", "ET-Ms", "ET-Hs"]

    # X轴 (0-100%)
    x = np.linspace(0, 100, Y.shape[1])

    for i, data in enumerate(balanced_groups):
        mean = np.mean(data, axis=0)
        std = np.std(data, axis=0)
        # 绘制标准差阴影
        ax.fill_between(x, mean - std, mean + std, color=line_colors[i],
                        alpha=0.1, edgecolor='none', zorder=2)
        # 绘制均值线
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

        # 背景灰条
        ax.fill_between([0, 100], bottom, top, color='#F2F2F2',
                        zorder=1, clip_on=False, alpha=0.8)

        # 显著区域高亮
        for cluster in si_effect.clusters:
            if cluster.P < alpha:
                ax.fill_between([cluster.endpoints[0], cluster.endpoints[1]],
                                bottom, top, color='#4A90E2',
                                zorder=2, clip_on=False, alpha=0.5)
                # P值标注
                ax.text((cluster.endpoints[0] + cluster.endpoints[1]) / 2, bottom,
                        f'p={cluster.P:.3f}', ha='center', va='top',
                        fontsize=12, color='#E35B5B', fontweight='bold')

        ax.text(-2, (top + bottom) / 2, name, ha='right', va='center',
                fontsize=14, fontweight='bold', color=color)

    """
    模块 6: 视觉美化与导出
    """
    ax.set_title(plot_title, fontsize=20, pad=35, fontweight='bold')  # 标题字体加大

    ax.set_xlabel("Stance (%)", fontsize=16, fontweight='bold')
    ax.set_ylabel(y_label, fontsize=16, fontweight='bold')  # <-- 使用传入的 y_label
    ax.set_xlim(0, 100)

    # 自动调整Y轴范围，给下方的显著性条留出空间
    ax.set_ylim(data_ymin - y_range * 0.45, data_ymax)

    leg = ax.legend(loc='upper right', bbox_to_anchor=(1.0, 1.0), frameon=False, fontsize=10)
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
    print(f"--- 绘图成功: {plot_title}")


# ================= 执行入口 =================
if __name__ == "__main__":
    # 1. 路径设置 (指向归一化后的功率数据文件夹)
    # 请确认这里是您存放 "Time_Series_Power_..." 文件（且已插值到101点）的根目录
    base_dir = r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Result_Average"
    save_dir = r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\Picture\Power_Pictures"

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 2. 待处理的功率指标列表 (文件名，不带后缀)
    target_metrics = [
        "Time_Series_Power_ankle_angle_r",
        "Time_Series_Power_knee_angle_r",
        "Time_Series_Power_hip_flexion_r",
        "Time_Series_Power_mtp_angle_r"
    ]

    # 3. 假设子文件夹名为 'Joint_Power' (如果您的文件直接在 T1 下，请删除 'Joint_Power')
    # 根据之前的步骤，文件可能在 ...\T1\Joint_Power\ 下，也可能直接在 ...\T1\ 下
    # 这里我保留 Joint_Power，如果报错找不到文件，请删除它
    sub_folder = "Joint_Power"  # 如果文件在 T1/Joint_Power 下，改成 "Joint_Power"

    for metric in target_metrics:
        print(f"\n>>>> 正在开始处理指标: {metric} <<<<")

        # 4. 动态拼接 6 个组的文件路径
        # 注意：这里假设目录结构为: base_dir \ Amateur_Runner \ T1 \ [sub_folder] \ metric.csv
        current_files = [
            os.path.join(base_dir, r"Amateur_Runner\T1", sub_folder, f"{metric}.csv"),
            os.path.join(base_dir, r"Amateur_Runner\T2", sub_folder, f"{metric}.csv"),
            os.path.join(base_dir, r"Amateur_Runner\T3", sub_folder, f"{metric}.csv"),
            os.path.join(base_dir, f"Elite_Runner\T1", sub_folder, f"{metric}.csv"),
            os.path.join(base_dir, f"Elite_Runner\T2", sub_folder, f"{metric}.csv"),
            os.path.join(base_dir, f"Elite_Runner\T3", sub_folder, f"{metric}.csv"),
        ]

        # 5. 文件检查
        missing_files = [f for f in current_files if not os.path.exists(f)]
        if missing_files:
            print(f"[警告] {metric} 缺少 {len(missing_files)} 个数据文件。路径示例:\n{missing_files[0]}")
            continue

        # 6. 生成美化的标题和保存路径
        display_title = format_power_title(metric)  # 自动变成 "Knee Power"
        current_save_path = os.path.join(save_dir, f"{display_title}.png")

        # 7. 调用函数
        try:
            spm_integrated_plot(
                file_list=current_files,
                factor_A_levels=2,
                factor_B_levels=3,
                factor_A_name="Group",
                factor_B_name="Stiffness",
                save_path=current_save_path,
                plot_title=display_title,  # 传入 "Knee Power"
                y_label="Power (W/kg)"  # 传入功率单位
            )
        except Exception as e:
            print(f"[错误] {metric} 绘图失败: {e}")

    print("\n" + "=" * 30)
    print("所有功率图表绘制完成！")
    print("=" * 30)