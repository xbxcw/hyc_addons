"""
Node Connector - 节点连接核心功能
"""

import traceback


class NodeConnector:
    """节点连接工具"""
    
    NODE_DEFS = {
        "blend": "sbs::compositing::blend",
        "curve": "sbs::compositing::curve",
        "levels": "sbs::compositing::levels",
        "normal": "sbs::compositing::normal",
        "hsl": "sbs::compositing::hsl",
        "uniform": "sbs::compositing::uniform",
        "blur": "sbs::compositing::blur",
        "warp": "sbs::compositing::warp",
        "transform": "sbs::compositing::transformation",
        "distance": "sbs::compositing::distance",
    }
    
    @staticmethod
    def add_node(node_type_name):
        """在选中节点后添加新节点"""
        try:
            import sd
            from sd.api.sdbasetypes import SDPoint2
            
            ctx = sd.getContext()
            app = ctx.getSDApplication()
            ui = app.getQtForPythonUIMgr()
            graph = ui.getCurrentGraph()
            
            if not graph:
                print("[ERROR] 没有活动的图形")
                return False
            
            selected = ui.getCurrentGraphSelectedNodes()
            if not selected or len(selected) == 0:
                print("[ERROR] 请先选择一个节点")
                return False
            
            # 计算平均位置
            avg_x = 0
            avg_y = 0
            for node in selected:
                pos = node.getPosition()
                avg_x += pos.x
                avg_y += pos.y
            avg_x /= len(selected)
            avg_y /= len(selected)
            
            # 查找节点定义ID
            did = NodeConnector.NODE_DEFS.get(node_type_name.lower())
            if not did:
                print(f"[ERROR] 未知类型: {node_type_name}")
                print(f"  可用类型: {list(NodeConnector.NODE_DEFS.keys())}")
                return False
            
            # 创建新节点
            new_node = graph.newNode(did, SDPoint2(avg_x + 300, avg_y))
            nid = new_node.getIdentifier()
            print(f"[OK] 创建节点: {node_type_name} ({nid})")
            
            # 处理连接
            if node_type_name.lower() == "blend":
                NodeConnector._connect_blend(selected, new_node)
            else:
                # 其他节点：只连第一个节点的输出
                source = selected[0]
                sid = source.getIdentifier()
                
                # 连接
                src_out = None
                for p in source.getDefinition().getProperties():
                    if p.getCategory() == 2:  # Output
                        src_out = p
                        break
                
                dest_in = None
                for p in new_node.getDefinition().getProperties():
                    if p.getCategory() == 1:  # Input
                        dest_in = p
                        break
                
                if src_out and dest_in:
                    source.newPropertyConnection(src_out, new_node, dest_in)
                    print(f"[OK] 已连接: {sid} -> {nid}")
            
            return True
        
        except Exception as e:
            print(f"[ERROR] {e}")
            traceback.print_exc()
            return False
    
    @staticmethod
    def _connect_blend(source_nodes, blend_node):
        """智能连接Blend节点：
        选1个 → 连input1
        选2个 → 连input1和input2
        选3个 → 连全部
        选3个以上 → 不连接
        """
        n = len(source_nodes)
        
        if n > 3:
            print(f"[WARNING] 选择了{n}个节点，Blend只支持最多3个输入，不连接")
            return
        
        # 收集Blend的输入属性
        input_props = []
        for p in blend_node.getDefinition().getProperties():
            if p.getCategory() == 1:  # Input
                # 优先找input1, input2, input3
                prop_id = p.getId()
                if "input" in prop_id.lower():
                    input_props.append(p)
        
        if not input_props:
            print("[WARNING] 未找到Blend的输入属性")
            return
        
        # 按input1, input2, input3排序
        def get_input_order(p):
            name = p.getId().lower()
            if "input1" in name:
                return 0
            elif "input2" in name:
                return 1
            elif "input3" in name:
                return 2
            return 3
        
        input_props.sort(key=get_input_order)
        
        # 连接
        for i, source in enumerate(source_nodes):
            if i >= len(input_props):
                break
            
            # 获取源节点输出
            src_out = None
            for p in source.getDefinition().getProperties():
                if p.getCategory() == 2:  # Output
                    src_out = p
                    break
            
            if src_out:
                source.newPropertyConnection(src_out, blend_node, input_props[i])
                print(f"[OK] 连接 {source.getIdentifier()} -> {input_props[i].getId()}")
    
    # 快捷方法
    @staticmethod
    def add_blend(): NodeConnector.add_node("blend")
    @staticmethod
    def add_curve(): NodeConnector.add_node("curve")
    @staticmethod
    def add_levels(): NodeConnector.add_node("levels")
    @staticmethod
    def add_normal(): NodeConnector.add_node("normal")
    @staticmethod
    def add_hsl(): NodeConnector.add_node("hsl")
    @staticmethod
    def add_uniform(): NodeConnector.add_node("uniform")
    @staticmethod
    def add_blur(): NodeConnector.add_node("blur")
    @staticmethod
    def add_warp(): NodeConnector.add_node("warp")
    @staticmethod
    def add_transform(): NodeConnector.add_node("transform")
    @staticmethod
    def add_distance(): NodeConnector.add_node("distance")
