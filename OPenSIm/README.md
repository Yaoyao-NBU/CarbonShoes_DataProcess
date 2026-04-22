# 碳板跑鞋力台数据处理工具

基于 OpenSim 力台数据（STO 格式）的批量处理工具，用于步态 stance 阶段的截取、异常值补偿与可视化。

## 文件说明

### `Batch_Draw_DrawStanceWithPeak.py`

批量处理主脚本，完成以下流程：

1. **遍历数据目录** — 按三层目录结构（被试/试验/速度）收集所有 `.sto` 文件，按 Trial（T1, T2, ...）分组
2. **Stance 检测** — 基于峰值向两侧搜索力阈值边界，确定真实触地时间段
3. **数据截取** — 在 stance 前后各补充 20 帧作为 padding，截取后时间列从 0.0 重新生成，padding 区域力台数据归零
4. **异常值补偿** — 对真实 stance 阶段的 COPx 和 COPz 数据，距离各自中位数超过阈值（默认 0.1m）的点替换为中位数
5. **绘图输出** — 按 Trial 绘制 Fy / COPx / COPy 对比折线图，以及每个文件的 Fy+COPx+COPz 组合图

#### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `source_dir` | — | 输入数据根目录 |
| `output_dir` | — | 绘图输出目录 |
| `output_cut_dir` | — | 截取后的 STO 文件输出目录 |
| `fs_sto` | 200 | 采样频率 (Hz) |
| `threshold` | 30 | Stance 检测力阈值 (N) |
| `padding_frames` | 20 | 前后补充帧数 |
| `distance_threshold` | 0.1 | COPx/COPz 异常值距离阈值 (m) |
| `dpi` | 600 | 图像分辨率 |

#### 输入目录结构要求

```
source_dir/
├── Amateur_Runner/
│   ├── S1/
│   │   ├── T1/
│   │   │   └── *.sto
│   │   └── T2/
│   │       └── *.sto
│   └── S2/
│       └── ...
└── Elite_Runner/
    └── ...
```

路径中需包含 `T1`/`T2`/`T3` 等 Trial 名称用于分组。

---

### `Data_ProcessFunction.py`

数据处理函数库，提供以下功能模块：

#### 滤波器

| 函数 | 说明 |
|------|------|
| `butter_lowpass_filter(data, cutoff, fs, order=4)` | Butterworth 低通滤波器 |
| `gaussian_filter_stance_cop(data, window_size=7, sigma=None)` | 高斯滤波器，用于 COP stance 阶段去噪 |

#### 文件滤波

| 函数 | 说明 |
|------|------|
| `filter_trc(input_path, output_path, cutoff=6, fs=200)` | 对 TRC 文件进行低通滤波，保留 6 行 header |
| `filter_mot(input_path, output_path, cutoff=50, fs=1000)` | 对 MOT/STO 文件进行低通滤波，保留 8 行 header |

#### 文件截取

| 函数 | 说明 |
|------|------|
| `cut_sto_by_time(sto_path, output_path, t_start, t_end, fs, t_stance_start, t_stance_end)` | 按时间截取 STO 文件，padding 区域力台数据归零，可选重建时间列 |
| `cut_trc_by_time(trc_path, output_path, t_start, t_end, fs)` | 按时间截取 TRC 文件，自动更新 header 帧数 |
| `cut_sto_with_gaussian_filter_cop(...)` | 截取 STO 并对 stance 阶段 COP 数据应用高斯滤波 |

#### Stance 检测

| 函数 | 说明 |
|------|------|
| `get_stance_time_from_sto(sto_path, fs, fz_pattern, threshold)` | 从力台数据中识别 stance 时间段（简单阈值法） |
| `get_stance_time_from_sto_with_peak(sto_path, fs, fz_pattern, threshold, padding_frames)` | 基于峰值检测的 stance 识别，从 Peak 向两侧搜索阈值边界，返回含补偿的时间范围 |

#### 数据处理

| 函数 | 说明 |
|------|------|
| `process_copx_outliers(data_dict, distance_threshold, t_stance_start, t_stance_end)` | 对 stance 阶段 COPx/COPz 异常值进行中位数补偿：距离中位数超过阈值的点替换为中位数，padding 区域保持归零 |
| `remove_baseline_force_sto(sto_path, output_path, threshold)` | 去除力台数据基线漂移（空台阶段均值扣除） |
| `fix_sto_ground_force_units(sto_path, output_path)` | 修正 STO 文件中 COP 单位 `ground_force_p=mm` → `ground_force_p=m` |

#### 其他

| 函数 | 说明 |
|------|------|
| `remove_marker_prefix_trc(input_path, output_path)` | 去除 TRC 文件 marker 名称的冒号前缀（如 `Pre_test_run:LSHO` → `LSHO`） |
| `expand_trc_single_frame(input_path, output_path, duration_sec)` | 将单帧 TRC 数据扩充为指定时间长度的连续帧 |

---

## 处理流程示意

```
原始 STO 文件
    │
    ▼
get_stance_time_from_sto_with_peak()  ──  检测 stance 时间段
    │
    ▼
cut_sto_by_time()  ──  截取 + padding 归零 + 时间列重建
    │
    ▼
process_copx_outliers()  ──  COPx/COPz 异常值中位数补偿
    │
    ▼
输出: 截取后的 STO 文件 + 绘图
```

## 依赖

- Python 3.x
- numpy
- pandas
- scipy
- matplotlib

## 运行

```bash
# 修改 Batch_Draw_DrawStanceWithPeak.py 中的目录配置后直接运行
python Batch_Draw_DrawStanceWithPeak.py
```
