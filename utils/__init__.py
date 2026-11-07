import os
import bpy


def has_project() -> bool:
    """判断当前文件是否处于 Blender 项目（5.3+）中"""
    return getattr(bpy.data, "project", None) is not None


def get_workspace_dir(context=None) -> str:
    """获取工作目录

    优先级：
    1. Blender 项目根目录（bpy.data.project.root_path）
    2. 场景属性 workspaceDir
    3. 当前 blend 文件所在目录
    """
    project = getattr(bpy.data, "project", None)
    if project is not None:
        root_path = getattr(project, "root_path", "")
        if root_path:
            return os.path.normpath(root_path)

    context = context or bpy.context
    scene = getattr(context, "scene", None)
    props = getattr(scene, "hyc_props", None)
    if props is not None and props.workspaceDir:
        return os.path.normpath(props.workspaceDir)

    if bpy.data.filepath:
        return os.path.normpath(os.path.dirname(bpy.data.filepath))

    return ""