import pandas as pd
import numpy as np
import os
import fnmatch

# ================= 配置区域 (请修改这里) =================

# 1. 基础输入路径 (Raw_Data 的上一级或包含 Runner_Type 的文件夹)
# 假设结构: .../WorkAndPower/Moment_AngleVel/Amateur_Runner/T1/Joint_Velocity
#          .../WorkAndPower/Moment_AngleVel/Amateur_Runner/T1/Joint_moment
# 注意：这里请填入包含 Amateur_Runner 和 Elite_Runner 的那个【根目录】
BASE_INPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\WorkAndPower\Moment_AngleVel\interpalte'

# 2. 基础输出路径
BASE_OUTPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\WorkAndPower\Moment_AngleVel\interpalte'

# 3. 循环列表
RUNNER_TYPES = ['Amateur_Runner', 'Elite_Runner']
STIFFNESS_LIST = ['T1', 'T2', 'T3']

# 4. 关节配对关键词 (Key: 关节名, Value: 文件名中的独特标识)
# 程序会用这个标识去文件名里搜索
JOINT_KEYWORDS = {
    'Ankle': 'ankle_angle_r',
    'Knee': 'knee_angle_r',
    'Hip': 'hip_flexion_r',
    'MTP': 'mtp_angle_r'
}

# 5. 采样设置
SAMPLING_RATE = 200
DT = 1 / SAMPLING_RATE
INPUT_IS_DEGREES = False  # OpenSim 输出通常是弧度，设为 False


# ================= 核心计算函数 (复用之前的逻辑) =================
def calculate_and_save(vel_path, mom_path, out_dir, joint_name):
    try:
        df_vel = pd.read_csv(vel_path)
        df_mom = pd.read_csv(mom_path)
    except Exception as e:
        print(f"    ❌ 读取失败: {e}")
        return

    # 对齐 Trial
    common_cols = [c for c in df_vel.columns.intersection(df_mom.columns) if 'time' not in c.lower()]
    if not common_cols:
        print(f"    ⚠️ {joint_name}: 无匹配列 (Trial)")
        return

    # 准备数据
    df_omega = df_vel[common_cols].copy()
    if INPUT_IS_DEGREES:
        df_omega = df_omega * (np.pi / 180)

    # 计算功率 P = M * w
    df_power = df_mom[common_cols] * df_omega

    # --- 1. 保存功率曲线 (Time Series) ---
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    power_filename = f"Time_Series_Power_{joint_name}.csv"
    df_power.to_csv(os.path.join(out_dir, power_filename), index=False)

    # --- 2. 计算离散指标 (Work & Peak Power) ---
    results = {'Positive_Work': {}, 'Negative_Work': {}, 'Net_Work': {}, 'Peak_Power': {}}

    for col in common_cols:
        p = df_power[col].dropna()
        if p.empty: continue

        pos_work = np.trapz(p[p > 0], dx=DT) if not p[p > 0].empty else 0
        neg_work = np.trapz(p[p < 0], dx=DT) if not p[p < 0].empty else 0
        net_work = np.trapz(p, dx=DT)
        peak_power = p.max()

        results['Positive_Work'][col] = pos_work
        results['Negative_Work'][col] = neg_work
        results['Net_Work'][col] = net_work
        results['Peak_Power'][col] = peak_power

    # --- 3. 保存离散指标 ---
    for metric, data in results.items():
        df_res = pd.DataFrame(data, index=[0])
        # 文件名例如: Raw_Positive_Work_knee_angle_r.csv
        fname = f"Raw_{metric}_{joint_name}.csv"
        df_res.to_csv(os.path.join(out_dir, fname), index=False)

    print(f"    ✅ 完成: {joint_name}")


# ================= 批量遍历逻辑 =================
def run_batch_processing():
    print("🚀 开始批量计算功率与做功...\n")

    for runner in RUNNER_TYPES:
        for stiff in STIFFNESS_LIST:
            # 构建输入子路径
            # 假设结构: .../Amateur_Runner/T1/Joint_Velocity
            #          .../Amateur_Runner/T1/Joint_moment
            current_base = os.path.join(BASE_INPUT_DIR, runner, stiff)
            vel_dir = os.path.join(current_base, 'Joint_Velocity')
            mom_dir = os.path.join(current_base, 'Joint_moment')
            # 注意：请确认您的力矩文件夹名是 'Joint_moment' 还是 'Joint_Moment' 等

            # 构建输出子路径
            # .../Calculated_Power_Work/Amateur_Runner/T1/Joint_Power
            out_dir = os.path.join(BASE_OUTPUT_DIR, runner, stiff, 'Joint_Power')

            print(f"--------------------------------------------------")
            print(f"📂 处理分组: [{runner}] - [{stiff}]")

            if not os.path.exists(vel_dir) or not os.path.exists(mom_dir):
                print(f"  ⚠️ 跳过: 找不到 Joint_Velocity 或 Joint_moment 文件夹")
                continue

            # 获取文件夹下所有文件
            vel_files = os.listdir(vel_dir)
            mom_files = os.listdir(mom_dir)

            # 遍历我们定义的关节 (Knee, Ankle...)
            for joint_key, keyword in JOINT_KEYWORDS.items():
                # 模糊匹配文件名
                # 在 vel_files 里找包含 'knee_angle_r' 的文件
                v_file = next((f for f in vel_files if keyword in f and f.endswith('.csv')), None)
                m_file = next((f for f in mom_files if keyword in f and f.endswith('.csv')), None)

                if v_file and m_file:
                    v_path = os.path.join(vel_dir, v_file)
                    m_path = os.path.join(mom_dir, m_file)

                    # 使用关键词作为输出文件名的一部分
                    calculate_and_save(v_path, m_path, out_dir, keyword)
                else:
                    print(f"    ⚠️ 未配对: {joint_key} (缺速度或力矩文件)")

    print("\n🎉 所有批量计算任务结束！")


if __name__ == '__main__':
    run_batch_processing()