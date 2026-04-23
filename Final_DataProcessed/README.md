# Final_DataProcessed - 数据处理脚本集

本目录包含碳板跑鞋生物力学实验数据的**最终处理脚本**，涵盖从 OpenSim 原始输出到统计就绪数据的全流程。

---

## 目录结构概览

```
Final_DataProcessed/
├── Function_FinalProcessed.py    ← 核心函数库（被其他脚本调用）
├── STOAndMOT_TO_CSV.py           ← 格式转换（STO/MOT → CSV）
├── Batch_Interpolate_Code.py     ← 单进程批量插值
├── Batch_interpolate_Executor.py ← 多进程批量插值
├── LBS_DataHuizhong_JointAngle.py  ← 汇总：关节角度
├── LBS_DataHuizhong_JointVel.py    ← 汇总：关节角速度
├── LBS_DataHuizhong_Jointmoment.py ← 汇总：关节力矩/力
├── Batch_LBS_MAForceHuizhong.py    ← 汇总：肌肉力（跟腱相关）
├── compute_ATForce.py              ← 计算：跟腱总力
├── Average_FIle_Processed.py       ← 多 Trial 取平均
├── BodyWight_NormalizeData.py      ← 体重标准化
├── Cal_Load_JointAngle.py          ← 统计提取：落地时刻值
├── Cal_MaxValue.py                 ← 统计提取：最大值
├── Cal_MinValue.py                 ← 统计提取：最小值
├── Cal_Range.py                    ← 统计提取：活动范围 (Max-Min)
├── Cal_Power.py                    ← 计算：关节功率与做功
├── Cal_AT_Impulse.py               ← 统计提取：冲量积分（汇总宽表）
├── Cal_AT_Impulse_ForStatis.py     ← 统计提取：冲量积分（SPSS 长表）
```

---

## 数据处理流水线

按照以下顺序使用这些脚本：

```
1. STO/MOT → CSV        (STOAndMOT_TO_CSV.py)
2. 时间归一化插值        (Batch_Interpolate_Code.py 或 Batch_interpolate_Executor.py)
3. 按特征汇总            (LBS_DataHuizhong_*.py, Batch_LBS_MAForceHuizhong.py)
4. 计算跟腱总力          (compute_ATForce.py)
5. 多 Trial 取平均       (Average_FIle_Processed.py)
6. 体重标准化            (BodyWight_NormalizeData.py)
7. 计算功率与做功         (Cal_Power.py)
8. 统计特征提取          (Cal_*.py)
```

---

## 各脚本详细说明

---

### 1. Function_FinalProcessed.py — 核心函数库

**用途**：本项目的"工具箱"，定义了所有可复用的核心函数。其他脚本通过 `import Function_FinalProcessed` 来调用。

**包含的函数**：

| 函数名 | 功能 |
|--------|------|
| `sto_mot_to_csv_single()` | 将单个 .sto/.mot 文件转为 CSV |
| `interpolate_single_file_simple()` | 对单个 CSV 进行时间归一化插值 |
| `process_single_csv()` | 从 CSV 中提取指定列 |
| `process_csv()` | 对同一受试者的多个 Trial 取均值 |
| `batch_process()` | 批量调用 `process_csv()` |
| `calculate_achilles_total_force()` | 计算跟腱总力 = 腓肠肌外侧 + 腓肠肌内侧 + 比目鱼肌 |
| `batch_normalize_by_weight()` | 按体重标准化动力学数据 |

**使用方式**：
```python
import Function_FinalProcessed as FTP
FTP.interpolate_single_file_simple(input_file, output_file)
```

---

### 2. STOAndMOT_TO_CSV.py — 格式转换

**用途**：将 OpenSim 输出的 `.sto` 和 `.mot` 文件批量转换为 `.csv` 格式。

**为什么需要这一步**：OpenSim 的结果文件是自定义文本格式，以 `endheader` 分隔元信息和数据区。本脚本自动定位 `endheader` 行，跳过元信息，只保留纯数据部分。

**工作原理**：
1. 读取文件，逐行查找 `endheader` 标记
2. 从 `endheader` 下一行开始，用 `pd.read_csv(sep="\s+")` 解析空白分隔的数据
3. 保存为标准 CSV

**配置**：修改 `source_dir` 和 `csv_output_dir` 变量。

---

### 3. Batch_interpolate_Executor.py — 多进程批量插值

**用途**：使用 Python 多进程 (`ProcessPoolExecutor`) 并行执行时间归一化插值，大幅提升处理速度。

**工作原理**：
1. 扫描输入目录下所有 CSV 文件
2. 将插值任务打包成元组列表
3. 用进程池并行调用 `FTP.interpolate_single_file_simple()`
4. 每 10 个文件打印一次进度

