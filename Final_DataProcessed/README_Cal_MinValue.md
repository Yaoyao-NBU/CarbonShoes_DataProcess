# Cal_MinValue.py 修改说明

## 文件说明

本文件是基于 `Cal_MaxValue.py` 修改而来，用于计算数据的最小值（Minimum）而非最大值（Maximum）。

---

## 修改内容对比

### 1. 核心计算逻辑（第74-76行）

**Cal_MaxValue.py（原文件）:**
```python
# =======================================================
# 🔥 修改点：这里改为计算每一列的最大值 (Max)
# =======================================================
# df.max() 会返回一个 Series，索引是列名，值是该列的最大值
feature_series = df.max()
```

**Cal_MinValue.py（本文件）:**
```python
# =======================================================
# 🔥 核心修改点：计算每一列的最小值 (Min)
# 与 Cal_MaxValue.py 的唯一区别：
# Cal_MaxValue.py 使用 df.max() 计算最大值
# 本文件使用 df.min() 计算最小值
# =======================================================
# df.min() 会返回一个 Series，索引是列名，值是该列的最小值
feature_series = df.min()
```

---

### 2. 输出文件名前缀（第109行）

**Cal_MaxValue.py（原文件）:**
```python
# 保存文件，前缀改为 Summary_Max_
save_file = os.path.join(output_path, f"Summary_Max_{filename}")
```

**Cal_MinValue.py（本文件）:**
```python
# 保存文件，前缀改为 Summary_Min_
save_file = os.path.join(output_path, f"Summary_Min_{filename}")
```

---

### 3. 程序运行提示信息

| 位置 | Cal_MaxValue.py | Cal_MinValue.py |
|------|-----------------|-----------------|
| 第124行 | `开始提取最大值...` | `开始提取最小值...` |
| 第111行 | `已生成最大值汇总表` | `已生成最小值汇总表` |
| 第129行 | `最大值已提取` | `最小值已提取` |

---

### 4. 函数文档字符串（第44行）

**Cal_MaxValue.py（原文件）:**
```python
def process_single_feature(filename, file_info_list, output_path):
    """
    处理单个特征文件，计算最大值，并按宽格式汇总（无Subject列）。
    """
```

**Cal_MinValue.py（本文件）:**
```python
def process_single_feature(filename, file_info_list, output_path):
    """
    处理单个特征文件，计算最小值，并按宽格式汇总（无Subject列）。
    """
```

---

## 总结

| 修改项 | 说明 |
|--------|------|
| **核心算法** | `df.max()` → `df.min()` |
| **输出文件名** | `Summary_Max_*.csv` → `Summary_Min_*.csv` |
| **提示信息** | 所有"最大"改为"最小" |
| **文档注释** | 函数说明中的"最大值"改为"最小值" |

**代码的其他部分（包括目录结构、分组逻辑、数据处理方式等）均与 `Cal_MaxValue.py` 保持一致，未做任何修改。**
