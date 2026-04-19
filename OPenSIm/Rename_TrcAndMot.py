"""
用于对已经命名具有一定规律的文件名字，尽心更改!
"""
#######################################################################################################################
import os
import shutil
#######################################################################################################################
def export_with_structure(root_folder, file_extensions, remove_str, output_root):
    """
    递归遍历 root_folder →
    处理指定后缀文件 (.trc / .mot / .sto 等) →
    删除文件名中的 remove_str →
    保留原文件夹结构输出到 output_root

    参数：
        root_folder    : 原始文件夹
        file_extensions: 需要处理的文件后缀列表，如 ['.trc', '.mot', '.sto']
        remove_str     : 文件名中需要删除的字符串（如 '_c3d'）
        output_root    : 输出文件夹
    """

    # 统一小写后缀，避免大小写问题
    file_extensions = [ext.lower() for ext in file_extensions]

    for current_path, dirs, files in os.walk(root_folder):

        # 过滤出需要的文件类型
        target_files = [
            f for f in files if os.path.splitext(f)[1].lower() in file_extensions
        ]

        if not target_files:
            continue

        # 当前路径在 root_folder 中的相对路径
        rel_path = os.path.relpath(current_path, root_folder)

        # 创建输出路径结构
        export_path = os.path.join(output_root, rel_path)
        os.makedirs(export_path, exist_ok=True)

        for filename in target_files:

            # 删除指定字符串，例如 "_c3d"
            new_name = filename.replace(remove_str, "").lstrip("_- ")

            old_file = os.path.join(current_path, filename)
            new_file = os.path.join(export_path, new_name)

            shutil.copy2(old_file, new_file)

            print(f"Exported: {rel_path}/{filename}  →  {rel_path}/{new_name}")

    print("\nAll selected files processed and exported successfully!")


# ====================== 使用示例 ======================

export_with_structure(
    root_folder=r"G:\Carbon_Plate_Shoes_Data\Data_TrcAndSto\Data\ceshi\filter_File",
    file_extensions=[".trc", ".mot", ".sto"],  # 选择你想处理的后缀
    remove_str="_filtered",  # 你文件名里统一需要删除的部分
    output_root=r"G:\Carbon_Plate_Shoes_Data\Data_TrcAndSto\Data\ceshi\filter_File\rename"
)