**插值方法**：线性插值 (`linear`)，将每个 Trial 的时间轴归一化到 101 帧 (0%~100% stance phase)。

**配置**：修改 `InputBase` 和 `OutputBase`。

**注意**：Windows 下必须将代码放在 `if __name__ == '__main__':` 下，否则多进程会报错。

---

### 4. Batch_Interpolate_Code.py — 单进程批量插值

**用途**：与上一个脚本功能相同，但使用简单的 `for` 循环而非多进程。适合数据量较小或调试时使用。

**工作原理**：
1. 用 `os.walk()` 递归遍历所有子文件夹
2. 逐个调用 `FTP.interpolate_single_file_simple()`
3. 自动保持输入目录结构

**配置**：修改 `InputFile` 和 `OutputFIle`。

---

### 5. LBS_DataHuizhong_JointAngle.py — 汇总关节角度

**用途**：从每个受试者每个 Trial 的 IK（逆运动学）文件中，提取指定的关节角度列，按 Trial 名汇总成一个大表。

**输出文件命名**：`IK_关节名.csv`，例如 `IK_knee_angle_r.csv`。

**表的结构**：
- 每一列 = 一个 Trial（如 `S1T1V1`）
- 每一行 = 一个时间帧
- 值 = 该关节在该帧的角度值

**匹配逻辑**：文件名匹配 `*_IK.csv`，从中提取 `hip_flexion_r`、`knee_angle_r`、`ankle_angle_r` 等列。

**配置**：修改 `BASE_INPUT_DIR`、`BASE_OUTPUT_DIR`，以及 `TARGET_COLUMNS` 列表。

---

### 6. LBS_DataHuizhong_Jointmoment.py — 汇总关节力矩/力

**用途**：与上一个脚本逻辑完全一致，区别在于处理的是 ID（逆动力学）文件，提取的是关节力矩和地面反力。

**匹配逻辑**：文件名匹配 `*_ID.csv`。

**输出文件命名**：`ID_变量名.csv`，例如 `ID_knee_angle_r_moment.csv`、`ID_pelvis_tx_force.csv`。

**提取的变量**：
- 力矩：`hip_flexion_r_moment`、`knee_angle_r_moment`、`ankle_angle_r_moment` 等
- 力：`pelvis_tx_force`、`pelvis_ty_force`、`pelvis_tz_force`

---

### 7. LBS_DataHuizhong_JointVel.py — 汇总关节角速度

**用途**：从 OpenSim 的 StatesReporter 输出文件中，提取关节角速度（`/speed` 列），汇总成大表。

**匹配逻辑**：文件名匹配 `*_StatesReporter_states.csv`，在列名中搜索以 `/<关节名>/speed` 结尾的列。

**输出文件命名**：`Velocity_关节名.csv`，例如 `Velocity_knee_angle_r.csv`。

**注意**：OpenSim 输出的角速度单位为 **rad/s**（弧度/秒），可直接用于功率计算 (Power = Moment × AngularVelocity)。

---

### 8. Batch_LBS_MAForceHuizhong.py — 汇总肌肉力

**用途**：从 Static Optimization 结果文件中提取跟腱相关肌肉的力，按 Trial 汇总。

**匹配逻辑**：文件名匹配 `LBSModel-scaled_StaticOptimization_force.csv`。

**提取的变量**：`soleus_r`（比目鱼肌）、`gaslat_r`（腓肠肌外侧）、`gasmed_r`（腓肠肌内侧）。

**输出文件命名**：`AT_soleus_r.csv`、`AT_gaslat_r.csv`、`AT_gasmed_r.csv`。

---

### 9. compute_ATForce.py — 计算跟腱总力

**用途**：将三块肌肉的力相加，得到跟腱总力。

**公式**：`AT_Total = AT_gasmed + AT_gaslat + AT_soleus`

**工作原理**：
1. 遍历所有子文件夹，检查是否同时存在三个肌肉力文件
2. 调用 `FFP.calculate_achilles_total_force()` 直接将三个 DataFrame 相加
3. 结果保存为 `AT_Total_Force_r.csv`

**注意**：该脚本会自动跳过缺失文件的文件夹。

---

### 10. Average_FIle_Processed.py — 多 Trial 取平均

**用途**：对同一受试者的多个 Trial 取均值，简化数据。

**分组逻辑**：按列名去掉最后一位数字进行分组。例如：
- `S1T1V1` 和 `S1T1V2` → 组名为 `S1T1V`，取两列的平均值
- `S1T1V11` → 组名为 `S1T1V1`

**工作原理**：
1. 用 `os.walk()` 递归遍历所有子文件夹
2. 对每个 CSV 执行分组求均值
3. 保持原始目录结构输出

