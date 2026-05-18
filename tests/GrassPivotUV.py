import bpy

# 全局定义轴心UV集合名
GRASS_PIVOT_UV_NAME = "GrassPivotUV"

# 单位转换：Maya 默认使用厘米(cm)，Blender 默认使用米(m)
# 从 Maya 导入的模型坐标需要乘以 100 才能匹配原始 Maya 坐标
UNIT_SCALE = 100.0  # 1m = 100cm

def get_all_selected_transform_objects():
    """递归获取选中物体及所有子级物体"""
    result_objs = []
    
    def collect_child_obj(obj):
        if obj.type == 'MESH':
            if obj not in result_objs:
                result_objs.append(obj)
        # 递归遍历子物体
        for child in obj.children:
            collect_child_obj(child)
    
    # 遍历所有选中物体
    for sel_obj in bpy.context.selected_objects:
        collect_child_obj(sel_obj)
    return result_objs

def get_obj_world_origin(obj):
    """获取物体原点世界坐标 (X,Y,Z)"""
    return obj.matrix_world.translation

def create_or_switch_uv_layer(mesh):
    """创建GrassPivotUV UV层，不存在则新建"""
    uv_layers = mesh.uv_layers
    # 判断是否存在第二个UV层（索引为1）
    if len(uv_layers) > 1:
        uv_layer = uv_layers[1]
    else:
        # 不存在则创建新的UV层
        uv_layer = uv_layers.new(name=GRASS_PIVOT_UV_NAME)
    # 激活目标UV层
    uv_layers.active = uv_layer
    return uv_layer

def show_message(message):
    """显示消息弹窗"""
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title="提示", icon='INFO')

def bake_pivot_to_uv():
    """主逻辑：将物体原点坐标烘焙进UV"""
    selected_meshes = get_all_selected_transform_objects()
    if not selected_meshes:
        show_message("请至少选中一个模型物体")
        return
    
    for obj in selected_meshes:
        if obj.type != 'MESH':
            continue
        print(f"==== 处理物体: {obj.name} ====")
        
        mesh = obj.data
        # 创建并激活目标UV层
        uv_layer = create_or_switch_uv_layer(mesh)
        if not uv_layer:
            print(f"创建UV层失败: {obj.name}")
            continue
        
        # 获取物体世界原点
        world_pos = get_obj_world_origin(obj)
        # Maya vs Blender 坐标系映射:
        # Maya: X=右, Y=上, Z=前(深度)
        # Blender: X=右, Y=前(深度), Z=上
        # 单位转换：Blender 的米 -> Maya 的厘米（乘以 100）
        u_val = world_pos.x * UNIT_SCALE
        v_val = 1.0 - (-world_pos.y * UNIT_SCALE)  # Maya.Z = -Blender.Y
        
        # 遍历所有顶点UV，统一赋值
        for uv_data in uv_layer.data:
            uv_data.uv = (u_val, v_val)
        
        print(f"赋值完成 U:{u_val:.3f}  V:{v_val:.3f}")
    
    # 弹窗提示完成
    show_message("草叶轴心UV烘焙完成！")
    print("\n>>> 全部烘焙结束")

# 执行运行
bake_pivot_to_uv()