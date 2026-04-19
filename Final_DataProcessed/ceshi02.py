import pandas as pd
import numpy as np
import os

# ================= 配置区域 (请修改这里) =================

# 1. 输入文件的路径
# 注意：这里请填入您刚刚生成的 "Velocity_..." 文件
VELOCITY_FILE_PATH = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\WorkAndPower\Moment_AngleVel\Amateur_Runner\T1\Joint_Velocity\Velocity_knee_angle_r.csv'

# 力矩文件保持不变
MOMENT_FILE_PATH = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\WorkAndPower\Moment_AngleVel\Amateur_Runner\T1\Joint_moment\ID_knee_angle_r_moment.csv'

# 2. 输出文件夹
OUTPUT_DIR = r'G:\Carbon_Plate_Shoes_Data\Carbon_Fiber_Shoes_DataProcessed\Speed_Spilt\High_Speed\WorkAndPower\Result_Amateur_T1_Knee'

# 3. 采样设置 (用于积分计算做功)
SAMPLING_RATE = 200
DT = 1 / SAMPLING_RATE

# 4. 单位确认
# OpenSim 输出的速度通常是 弧度/秒 (rad/s)，如果是这样，设为 False
# 如果您的速度文件是 度/秒 (deg/s)，请设为 True
INPUT_IS_DEGREES = False


# ================= 核心处理逻辑 =================
def process_velocity_moment_pair(velocity_path, moment_path, output_dir):
    print(f"🚀 正在处理配对文件...")
    print(f"  📂 速度: {os.path.basename(velocity_path)}")
    print(f"  📂 力矩: {os.path.basename(moment_path)}")

    # 1. 读取数据
    try:
        df_vel = pd.read_csv(velocity_path)
        df_mom = pd.read_csv(moment_path)
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        return

    # 2. 对齐 Trial (找到共有的列)
    common_cols = [c for c in df_vel.columns.intersection(df_mom.columns) if 'time' not in c.lower()]

    if not common_cols:
        print("⚠️ 没有匹配的列！请检查两个文件的表头是否一致（都需要是 S1T1V1 这种格式）。")
        return

    print(f"✅ 匹配到 {len(common_cols)} 个 Trial...")

    # 3. 准备数据
    df_omega = df_vel[common_cols].copy()

    # 单位检查与转换
    if INPUT_IS_DEGREES:
        print("  ℹ️ 检测到输入为角度制，正在转换为弧度...")
        df_omega = df_omega * (np.pi / 180)
    else:
        print("  ℹ️ 默认输入为弧度制 (rad/s)，直接计算...")

    # 4. 计算功率 (Watts) [P = M * ω]
    # 直接相乘，无需差分
    df_power = df_mom[common_cols] * df_omega

    # ==========================================
    # 🔥 保存每一帧的功率曲线数据 (用于作图)
    # ==========================================
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    power_curve_file = os.path.join(output_dir, "Time_Series_Power.csv")
    df_power.to_csv(power_curve_file, index=False)
    print(f"  📈 已保存功率曲线: Time_Series_Power.csv")

    # 5. 逐列计算离散指标 (积分/峰值)
    results = {
        'Positive_Work': {},
        'Negative_Work': {},
        'Net_Work': {},
        'Peak_Power': {}
    }

    for col in common_cols:
        p = df_power[col].dropna()
        if p.empty: continue

        # 积分计算功 (J) = 功率对时间的积分
        pos_work = np.trapz(p[p > 0], dx=DT) if not p[p > 0].empty else 0
        neg_work = np.trapz(p[p < 0], dx=DT) if not p[p < 0].empty else 0
        net_work = np.trapz(p, dx=DT)

        # 峰值功率 (W)
        peak_power = p.max()

        # 存入字典
        results['Positive_Work'][col] = pos_work
        results['Negative_Work'][col] = neg_work
        results['Net_Work'][col] = net_work
        results['Peak_Power'][col] = peak_power

    # 6. 保存离散指标文件
    for metric_name, data_dict in results.items():
        # 转为 DataFrame (单行)
        df_output = pd.DataFrame(data_dict, index=[0])

        # 保存
        file_name = f"Raw_{metric_name}.csv"
        save_path = os.path.join(output_dir, file_name)

        df_output.to_csv(save_path, index=False)
        print(f"  💾 已生成统计值: {file_name}")

    print(f"\n🎉 全部完成！结果在文件夹: {output_dir}")


# ================= 执行 =================
if __name__ == '__main__':
    process_velocity_moment_pair(VELOCITY_FILE_PATH, MOMENT_FILE_PATH, OUTPUT_DIR)