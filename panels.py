import bpy
from . import operators

# class BasePanel(object):
#     bl_space_type = "VIEW_3D"
#     bl_region_type = "UI"
#     bl_category = "ExampleAddon"

#     @classmethod
#     def poll(cls, context: bpy.types.Context):
#         return True

class HYC_PT_panel(bpy.types.Panel):
    bl_idname = 'HYC_PT_panel'
    bl_label = "简单面板"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "我的工具"

    def draw(self,context):
        layout = self.layout
        scene = context.scene
        hyc_props = scene.hyc_props
        
        # 横向排列的通道设置行
        row = layout.row()
        row.label(text='Mask:')
        row.prop(hyc_props, "metal_channel", text="M")
        row.prop(hyc_props, "rough_channel", text="R")
        row.prop(hyc_props, "occlusion_channel", text="O")
        row.prop(hyc_props, "directX", text="DirectX")
        
        row = layout.row()
        # row.label(text='LOD Name:')
        row.prop(hyc_props, "workspaceDir", text="Workspace")
        # layout.separator()
        row.operator(operators.HYC_Create_LOD.bl_idname)
        layout.separator()
        layout.label(text='fengdong')
        row =layout.row()
        row.operator(operators.HYC_OT_BakeGrassPivotUV.bl_idname)
# @reg_order(0)
# class ExampleAddonPanel(BasePanel, bpy.types.Panel):
#     bl_label = "Example Addon Side Bar Panel"
#     bl_idname = "SCENE_PT_sample"

#     def draw(self, context: bpy.types.Context):
#         addon_prefs = context.preferences.addons['hyc'].preferences

#         layout = self.layout

#         layout.label(text=i18n("Example Functions") + ": " + str(addon_prefs.number))
#         layout.prop(addon_prefs, "filepath")
#         layout.separator()

#         row = layout.row()
#         row.prop(addon_prefs, "number")
#         row.prop(addon_prefs, "boolean")

#         layout.operator(ExampleOperator.bl_idname)

#     @classmethod
#     def poll(cls, context: bpy.types.Context):
#         return True


# # This panel will be drawn after ExampleAddonPanel since it has a higher order value
# @reg_order(1)
# class ExampleAddonPanel2(BasePanel, bpy.types.Panel):
#     bl_label = "Example Addon Side Bar Panel"
#     bl_idname = "SCENE_PT_sample2"

#     def draw(self, context: bpy.types.Context):
#         layout = self.layout
#         layout.label(text="Second Panel")
#         layout.operator(ExampleOperator.bl_idname)