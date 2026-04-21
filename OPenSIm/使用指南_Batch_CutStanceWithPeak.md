# Batch_CutStanceWithPeak 使用指南

## 概述

`Batch_CutStanceWithPeak.py` 是一个基于峰值检测的 Stance 阶段截取工具。与传统的阈值检测相比，此工具先找到力台数据的峰值位置，然后向两侧搜索阈值边界，能有效避免因力台杂力导致的误检问题。

## 工作原理

### 1. Peak 检测策略
- 首先在垂直力数据中找到最大值（Peak）的位置
- 从 Peak 位置向左搜索第一个低于阈值的点作为 Stance 起始点
- 从 Peak 位置向右搜索第一个低于阈值的点作为 Stance 结束点
- 前后各补偿指定帧数（默认 20 帧）作为上下文

### 2. 数据归零处理
- 在补偿的帧数区间内（非 Stance 阶段），力台数据（Fx, Fy, Fz, Copx, Copy, Copz, Torque）会被归零
- 这样可以避免噪声对后续分析的影响

## 使用方法

### 1. 配置参数

在运行前，修改脚本中的配置参数：

```python
# 配置参数
source_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\input'  # 输入目录
target_dir = r'E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm\Data\output'  # 输出目录

# 采样频率
fs_trc = 200   # TRC 文件采样频率
fs_sto = 200   # STO 文件采样频率

# Stance 检测参数
threshold = 40                # 力阈值 (N)，超过此值认为在 Stance 阶段
fz_pattern = r".*_ground_force_v[yz]$"  # 垂直力列名匹配模式
padding_frames = 20           # 前后各补充的帧数（上下文）
```

### 2. 运行脚本

在命令行中执行：

```bash
cd E:\Python_Learn\CarbonShoes_DataProcess\OPenSIm
python Batch_CutStanceWithPeak.py
```

### 3. 输出结果

脚本会输出以下内容：

- 处理进度信息（每个文件的峰值位置、Stance 时间范围等）
- 错误信息（如果处理失败）
- 处理总结（成功/失败文件数量）

### 4. 输出文件

在 `target_dir` 中生成：

1. **TRC 文件**：截取后的运动捕捉数据
2. **STO 文件**：截取后的力台数据（非 Stance 阶段力数据已归零）
3. **Cut_Records_Peak.csv**：处理记录文件，包含：
   - File Name: 文件名
   - Start Time: 截取起始时间
   - End Time: 截取结束时间
   - Stance Start: 实际 Stance 起始时间
   - Stance End: 实际 Stance 结束时间
   - Peak Value: 峰值力大小 (N)
   - Peak Index: 峰值在数据中的索引位置
   - Start Frame: 截取起始帧号
   - End Frame: 截取结束帧号
   - Stance Start Frame: Stance 起始帧号
   - Stance End Frame: Stance 结束帧号

## 目录结构要求

输入目录应保持以下结构：

```
input/
├── Amateur_Runner/
│   ├── S1/
│   │   ├── T1/
│   │   │   ├── S1T1V11.sto
│   │   │   ├── S1T1V11.trc
│   │   │   ├── S1T1V12.sto
│   │   │   └── ...
```

脚本会自动遍历三层目录，处理所有 STO 文件，并自动配对对应的 TRC 文件。

## 注意事项

1. **阈值设置**：
   - 阈值应根据实际数据调整
   - 建议先用几个样本测试，观察检测结果是否合理

2. **补偿帧数**：
   - 补偿帧数用于提供上下文，默认 20 帧（0.1秒 @ 200Hz）
   - 可根据分析需求调整，但建议不超过 50 帧

3. **采样频率**：
   - 确保 `fs_trc` 和 `fs_sto` 与实际数据采样频率一致
   - 不一致会导致时间轴错误

4. **错误处理**：
   - 如果某个文件处理失败，会跳过并记录错误信息
   - 常见错误原因：
     - 未找到垂直力列（检查 `fz_pattern`）
     - Peak 值低于阈值（调整 `threshold`）
     - 文件格式不正确

5. **数据安全**：
   - 脚本只读取输入文件，不会修改原始数据
   - 所有输出都写入 `target_dir`

## 故障排查

### 问题：Peak 值低于阈值

**症状**：`❌ Peak 值低于阈值，无法检测 stance`

**解决方案**：
1. 降低 `threshold` 值
2. 检查 STO 文件是否正确
3. 查看力台数据是否经过归一化

### 问题：未找到垂直力列

**症状**：`❌ 未找到垂直方向 ground_force_v 列`

**解决方案**：
1. 检查 `fz_pattern` 正则表达式
2. 查看 STO 文件第 8 行的列名
3. 调整 `fz_pattern` 以匹配实际的列名

### 问题：检测到的 Stance 时间不合理

**症状**：Stance 时间过长或过短

**解决方案**：
1. 调整 `threshold` 值
2. 检查数据质量
3. 手动检查该 STO 文件的力台数据

## 与原方法对比

| 特性 | 原方法 (get_stance_time_from_sto) | 新方法 (get_stance_time_from_sto_with_peak) |
|------|-----------------------------------|-----------------------------------------------|
| 检测策略 | 从头到尾遍历找阈值 | 先找峰值，再向两侧搜索 |
| 抗噪性 | 较低，易受杂力影响 | 较高，峰值位置更可靠 |
| 适用场景 | 数据质量较好时 | 数据有噪声或杂力时 |
| 计算复杂度 | O(n) | O(n) |

## 技术细节

### 峰值检测算法

```python
# 找到 Peak 位置（最大值索引）
peak_idx = fz.idxmax()
peak_value = fz[peak_idx]

# 从 Peak 向左搜索第一个小于阈值的点
left_idx = peak_idx
for i in range(peak_idx, -1, -1):
    if fz[i] < threshold:
        left_idx = i
        break

# 从 Peak 向右搜索第一个小于阈值的点
right_idx = peak_idx
for i in range(peak_idx, len(fz)):
    if fz[i] < threshold:
        right_idx = i
        break
```

### 力数据归零

归零的列包括：
- `ground_force_vx`, `ground_force_vy`, `ground_force_vz` (力)
- `ground_force_px`, `ground_force_py`, `ground_force_pz` (压力中心)
- `ground_force_torque` (力矩)

## 联系与支持

如有问题或建议，请检查：
1. [Data_ProcessFunction.py](Data_ProcessFunction.py) - 函数库
2. [Batch_ZeroNonStanceForce.py](Batch_ZeroNonStanceForce.py) - 原始批处理脚本
