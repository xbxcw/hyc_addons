import os
import subprocess
import json
import math
import re


def get_sbsar_exposed_params(sbsrender_exe, sbsar_file):
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
    return params


def _parse_text_output(output):
    params = []
    lines = output.split('\n')
    pattern = re.compile(
        r'[-*]\s*'
        r'(?P<name>[\w]+)'
        r'\s*[\(:]\s*'
        r'(?P<type>[\w]+)'
        r'[\):]?\s*'
        r'(?P<default>.*?)$'
    )

    for line in lines:
        line = line.strip()
        match = pattern.search(line)
        if match:
            params.append({
                'name': match.group('name'),
                'type': match.group('type'),
                'default': match.group('default').strip().rstrip(',')
            })

    if not params:
        pattern2 = re.compile(r'^\s*(?P<name>\w+)\s*:\s*(?P<type>\w+)', re.IGNORECASE)
        for line in lines:
            match = pattern2.search(line)
            if match:
                params.append({
                    'name': match.group('name'),
                    'type': match.group('type'),
                    'default': ''
                })

    return params


def get_image_dimensions(image_path):
    from PIL import Image
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        print(f'读取图片尺寸失败: {e}')
        return None


def get_power_exponent(pixel_size):
    if pixel_size <= 0:
        return 8
    exponent = round(math.log2(pixel_size))
    return max(8, min(exponent, 11))