**输出文件名**：与原文件同名（无 `AVG_` 前缀）。

---

### 11. BodyWight_NormalizeData.py — 体重标准化

**用途**：将动力学数据（力矩、力、功率）按受试者体重进行标准化，消除个体体重差异的影响。

**标准化公式**：
- 力矩/力 → **BW（体重倍数）**：`标准化值 = 原始值 / (体重kg × 9.81)`
- 功率 → **W/kg**：`标准化值 = 原始值 / 体重kg`

**工作原理**：
1. 读取体重信息表（CSV，需有 `People` 和 `Weight` 两列）
2. 遍历数据文件的列名，用正则提取受试者 ID（如 `S1T1V1` → `S1`）
3. 匹配体重后进行除法运算
4. 智能判断：文件名含 `Power` 或 `Work` 时使用 `gravity=1.0`（W/kg），否则使用 `gravity=9.81`（BW）

**体重表格式要求**：
```csv
People,Weight
S1,65.2
S2,72.0
...
```

**配置**：修改 `input_root`、`output_root`、`weight_file`，以及 `target_filenames` 列表。

---

### 12. Cal_Load_JointAngle.py — 提取落地时刻值

**用途**：从汇总的关节角度数据中，提取**落地时刻**（第 1 帧，索引 0）的值，并按人群和刚度分类汇总成统计表。

**输出格式**：
- 列标题：`Amateur_Runner_T1`、`Amateur_Runner_T2`、...、`Elite_Runner_T3`
- 每行 = 一个受试者
- 同一受试者的多个 Trial 取平均

**输出文件名**：`Summary_<原文件名>`。

**文件扫描逻辑**：根据路径中是否包含 `Amateur_Runner`/`Elite_Runner` 和 `T1`/`T2`/`T3` 来自动分类。

---

### 13. Cal_MaxValue.py — 提取最大值

**用途**：计算每个 Trial 时间序列的**最大值**，并按人群/刚度分类汇总。

**与 Cal_Load_JointAngle.py 的区别**：
- Cal_Load_JointAngle 取的是第 1 帧的值（落地时刻）
- Cal_MaxValue 取的是整条曲线的最大值

**输出文件名**：`Summary_Max_<原文件名>`。

**其他逻辑**（文件扫描、分组、合并）与 Cal_Load_JointAngle.py 完全一致。

---

### 14. Cal_MinValue.py — 提取最小值

**用途**：与 Cal_MaxValue.py 逻辑一致，唯一区别是使用 `df.min()` 计算最小值。

**输出文件名**：`Summary_Min_<原文件名>`。

---

### 15. Cal_Range.py — 提取活动范围

**用途**：计算每个 Trial 的活动范围 = 最大值 - 最小值（`df.max() - df.min()`）。

**适用场景**：关节角度的活动范围（ROM）是生物力学研究中的重要指标。

**输出文件名**：`Summary_Range_<原文件名>`。

---

### 16. Cal_Power.py — 计算关节功率与做功

**用途**：将关节力矩和关节角速度相乘，得到关节功率，然后通过积分计算做功。

**核心公式**：
- **功率**：`P = M × ω`（力矩 × 角速度）
- **正功**：`∫ P dt`（当 P > 0 的部分）
- **负功**：`∫ P dt`（当 P < 0 的部分）
- **净功**：`∫ P dt`（全时段积分）

**工作原理**：
1. 自动遍历 `Runner_Type × Stiffness` 组合
2. 在对应文件夹中模糊匹配关节的速度文件和力矩文件
3. 对齐 Trial 列名后计算功率
4. 保存功率曲线（Time Series）和离散指标（Work、Peak Power）

**输出文件**：
- `Time_Series_Power_<关节名>.csv` — 功率曲线
- `Raw_Positive_Work_<关节名>.csv` — 正功
- `Raw_Negative_Work_<关节名>.csv` — 负功
- `Raw_Net_Work_<关节名>.csv` — 净功
- `Raw_Peak_Power_<关节名>.csv` — 峰值功率

**关节配置**：通过 `JOINT_KEYWORDS` 字典定义，默认包含 Ankle、Knee、Hip、MTP。

**注意**：确保 `INPUT_IS_DEGREES` 设置正确。OpenSim 输出通常是弧度，设为 `False`。

---

### 17. Cal_AT_Impulse.py — 冲量积分（汇总宽表格式）

**用途**：对力/力矩曲线进行时间积分，计算冲量（Impulse），输出为与 Cal_MaxValue 等脚本一致的宽表格式。

**核心公式**：`Impulse = ∫ F dt`（梯形积分）

**工作原理**：
1. 读取 CSV，按列剔除 NaN 后进行梯形积分
2. 同一受试者的多个 Trial 取平均
3. 按人群和刚度分组，输出宽表

