# Cal_MaxValue.py 运行逻辑说明

## 一句话概括

从按「人群 × 刚度」组织的 CSV 数据文件夹中，批量提取每一列的最大值，按受试者取多次试验均值后，汇总输出宽格式统计表。

---

## 数据目录结构（前提条件）

脚本依赖固定的文件夹层级来识别人群和刚度：

```
INPUT_ROOT_DIR/
├── Amateur_Runner/
│   ├── T1/
│   │   ├── ankle_angle_r.csv       ← 每个CSV的列名形如 S1T1V1, S2T1V2...
│   │   ├── knee_angle_r.csv
│   │   └── ...
│   ├── T2/
│   │   └── ...
│   └── T3/
│       └── ...
└── Elite_Runner/
    ├── T1/
    ├── T2/
    └── T3/
```

- **GROUPS**：`Amateur_Runner`（业余跑者）、`Elite_Runner`（精英跑者）
- **STIFFNESSES**：`T1`（最软）、`T2`（中等）、`T3`（最硬）
- CSV 列名格式：`S<编号>T<刚度>V<试验号>`，例如 `S1T1V1` = 受试者1、刚度1、第1次试验

---

## 整体流程

```
扫描目录 → 按文件名归类 → 逐特征处理 → 输出汇总表
```

共 3 步，对应 3 个核心函数：

### 1. `scan_and_group_files(root_dir)` — 扫描 & 归类

- 递归遍历输入目录
- 通过路径中的关键字（`Amateur_Runner`、`T1` 等）识别每份文件的人群和刚度
- 按 **文件名** 归类，生成字典：

```python
{
    'ankle_angle_r.csv': [
        {'path': '.../Amateur_Runner/T1/ankle_angle_r.csv', 'group': 'Amateur_Runner', 'stiffness': 'T1'},
        {'path': '.../Amateur_Runner/T2/ankle_angle_r.csv', 'group': 'Amateur_Runner', 'stiffness': 'T2'},
        {'path': '.../Elite_Runner/T3/ankle_angle_r.csv',   'group': 'Elite_Runner',   'stiffness': 'T3'},
        ...
    ],
    'knee_angle_r.csv': [...],
    ...
}
```

### 2. `process_single_feature(filename, file_info_list, output_path)` — 提取最大值 & 汇总

对单个特征文件（如 `ankle_angle_r.csv`），执行双层循环：

```
外层循环: 遍历人群 (Amateur → Elite)
  内层循环: 遍历刚度 (T1 → T2 → T3)
    ├─ 读取对应 CSV
    ├─ df.max() 计算每列最大值 → Series
    ├─ 从列名提取受试者ID (S1T1V1 → S1)
    ├─ 同一受试者的多次试验取平均 (groupby.mean)
    └─ 按索引横向合并 (merge)
  → 得到当前人群的 DataFrame (列: Amateur_T1, Amateur_T2, Amateur_T3)
  → 删除 Subject 索引

最终: 两个人群的 DataFrame 横向拼接 (pd.concat axis=1)
```

**数据变换示意：**

```
原始CSV:                     df.max() 后:              groupby('Subject').mean() 后:
   S1T1V1  S1T1V2  S2T1V1      S1T1V1  S1T1V2  S2T1V1     Subject  Amateur_Runner_T1
   1.2     1.5     0.8          3.4     3.1     2.9        S1       3.25  ← (3.4+3.1)/2
   3.4     3.1     2.9          ↑最大值                     S2       2.9
```

### 3. 主程序入口 `__main__`

```
创建输出目录 → 扫描文件 → 遍历每个特征 → 调用 process_single_feature → 保存 Summary_Max_<filename>.csv
```

---

## 输出格式

文件名：`Summary_Max_<原文件名>`

| Amateur_Runner_T1 | Amateur_Runner_T2 | Amateur_Runner_T3 | Elite_Runner_T1 | Elite_Runner_T2 | Elite_Runner_T3 |
|---|---|---|---|---|---|
| 3.25 | 2.87 | 3.01 | 4.12 | 3.56 | 3.89 |
| 2.90 | 2.45 | 2.78 | 3.88 | 3.21 | 3.67 |

- 每行 = 一个受试者（匿名，无 Subject 列）
- 每列 = 人群_刚度 组合下的最大值均值

---

## 与同类脚本的区别

| 脚本 | 核心计算行 | 输出前缀 |
|---|---|---|
| **Cal_MaxValue.py** | `df.max()` | `Summary_Max_` |
| Cal_MinValue.py | `df.min()` | `Summary_Min_` |
| Cal_Range.py | `df.max() - df.min()` | `Summary_Range_` |
| Cal_AT_Impulse.py | `trapezoid(valid_data, dx=DT)` | `Summary_Impulse_` |
| Cal_Power.py | `df_moment * df_velocity` + 积分 | `Raw_*` / `Time_Series_*` |

结构完全相同，只需替换核心计算那一行即可切换统计指标。

---

## 使用方法

1. 修改脚本顶部的两个路径：
   ```python
   INPUT_ROOT_DIR = r'你的输入目录'
   OUTPUT_DIR = r'你的输出目录'
   ```
2. 确认 `GROUPS` 和 `STIFFNESSES` 与你的文件夹层级匹配
3. 运行：`python Cal_MaxValue.py`

---

## 关键函数速查

| 函数 | 作用 |
|---|---|
| `get_subject_id(col_name)` | 正则提取受试者 ID，如 `S1T1V1` → `S1` |
| `scan_and_group_files(root_dir)` | 扫描目录，按文件名归类，标注人群和刚度 |
| `process_single_feature(...)` | 读取 CSV → 计算最大值 → 按受试者平均 → 横向合并 → 保存 |
