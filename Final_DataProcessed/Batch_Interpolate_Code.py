########################################################################################################################
#通过一个批量循环程序来对每一个文件进行插值处理!
import Function_FinalProcessed as FTP
import os

InputFile = r'G:\xiangrongjie_PHD\xiangrong_jie_Data'
OutputFIle = r'G:\xiangrongjie_PHD\xiangrong_jie_Data\interplate'
for root, dirs, files in os.walk(InputFile):

    for file in files:
        if not file.lower().endswith(".csv"):
            continue
        input_file = os.path.join(root, file)
        rel_path = os.path.relpath(root, InputFile)
        output_dir = os.path.join(OutputFIle, rel_path)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, file)
        # interpolate_single_file_simple(input_file, output_file)
        FTP.interpolate_single_file_simple(input_file, output_file)
