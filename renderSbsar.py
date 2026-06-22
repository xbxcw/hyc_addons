import subprocess
import os
import math
from PIL import Image

# ===================== 配置区 =====================

def get_image_dimensions(image_path):
    """
    使用Pillow获取图片尺寸
    
    Args:
        image_path: 图片文件路径
    
    Returns:
        (width, height) 或 None
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        print(f"读取图片尺寸失败: {e}")
        return None


def get_power_exponent(pixel_size):
    """
    使用math.log2获取2的幂次指数
    
    Args:
        pixel_size: 像素尺寸
        
    Returns:
        指数值 (如 10 表示 2^10 = 1024)
    """
    if pixel_size <= 0:
        return 8  # 默认 2^8 = 256
    
    exponent = round(math.log2(pixel_size))
    # 限制在有效范围内 (8-11 对应 256-2048)
    return max(8, min(exponent, 11))


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


def get_da_nr_pairs(input_folder):
    """
    获取DA和对应的NR文件对列表

    Args:
        input_folder: 输入图片文件夹

    Returns:
        (valid_pairs, missing_nr_list) - 有效的DA-NR文件对列表和缺少NR的DA文件列表
    """
    texture_files = find_specified_file(input_folder, ".tga")
    da_files = {}
    valid_pairs = []
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
            valid_pairs.append({"base_name": base_name, "da_path": da_path, "nr_path": nr_path})
        else:
            missing_nr_list.append({"base_name": base_name, "da_path": da_path, "nr_filename": nr_filename})

    return valid_pairs, missing_nr_list


def render_single_billboard(
    sbsrender_exe,
    sbsar_file,
    base_name,
    da_path,
    nr_path,
    output_root,
    output_format="tga",
):
    """
    渲染单个Billboard纹理，保持输入图片的像素比例

    Args:
        sbsrender_exe: sbsrender.exe路径
        sbsar_file: sbsar文件路径
        base_name: 基础名称
        da_path: DA文件路径
        nr_path: NR文件路径
        output_root: 输出根目录
        output_format: 输出格式

    Returns:
        是否渲染成功
    """
    print(f"\n===== 处理: {base_name} =====")
    print(f"DA: {da_path}")
    print(f"NR: {nr_path}")

    # 使用Pillow获取输入图片尺寸
    dimensions = get_image_dimensions(da_path)
    if dimensions:
        src_width, src_height = dimensions
        # 使用math.log2计算2的幂次指数
        width_exp = get_power_exponent(src_width)
        height_exp = get_power_exponent(src_height)
        output_width = 2 ** width_exp
        output_height = 2 ** height_exp
        print(f"输入尺寸: {src_width}x{src_height}")
        print(f"输出指数: {width_exp}, {height_exp} (对应 {output_width}x{output_height})")
    else:
        # 如果读取失败，使用默认指数
        width_exp = 11
        height_exp = 11
        print(f"无法读取输入尺寸，使用默认指数: {width_exp},{height_exp}")

    os.makedirs(output_root, exist_ok=True)

    cmd = [
        sbsrender_exe,
        "render",
        "--input",
        sbsar_file,
        "--output-path",
        output_root,
        "--output-name",
        f"{base_name}{{outputNodeName}}",
        "--set-entry",
        f"DA@{da_path}",
        "--set-entry",
        f"NR@{nr_path}",
        "--set-value",
        f"$outputsize@{width_exp},{height_exp}",
        "--output-format",
        output_format,
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.stderr:
        print(f"警告/错误: {proc.stderr}")
    if proc.returncode == 0:
        print(f"处理完成，输出: {output_root}")
        return True
    else:
        print(f"处理失败！")
        return False


SBSRENDER_EXE = r"C:\Program Files\Adobe\Adobe Substance 3D Designer\sbsrender.exe"

GRAPH_FILE = r"C:\Users\Administrator\Documents\github\xbxcw\hyc_sd\Billboard.sbsar"

INPUT_IMG_FOLDER = r"E:\work\SM_Holly\Bake\SM_Component_Door001_a"  # 待处理图片文件夹

OUT_ROOT = r"E:\work\SM_Plant\Tex"  # 批量输出根目录

EXPOSED_BITMAP_NAME = "DA"  # 根据sbsrender info结果，正确的位图输入参数是 DA 和 NR
OUT_SIZE = 2048
OUT_FORMAT = "tga"

if __name__ == "__main__":
    print("=== 获取 sbsar 暴露参数 ===")
    params = get_sbsar_exposed_params(SBSRENDER_EXE, GRAPH_FILE)
    for param in params:
        print(f"参数名: {param['name']}, 类型: {param['type']}")

    print("\n=== 获取文件对列表 ===")
    valid_pairs, missing_nr_list = get_da_nr_pairs(INPUT_IMG_FOLDER)
    total_da_files = len(valid_pairs) + len(missing_nr_list)

    print(f"统计信息:")
    print(f"  - 总DA文件数: {total_da_files}")
    print(f"  - 有效DA-NR文件对: {len(valid_pairs)}")
    print(f"  - 缺少NR的DA文件: {len(missing_nr_list)}")

    if missing_nr_list:
        print("\n===== 以下DA文件缺少对应的NR文件 =====")
        for item in missing_nr_list:
            print(f"  {item['da_path']} (缺少 {item['nr_filename']})")

    print("\n=== 开始渲染 Billboard 纹理 ===")
    success_count = 0
    fail_count = 0


    for index, pair in enumerate(valid_pairs, start=1):
        print(f"\n[{index}/{len(valid_pairs)}]")
        success = render_single_billboard(
            sbsrender_exe=SBSRENDER_EXE,
            sbsar_file=GRAPH_FILE,
            base_name=pair["base_name"],
            da_path=pair["da_path"],
            nr_path=pair["nr_path"],
            output_root=OUT_ROOT,
            output_format=OUT_FORMAT,
        )
        if success:
            success_count += 1
        else:
            fail_count += 1
        # break
    print("\n=== 渲染任务结束 ===")
    print(f"统计结果:")
    print(f"  - 总处理数: {len(valid_pairs)}")
    print(f"  - 成功: {success_count}")
    print(f"  - 失败: {fail_count}")
    if missing_nr_list:
        print(f"  - 跳过(缺少NR): {len(missing_nr_list)}")