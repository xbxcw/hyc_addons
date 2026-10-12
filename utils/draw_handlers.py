import bpy
import blf

from .mesh_stats import get_visible_mesh_stats

# 全局变量存储 draw handler
g_draw_handler = None


def draw_face_count():
    """绘制面数统计信息"""
    stats = get_visible_mesh_stats()
    
    font_id = 0
    blf.size(font_id, 20)
    blf.color(font_id, 1.0, 1.0, 1.0, 1.0)  # 白色
    
    blf.position(font_id, 10, 50, 0)
    blf.draw(font_id, f"面数: {stats['faces']:,}")
    
    blf.position(font_id, 10, 25, 0)
    blf.draw(font_id, f"三角面: {stats['tris']:,}")


class HYC_DrawHelloWorld:
    """在3D视图绘制 hello world 的类"""
    
    def __init__(self):
        global g_draw_handler
        self.draw_handler = g_draw_handler
    
    def register(self):
        """注册 draw handler"""
        global g_draw_handler
        if g_draw_handler is None:
            g_draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_face_count,
                tuple(),
                'WINDOW',
                'POST_PIXEL'
            )
            self.draw_handler = g_draw_handler
            print(f"Draw handler registered: {g_draw_handler}")
            # 强制刷新所有3D视图
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

    def unregister(self):
        """注销 draw handler"""
        global g_draw_handler
        if g_draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(g_draw_handler, 'WINDOW')
            g_draw_handler = None
            self.draw_handler = None
            print("Draw handler unregistered")
            # 强制刷新所有3D视图
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()