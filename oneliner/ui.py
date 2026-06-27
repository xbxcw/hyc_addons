"""OneLiner Blender UI — 面板、预览列表、弹窗。"""
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty, IntProperty
from bpy.types import Panel, UIList, Operator, Scene, PropertyGroup, Menu
from . import engine


# ---------------------------------------------------------------------------
# 场景属性
# ---------------------------------------------------------------------------

class OneLinerPreviewEntry(PropertyGroup):
    """预览列表中每一项的属性。"""
    display_text: StringProperty(name="显示文本")
    raw_text: StringProperty(name="原始文本")
    type_name: StringProperty(name="类型")
    path: StringProperty(name="路径")


# ---------------------------------------------------------------------------
# 预览更新
# ---------------------------------------------------------------------------

def _on_rule_changed(scene, context):
    """规则变更时更新预览。"""
    if not scene.oneLiner_preview_enabled:
        scene.oneLiner_preview_items.clear()
        scene.oneLiner_preview_count = 0
        return

    rule = scene.oneLiner_rule
    result = engine.preview(
        rule,
        scene.oneLiner_scope_mode,
        scene.oneLiner_use_forced_mode,
    )

    scene.oneLiner_preview_items.clear()
    for item in result.preview_items:
        entry = scene.oneLiner_preview_items.add()
        entry.display_text = item.display_text
        entry.raw_text = item.raw_text
        entry.type_name = item.type_name
        entry.path = item.path
    scene.oneLiner_preview_count = len(result.preview_items)


class ONELINER_OT_update_preview(Operator):
    """手动刷新预览（双击预览项时触发）"""
    bl_idname = "oneliner.update_preview"
    bl_label = ""
    bl_options = {'INTERNAL'}

    def execute(self, context):
        _on_rule_changed(context.scene, context)
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# 预览列表
# ---------------------------------------------------------------------------

class ONELINER_UL_preview(UIList):
    """预览列表 UI。"""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # 显示层级缩进
            row = layout.row(align=True)
            # 计算缩进
            depth = item.display_text.count('  ') if item.display_text.startswith('  ') else 0
            indent = depth * 0.6
            # 类型图标
            icon_name = self._type_icon(item.type_name)
            # 显示文本（去掉缩进空格）
            clean_text = item.display_text.lstrip()
            row.label(text=clean_text, icon=icon_name)

            # 双击填充原始文本
            op = row.operator("oneliner.execute", text="", icon='PLAY')
            op.rule = item.raw_text

    def _type_icon(self, type_name: str) -> str:
        icon_map = {
            'MESH': 'OUTLINER_OB_MESH',
            'CURVE': 'OUTLINER_OB_CURVE',
            'SURFACE': 'OUTLINER_OB_SURFACE',
            'META': 'OUTLINER_OB_META',
            'FONT': 'OUTLINER_OB_FONT',
            'ARMATURE': 'OUTLINER_OB_ARMATURE',
            'LATTICE': 'OUTLINER_OB_LATTICE',
            'EMPTY': 'OUTLINER_OB_EMPTY',
            'GPENCIL': 'OUTLINER_OB_GREASEPENCIL',
            'CAMERA': 'OUTLINER_OB_CAMERA',
            'LIGHT': 'OUTLINER_OB_LIGHT',
            'SPEAKER': 'OUTLINER_OB_SPEAKER',
            'LIGHT_PROBE': 'OUTLINER_OB_LIGHTPROBE',
            'VOLUME': 'OUTLINER_OB_VOLUME',
            'POINTCLOUD': 'OUTLINER_OB_POINTCLOUD',
        }
        return icon_map.get(type_name, 'OUTLINER_OB_EMPTY')


# ---------------------------------------------------------------------------
# 工具菜单
# ---------------------------------------------------------------------------

class ONELINER_MT_tools(Menu):
    """右键工具菜单。"""
    bl_idname = "ONELINER_MT_tools"
    bl_label = "OneLiner 工具"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "oneLiner_preview_enabled", text="启用预览")
        layout.prop(scene, "oneLiner_auto_close", text="自动关闭")
        layout.prop(scene, "oneLiner_wildcard_include_children",
                    text="通配符包含子级对象")

        layout.separator()

        op = layout.operator("oneliner.clear_pasted", text="清除 pasted__ 前缀",
                             icon='TRASH')

        layout.separator()

        op = layout.operator("oneliner.show_help", text="帮助", icon='HELP')


