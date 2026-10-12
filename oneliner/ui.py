"""OneLiner Blender UI — 面板、预览列表、弹窗。"""
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty, IntProperty
from bpy.types import Panel, UIList, Operator, Scene, PropertyGroup, Menu
from . import engine

# 按键映射存储（用于取消注册）
keymap_items = []


# ---------------------------------------------------------------------------
# 场景属性
# ---------------------------------------------------------------------------

class OneLinerPreviewEntry(PropertyGroup):
    """预览列表中每一项的属性。"""
    display_text: StringProperty(name="显示文本")
    raw_text: StringProperty(name="原始文本")
    type_name: StringProperty(name="类型")
    path: StringProperty(name="路径")


class OneLinerChainEntry(PropertyGroup):
    """链式规则中的每一项。"""
    rule: StringProperty(name="规则")


class OneLinerFavoriteEntry(PropertyGroup):
    """收藏列表中每一项的属性。"""
    rule: StringProperty(name="规则")
    scope_mode: StringProperty(name="作用域", default="SELECTED")
    use_forced_mode: BoolProperty(name="强制模式", default=False)


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
    chain_rules = [e.rule for e in scene.oneLiner_chain_rules]

    if chain_rules:
        result = engine.preview_chain(
            chain_rules,
            rule,
            scene.oneLiner_scope_mode,
            scene.oneLiner_use_forced_mode,
        )
    else:
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
# 链式规则操作
# ---------------------------------------------------------------------------

class ONELINER_OT_apply_rule(Operator):
    """将当前规则加入规则链（不重命名）"""
    bl_idname = "oneliner.apply_rule"
    bl_label = "加入规则链"
    bl_description = "将当前规则加入规则链，预览组合效果"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        rule = scene.oneLiner_rule.strip()
        if not rule:
            self.report({'WARNING'}, "OneLiner: 请先输入规则")
            return {'CANCELLED'}

        entry = scene.oneLiner_chain_rules.add()
        entry.rule = rule
        scene.oneLiner_chain_count += 1
        scene.oneLiner_rule = ""

        _on_rule_changed(scene, context)
        return {'FINISHED'}


class ONELINER_OT_remove_chain_rule(Operator):
    """从规则链中移除指定规则"""
    bl_idname = "oneliner.remove_chain_rule"
    bl_label = "移除规则"
    bl_description = "从规则链中移除该规则"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        scene = context.scene
        if 0 <= self.index < len(scene.oneLiner_chain_rules):
            scene.oneLiner_chain_rules.remove(self.index)
            scene.oneLiner_chain_count -= 1
            _on_rule_changed(scene, context)
        return {'FINISHED'}


class ONELINER_OT_clear_chain(Operator):
    """清空规则链"""
    bl_idname = "oneliner.clear_chain"
    bl_label = "清空规则链"
    bl_description = "清空所有已加入的规则，恢复原始预览"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.oneLiner_chain_rules.clear()
        scene.oneLiner_chain_count = 0
        _on_rule_changed(scene, context)
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

        # 应用按钮（加入链）
        op = row.operator("oneliner.apply_rule", text="", icon='FORWARD')
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

        # --- 链式规则 ---
        if scene.oneLiner_chain_count > 0:
            box = layout.box()
            row = box.row()
            row.label(text=f"规则链 ({scene.oneLiner_chain_count} 步)", icon='RENDERLAYERS')
            row.operator("oneliner.clear_chain", text="", icon='TRASH')
            col = box.column(align=True)
            for i, entry in enumerate(scene.oneLiner_chain_rules):
                row = col.row(align=True)
                row.label(text=f"  {i + 1}. {entry.rule}")
                op = row.operator("oneliner.remove_chain_rule", text="", icon='X', emboss=False)
                op.index = i

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
                op = row.operator("oneliner.add_favorite", text="", icon='SOLO_ON', emboss=False)
                op.rule_text = h

        # --- 收藏 ---
        if scene.oneLiner_favorite_count > 0:
            box = layout.box()
            row = box.row()
            row.label(text=f"收藏 ({scene.oneLiner_favorite_count})", icon='SOLO_ON')
            row.operator("oneliner.add_favorite", text="", icon='ADD')
            col = box.column(align=True)
            for i, entry in enumerate(scene.oneLiner_favorites):
                row = col.row(align=True)
                op = row.operator("oneliner.use_favorite", text=entry.rule, emboss=False)
                op.index = i
                op = row.operator("oneliner.remove_favorite", text="", icon='X', emboss=False)
                op.index = i
        else:
            box = layout.box()
            row = box.row()
            row.label(text="收藏", icon='SOLO_OFF')
            row.operator("oneliner.add_favorite", text="", icon='ADD')


# ---------------------------------------------------------------------------
# 收藏操作符
# ---------------------------------------------------------------------------

