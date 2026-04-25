import pandas as pd
import Function_FinalProcessed as FFP
import os

root_dir = r'G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\uninterpolte\uninterpolte_huizhong_data'

for subdir, dirs, files in os.walk(root_dir):
    # 检查当前文件夹是否包含这三个目标文件
    targets = {"AT_gasmed_r.csv", "AT_gaslat_r.csv", "AT_soleus_r.csv"}

    if targets.issubset(set(files)):
        print(f"正在处理: {subdir}")

        # 构建路径
        path_med = os.path.join(subdir, "AT_gasmed_r.csv")
        path_lat = os.path.join(subdir, "AT_gaslat_r.csv")
        path_sol = os.path.join(subdir, "AT_soleus_r.csv")
        save_path = os.path.join(subdir, "AT_Total_Force_r.csv")
        FFP.calculate_achilles_total_force(path_med, path_lat, path_sol, save_path)
print("所有文件夹批量处理完成！")