# ---------------------------------------------------------------------------
# 主面板
# ---------------------------------------------------------------------------

class ONELINER_PT_main(Panel):
    """OneLiner 主面板 — 3D View 侧边栏。"""
    bl_idname = "ONELINER_PT_main"
    bl_label = "OneLiner"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "OneLiner"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # --- 输入行 ---
        row = layout.row(align=True)
        row.prop(scene, "oneLiner_rule", text="")

        # 执行按钮
        op = row.operator("oneliner.execute", text="", icon='CHECKMARK')
        op.rule = scene.oneLiner_rule
        op.scope_mode = scene.oneLiner_scope_mode
        op.use_forced_mode = scene.oneLiner_use_forced_mode

        # 工具菜单按钮
        row.menu("ONELINER_MT_tools", text="", icon='DOWNARROW_HLT')

        # --- 设置行 ---
        row = layout.row(align=True)
        row.prop(scene, "oneLiner_scope_mode", text="")
        row.prop(scene, "oneLiner_preview_enabled", text="", icon='HIDE_OFF' if scene.oneLiner_preview_enabled else 'HIDE_ON')

        # --- 预览列表 ---
        if scene.oneLiner_preview_enabled and scene.oneLiner_preview_count > 0:
            box = layout.box()
            # 标题
            row = box.row()
            row.label(text=f"预览 ({scene.oneLiner_preview_count} 项)", icon='OUTLINER')
            # 列表
            row = box.row()
            row.template_list(
                "ONELINER_UL_preview",
                "",
                scene,
                "oneLiner_preview_items",
                scene,
                "oneLiner_preview_count",
                rows=min(10, scene.oneLiner_preview_count),
            )
        elif scene.oneLiner_preview_enabled:
            box = layout.box()
            box.label(text="请选择对象并输入规则", icon='INFO')

        # --- 历史记录 ---
        history = engine.get_history()
        if history:
            box = layout.box()
            box.label(text=f"历史记录 ({len(history)})", icon='TIME')
            col = box.column(align=True)
            # 显示最近 10 条
            for h in reversed(history[-10:]):
                row = col.row(align=True)
                op = row.operator("oneliner.execute", text=h, emboss=False)
                op.rule = h
                op.scope_mode = scene.oneLiner_scope_mode
                op.use_forced_mode = scene.oneLiner_use_forced_mode


# ---------------------------------------------------------------------------
# 模块级注册/注销 — 仅处理场景属性
# ---------------------------------------------------------------------------

def register():
    # 场景级属性
    Scene.oneLiner_rule = StringProperty(
        name="规则",
        description="重命名规则",
        default="",
        update=lambda self, ctx: _on_rule_changed(self, ctx),
    )
    Scene.oneLiner_scope_mode = EnumProperty(
        name="作用域",
        items=[
            ('SELECTED', "选中", "当前选中对象"),
            ('HIERARCHY', "层级", "选中对象及其子级"),
            ('ALL', "全部", "场景中所有对象"),
        ],
        default='SELECTED',
        update=lambda self, ctx: _on_rule_changed(self, ctx),
    )
    Scene.oneLiner_use_forced_mode = BoolProperty(
        name="强制模式",
        default=False,
        update=lambda self, ctx: _on_rule_changed(self, ctx),
    )
    Scene.oneLiner_preview_enabled = BoolProperty(
        name="启用预览",
        default=True,
        update=lambda self, ctx: _on_rule_changed(self, ctx),
    )
    Scene.oneLiner_auto_close = BoolProperty(
        name="自动关闭",
        default=True,
    )
    Scene.oneLiner_wildcard_include_children = BoolProperty(
        name="包含子级对象",
        default=False,
        description="通配符检索时包含所有子级对象",
        update=lambda self, ctx: _on_rule_changed(self, ctx),
    )

    Scene.oneLiner_preview_items = CollectionProperty(type=OneLinerPreviewEntry)
    Scene.oneLiner_preview_count = IntProperty(name="预览数量", default=0)
    Scene.oneLiner_history_index = IntProperty(name="历史索引", default=-1)


def unregister():
    del Scene.oneLiner_history_index
    del Scene.oneLiner_preview_count
    del Scene.oneLiner_preview_items
    del Scene.oneLiner_wildcard_include_children
    del Scene.oneLiner_auto_close
    del Scene.oneLiner_preview_enabled
    del Scene.oneLiner_use_forced_mode
    del Scene.oneLiner_scope_mode
    del Scene.oneLiner_rule