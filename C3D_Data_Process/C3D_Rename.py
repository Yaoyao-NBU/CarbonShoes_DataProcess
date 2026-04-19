import os
import shutil

def export_c3d_with_structure(root_folder, remove_str, output_root):
    """
    递归搜索 C3D 文件 → 删除指定字符串 → 保留原文件夹结构导出

    参数：
        root_folder : 原始文件夹（包含分组、受试者等）
        remove_str  : 需要从文件名中删除的字符串
        output_root : 输出文件夹（自动创建结构）
    """

    for current_path, dirs, files in os.walk(root_folder):

        # 只处理 C3D 文件
        c3d_files = [f for f in files if f.lower().endswith(".c3d")]
        if not c3d_files:
            continue

        # 计算相对于 root_folder 的路径
        rel_path = os.path.relpath(current_path, root_folder)

        # 在输出路径中创建相同结构
        export_path = os.path.join(output_root, rel_path)
        os.makedirs(export_path, exist_ok=True)

        for filename in c3d_files:

            # 生成新文件名
            new_name = filename.replace(remove_str, "").lstrip("_- ")

            old_file = os.path.join(current_path, filename)
            new_file = os.path.join(export_path, new_name)

            shutil.copy2(old_file, new_file)

            print(f"Exported: {rel_path}/{filename}  →  {rel_path}/{new_name}")

    print("\nAll C3D files processed and exported successfully!")

export_c3d_with_structure(r"G:\Carbon_Plate_Shoes_Data\ceshi\Amateur_Runner",'Trimmed',r'G:\Carbon_Plate_Shoes_Data\ceshi\Rename')