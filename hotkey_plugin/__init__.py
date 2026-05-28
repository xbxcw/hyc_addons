"""
Hotkey Plugin - 快速节点连接
"""

import sd
from sd.api.sdbasetypes import SDPoint2
import traceback


def add_blend():
    """添加Blend节点并连接"""
    print("=" * 60)
    print("开始添加Blend节点...")
    
    try:
        ctx = sd.getContext()
        app = ctx.getSDApplication()
        ui = app.getQtForPythonUIMgr()
        graph = ui.getCurrentGraph()
        
        if not graph:
            print("没有活动的图形")
            return
        
        selected = ui.getCurrentGraphSelectedNodes()
        if not selected or len(selected) == 0:
            print("请先选择节点")
            return
        
        print(f"选择了 {len(selected)} 个节点")
        
        # 计算平均位置
        avg_x = 0
        avg_y = 0
        for node in selected:
            pos = node.getPosition()
            avg_x += pos.x
            avg_y += pos.y
        avg_x /= len(selected)
        avg_y /= len(selected)
        
        # 创建新的Blend节点
        new_node = graph.newNode(
            "sbs::compositing::blend", 
            SDPoint2(avg_x + 300, avg_y)
        )
        nid = new_node.getIdentifier()
        print(f"创建Blend节点: {nid}")
        
        # 处理连接
        if len(selected) <= 3:
            # 获取Blend节点的输入属性
            input_props = []
            for prop in new_node.getDefinition().getProperties():
                if prop.getCategory() == 1:  # Input
                    input_props.append(prop)
            
            # 排序，优先input1, input2, input3
            def get_input_order(prop):
                name = prop.getId().lower()
                if "input1" in name:
                    return 0
                elif "input2" in name:
                    return 1
                elif "input3" in name:
                    return 2
                return 3
            input_props.sort(key=get_input_order)
            
            # 连接
            for i, source in enumerate(selected):
                if i >= len(input_props):
                    break
                
                # 获取源节点的输出
                src_out = None
                for prop in source.getDefinition().getProperties():
                    if prop.getCategory() == 2:  # Output
                        src_out = prop
                        break
                
                if src_out:
                    source.newPropertyConnection(src_out, new_node, input_props[i])
                    print(f"已连接: {source.getIdentifier()} -> {input_props[i].getId()}")
        
    except Exception as e:
        print(f"错误: {e}")
        traceback.print_exc()


# ============================================================
# SD 插件入口
# ============================================================

def initializeSDPlugin():
    print("=" * 60)
    print("Hotkey Plugin 已加载")
    print("可用函数: add_blend()")


def uninitializeSDPlugin():
    pass
