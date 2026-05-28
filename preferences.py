import bpy
from bpy.props import StringProperty


class HYC_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    
    workspaceDir: StringProperty(
        name="工作目录",
        default="",
        subtype="DIR_PATH",
        description="选择工作目录，该设置会持久化保存",
    )# type: ignore
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "workspaceDir")


def get_preferences():
    """获取插件偏好设置"""
    return bpy.context.preferences.addons[__package__].preferences
