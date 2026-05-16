import bpy
import json
import os
Albedo = 'Albedo'
Normals = 'Normal'
Mask = 'Mask'
ER = []
# 语义名 -> 可能的 key 列表
SEMANTIC_KEYS = {
    Albedo:   ["D", "Albedo","D/DA","WindowBase","BaseAlbedo (A:Height)","DA","ColorOpacity"],
    Normals:  ["Normal",'Normal Map',"WindowNR","BaseNormal","NormalMask","NormalMap"],
    Mask:     ["ORM", "Mix Map","BaseORM"],
}

def get_value_by_semantic(data, semantic_name, semantic_map=None) :
    """
    根据语义名称从字典中获取第一个存在的 key 对应的值。

    参数:
        data: dict, 原始字典
        semantic_name: str, 语义名（如 "Albedo"）
        semantic_map: dict, 语义到 key 列表的映射（可选，默认使用全局 SEMANTIC_KEYS）

    返回:
        对应的值；如果都不存在则返回 None
    """
    if semantic_map is None:
        semantic_map = SEMANTIC_KEYS
    
    possible_keys = semantic_map.get(semantic_name)
    if not possible_keys:          # 没有定义该语义
        return None

    for key in possible_keys:
        if key in data:
            return data[key]
    return None

def connect_pbr_textures_from_json(json_path):
    """根据 JSON 映射文件连接贴图到材质节点。
    
    JSON 结构: {模型名: {材质名: {后缀: 路径}}}
    """
    a = []
    if not os.path.exists(json_path):
        print(f"JSON 文件不存在: {json_path}")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        texture_map = json.load(f)
    
    print(f"加载映射文件: {json_path}")
    
    # 遍历每个模型和其材质

    for material_name, texture_paths in texture_map.items():
        print(f"  处理材质: {material_name}")
        
        # 在 Blender 中查找对应的材质
        material = bpy.data.materials.get(material_name)
        if not material:
            print(f"    警告: 未找到材质 '{material_name}'")
            continue
        
        # 启用节点树编辑
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        # 清理旧节点（仅保留 Principled BSDF 和 Material Output）
        principled_bsdf = None
        material_output = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_bsdf = node
            elif node.type == 'OUTPUT_MATERIAL':
                material_output = node
        
        # 删除其他节点
        for node in nodes[:]:
            if node not in [principled_bsdf, material_output]:
                nodes.remove(node)
        
        if not principled_bsdf or not material_output:
            print(f"    错误: 无法找到 Principled BSDF 或 Material Output 节点")
            continue
        
        # 处理基础色贴图 (D)
        print(texture_paths)

        d_path = get_value_by_semantic(texture_paths,Albedo)
        print(d_path)
        if d_path:
            if os.path.exists(d_path):
                # 检查贴图是否已加载
                img_d = bpy.data.images.get(os.path.basename(d_path))
                if not img_d:
                    img_d = bpy.data.images.load(d_path)
                img_node = nodes.new(type='ShaderNodeTexImage')
                img_node.image = img_d
                img_node.label = 'Diffuse'
                links.new(img_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
                # alpha
                links.new(img_node.outputs['Alpha'], principled_bsdf.inputs['Alpha']) 
                print(f"    已连接 D: {os.path.basename(d_path)} -> Base Color")
            else:
                print(f"    警告: D 贴图文件不存在: {d_path}")
        else:
            ER.append(json_path)
        
        # 处理金属/粗糙度贴图 (M)
        m_path = get_value_by_semantic(texture_paths,Mask)
        if m_path is not None:
            if os.path.exists(m_path):
                # 检查贴图是否已加载
                img_m = bpy.data.images.get(os.path.basename(m_path))
                if not img_m:
                    img_m = bpy.data.images.load(m_path)
                img_node_m = nodes.new(type='ShaderNodeTexImage')
                img_node_m.image = img_m
                img_node_m.image.colorspace_settings.name = 'Non-Color'
                img_node_m.label = 'Metallic/Roughness'
                
                # 分离颜色
                sep_rgb = nodes.new(type='ShaderNodeSeparateColor')
                links.new(img_node_m.outputs['Color'], sep_rgb.inputs['Color'])
                
                # G 通道 -> 粗糙度
                links.new(sep_rgb.outputs['Red'], principled_bsdf.inputs['Roughness'])
                
                # B 通道 -> 金属度
                # links.new(sep_rgb.outputs['Blue'], principled_bsdf.inputs['Metallic'])
                
                print(f"    已连接 M: {os.path.basename(m_path)}")
                print(f"      G -> Roughness")
                print(f"      B -> Metallic")
            else:
                print(f"    警告: M 贴图文件不存在: {m_path}")
        else:
            ER.append(json_path) 

        # 处理法线贴图 (N)
        n_path = get_value_by_semantic(texture_paths,Normals)
        if n_path:
            if os.path.exists(n_path):
                # 检查贴图是否已加载
                img_n = bpy.data.images.get(os.path.basename(n_path))
                if not img_n:
                    img_n = bpy.data.images.load(n_path)
                img_node_n = nodes.new(type='ShaderNodeTexImage')
                img_node_n.image = img_n
                img_node_n.image.colorspace_settings.name = 'Non-Color'
                img_node_n.label = 'Normal'
                
                # 法线贴图节点 (DirectX 格式)
                normal_map = nodes.new(type='ShaderNodeNormalMap')
                normal_map.space = 'TANGENT'
                normal_map.convention = 'DIRECTX'
                links.new(img_node_n.outputs['Color'], normal_map.inputs['Color'])
                
                # 连接到 Normal 输入
                links.new(normal_map.outputs['Normal'], principled_bsdf.inputs['Normal'])
                
                print(f"    已连接 N: {os.path.basename(n_path)} -> Normal (DirectX)")
            else:
                print(f"    警告: N 贴图文件不存在: {n_path}")
        else:
            ER.append(json_path)

    
    print("\n贴图连接完成!")

def find_specified_file(path, suffix=''):
    """
    查找指定文件
    :param path: 根目录
    :param suffix: 格式，默认是空
    :return: 文件地址列表
    """
    _file = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(suffix):
                _file.append(os.path.join(root, file))
    return _file



# if __name__ == "__main__":
#     # 获取脚本同目录下的 material_texture_map.json
#     script_dir = Path(__file__).parent
#     json_file = script_dir / "material_texture_map.json"
    
    # 或者使用指定路径
    # json_file = r"E:\work\LV_FloatingCastle_LA\Tex\material_texture_map.json"
    # Tex = r"E:\work\BP_FloatingCastle_Building_21\Tex"
    # js_dir = find_specified_file(Tex,'.json')

    # for js in js_dir:
    #     connect_pbr_textures_from_json(str(js))
    #     # time.sleep(1)
    #     # break
    # for i in ER:
    #     print(i)

# if not json_file.exists():
#     # 使用指定路径
filepath = bpy.data.filepath
fileName = os.path.basename(filepath)
workDir = os.path.dirname(filepath)
jsonName = fileName.replace('blend','json')

json_file = os.path.join(workDir,'Tex',jsonName)
# print(filepath)
connect_pbr_textures_from_json(str(json_file))
