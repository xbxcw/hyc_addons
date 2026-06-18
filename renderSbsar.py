import subprocess
import os

# ===================== 配置区 =====================


def find_specified_file(path, suffix=""):
    """
    查找指定文件
    :param path: 根目录
    :param suffix: 格式，默认是空
    :return: 文件地址列表
    """
    _file = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(suffix):
                _file.append(os.path.join(root, file))
    return _file


def get_sbsar_exposed_params(sbsrender_exe, sbsar_file):
    """
    获取sbsar文件暴露的所有参数信息

    Args:
        sbsrender_exe: sbsrender.exe的完整路径
        sbsar_file: sbsar文件的完整路径

    Returns:
        参数信息列表，每个元素包含参数名、类型、默认值等信息
    """
    cmd = [sbsrender_exe, "info", sbsar_file]
    result = subprocess.run(cmd, capture_output=True, text=True, shell=False)

    if result.returncode != 0:
        print(f"获取参数失败: {result.stderr}")
        return []

    params = []
    lines = result.stdout.strip().split("\n")

    for line in lines:
        line = line.strip()
        if line.startswith("INPUT "):
            parts = line.split()
            if len(parts) >= 3:
                name = parts[1]
                param_type = parts[2]
                params.append({"name": name, "type": param_type, "default": ""})

    return params


def render_billboard_textures(
    sbsrender_exe,
    sbsar_file,
    input_folder,
    output_root,
    output_size=2048,
    output_format="tga",
):
    """
    渲染Billboard纹理，需要DA和NR两个参数同时传入

    Args:
        sbsrender_exe: sbsrender.exe路径
        sbsar_file: sbsar文件路径
        input_folder: 输入图片文件夹
        output_root: 输出根目录
        output_size: 输出尺寸，默认2048
        output_format: 输出格式，默认tga

    Returns:
        缺失NR的DA文件列表
    """
    texture_files = find_specified_file(input_folder, ".tga")

    da_files = {}
    missing_nr_list = []

    for img_path in texture_files:
        filename = os.path.basename(img_path)
        if "DA.tga" in filename:
            base_name = filename.replace("DA.tga", "")
            da_files[base_name] = img_path

    for base_name, da_path in da_files.items():
        nr_filename = f"{base_name}NR.tga"
        da_dir = os.path.dirname(da_path)
        nr_path = os.path.join(da_dir, nr_filename)

        if os.path.exists(nr_path):
            print(f"\n===== 处理: {base_name} =====")
            print(f"DA: {da_path}")
            print(f"NR: {nr_path}")

            single_out_dir = output_root
            os.makedirs(single_out_dir, exist_ok=True)

            cmd = [
                sbsrender_exe,
                "render",
                "--input",
                sbsar_file,
                "--output-path",
                single_out_dir,
                "--output-name",
                f"{base_name}{{outputNodeName}}",
                "--set-entry",
                f"DA@{da_path}",
                "--set-entry",
                f"NR@{nr_path}",
                # "--size",
                # str(output_size),
                "--output-format",
                output_format,
            ]

            print(f"执行命令: {' '.join(cmd)}")
            proc = subprocess.run(cmd, capture_output=True, text=True)

            if proc.stderr:
                print(f"警告/错误: {proc.stderr}")
            if proc.returncode == 0:
                print(f"处理完成，输出: {single_out_dir}")
            else:
                print(f"处理失败！")
        else:
            missing_nr_list.append(da_path)
            print(f"警告: {da_path} 缺少对应的NR文件 ({nr_filename})")

    if missing_nr_list:
        print(f"\n===== 以下DA文件缺少对应的NR文件 =====")
        for da_path in missing_nr_list:
            print(da_path)

    return missing_nr_list


SBSRENDER_EXE = r"C:\Program Files\Adobe\Adobe Substance 3D Designer\sbsrender.exe"

GRAPH_FILE = r"C:\Users\Administrator\Documents\github\xbxcw\hyc_sd\Billboard.sbsar"

INPUT_IMG_FOLDER = r"E:\work\SM_Plant\bake"  # 待处理图片文件夹

OUT_ROOT = r"C:\Users\Administrator\Desktop\temp\Tex"  # 批量输出根目录

EXPOSED_BITMAP_NAME = "DA"  # 根据sbsrender info结果，正确的位图输入参数是 DA 和 NR
OUT_SIZE = 2048
OUT_FORMAT = "tga"
if __name__ == "__main__":
    print("=== 获取 sbsar 暴露参数 ===")
    params = get_sbsar_exposed_params(SBSRENDER_EXE, GRAPH_FILE)
    for param in params:
        print(f"参数名: {param['name']}, 类型: {param['type']}")

    print("\n=== 开始渲染 Billboard 纹理 ===")
    missing_nr = render_billboard_textures(
        sbsrender_exe=SBSRENDER_EXE,
        sbsar_file=GRAPH_FILE,
        input_folder=INPUT_IMG_FOLDER,
        output_root=OUT_ROOT,
        output_size=OUT_SIZE,
        output_format=OUT_FORMAT,
    )

    print("\n=== 渲染任务结束 ===")
    if missing_nr:
        print(f"有 {len(missing_nr)} 个DA文件缺少对应的NR文件")


# # 遍历输入文件夹
# for filename in os.listdir(INPUT_IMG_FOLDER):
#     # 过滤图片格式
#     if not filename.lower().endswith(SUPPORT_EXT):
#         continue

#     img_full_path = os.path.join(INPUT_IMG_FOLDER, filename)
#     file_name_no_ext = os.path.splitext(filename)[0]
#     # 每张图片单独建立输出子文件夹，避免贴图覆盖
#     single_out_dir = os.path.join(OUT_ROOT, file_name_no_ext)
#     os.makedirs(single_out_dir, exist_ok=True)

#     # 构造命令


#     print(f"\n===== 正在处理：{filename} =====")
#     proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)

#     if proc.stderr:
#         print("警告/错误：", proc.stderr)
#     if proc.returncode == 0:
#         print(f"{filename} 处理完成，输出：{single_out_dir}")
#     else:
#         print(f"{filename} 处理失败！")

# print("\n===== 全部图片处理任务结束 =====")