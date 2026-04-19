import ezc3d
import numpy as np
import os

def reconstruct_ultimate_c3d(input_path, output_path):
    print(f">>> 正在执行终极标准化重构: {os.path.basename(input_path)}")
    old_c3d = ezc3d.c3d(input_path)
    
    # ==========================================
    # 1. 提取核心参数与原始数据
    # ==========================================
    old_labels = old_c3d['parameters']['ANALOG']['LABELS']['value']
    old_analogs = np.squeeze(old_c3d['data']['analogs'])
    p_rate = float(old_c3d['parameters']['POINT']['RATE']['value'][0])
    a_rate = float(old_c3d['parameters']['ANALOG']['RATE']['value'][0])

    # ==========================================
    # 2. 核心动力学解算 (Kistler 9287CA)
    # ==========================================
    def get_idx(p):
        t = [f'{p}X1', f'{p}X3', f'{p}Y1', f'{p}Y2', f'{p}Z1', f'{p}Z2', f'{p}Z3', f'{p}Z4']
        return [old_labels.index(i) for i in t]

    W = np.array([
        [   1,    1,    0,    0,    0,    0,    0,    0], 
        [   0,    0,    1,    1,    0,    0,    0,    0], 
        [   0,    0,    0,    0,    1,    1,    1,    1],
        [   0,    0,    0,    0,  350,  350, -350, -350], 
        [   0,    0,    0,    0, -210,  210,  210, -210], 
        [-350,  350,  210, -210,    0,    0,    0,    0]
    ])

    data_f1 = np.dot(W, old_analogs[get_idx('F1'), :])
    data_f2 = np.dot(W, old_analogs[get_idx('F2'), :])
    
    az0 = -40.0
    for d in [data_f1, data_f2]:
        d[3, :] += (d[1, :] * az0) # Mx'
        d[4, :] -= (d[0, :] * az0) # My'
        
        # 智能底噪屏蔽
        threshold = -20.0
        empty_mask = d[2, :] > threshold
        d[:, empty_mask] = 0.0

    combined = np.vstack((data_f1, data_f2))

    # ==========================================
    # 3. 构建纯净的 C3D 对象
    # ==========================================
    new_c3d = ezc3d.c3d()

    # --- A. 注入底层数据阵列 ---
    points_data = old_c3d['data']['points']
    new_c3d['data']['points'] = points_data
    new_c3d['data']['analogs'] = np.expand_dims(combined, axis=0)

    # --- B. 运动学 (POINT) 元数据对齐 ---
    # 【完美避坑法】：使用纯标量 int，精准调用 C++ set(int) 接口
    new_c3d.add_parameter('POINT', 'USED', int(points_data.shape[1]))
    new_c3d.add_parameter('POINT', 'RATE', [p_rate])
    
    if 'LABELS' in old_c3d['parameters']['POINT']:
        new_c3d.add_parameter('POINT', 'LABELS', tuple(old_c3d['parameters']['POINT']['LABELS']['value']))
    if 'DESCRIPTIONS' in old_c3d['parameters']['POINT']:
        new_c3d.add_parameter('POINT', 'DESCRIPTIONS', tuple(old_c3d['parameters']['POINT']['DESCRIPTIONS']['value']))
    if 'UNITS' in old_c3d['parameters']['POINT']:
        new_c3d.add_parameter('POINT', 'UNITS', tuple(old_c3d['parameters']['POINT']['UNITS']['value']))

    # --- C. 动力学 (ANALOG) 元数据对齐 ---
    new_c3d.add_parameter('ANALOG', 'RATE', [a_rate])
    new_labels = [f'F1{s}' for s in ['Fx','Fy','Fz','Mx','My','Mz']] + \
                 [f'F2{s}' for s in ['Fx','Fy','Fz','Mx','My','Mz']]
    
    # 【完美避坑法】：标量 12 保证是纯 INT
    new_c3d.add_parameter('ANALOG', 'USED', int(12))
    new_c3d.add_parameter('ANALOG', 'LABELS', tuple(new_labels))
    new_c3d.add_parameter('ANALOG', 'UNITS', tuple(['N','N','N','Nmm','Nmm','Nmm'] * 2))
    
    new_c3d.add_parameter('ANALOG', 'SCALE', tuple([1.0] * 12))
    new_c3d.add_parameter('ANALOG', 'GEN_SCALE', [1.0]) 
    new_c3d.add_parameter('ANALOG', 'OFFSET', tuple([0] * 12))

    # --- D. 力台物理映射 (解决 Matlab 读取崩溃的终极方案) ---
    # 【完美避坑法】：标量 2 保证是纯 INT，禁用 NumPy 数组
    new_c3d.add_parameter('FORCE_PLATFORM', 'USED', int(2))
    new_c3d.add_parameter('FORCE_PLATFORM', 'TYPE', [2, 2])
    new_c3d.add_parameter('FORCE_PLATFORM', 'ZERO', [1, 1])
    
    # 使用纯 Python 元组嵌套，防止 SWIG 解析 NumPy 二维数组时崩溃
    ch_map = (
        (1, 7),
        (2, 8),
        (3, 9),
        (4, 10),
        (5, 11),
        (6, 12)
    )
    new_c3d.add_parameter('FORCE_PLATFORM', 'CHANNEL', ch_map)

    if 'FORCE_PLATFORM' in old_c3d['parameters']:
        old_fp = old_c3d['parameters']['FORCE_PLATFORM']
        
        # 将 NumPy 数组转回纯粹的 Python 列表 (tolist)
        corners_list = np.array(old_fp['CORNERS']['value'], dtype=float).tolist()
        new_c3d.add_parameter('FORCE_PLATFORM', 'CORNERS', corners_list)
        
        orig_shape = np.array(old_fp['ORIGIN']['value']).shape
        pure_zero_orig = np.zeros(orig_shape, dtype=float).tolist()
        new_c3d.add_parameter('FORCE_PLATFORM', 'ORIGIN', pure_zero_orig)

    # ==========================================
    # 4. 导出文件
    # ==========================================
    new_c3d.write(output_path)
    print(f">>> 重构大功告成！完美格式的 C3D 数据已保存至: \n{output_path}")

# 执行入口
if __name__ == "__main__":
    IN = r"E:\Python_Learn\CarbonShoes_DataProcess\C3D_Data_Process\Data\S15T1V11.c3d"
    OUT = r"E:\Python_Learn\CarbonShoes_DataProcess\C3D_Data_Process\Data\S15T1V11_Perfect.c3d"
    
    if os.path.exists(IN):
        reconstruct_ultimate_c3d(IN, OUT)
    else:
        print("未找到输入文件，请检查路径！")