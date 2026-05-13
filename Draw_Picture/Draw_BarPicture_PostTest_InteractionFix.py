"""
交互作用显著的柱状图绘制脚本 (修复版)
==========================================

功能说明：
-----------
本脚本用于绘制2x3混合设计的柱状图，并正确标注：
    1. 组内差异 (Within-Group): 每组内 T1 vs T2 vs T3 的两两比较
    2. 组间差异 (Between-Group): 每个刚度水平下 Amateur vs Elite 的比较
    3. 交互效应的简单主效应分析结果

解决的问题：
-----------
原始 Draw_BarPicture_PostTest.py 在交互作用显著时，
只画出了主效应的显著性，没有画出交互作用中的简单主效应差异。
本脚本修复了这一问题。

作者：[Your Name]
日期：2026-05-03
"""

import pandas as pd
import pingouin as pg
import os
import matplotlib.pyplot as plt
import numpy as np


# ==========================================
# 1. 设置配置 (请在这里指定您的单个文件)
# ==========================================
# 直接写死您想处理的那个单文件路径
TARGET_FILE = r'E:\Python_Learn\CarbonShoes_DataProcess\Draw_Picture\data\Summary_Range_IK_hip_rotation_r.csv'

# 结果保存的文件夹
OUTPUT_DIR = r'E:\Python_Learn\CarbonShoes_DataProcess\Draw_Picture\data\bar_plots'

# 自定义图表 Y 轴标签
Y_AXIS_LABEL = 'Rom R Hip Trans.Angle(°)'


