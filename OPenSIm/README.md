# OPenSIm - OpenSim 生物力学数据处理工具集

针对 OpenSim 格式的 TRC（运动学标记）和 STO（力台力学）文件，提供从预处理、Stance 截取、COP 异常值纠正到可视化绘图的完整处理流水线。

## 目录结构

```
OPenSIm/
├── Data_ProcessFunction.py          # 核心函数库（所有处理函数）
├── filter_ForTrcAndMot.py           # 批量低通滤波
├── Rename_TrcAndMot.py              # 批量重命名
├── mirror_LeftFoot_Load.py          # TRC 左右镜像（左脚数据转右脚）
├── Batch_CUT_TrcSto.py              # 基础 Stance 截取
├── Batch_ZeroNonStanceForce.py      # Stance 截取 + 非受力段归零 + 单位修正
├── Batch_CutStanceWithPeak.py       # Peak 检测 Stance 截取
├── Batch_CutStanceWithPeak_Median.py      # Peak + COP 中值补偿
├── Batch_CutStanceWithPeak_Linear.py      # Peak + COP 线性趋势填补
├── Batch_CutStanceWithPeak_SlopeCorrect.py # Peak + COP 斜率纠正
├── Batch_Draw_DrawStanceWithPeak.py            # Peak + 中值补偿 + 高斯滤波 + 绘图
├── Batch_Draw_DrawStanceWithPeak_Linear.py    # Peak + 线性填补 + 绘图
├── Batch_Draw_DrawStanceWithPeak_SlopeCorrect.py # Peak + 斜率纠正 + 绘图
├── ceshi.py                         # 单文件 TRC 镜像测试
├── ceshi01.py                       # 单文件 STO GRF 镜像测试
└── Data/                            # 输入/输出数据目录
    ├── input/                       # 原始数据（受试者/试验/文件）
    └── output*/                     # 各流程输出结果
```

## 核心函数库 — Data_ProcessFunction.py

提供所有底层处理函数，供批量脚本调用：

| 函数 | 功能 |
|------|------|
| `butter_lowpass_filter()` | Butterworth 低通滤波器 |
| `gaussian_filter_stance_cop()` | 高斯滤波，用于 COP 信号平滑 |
| `filter_trc()` | 对 TRC 文件低通滤波（保留 6 行 header） |
| `filter_mot()` | 对 MOT/STO 文件低通滤波（保留 8 行 header） |
| `remove_marker_prefix_trc()` | 去除 TRC 标记名前缀（如 `Pre_test_run:LSHO` → `LSHO`） |
| `remove_baseline_force_sto()` | 去除 STO 力台基线漂移 |
| `expand_trc_single_frame()` | 单帧 TRC 扩展为指定时长 |
| `get_stance_time_from_sto()` | 基于阈值检测 Stance 时间段 |
| `get_stance_time_from_sto_with_peak()` | 基于 Peak 检测 Stance 时间段（更精确） |
| `cut_sto_by_time()` | 按时间截取 STO 文件，可归零补充帧力数据 |
| `cut_trc_by_time()` | 按时间截取 TRC 文件，重建帧号/时间列 |
| `cut_sto_with_gaussian_filter_cop()` | 截取 STO 并对 COP 施加高斯滤波 |
| `process_copx_outliers()` | COP 异常值中值补偿（距中位数超阈值→替换为中位数） |
| `process_cop_outliers_linear()` | COP 异常值线性趋势填补（中位数距离 + 帧间跳变双重检测） |
| `process_cop_outliers_slope()` | COP 异常值斜率纠正（基于中间部分线性斜率递推） |
| `fix_sto_ground_force_units()` | 修正 STO 文件 COP 单位（mm → m） |

## 数据预处理

### filter_ForTrcAndMot.py — 批量低通滤波

对指定目录下所有 TRC 和 STO 文件进行低通滤波处理：
- TRC 文件：截止频率 6 Hz（运动学标记），同时去除标记名前缀
- STO 文件：截止频率 50 Hz（地面反力）

### Rename_TrcAndMot.py — 批量重命名

递归遍历目录，删除文件名中的指定字符串（如 `_filtered`、`_c3d`），保持原文件夹结构输出。

### mirror_LeftFoot_Load.py — 左脚力台数据镜像

当受试者左脚踩在 2 号力台上时，需要对数据进行左右镜像使其与右脚数据一致：
- 以 SACR（骶骨）Z 坐标均值为镜像中心
- Z 轴原地镜像：`Z_new = 2 × z_center - Z_old`
- 左右标记名互换（L ↔ R），对应数据列重排