class ONELINER_OT_add_favorite(Operator):
    """将当前规则添加到收藏"""
    bl_idname = "oneliner.add_favorite"
    bl_label = "添加到收藏"
    bl_description = "将当前输入的规则添加到收藏列表"
    bl_options = {'INTERNAL'}

    rule_text: StringProperty(name="规则文本", default="")

    def execute(self, context):
        scene = context.scene
        rule = self.rule_text.strip() if self.rule_text.strip() else scene.oneLiner_rule.strip()
        if not rule:
            self.report({'WARNING'}, "规则为空，无法收藏")
            return {'CANCELLED'}

        for entry in scene.oneLiner_favorites:
            if entry.rule == rule:
                self.report({'INFO'}, "该规则已在收藏中")
                return {'FINISHED'}

        entry = scene.oneLiner_favorites.add()
        entry.rule = rule
        entry.scope_mode = scene.oneLiner_scope_mode
        entry.use_forced_mode = scene.oneLiner_use_forced_mode
        scene.oneLiner_favorite_count = len(scene.oneLiner_favorites)
        self.report({'INFO'}, f"已收藏规则: {rule}")
        return {'FINISHED'}


class ONELINER_OT_remove_favorite(Operator):
    """从收藏中移除指定规则"""
    bl_idname = "oneliner.remove_favorite"
    bl_label = "移除收藏"
    bl_description = "从收藏列表中移除此规则"
    bl_options = {'INTERNAL'}

    index: IntProperty(name="索引", default=-1)

    def execute(self, context):
        scene = context.scene
        if 0 <= self.index < len(scene.oneLiner_favorites):
            scene.oneLiner_favorites.remove(self.index)
            scene.oneLiner_favorite_count = len(scene.oneLiner_favorites)
            self.report({'INFO'}, "已移除收藏")
        return {'FINISHED'}


class ONELINER_OT_use_favorite(Operator):
    """使用收藏的规则"""
    bl_idname = "oneliner.use_favorite"
    bl_label = "使用收藏"
    bl_description = "将收藏的规则填入输入框"
    bl_options = {'INTERNAL'}

    index: IntProperty(name="索引", default=-1)

    def execute(self, context):
        scene = context.scene
        if 0 <= self.index < len(scene.oneLiner_favorites):
            entry = scene.oneLiner_favorites[self.index]
            scene.oneLiner_rule = entry.rule
            scene.oneLiner_scope_mode = entry.scope_mode
            scene.oneLiner_use_forced_mode = entry.use_forced_mode
            self.report({'INFO'}, f"已载入收藏: {entry.rule}")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# 模块级注册/注销 — 仅处理场景属性
# ---------------------------------------------------------------------------

def register():
    # 场景级属性
    Scene.oneLiner_rule = StringProperty(
        name="规则",
        description="重命名规则",
        default="",
        options={'TEXTEDIT_UPDATE'},
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

    Scene.oneLiner_favorites = CollectionProperty(type=OneLinerFavoriteEntry)
    Scene.oneLiner_favorite_count = IntProperty(name="收藏数量", default=0)

    Scene.oneLiner_chain_rules = CollectionProperty(type=OneLinerChainEntry)
    Scene.oneLiner_chain_count = IntProperty(name="规则链数量", default=0)

    # 按键映射：Enter 键加入规则链
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(
            ONELINER_OT_apply_rule.bl_idname,
            'RET', 'PRESS',
        )
        keymap_items.append((km, kmi))

    # 选中变更监控
    _selection_check_handler()


def _selection_check_handler():
    """定期检查选中状态，变更时清空规则链。"""
    _prev_selection = set()

    def _check():
        try:
            current = set()
            for obj in bpy.context.selected_objects:
                current.add(obj.name)
            if not current and _prev_selection:
                # 点击空白处，清空规则链
                scene = bpy.context.scene
                if scene.oneLiner_chain_count > 0:
                    scene.oneLiner_chain_rules.clear()
                    scene.oneLiner_chain_count = 0
                    scene.oneLiner_rule = ""
                    _on_rule_changed(scene, bpy.context)
            elif current and current != _prev_selection and _prev_selection:
                # 选中变更，清空规则链
                scene = bpy.context.scene
                if scene.oneLiner_chain_count > 0:
                    scene.oneLiner_chain_rules.clear()
                    scene.oneLiner_chain_count = 0
                    _on_rule_changed(scene, bpy.context)
            _prev_selection.clear()
            _prev_selection.update(current)
        except Exception:
            pass
        return 0.3  # 每 0.3 秒检查一次

    if not bpy.app.timers.is_registered(_check):
        bpy.app.timers.register(_check, persistent=True)


def unregister():
    # 清理按键映射
    for km, kmi in keymap_items:
        km.keymap_items.remove(kmi)
    keymap_items.clear()

    del Scene.oneLiner_chain_count
    del Scene.oneLiner_chain_rules
    del Scene.oneLiner_favorite_count
    del Scene.oneLiner_favorites
    del Scene.oneLiner_history_index
    del Scene.oneLiner_preview_count
    del Scene.oneLiner_preview_items
    del Scene.oneLiner_wildcard_include_children
    del Scene.oneLiner_auto_close
    del Scene.oneLiner_preview_enabled
    del Scene.oneLiner_use_forced_mode
    del Scene.oneLiner_scope_mode
    del Scene.oneLiner_rule