**输出文件名**：`Summary_Impulse_<原文件名>`。

**采样率配置**：`SAMPLING_RATE = 200.0`（请确保与实际采样率一致）。

**文件筛选**：通过 `TARGET_FILES` 列表指定要处理的文件名。列表为空时，自动处理文件名含 `Force`/`moment`/`Power` 的文件。

---

### 18. Cal_AT_Impulse_ForStatis.py — 冲量积分（SPSS 长表格式）

**用途**：与 Cal_AT_Impulse.py 功能相同，但输出格式为 **SPSS/JASP 友好的长表格式**。

**输出格式**：
| Subject | Group | T1 | T2 | T3 |
|---------|-------|----|----|----|
| S1 | Amateur_Runner | 0.52 | 0.48 | 0.55 |
| S2 | Amateur_Runner | 0.61 | 0.57 | 0.63 |

**输出文件名**：`SPSS_Ready_Impulse_<原文件名>`。

**何时使用**：
- 如果后续用 Python 做统计 → 使用 `Cal_AT_Impulse.py`
- 如果后续用 SPSS/JASP 做统计 → 使用本脚本

---

## 常见问题

### Q: 体重标准化脚本报错怎么办？
请参考下方的"BodyWight_NormalizeData.py 报错排查"章节。

### Q: 插值后的帧数是多少？
默认 101 帧（0%~100% stance phase），可在 `interpolate_single_file_simple()` 的 `num_frames` 参数中修改。

### Q: 标准化后的单位是什么？
- 力矩/力 除以 `体重×9.81` → 单位为 **BW**（体重倍数）
- 功率 除以 `体重` → 单位为 **W/kg**

---

## BodyWight_NormalizeData.py 报错排查

经过代码分析，该脚本可能出现的报错原因如下：

### 原因 1：体重表路径不存在或格式不正确

脚本配置的体重文件路径为：
```
G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\baseline_01.csv
```

**检查方法**：确认该文件是否真实存在，以及是否包含 `People` 和 `Weight` 两列。

**体重表必须满足**：
- 第一列名为 `People`，值为受试者编号（如 `S1`, `S2`...）
- 第二列名为 `Weight`，值为体重（单位：kg）
- 格式示例：
```csv
People,Weight
S1,65.2
S2,72.0
S3,58.5
```

### 原因 2：体重表中 ID 与数据列名不匹配

脚本使用正则 `re.match(r'([sS]\d+)', col)` 从列名提取受试者 ID。

**可能的问题**：
- 体重表中 `People` 列的值如果带有空格（如 `"S1 "` 或 `" S1"`），虽然代码中做了 `.str.strip()`，但如果写的是 `"s1"` 而非 `"S1"`，代码也会用 `.upper()` 转换，所以大小写没问题
- **但如果体重表中写的是 `1`、`2` 而不是 `S1`、`S2`，就会匹配失败**，导致所有列都跳过，输出"未找到匹配的受试者ID"

### 原因 3：输入数据文件路径不存在

配置的输入路径为：
```
G:\Carbon_Plate_Shoes_Data\STO_ForDeepLearning\Data_CSV_Split\High_Speed\Interpolte_huizhong_data
```

如果该路径不存在或下级文件夹结构与预期不符，`os.walk()` 将找不到任何文件。

### 原因 4：数据文件列名格式不符合正则规则

正则 `re.match(r'([sS]\d+)', col)` 要求列名以 `S` 或 `s` 加数字开头。如果列名是：
- `time` → 跳过（正常）
- `S1T1V1` → 匹配到 `S1`（正常）
- `subject1_T1_V1` → **匹配失败**（不以 S 开头）
- `S_T1_V1` → **匹配失败**（S 后面没有数字）

### 原因 5：输出路径拼写错误

输出路径中的文件夹名有拼写问题：
```
interpolte_huizhong_noemalization
```
注意 `noemalization` 应为 `normalization`。虽然这不影响程序运行，但可能导致后续找不到文件。

### 最可能的报错原因总结

根据代码结构分析，**最常见的报错原因是原因 1 和原因 2**：体重表文件不存在、列名不对（不是 `People`/`Weight`），或者体重表中的受试者 ID 格式与数据列名不匹配（如体重表写 `1` 而非 `S1`）。

**快速排查步骤**：
1. 打开 `baseline_01.csv`，确认有 `People` 和 `Weight` 两列
2. 确认 `People` 列的值形如 `S1`, `S2`...（而非 `1`, `2`...）
3. 确认数据文件的列名形如 `S1T1V1`（以 S+数字 开头）
4. 如果仍有问题，请提供具体的报错信息以便进一步排查
