import json
import os

# JSON_FILE_PATH = r"D:\temp\Tex\Suzanne.json"


import mset 
selected_file_path = "json path"
Albedo = 'Albedo'
Normals = 'Normal'
Mask = 'Mask'
SEMANTIC_KEYS = {
    Albedo:   ["D", "Albedo","D/DA","WindowBase","BaseAlbedo (A:Height)","DA"],
    Normals:  ["Normal",'Normal Map',"WindowNR","BaseNormal"],
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
            return key
    return None

def load_texture_map(path):
    if not os.path.exists(path):
        print(f"JSON file not found: {path}")
        return None

    with open(path, 'r', encoding='utf-8') as f:
        print('*'*50)
        print(os.path.basename(path))
        return json.load(f)


def find_material(material_name):

    if hasattr(mset, 'findMaterial'):
        try:
            mat = mset.findMaterial(material_name)
            if mat is not None:
                return mat
        except Exception:
            pass

    if hasattr(mset, 'getAllMaterials'):
        try:
            for mat in mset.getAllMaterials():
                if getattr(mat, 'name', '') == material_name:
                    return mat
        except Exception:
            pass

    return None


def connect_texture_to_subroutine(material, sub_name, texture_path, channel=None, flip_y=False, log_name=None):
    """
    将纹理连接到材质的指定子程序（subroutine）。

    参数:
    - material: Material 对象，材质实例
    - sub_name: str，子程序名称，如 'albedo', 'surface', 'microsurface', 'reflectivity', 'occlusion'
    - texture_path: str，纹理文件路径
    - channel: int，可选，纹理通道，0=R, 1=G, 2=B, 3=A，用于packed纹理
    - flip_y: bool，可选，是否翻转Y轴（用于法线贴图）
    - log_name: str，可选，日志显示名称，如 '_D -> albedo'

    返回:
    - bool: 是否成功连接纹理
    """
    if material is None:
        return False

    try:
        sub = material.getSubroutine(sub_name)
    except Exception:
        print(f"    Subroutine not found: '{sub_name}'")
        return False

    if not os.path.exists(texture_path):
        print(f"    Texture file not found: {texture_path}")
        return False

    # 根据sub_name设置纹理字段
    field_map = {
        'albedo': 'Albedo Map',
        'surface': 'Normal Map',
        'microsurface': 'Roughness Map',
        'reflectivity': 'Metalness Map',
        'occlusion': 'Occlusion Map'
    }

    if sub_name in field_map:
        try:
            sub.setField(field_map[sub_name], texture_path)
            if log_name:
                print(f"    Connected {log_name}")
            else:
                print(f"    Connected texture to {sub_name}")
            
            # 对于albedo，设置texture的sRGB
            if sub_name == 'albedo':
                try:
                    tex = sub.getField(field_map[sub_name])
                    if tex and hasattr(tex, 'sRGB'):
                        tex.sRGB = True
                        print(f"    Set texture sRGB to True")
                    else:
                        print(f"    Texture object not found or no sRGB attribute")
                except Exception as e:
                    print(f"    Failed to set texture sRGB: {e}")
        except Exception as e:
            print(f"    Failed to set {field_map[sub_name]}: {e}")
            return False
    else:
        print(f"    Unknown sub_name: {sub_name}")
        return False

    if sub_name == 'albedo':
        print(f"    Available fields for albedo: {sub.getFieldNames()}")

    # 对于roughness和metalness，设置值为1
    if sub_name == 'microsurface':
        try:
            sub.setField("Roughness", 1.0)
            print(f"    Set Roughness to 1.0")
        except Exception as e:
            print(f"    Failed to set Roughness: {e}")
    elif sub_name == 'reflectivity':
        try:
            sub.setField("Metalness", 1.0)
            print(f"    Set Metalness to 1.0")
        except Exception as e:
            print(f"    Failed to set Metalness: {e}")

    # 设置通道（只对packed textures）
    if channel is not None and sub_name in ['microsurface', 'reflectivity']:
        try:
            sub.setField("Channel", channel)
            print(f"    Set channel to {channel}")
        except Exception as e:
            print(f"    Failed to set channel: {e}")

    # 设置Flip Y
    if flip_y:
        try:
            sub.setField("Flip Y", True)
            print(f"    Enabled Flip Y")
        except Exception as e:
            print(f"    Failed to set Flip Y: {e}")

    return True


def connect_material_from_json(material_name, texture_paths):
    material = find_material(material_name)
    if material is None:
        print(f"  Warning: material not found: '{material_name}'")
        return

    print(f"  Processing material: {material_name}")
    # print(f"    Texture paths: {texture_paths}")

    # 设置subroutine类型（shader）
    a = get_value_by_semantic(texture_paths,Albedo)
    print('=='*50)
    n = get_value_by_semantic(texture_paths,Normals)
    
    m = get_value_by_semantic(texture_paths,Mask)

    try:
        if a in texture_paths:
            material.setSubroutine("albedo", "Albedo")
            print("    Set albedo to Albedo")
        if n in texture_paths:
            material.setSubroutine("surface", "Normals")
            print("    Set surface to Normals")
        if m in texture_paths:
            material.setSubroutine("microsurface", "Roughness")
            material.setSubroutine("reflectivity", "Metalness")
            material.setSubroutine("occlusion", "Occlusion")
            print("    Set microsurface, reflectivity, occlusion")
    except Exception as e:
        print(f"  Warning: failed to set subroutine for {material_name}: {e}")

    if a in texture_paths:
        connect_texture_to_subroutine(material, 'albedo', texture_paths[a], log_name='BaseColor -> albedo')

    if n in texture_paths:
        connect_texture_to_subroutine(material, 'surface', texture_paths[n], flip_y=True, log_name='N -> surface normal')

    if m in texture_paths:
        m_path = texture_paths[m]
        # G channel for Roughness (1 = G)
        connect_texture_to_subroutine(material, 'microsurface', m_path, channel=1, log_name='M(G) -> microsurface.Roughness')
        # B channel for Metalness (2 = B)
        connect_texture_to_subroutine(material, 'reflectivity', m_path, channel=2, log_name='M(B) -> reflectivity.Metalness')
        # R channel for Occlusion (0 = R)
        connect_texture_to_subroutine(material, 'occlusion', m_path, channel=0, log_name='M(R) -> occlusion.Occlusion')


def connect_materials_from_json(json_path=None):
    if json_path is None:
        json_path = JSON_FILE_PATH
    
    texture_map = load_texture_map(json_path)
    if texture_map is None:
        return

    print(f"Loading JSON: {json_path}")

    for material,texture_paths in texture_map.items():
        # print(material)
        connect_material_from_json(material, texture_paths)

    print("\nTexture connection completed")
# def choose_file():

#     path = mset.showOpenFileDialog()


#     if path:
#         print('true')
#         selected_file_path = path
#         print(selected_file_path)

def create_toolbar_window():

    window = mset.UIWindow("File Selector")

    label = mset.UILabel("No file selected")
    window.addElement(label)
    window.addReturn()
    def choose_file():

        path = mset.showOpenFileDialog()
        if path:
            label.text = path

    button01 = mset.UIButton("Select File")
    button01.onClick = choose_file
    button02 = mset.UIButton('Enter')
    button02.onClick = lambda:connect_materials_from_json(label.text)

    window.addElement(button01)
    window.addStretchSpace()
    window.addElement(button02)

    window.visible = True

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

if __name__ == '__main__':

    # create_toolbar_window()
    json_path = r"E:\work\BP_FloatingCastle_Building_21\Tex"
    json_file = find_specified_file(json_path,'.json')
    for i in json_file:
        connect_materials_from_json(i)
        # break
    