# ==========================================
# 2. 绘图引擎：完整标注交互作用 + 组间差异
# ==========================================
def generate_interaction_bar_plot(desc_stats, posthoc_results, aov_table,
                                   feature_name, save_dir, y_label):
    """
    绘制柱状图，标注所有显著性差异：
    - 组内差异 (Simple Main Effect): 同组内不同刚度之间的比较
    - 组间差异 (Between-Group Effect): 同一刚度下两组之间的比较
    """
    # --- 提取绘图数据 ---
    plot_data = desc_stats[desc_stats['Stiffness'] != 'Total_Average'].copy()
    amateur_data = plot_data[plot_data['Group'] == 'Amateur'].set_index('Stiffness').reindex(['T1', 'T2', 'T3'])
    elite_data = plot_data[plot_data['Group'] == 'Elite'].set_index('Stiffness').reindex(['T1', 'T2', 'T3'])

    if amateur_data.empty or elite_data.empty or amateur_data['Mean'].isna().all():
        print("  [WARN] 数据为空，跳过绘图")
        return

    # --- 基本参数 ---
    labels = ['T1 (Low)', 'T2 (Medium)', 'T3 (High)']
    x = np.arange(len(labels))
    width = 0.35

    # --- 颜色方案 (与SPM信号图保持一致) ---
    color_amateur = '#FF3333'
    color_elite = '#33CC33'

    fig, ax = plt.subplots(figsize=(10, 7), dpi=300)

    # --- 画柱子 ---
    bars_am = ax.bar(x - width / 2, amateur_data['Mean'], width,
                     yerr=amateur_data['SD'], capsize=5,
                     label='Amateur Runners', color=color_amateur,
                     edgecolor='black', alpha=0.5, linewidth=1.5,
                     error_kw=dict(lw=1.5, capthick=1.5))
    bars_el = ax.bar(x + width / 2, elite_data['Mean'], width,
                     yerr=elite_data['SD'], capsize=5,
                     label='Elite Runners', color=color_elite,
                     edgecolor='black', alpha=0.5, linewidth=1.5,
                     error_kw=dict(lw=1.5, capthick=1.5))

    # --- 计算 Y 轴范围 ---
    y_max_data = max(
        (amateur_data['Mean'] + amateur_data['SD']).max(),
        (elite_data['Mean'] + elite_data['SD']).max()
    )
    y_min_data = min(
        (amateur_data['Mean'] - amateur_data['SD']).min(),
        (elite_data['Mean'] - elite_data['SD']).min()
    )
    y_max = max(y_max_data, 0)
    y_min = min(y_min_data, 0)
    y_range = y_max - y_min if y_max != y_min else 1.0

    # 如果有负数，画0基准线
    if y_min < 0:
        ax.axhline(0, color='black', linewidth=1.2)

    # =============================================
    # 核心修复：标注所有显著性差异
    # =============================================
    stiff_idx = {'T1': 0, 'T2': 1, 'T3': 2}
    current_y_offset = y_max + y_range * 0.05
    step_y = y_range * 0.08

    def get_stars(p_val):
        """将p值转换为星号"""
        if pd.isna(p_val) or p_val >= 0.05:
            return None
        if p_val < 0.001:
            return '***'
        if p_val < 0.01:
            return '**'
        return '*'

    def draw_bracket(x1, x2, y, h, text, color='black'):
        """绘制显著性括号和星号"""
        ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y],
                lw=1.5, color=color)
        ax.text((x1 + x2) / 2, y + h + y_range * 0.01, text,
                ha='center', va='bottom', color=color,
                fontsize=14, fontweight='bold')

    # --- 1. 先画组内差异 (Within-Group: Simple Main Effect) ---
    within_significant = False
    if not posthoc_results.empty and 'p-corr' in posthoc_results.columns:
        for _, row in posthoc_results.iterrows():
            if row.get('Type') != 'Simple_Main_Effect':
                continue

            p_val = row.get('p-corr', row.get('p-unc', 1))
            stars = get_stars(p_val)
            if stars is None:
                continue

            col_A, col_B = row['A'], row['B']
            if col_A not in stiff_idx or col_B not in stiff_idx:
                continue

            idx_A, idx_B = stiff_idx[col_A], stiff_idx[col_B]
            group = row.get('Group', '')

            # 根据Group确定x偏移
            if group == 'Amateur':
                x1_pos = x[idx_A] - width / 2
                x2_pos = x[idx_B] - width / 2
            else:
                x1_pos = x[idx_A] + width / 2
                x2_pos = x[idx_B] + width / 2

            h = y_range * 0.02
            draw_bracket(x1_pos, x2_pos, current_y_offset, h, stars)
            current_y_offset += step_y
            within_significant = True

    # --- 2. 再画组间差异 (Between-Group: Amateur vs Elite at each Stiffness) ---
    between_significant = False
    if not posthoc_results.empty:
        # 获取可用的p值列
        p_col = 'p-corr' if 'p-corr' in posthoc_results.columns else 'p-unc'
        for _, row in posthoc_results.iterrows():
            if row.get('Type') != 'Between_Group':
                continue

            p_val = row.get(p_col, 1)
            if pd.isna(p_val):
                p_val = row.get('p-unc', 1)
            stars = get_stars(p_val)
            if stars is None:
                continue

            # 组间比较：用Stiffness_Level列确定刚度水平
            stiff_level = row.get('Stiffness_Level', row.get('A', ''))
            if stiff_level not in stiff_idx:
                continue

            idx = stiff_idx[stiff_level]
            # 在该刚度水平的两组柱子之间画括号
            x1_pos = x[idx] - width / 2
            x2_pos = x[idx] + width / 2

            h = y_range * 0.02
            draw_bracket(x1_pos, x2_pos, current_y_offset, h, stars, color='#4A90E2')
            current_y_offset += step_y
            between_significant = True

    # --- 3. 刚度主效应 (Main Effect Stiffness): 整体T1 vs T2 vs T3 ---
    main_effect_drawn = False
    if not posthoc_results.empty:
        p_col = 'p-corr' if 'p-corr' in posthoc_results.columns else 'p-unc'
        for _, row in posthoc_results.iterrows():
            if row.get('Type') != 'Main_Effect_Stiffness':
                continue

            p_val = row.get(p_col, 1)
            if pd.isna(p_val):
                p_val = row.get('p-unc', 1)
            stars = get_stars(p_val)
            if stars is None:
                continue

            col_A, col_B = row['A'], row['B']
            if col_A not in stiff_idx or col_B not in stiff_idx:
                continue

            idx_A, idx_B = stiff_idx[col_A], stiff_idx[col_B]
            # 主效应：画在两组柱子的中心位置
            x1_pos, x2_pos = x[idx_A], x[idx_B]

            h = y_range * 0.02
            draw_bracket(x1_pos, x2_pos, current_y_offset, h, stars, color='#E35B5B')
            current_y_offset += step_y
            main_effect_drawn = True

    # --- 4. 兼容旧格式 (如果以上都没有匹配) ---
    if not within_significant and not between_significant and not main_effect_drawn:
        if not posthoc_results.empty and 'p-corr' in posthoc_results.columns:
            for _, row in posthoc_results.iterrows():
                p_val = row.get('p-corr', row.get('p-unc', 1))
                stars = get_stars(p_val)
                if stars is None:
                    continue

                col_A, col_B = row['A'], row['B']
                if col_A not in stiff_idx or col_B not in stiff_idx:
                    continue

                idx_A, idx_B = stiff_idx[col_A], stiff_idx[col_B]
                x1_pos, x2_pos = x[idx_A], x[idx_B]

                h = y_range * 0.02
                draw_bracket(x1_pos, x2_pos, current_y_offset, h, stars)
                current_y_offset += step_y

    # --- 动态调整Y轴 (强制从0开始) ---
    top_padding = y_range * 0.15
    ax.set_ylim(0, current_y_offset + top_padding)

    # --- 美化与导出 ---
    ax.set_ylabel(y_label, fontsize=14, fontweight='bold', labelpad=10)
    ax.set_xlabel('Longitudinal Bending Stiffness', fontsize=14, fontweight='bold', labelpad=10)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12, fontweight='bold')
    ax.tick_params(axis='y', labelsize=12)

    leg = ax.legend(frameon=False, fontsize=12, loc='upper right')
    for text in leg.get_texts():
        text.set_fontweight('bold')

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
    print(f">> 正在深入分析: {filename_full} ...")

    try:
        # --- A. 数据清洗 ---
        df_raw = pd.read_csv(file_path)

        cols_amateur = [c for c in df_raw.columns if 'Amateur' in c]
        if not cols_amateur:
            print("[WARN] 未找到 Amateur 数据列")
            return
        df_amateur = df_raw[cols_amateur].copy()
        df_amateur['Subject'] = [f'Amateur_{i + 1}' for i in range(len(df_amateur))]
        df_long_amateur = pd.melt(df_amateur, id_vars=['Subject'], var_name='Condition', value_name='Value')
        df_long_amateur['Group'] = 'Amateur'

        cols_elite = [c for c in df_raw.columns if 'Elite' in c]
        if not cols_elite:
            print("[WARN] 未找到 Elite 数据列")
            return
        df_elite = df_raw[cols_elite].copy()
        df_elite['Subject'] = [f'Elite_{i + 1}' for i in range(len(df_elite))]
        df_long_elite = pd.melt(df_elite, id_vars=['Subject'], var_name='Condition', value_name='Value')
        df_long_elite['Group'] = 'Elite'

        df_final = pd.concat([df_long_amateur, df_long_elite], ignore_index=True)
        df_final['Stiffness'] = df_final['Condition'].apply(lambda x: x.split('_')[-1])
        df_final.dropna(subset=['Value'], inplace=True)

        # --- B. 计算描述性统计 ---
        desc_stats = df_final.groupby(['Group', 'Stiffness'])['Value'].agg(['mean', 'std', 'count']).reset_index()
        desc_stats.rename(columns={'mean': 'Mean', 'std': 'SD', 'count': 'N'}, inplace=True)

        desc_stats_group = df_final.groupby(['Group'])['Value'].agg(['mean', 'std', 'count']).reset_index()
        desc_stats_group['Stiffness'] = 'Total_Average'

        # --- C. 混合方差分析 ---
        aov = pg.mixed_anova(dv='Value', within='Stiffness', between='Group',
                             subject='Subject', data=df_final, correction=True)

        # --- D. 自动判断 Post-hoc (修复版：同时处理交互作用和主效应) ---
        posthoc_results = pd.DataFrame()
        p_inter = aov.loc[aov['Source'] == 'Interaction', 'p-unc'].values[0]

        if 'p-GG-corr' in aov.columns:
            p_val_raw = aov.loc[aov['Source'] == 'Stiffness', 'p-GG-corr'].values[0]
            p_stiff = aov.loc[aov['Source'] == 'Stiffness', 'p-unc'].values[0] if pd.isna(p_val_raw) else p_val_raw
        else:
            p_stiff = aov.loc[aov['Source'] == 'Stiffness', 'p-unc'].values[0]

        if 'p-GG-corr' in aov.columns:
            p_val_raw = aov.loc[aov['Source'] == 'Group', 'p-GG-corr'].values[0]
            p_group = aov.loc[aov['Source'] == 'Group', 'p-unc'].values[0] if pd.isna(p_val_raw) else p_val_raw
        else:
            p_group = aov.loc[aov['Source'] == 'Group', 'p-unc'].values[0]

        status_parts = []

        # --- 交互作用显著 -> 简单主效应 + 组间比较 ---
        if p_inter < 0.05:
            status_parts.append("交互作用显著")

            # 1. 简单主效应：每组内 T1 vs T2 vs T3
            for group_name in ['Amateur', 'Elite']:
                group_data = df_final[df_final['Group'] == group_name]
                if group_data['Subject'].nunique() < 2:
                    continue
                ph = pg.pairwise_tests(dv='Value', within='Stiffness', subject='Subject',
                                       data=group_data, padjust='bonf')
                ph.insert(0, 'Type', 'Simple_Main_Effect')
                ph.insert(1, 'Group', group_name)
                posthoc_results = pd.concat([posthoc_results, ph], ignore_index=True)

            # 2. 组间比较：每个刚度水平下 Amateur vs Elite
            for stiff_level in ['T1', 'T2', 'T3']:
                stiff_data = df_final[df_final['Stiffness'] == stiff_level]
                if stiff_data['Group'].nunique() < 2:
                    continue
                ph = pg.pairwise_tests(dv='Value', between='Group', subject='Subject',
                                       data=stiff_data, padjust='bonf')
                ph.insert(0, 'Type', 'Between_Group')
                ph.insert(1, 'Stiffness_Level', stiff_level)
                posthoc_results = pd.concat([posthoc_results, ph], ignore_index=True)

        # --- 刚度主效应显著 -> 整体两两比较 (独立于交互作用) ---
        if p_stiff < 0.05:
            status_parts.append("刚度主效应显著")
            ph = pg.pairwise_tests(dv='Value', within='Stiffness', subject='Subject',
                                   data=df_final, padjust='bonf')
            ph.insert(0, 'Type', 'Main_Effect_Stiffness')
            posthoc_results = pd.concat([posthoc_results, ph], ignore_index=True)

        # --- 组别主效应显著 -> 组间比较 ---
        if p_group < 0.05:
            status_parts.append("组别主效应显著")
            ph = pg.pairwise_tests(dv='Value', between='Group', subject='Subject',
                                   data=df_final, padjust='bonf')
            ph.insert(0, 'Type', 'Main_Effect_Group')
            posthoc_results = pd.concat([posthoc_results, ph], ignore_index=True)

        status_msg = " + ".join(status_parts) if status_parts else "无显著效应"

        print(f"  -> 统计分析完成: {status_msg}")

        # --- E. 保存结果 ---
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

        # --- F. 绘图 ---
        generate_interaction_bar_plot(desc_stats, posthoc_results, aov,
                                       filename_no_ext, save_dir, y_axis_label)
        print("  -> 高清显著性柱状图生成完毕！\n")

    except Exception as e:
        print(f"  !!! 处理发生错误: {e}\n")
        import traceback
        traceback.print_exc()


# ==========================================
# 4. 主程序入口
# ==========================================
if __name__ == '__main__':
    if not os.path.exists(TARGET_FILE):
        print(f"[ERROR] 找不到文件: '{TARGET_FILE}'。请检查路径或文件名拼写！")
    else:
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        process_single_file(TARGET_FILE, OUTPUT_DIR, Y_AXIS_LABEL)
        print(f">> 专属单文件处理完成！请前往 '{OUTPUT_DIR}' 文件夹查看结果与图表。")
