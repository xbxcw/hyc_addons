import os
import subprocess
import json
import math
import re


def get_sbsar_exposed_params(sbsrender_exe, sbsar_file):
    """通过 sbsrender.exe 获取 SBSAR 文件的所有暴露参数。

    参数:
        sbsrender_exe: sbsrender.exe 的完整路径。
        sbsar_file: SBSAR 文件的完整路径。

    返回:
        list[dict]: 参数列表，每个参数包含 name, type, default 字段。

    异常:
        FileNotFoundError: sbsrender.exe 或 SBSAR 文件不存在。
        RuntimeError: sbsrender 执行失败或输出无法解析。
    """
    if not os.path.exists(sbsrender_exe):
        raise FileNotFoundError(f'sbsrender.exe 不存在: {sbsrender_exe}')
    if not os.path.exists(sbsar_file):
        raise FileNotFoundError(f'SBSAR 文件不存在: {sbsar_file}')

    cmd = [sbsrender_exe, 'info', '--input', sbsar_file]
    result = subprocess.run(cmd, capture_output=True, text=True, shell=False)

    if result.returncode != 0:
        raise RuntimeError(f'sbsrender info 执行失败: {result.stderr.strip()}')

    output = result.stdout.strip()
    if not output:
        raise RuntimeError('sbsrender info 返回空输出')

    try:
        return _parse_json_output(output)
    except (json.JSONDecodeError, ValueError):
        pass

    try:
        return _parse_text_output(output)
    except ValueError:
        pass

    raise RuntimeError(f'无法解析 sbsrender 输出:\n{output[:500]}')


def _parse_json_output(output):
    """解析 sbsrender JSON 格式的输出。

    参数:
        output: sbsrender 的 JSON 输出字符串。

    返回:
        list[dict]: 参数列表。

    异常:
        ValueError: 未找到任何参数。
    """
    params = []
    data = json.loads(output)
    graph_list = data if isinstance(data, list) else [data]

    for graph in graph_list:
        for param in graph.get('parameters', graph.get('inputs', [])):
            params.append({
                'name': param.get('name', param.get('identifier', '')),
                'type': param.get('type', param.get('usagetype', '')),
                'default': str(param.get('default', param.get('defaultValue', '')))
            })
    if not params:
        raise ValueError('未找到任何暴露的参数')
    return params


def _parse_text_output(output):
    """解析 sbsrender 纯文本格式的输出（备用方案）。

    参数:
        output: sbsrender 的文本输出字符串。

    返回:
        list[dict]: 参数列表。

    异常:
        ValueError: 未找到任何参数。
    """
    params = []
    lines = output.split('\n')
    pattern = re.compile(
        r'^\s*INPUT\s+'
        r'(?P<name>\$?\w+)'
        r'\s+'
        r'(?P<type>\w+)'
    )

    for line in lines:
        match = pattern.search(line)
        if match:
            name = match.group('name')
            params.append({
                'name': name,
                'type': match.group('type'),
                'default': ''
            })

    if not params:
        raise ValueError('未找到任何暴露的参数')
    return params


def get_image_dimensions(image_path):
    """获取图片的宽度和高度。

    参数:
        image_path: 图片文件的完整路径。

    返回:
        tuple 或 None: (width, height) 或读取失败时返回 None。
    """
    from PIL import Image
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        print(f'读取图片尺寸失败: {e}')
        return None


def is_checkbox_param(param):
    """判断参数是否应显示为复选框。

    规则：名称以 'is_' 开头且类型为 'INTEGER1'。

    参数:
        param: 参数字典，包含 name 和 type 字段。

    返回:
        bool: 是否应显示为复选框。
    """
    name = param.get('name', '')
    param_type = param.get('type', '')
    return name.startswith('is_') and param_type == 'INTEGER1'


def get_power_exponent(pixel_size):
    """将像素尺寸转换为最接近的 2 的幂指数（范围 8-11）。

    参数:
        pixel_size: 像素尺寸。

    返回:
        int: 2 的幂指数，范围 [8, 11]。
    """
    if pixel_size <= 0:
        return 8
    exponent = round(math.log2(pixel_size))
    return max(8, min(exponent, 11))