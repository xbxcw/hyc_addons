"""OneLiner Blender Operators。"""
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
from . import engine


class ONELINER_OT_execute(bpy.types.Operator):
    """执行重命名规则"""
    bl_idname = "oneliner.execute"
    bl_label = "OneLiner 执行"
    bl_options = {'REGISTER', 'UNDO'}

    rule: StringProperty(
        name="规则",
        description="重命名规则（支持 # @ ! old>new +N -N --N -h -s -type * ?）",
        default="",
    )

    scope_mode: EnumProperty(
        name="作用域",
        items=[
            ('SELECTED', "选中", "当前选中对象"),
            ('HIERARCHY', "层级", "选中对象及其子级"),
            ('ALL', "全部", "场景中所有对象"),
        ],
        default='SELECTED',
    )

    use_forced_mode: BoolProperty(
        name="强制模式",
        default=False,
    )

    def execute(self, context):
        engine.add_history(self.rule)
        success = engine.execute(
            self.rule,
            self.scope_mode,
            self.use_forced_mode,
        )
        if success:
            self.report({'INFO'}, f"OneLiner: 已执行规则 \"{self.rule}\"")
        else:
            self.report({'ERROR'}, "OneLiner: 执行失败")
        return {'FINISHED'} if success else {'CANCELLED'}

    def invoke(self, context, event):
        scene = context.scene
        self.rule = scene.oneLiner_rule
        self.scope_mode = scene.oneLiner_scope_mode
        self.use_forced_mode = scene.oneLiner_use_forced_mode
        return self.execute(context)


class ONELINER_OT_clear_pasted(bpy.types.Operator):
    """清除 pasted__ 前缀"""
    bl_idname = "oneliner.clear_pasted"
    bl_label = "清除 pasted__ 前缀"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if engine.clear_pasted_prefix():
            self.report({'INFO'}, "OneLiner: 已清除 pasted__ 前缀")
        else:
            self.report({'ERROR'}, "OneLiner: 清除失败")
        return {'FINISHED'}


class ONELINER_OT_show_help(bpy.types.Operator):
    """显示帮助"""
    bl_idname = "oneliner.show_help"
    bl_label = "OneLiner 帮助"
    bl_description = "显示 OneLiner 规则帮助"

    def execute(self, context):
        # 在 info 区域打印帮助信息
        help_text = """
OneLiner 规则帮助
=================

基础流程:
  1. 选中对象
  2. 输入规则
  3. 下方预览实时刷新
  4. 回车执行

序列符号:
  !  - 复用旧名称，例如 side_!
  #  - 数字编号，## 控制补零位数，例如 ctrl_## → 01, 02
       /N 指定起始：ctrl_##/3 → 03, 04
  @  - 字母编号，单 @ 可扩展进位 (A..Z,AA..ZZ)
       多 @ 固定宽度：@@ → AA, AB, ..., AZ, BA
       /Aa 控制起始与大小写：@@/Aa → Aa, Ab, ...

替换规则:
  old>new     - 单组替换
  A B>C D     - 多组顺序替换
  L_>R_       - 常用左右替换

裁剪规则:
  +N   - 从开头删除 N 个字符
  -N   - 从结尾删除 N 个字符
  --N  - 只保留前 N 个字符

层级与类型过滤:
  -h             - 包含选中对象及所有子级
  -h -s          - 层级模式包含所有子级对象
  -type MESH LIGHT  - 按 Blender 对象类型过滤

通配符选择:
  * ?  - 通配符匹配对象，回车直接选中
  例如：ctrl_*  L_arm_??

全角符号兼容:
  中文输入法下的！？＃＠＊＞／，　会自动转换为半角符号

右键菜单:
  启用预览 - 开关实时预览
  自动关闭 - 窗口失焦时自动关闭（仅弹窗模式）
  清除 pasted__ 前缀 - 移除所有对象的 pasted__ 前缀
        """
        self.report({'INFO'}, help_text)
        return {'FINISHED'}