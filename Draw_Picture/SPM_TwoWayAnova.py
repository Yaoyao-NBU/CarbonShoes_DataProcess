import spm1d
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def spm_integrated_plot(file_list, factor_A_levels, factor_B_levels,
                        factor_A_name="Group", factor_B_name="Stiffness",
                        alpha=0.05, save_path="SPM_Integrated_Result.png"):
    """
    模块 1: 全局环境配置
    设置字体和图形的基础属性，确保导出图片的质量和兼容性。
    """
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['axes.unicode_minus'] = False  # 正常显示坐标轴负号

    """
    模块 2: 数据加载与预处理
    将 CSV 数据转换为 NumPy 矩阵，并处理生物力学分析中常见的样本量对齐问题。
    """
    raw_data_groups = []
    for file in file_list:
        # .T 转置：确保每一行代表一个受试者的连续时间序列 (通常为 101 个数据点)
        data = pd.read_csv(file, header=0).T
        raw_data_groups.append(data.values)

    # 自动截断：确保所有组的样本量 (行数) 与最小的那组一致，满足 SPM ANOVA 要求
    min_n = min([d.shape[0] for d in raw_data_groups])
    balanced_groups = [d[:min_n, :] for d in raw_data_groups]
    Y = np.vstack(balanced_groups)  # 垂直堆叠形成分析总矩阵

    """
    模块 3: 统计计算 (SPM 核心)
    执行统计分析并进行推断，获取显著性结果对象 si。
    """
    # 生成实验设计标签：如 Group (0,1) 和 Stiffness (0,1,2)
    FACTOR_A = np.repeat(np.arange(factor_A_levels), factor_B_levels * min_n)
    FACTOR_B = np.tile(np.repeat(np.arange(factor_B_levels), min_n), factor_A_levels)

    # 执行 Two-Way ANOVA 及其统计推断
    s = spm1d.stats.anova2(Y, FACTOR_A, FACTOR_B, equal_var=True)
    si = s.inference(alpha)

    """
    模块 4: 画布初始化与均值曲线绘制
    绘制 6 条均值线以及代表标准差 (SD) 的半透明阴影区域。
    """
    fig, ax = plt.subplots(figsize=(16, 9), dpi=300)

    # 颜色与图例标签定义
    line_colors = ['#FF9999', '#FF3333', '#990000', # Group1 (Amateur)
                   '#99FF99', '#33CC33', '#006600'] # Group2 (Elite)
    labels = ["AM-LS", "AM-Ms", "AM-Hs", "ET-Ls", "ET-Ms", "ET-Hs"]

    x = np.linspace(0, 100, Y.shape[1])  # 步态周期 0-100%
    for i, data in enumerate(balanced_groups):
        mean = np.mean(data, axis=0)
        std = np.std(data, axis=0)

        # 绘制 SD 阴影：alpha=0.1 确保多层重叠时依然可辨识
        ax.fill_between(x, mean - std, mean + std, color=line_colors[i],
                        alpha=0.1, edgecolor='none', zorder=2)
        # 绘制均值实线：lw=3 增强线条表现力
        ax.plot(x, mean, color=line_colors[i], lw=3, label=labels[i], zorder=3)

    """
    模块 5: 显著性标识标注 (核心修改部分)
    在 X 轴外侧绘制灰色底带、蓝色显著色块以及红色 P 值文字。
    """
    # 动态获取 Y 轴量程，用于确定轴外标识的相对偏移位置
    data_ymin, data_ymax = ax.get_ylim()
    y_range = data_ymax - data_ymin

    # 布局参数：bar_h(高度), gap(行距), base_y(起始位置)
    bar_h = y_range * 0.05
    gap = y_range * 0.03
    base_y = data_ymin - (y_range * 0.15)

    # 统计效应行配置
    effects = [
        (si[0], f"Main Effect: {factor_A_name}", "#000000"), # 主效应 A
        (si[1], f"Main Effect: {factor_B_name}", "#000000"), # 主效应 B
        (si[2], "Interaction Effect", "#000000")             # 交互作用
    ]

    for i, (si_effect, name, color) in enumerate(effects):
        top = base_y - i * (bar_h + gap)
        bottom = top - bar_h

        # A. 绘制背景条：clip_on=False 允许在轴外渲染，alpha=0.8 保持清晰度
        ax.fill_between([0, 100], bottom, top, color='#F2F2F2',
                        zorder=1, clip_on=False, alpha=0.8)

        # B. 绘制显著性簇 (Clusters)：若 P < 0.05 则填充淡蓝色块
        for cluster in si_effect.clusters:
            if cluster.P < alpha:
                ax.fill_between([cluster.endpoints[0], cluster.endpoints[1]],
                                bottom, top, color='#4A90E2', # 显著区域色块
                                zorder=2, clip_on=False, alpha=0.2)

                # C. 标注 P 值：使用红色 (#E35B5B) 加粗 14 号字，挂在方块下方 (va='top')
                ax.text((cluster.endpoints[0] + cluster.endpoints[1]) / 2, bottom,
                        f'p={cluster.P:.3f}', ha='center', va='top',
                        fontsize=14, color='#E35B5B', fontweight='bold')

        # D. 效应名称标注：放置在 Y 轴左侧 (-2% 处)
        ax.text(-2, (top + bottom) / 2, name, ha='right', va='center',
                fontsize=14, fontweight='bold', color=color)

    """
    模块 6: 视觉美化与导出
    设置标题、坐标轴粗细、图例样式及最终的文件保存。
    """
    # 文本与标题设置
    ax.set_title(f"AT Force", fontsize=16, pad=35, fontweight='bold')
    ax.set_xlabel("Stance (%)", fontsize=16, fontweight='bold')
    ax.set_ylabel("BW (%)", fontsize=16, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.set_ylim(data_ymin, data_ymax) # 锁定 Y 轴，确保标识不挤占绘图区

    # 图例精修：定位在图外右上角，文字加粗
    leg = ax.legend(loc='upper right', bbox_to_anchor=(1.18, 1.0), frameon=False, fontsize=10)
    for text in leg.get_texts():
        text.set_fontweight('bold')

    # 坐标轴外观设置：加粗 Spine (2.0) 和 Tick (6)
    axis_linewidth = 2.0
    ax.spines['left'].set_linewidth(axis_linewidth)
    ax.spines['bottom'].set_linewidth(axis_linewidth)
    ax.tick_params(axis='both', which='major', width=axis_linewidth, length=6, direction='out', labelsize=10)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    # 图像导出：bbox_inches='tight' 自动包含轴外所有元素
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    print(f"\n绘图成功！文件已保存至: {save_path}")
    plt.show()

# --- 执行入口 ---
if __name__ == "__main__":
    # 使用你原本的文件列表
    files = [
        r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\ceshi\out\Amateur_Runner\T1\Joint_angle\IK_mtp_angle_r.csv",
        r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\ceshi\out\Amateur_Runner\T2\Joint_angle\IK_mtp_angle_r.csv",
        r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\ceshi\out\Amateur_Runner\T3\Joint_angle\IK_mtp_angle_r.csv",
        r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\ceshi\out\Elite_Runner\T1\Joint_angle\IK_mtp_angle_r.csv",
        r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\ceshi\out\Elite_Runner\T2\Joint_angle\IK_mtp_angle_r.csv",
        r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\ceshi\out\Elite_Runner\T3\Joint_angle\IK_mtp_angle_r.csv",
    ]

    spm_integrated_plot(
        file_list=files,
        factor_A_levels=2,
        factor_B_levels=3,
        factor_A_name="Group",
        factor_B_name="Stiffness",
        save_path=r"G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Draw_Picture_data\ceshi\IK_knee_angle_r.png"
    )