## Stance 截取流水线（4 种 COP 处理策略）

### 处理流程对比

```
                    ┌─ Batch_CutStanceWithPeak.py          → 仅截取 + 单位修正
                    ├─ Batch_CutStanceWithPeak_Median.py   → 截取 + COP 中值补偿
Peak检测Stance时间 →├─ Batch_CutStanceWithPeak_Linear.py   → 截取 + COP 线性趋势填补
                    └─ Batch_CutStanceWithPeak_SlopeCorrect.py → 截取 + COP 斜率纠正
```

### 1. Batch_CutStanceWithPeak.py — 基础截取

基于 Peak 检测识别 Stance 时间段，前后补充 padding 帧（默认 20 帧），截取 STO 和 TRC 文件，补充帧力数据归零，修正 COP 单位。

### 2. Batch_CutStanceWithPeak_Median.py — COP 中值补偿

在基础截取基础上，对 Stance 阶段 COPx/COPz 进行中值补偿：
- 计算 Stance 阶段 COP 中位数
- 距中位数超过阈值（默认 0.1m）的点替换为中位数
- 适用于 COP 突跳幅度较大的数据

### 3. Batch_CutStanceWithPeak_Linear.py — COP 线性趋势填补

在基础截取基础上，采用双重检测 + 线性趋势填补：
- **检测 1**：距中位数超过阈值（默认 0.08m）
- **检测 2**：帧间跳变超过阈值（默认 30mm）
- **填补**：用正常点拟合线性趋势 `y = k·t + b`，异常点按趋势值填补
- 比"中值替换"更能保持 COP 的连续变化趋势

### 4. Batch_CutStanceWithPeak_SlopeCorrect.py — COP 斜率纠正

在基础截取基础上，基于中间部分斜率递推纠正：
- 取 Stance 中间部分（默认 30%~70%）线性拟合，获取通用斜率 k
- 从中间向两端遍历，变化率超过 `rate_multiplier × k` 的帧视为异常
- 异常帧用 `上一正常值 ± k·dt` 修正，保持线性趋势连续性
- 最适合 COP 整体呈线性趋势的场景

## 绘图工具（3 种，含对应 COP 处理策略）

| 脚本 | COP 处理方式 | 绘图内容 |
|------|-------------|---------|
| Batch_Draw_DrawStanceWithPeak.py | 中值补偿 + 高斯滤波 | Trial 叠加图 + 单文件组合图 |
| Batch_Draw_DrawStanceWithPeak_Linear.py | 线性趋势填补 | Trial 叠加图 + 单文件组合图 |
| Batch_Draw_DrawStanceWithPeak_SlopeCorrect.py | 斜率纠正 | Trial 叠加图 + 单文件组合图 + **原始 vs 纠正对比图** |

绘图输出：
- **Trial 叠加图**：同一 Trial 下所有文件按 Fy / COPx / COPz 分别叠加
- **单文件组合图**：单个文件的 Fy / COPx / COPz 三子图
- **对比图**（仅斜率纠正版）：COPx / COPz 原始曲线 vs 纠正后曲线

## 早期版本脚本

| 脚本 | 说明 |
|------|------|
| Batch_CUT_TrcSto.py | 最早的版本，基础阈值检测 Stance + 截取，无 Peak 检测、无归零 |
| Batch_ZeroNonStanceForce.py | 基础阈值检测 + 非受力段归零 + 单位修正（Peak 检测前的过渡版本） |

## 数据目录约定

```
Data/input/{受试者类别}/{受试者ID}/{试验ID}/
    ├── S1T1V11.sto    # 力台力学数据
    ├── S1T1V11.trc    # 运动学标记数据
    └── ...
```

## 关键参数说明

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `fs_trc` / `fs_sto` | 200 Hz | TRC / STO 采样频率 |
| `threshold` | 30 N | Stance 检测力阈值 |
| `fz_pattern` | `.*_ground_force_v[yz]$` | 垂直力列名匹配模式 |
| `padding_frames` | 20 | Stance 前后补充帧数 |
| `distance_threshold` | 0.08~0.1 m | COP 异常值距离阈值 |
| `middle_ratio` | 0.3 | 斜率纠正中间部分占比（取 30%~70%） |
| `rate_multiplier` | 2.0 | 斜率纠正异常判定倍数 |
| `dpi` | 600 | 图像分辨率 |

## 依赖

- Python 3.x
- numpy, pandas, scipy, matplotlib
