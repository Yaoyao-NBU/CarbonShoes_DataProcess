import pandas as pd
import pingouin as pg
import os
import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# 1. 设置配置 (请在这里指定您的单个文件)
# ==========================================
TARGET_FILE = r'G:\Carbon_Plate_Shoes_Data\STO-Data_Processed\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Summary_Statistics_UnInterpolte\MinValue\Summary_Min_IK_hip_adduction_r.csv'
OUTPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\STO-Data_Processed\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Summary_Statistics_UnInterpolte\MinValue\Single_File_Stats_Result'

# 🎯 自定义您的图表 Y 轴标签
Y_AXIS_LABEL = 'Min R Hip.Add (°)'


# ==========================================
# 2. 自动绘图引擎 (完美兼容正负数，动态伸缩 Y 轴)
# ==========================================
def generate_auto_bar_plot(desc_stats, posthoc_df, feature_name, save_dir, y_label):
    plot_data = desc_stats[desc_stats['Stiffness'] != 'Total_Average'].copy()

    amateur_data = plot_data[plot_data['Group'] == 'Amateur'].set_index('Stiffness').reindex(['T1', 'T2', 'T3'])
    elite_data = plot_data[plot_data['Group'] == 'Elite'].set_index('Stiffness').reindex(['T1', 'T2', 'T3'])

    if amateur_data.empty or elite_data.empty or amateur_data['Mean'].isna().all():
        return

    labels = ['T1 (Low)', 'T2 (Medium)', 'T3 (High)']
    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)

    # 🌟 画大众组柱子
    ax.bar(x - width / 2, amateur_data['Mean'], width, yerr=amateur_data['SD'],
           capsize=5, label='Amateur Runners', color='#FF3333', edgecolor='black', alpha=0.5,
           linewidth=1.5, error_kw=dict(lw=1.5, capthick=1.5))

    # 🌟 画精英组柱子
    ax.bar(x + width / 2, elite_data['Mean'], width, yerr=elite_data['SD'],
           capsize=5, label='Elite Runners', color='#33CC33', edgecolor='black', alpha=0.5,
           linewidth=1.5, error_kw=dict(lw=1.5, capthick=1.5))

    # --- 💡 核心修复：智能计算 Y 轴绝对极值，完美兼容负数 ---
    # 找到所有柱子（均值+误差棒）的最高点和最低点
    y_max_data = max((amateur_data['Mean'] + amateur_data['SD']).max(), (elite_data['Mean'] + elite_data['SD']).max())
    y_min_data = min((amateur_data['Mean'] - amateur_data['SD']).min(), (elite_data['Mean'] - elite_data['SD']).min())

    # 强制让 Y 轴包含 0 刻度
    y_max = max(y_max_data, 0)
    y_min = min(y_min_data, 0)

    # 计算数据的跨度
    y_range = y_max - y_min if y_max != y_min else 1.0

    # 给 Y 轴顶部预留 25% 的空间画连线和图例，底部预留 10% 空间
    top_padding = y_range * 0.25
    bottom_padding = y_range * 0.10

    # 显著性连线开始的初始高度 (正好在最长柱子的上方一点点)
    current_y_offset = y_max + y_range * 0.05
    step_y = y_range * 0.08  # 连线每往上叠一层的高度

    # 💡 如果有负数，画一条贯穿的 X 轴 0 基准线
    if y_min < 0:
        ax.axhline(0, color='black', linewidth=1.2)

    # --- 智能标注显著性连线 ---
    if not posthoc_df.empty and 'p-corr' in posthoc_df.columns:
        stiff_idx = {'T1': 0, 'T2': 1, 'T3': 2}

        for _, row in posthoc_df.iterrows():
            p_val = row.get('p-corr', row.get('p-unc', 1))
            if pd.isna(p_val) or p_val >= 0.05:
                continue

            star = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*'

            col_A, col_B = row['A'], row['B']
            if col_A not in stiff_idx or col_B not in stiff_idx: continue

            idx_A, idx_B = stiff_idx[col_A], stiff_idx[col_B]

            if row['Type'] == 'Simple_Main_Effect':
                if row.get('Group') == 'Amateur':
                    x1, x2 = x[idx_A] - width / 2, x[idx_B] - width / 2
                else:
                    x1, x2 = x[idx_A] + width / 2, x[idx_B] + width / 2
            else:
                x1, x2 = x[idx_A], x[idx_B]

            # 连线下折的小竖线长度
            h = y_range * 0.02
            ax.plot([x1, x1, x2, x2], [current_y_offset, current_y_offset + h, current_y_offset + h, current_y_offset],
                    lw=1.5, color='black')
            # 放置星星的位置
            ax.text((x1 + x2) * 0.5, current_y_offset + h + y_range * 0.01, star, ha='center', va='bottom',
                    color='black',
                    fontsize=14, fontweight='bold')

            # 画完一层，高度上移，防止下一层重叠
            current_y_offset += step_y

    # 动态设置完美适应的 Y 轴上下限！
    ax.set_ylim(y_min - bottom_padding, current_y_offset + top_padding)

    # --- 美化与导出 ---
    ax.set_ylabel(y_label, fontsize=14, fontweight='bold', labelpad=10)
    ax.set_xlabel('Longitudinal Bending Stiffness', fontsize=14, fontweight='bold', labelpad=10)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12, fontweight='bold')
    ax.tick_params(axis='y', labelsize=12)

    ax.legend(frameon=False, fontsize=12, loc='upper right')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(1.5)
    ax.spines['left'].set_linewidth(1.5)

    plt.tight_layout()

    clean_feature_name = feature_name.replace("Summary_", "").replace("_Stats", "")
    plt.savefig(os.path.join(save_dir, f"{clean_feature_name}_BarChart.png"))
    plt.savefig(os.path.join(save_dir, f"{clean_feature_name}_BarChart.pdf"))
    plt.close()


