
import bpy


def get_visible_mesh_stats():
    """获取当前可见网格物体的面数统计
    
    Returns:
        dict: 包含 'faces' 和 'tris' 的统计字典
    """
    total_faces = 0
    total_tris = 0

    for obj in bpy.context.visible_objects:
        if obj.type != 'MESH':
            continue
        
        # 获取应用修改器后的最终网格
        eval_obj = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = eval_obj.data
        
        # 面数
        total_faces += len(mesh.polygons)
        
        # 三角面数
        for p in mesh.polygons:
            total_tris += len(p.vertices) - 2

    return {
        'faces': total_faces,
        'tris': total_tris
    }
