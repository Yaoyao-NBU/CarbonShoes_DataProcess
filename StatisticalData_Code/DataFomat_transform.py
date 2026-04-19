import pandas as pd
import pingouin as pg
import matplotlib.pyplot as plt
import seaborn as sns

# 1. 读取你的原始文件
df_raw = pd.read_csv(r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\Summary_Statistics_UnInterpolte\MaX_Value\Summary_Max_IK_ankle_angle_r.csv')

# ==========================================
# 2. 数据清洗与重塑 (关键步骤)
# ==========================================

# 2.1 分离 Amateur 组的数据
# 提取列名中包含 "Amateur" 的列
cols_amateur = [c for c in df_raw.columns if 'Amateur' in c]
df_amateur = df_raw[cols_amateur].copy()
# 生成受试者ID (A1, A2...)
df_amateur['Subject'] = [f'Amateur_{i + 1}' for i in range(len(df_amateur))]
# 重塑为长格式
df_long_amateur = pd.melt(df_amateur, id_vars=['Subject'],
                          var_name='Condition', value_name='Value')
df_long_amateur['Group'] = 'Amateur'

# 2.2 分离 Elite 组的数据
cols_elite = [c for c in df_raw.columns if 'Elite' in c]
df_elite = df_raw[cols_elite].copy()
# 生成受试者ID (E1, E2...) - 注意要和Amateur区分开
df_elite['Subject'] = [f'Elite_{i + 1}' for i in range(len(df_elite))]
# 重塑为长格式
df_long_elite = pd.melt(df_elite, id_vars=['Subject'],
                        var_name='Condition', value_name='Value')
df_long_elite['Group'] = 'Elite'

# 2.3 合并两组数据
df_final = pd.concat([df_long_amateur, df_long_elite], ignore_index=True)

# 2.4 从列名中提取刚度 (T1/T2/T3)
# 假设列名格式是 "Amateur_Runner_T1"，我们取最后两个字符作为刚度
df_final['Stiffness'] = df_final['Condition'].apply(lambda x: x.split('_')[-1])

# 删除空值 (如果有的话)
df_final.dropna(subset=['Value'], inplace=True)

print(">>> 转换后的数据前5行 (可以直接用于统计)：")
print(df_final[['Subject', 'Group', 'Stiffness', 'Value']].head())

# ==========================================
# 3. 开始统计分析 (混合方差分析)
# ==========================================

print("\n>>> 正在进行双因素混合方差分析...")
aov = pg.mixed_anova(dv='Value', within='Stiffness', between='Group',
                     subject='Subject', data=df_final, correction=True)
pg.print_table(aov)

# 获取交互作用的P值
p_inter = aov.loc[aov['Source'] == 'Interaction', 'p-unc'].values[0]

# ==========================================
# 4. 自动判断并执行事后检验
# ==========================================
if p_inter < 0.05:
    print(f"\n[结果] 交互作用显著 (p={p_inter:.3f})，正在进行简单主效应分析...")

    # 4.1 组内对比 (每个组别内部看刚度的影响)
    print("\n--- 简单主效应 1: Group -> Stiffness ---")
    posthoc_1 = df_final.groupby('Group').apply(
        lambda x: pg.pairwise_tests(dv='Value', within='Stiffness', subject='Subject',
                                    data=x, padjust='bonf')
    )
    print(posthoc_1[['Contrast', 'A', 'B', 'p-corr', 'hedges']])

else:
    print(f"\n[结果] 交互作用不显著 (p={p_inter:.3f})，仅查看主效应...")

    # 刚度主效应
    p_stiff = aov.loc[aov['Source'] == 'Stiffness', 'p-GG-corr'].values[0]
    if p_stiff < 0.05:
        print("\n--- 刚度主效应显著，进行两两比较 ---")
        posthoc_stiff = pg.pairwise_tests(dv='Value', within='Stiffness', subject='Subject',
                                          data=df_final, padjust='bonf')
        print(posthoc_stiff[['Contrast', 'A', 'B', 'p-corr', 'hedges']])

# ==========================================
# 5. 画图
# ==========================================
plt.figure(figsize=(8, 6))
sns.pointplot(data=df_final, x='Stiffness', y='Value', hue='Group',
              capsize=.1, errorbar='se', palette=['#1f77b4', '#d62728'],
              order=['T1', 'T2', 'T3'])  # 确保T1 T2 T3顺序
plt.title('Interaction Plot: Max Knee Angle')
plt.ylabel('Angle (deg)')
plt.show()