# ==========================================
# 3. 核心单文件处理逻辑
# ==========================================
def process_single_file(file_path, save_dir, y_axis_label):
    filename_full = os.path.basename(file_path)
    filename_no_ext = os.path.splitext(filename_full)[0]
    print(f"🔍 正在深入分析: {filename_full} ...")

    try:
        df_raw = pd.read_csv(file_path)

        cols_amateur = [c for c in df_raw.columns if 'Amateur' in c]
        if not cols_amateur:
            print("⚠️ 未找到 Amateur 数据列")
            return
        df_amateur = df_raw[cols_amateur].copy()
        df_amateur['Subject'] = [f'Amateur_{i + 1}' for i in range(len(df_amateur))]
        df_long_amateur = pd.melt(df_amateur, id_vars=['Subject'], var_name='Condition', value_name='Value')
        df_long_amateur['Group'] = 'Amateur'

        cols_elite = [c for c in df_raw.columns if 'Elite' in c]
        if not cols_elite:
            print("⚠️ 未找到 Elite 数据列")
            return
        df_elite = df_raw[cols_elite].copy()
        df_elite['Subject'] = [f'Elite_{i + 1}' for i in range(len(df_elite))]
        df_long_elite = pd.melt(df_elite, id_vars=['Subject'], var_name='Condition', value_name='Value')
        df_long_elite['Group'] = 'Elite'

        df_final = pd.concat([df_long_amateur, df_long_elite], ignore_index=True)
        df_final['Stiffness'] = df_final['Condition'].apply(lambda x: x.split('_')[-1])
        df_final.dropna(subset=['Value'], inplace=True)

        desc_stats = df_final.groupby(['Group', 'Stiffness'])['Value'].agg(['mean', 'std', 'count']).reset_index()
        desc_stats.rename(columns={'mean': 'Mean', 'std': 'SD', 'count': 'N'}, inplace=True)

        desc_stats_group = df_final.groupby(['Group'])['Value'].agg(['mean', 'std', 'count']).reset_index()
        desc_stats_group['Stiffness'] = 'Total_Average'

        aov = pg.mixed_anova(dv='Value', within='Stiffness', between='Group',
                             subject='Subject', data=df_final, correction=True)

        posthoc_results = pd.DataFrame()
        p_inter = aov.loc[aov['Source'] == 'Interaction', 'p-unc'].values[0]

        # 修复了如果出现空值时的读取问题
        if 'p-GG-corr' in aov.columns:
            p_val_raw = aov.loc[aov['Source'] == 'Stiffness', 'p-GG-corr'].values[0]
            p_stiff = aov.loc[aov['Source'] == 'Stiffness', 'p-unc'].values[0] if pd.isna(p_val_raw) else p_val_raw
        else:
            p_stiff = aov.loc[aov['Source'] == 'Stiffness', 'p-unc'].values[0]

        status_msg = "无显著效应"

        if p_inter < 0.05:
            status_msg = "交互作用显著 -> 追加简单主效应"
            ph = df_final.groupby('Group').apply(
                lambda x: pg.pairwise_tests(dv='Value', within='Stiffness', subject='Subject',
                                            data=x, padjust='bonf'),
                include_groups=False
            ).reset_index()
            if 'level_1' in ph.columns: ph = ph.drop(columns=['level_1'])
            ph.insert(0, 'Type', 'Simple_Main_Effect')
            posthoc_results = pd.concat([posthoc_results, ph])

        elif p_stiff < 0.05:
            status_msg = "刚度主效应显著 -> 追加两两比较"
            ph = pg.pairwise_tests(dv='Value', within='Stiffness', subject='Subject',
                                   data=df_final, padjust='bonf')
            ph.insert(0, 'Type', 'Main_Effect_Stiffness')
            posthoc_results = pd.concat([posthoc_results, ph])

        print(f"  -> 📈 统计分析完成: {status_msg}")

        output_filename = f"{filename_no_ext}_Stats.csv"
        output_path = os.path.join(save_dir, output_filename)

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            f.write("=== 1. Descriptive Statistics (描述性统计: Mean ± SD) ===\n")
            desc_stats.to_csv(f, index=False)
            f.write("\n")
            desc_stats_group.to_csv(f, index=False, header=False)
            f.write("\n\n")

            f.write("=== 2. ANOVA Results (方差分析结果) ===\n")
            aov.to_csv(f, index=False)
            f.write("\n\n")

            if not posthoc_results.empty:
                f.write("=== 3. Post-Hoc Results (事后检验结果) ===\n")
                posthoc_results.to_csv(f, index=False)
            else:
                f.write("No significant interaction or within-subject effects requiring post-hoc.\n")

        generate_auto_bar_plot(desc_stats, posthoc_results, filename_no_ext, save_dir, y_axis_label)
        print("  -> 📊 高清显著性柱状图生成完毕！\n")

    except Exception as e:
        print(f"  !!! 处理发生错误: {e}\n")


if __name__ == '__main__':
    if not os.path.exists(TARGET_FILE):
        print(f"❌ 找不到文件: '{TARGET_FILE}'。请检查路径或文件名拼写！")
    else:
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        process_single_file(TARGET_FILE, OUTPUT_DIR, Y_AXIS_LABEL)
        print(f"🎉 专属单文件处理完成！请前往 '{OUTPUT_DIR}' 文件夹查看结果与图表。")