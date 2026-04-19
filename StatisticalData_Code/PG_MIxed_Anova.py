import pandas as pd
import pingouin as pg
import glob
import os

# ==========================================
# 1. 设置配置
# ==========================================
# 输入路径
input_folder = r'G:\Carbon_Plate_Shoes_Data\STO-Data_Processed\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Summary_Statistics_UnInterpolte\MinValue'

# 结果保存文件夹
output_folder_name = 'Stats_Results_With_Mean_SD'
output_dir = os.path.join(input_folder, output_folder_name)


# ==========================================
# 2. 核心分析函数
# ==========================================
def process_single_file(file_path, save_dir):
    filename_full = os.path.basename(file_path)
    filename_no_ext = os.path.splitext(filename_full)[0]

    print(f"正在处理: {filename_full} ...")

    try:
        # --- A. 数据清洗 ---
        df_raw = pd.read_csv(file_path)

        # 提取 Amateur
        cols_amateur = [c for c in df_raw.columns if 'Amateur' in c]
        if not cols_amateur: return
        df_amateur = df_raw[cols_amateur].copy()
        df_amateur['Subject'] = [f'Amateur_{i + 1}' for i in range(len(df_amateur))]
        df_long_amateur = pd.melt(df_amateur, id_vars=['Subject'], var_name='Condition', value_name='Value')
        df_long_amateur['Group'] = 'Amateur'

        # 提取 Elite
        cols_elite = [c for c in df_raw.columns if 'Elite' in c]
        if not cols_elite: return
        df_elite = df_raw[cols_elite].copy()
        df_elite['Subject'] = [f'Elite_{i + 1}' for i in range(len(df_elite))]
        df_long_elite = pd.melt(df_elite, id_vars=['Subject'], var_name='Condition', value_name='Value')
        df_long_elite['Group'] = 'Elite'

        # 合并
        df_final = pd.concat([df_long_amateur, df_long_elite], ignore_index=True)
        df_final['Stiffness'] = df_final['Condition'].apply(lambda x: x.split('_')[-1])
        df_final.dropna(subset=['Value'], inplace=True)

        # --- NEW: B. 计算描述性统计 (均值 & 标准差) ---
        # 按 Group 和 Stiffness 分组计算 Mean, SD, Count
        desc_stats = df_final.groupby(['Group', 'Stiffness'])['Value'].agg(['mean', 'std', 'count']).reset_index()
        desc_stats.rename(columns={'mean': 'Mean', 'std': 'SD', 'count': 'N'}, inplace=True)

        # 另外算一个总的组间对比 (不分刚度)，方便回答"组间主效应显著"后的均值对比
        desc_stats_group = df_final.groupby(['Group'])['Value'].agg(['mean', 'std', 'count']).reset_index()
        desc_stats_group['Stiffness'] = 'Total_Average'  # 标记为总体平均

        # --- C. 混合方差分析 ---
        aov = pg.mixed_anova(dv='Value', within='Stiffness', between='Group',
                             subject='Subject', data=df_final, correction=True)

        # --- D. 自动判断 Post-hoc ---
        posthoc_results = pd.DataFrame()
        p_inter = aov.loc[aov['Source'] == 'Interaction', 'p-unc'].values[0]
        if 'p-GG-corr' in aov.columns:
            p_stiff = aov.loc[aov['Source'] == 'Stiffness', 'p-GG-corr'].values[0]
        else:
            p_stiff = aov.loc[aov['Source'] == 'Stiffness', 'p-unc'].values[0]

        status_msg = "无显著效应 (仅保存基础结果)"

        if p_inter < 0.05:
            status_msg = "交互作用显著 -> 追加简单主效应"
            ph = df_final.groupby('Group').apply(
                lambda x: pg.pairwise_tests(dv='Value', within='Stiffness', subject='Subject',
                                            data=x, padjust='bonf')
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

        print(f"  -> 分析完成: {status_msg}")

        # --- E. 保存结果 ---
        output_filename = f"{filename_no_ext}_Stats.csv"
        output_path = os.path.join(save_dir, output_filename)

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            # 1. 写入描述性统计 (最常用，放最前面)
            f.write("=== 1. Descriptive Statistics (描述性统计: Mean ± SD) ===\n")
            desc_stats.to_csv(f, index=False)
            f.write("\n")
            desc_stats_group.to_csv(f, index=False, header=False)  # 追加总体平均行
            f.write("\n\n")

            # 2. 写入 ANOVA
            f.write("=== 2. ANOVA Results (方差分析结果) ===\n")
            aov.to_csv(f, index=False)
            f.write("\n\n")

            # 3. 写入 Post-Hoc
            if not posthoc_results.empty:
                f.write("=== 3. Post-Hoc Results (事后检验结果) ===\n")
                posthoc_results.to_csv(f, index=False)
            else:
                f.write("No significant interaction or within-subject effects requiring post-hoc.\n")
                f.write(
                    "(Note: If Group effect is significant, refer to the Descriptive Statistics above for direction of difference.)\n")

        print(f"  -> 已保存至: {output_filename}\n")

    except Exception as e:
        print(f"  !!! 处理 {filename_full} 失败: {e}\n")


# ==========================================
# 3. 主程序
# ==========================================
if not os.path.exists(output_dir): os.makedirs(output_dir)
csv_files = glob.glob(os.path.join(input_folder, '*.csv'))
print(f"共发现 {len(csv_files)} 个文件，开始处理...\n")

for file in csv_files:
    process_single_file(file, output_dir)

print("✅ 全部完成！结果包含均值和标准差。")