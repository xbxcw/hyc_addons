import subprocess


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
