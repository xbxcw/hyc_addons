import os
import json
import sys
import unreal

def r(path):
    """就像Python的r字符串一样，返回原始路径"""
    return path.replace('\\', '/')  # 就这么简单！
def parse_arguments():
    """从 sys.argv 中解析命令行参数"""
    # 示例输入: ['脚本路径', '--folder_path', 'D:\Some\Path']
    args = {}
    # 从索引1开始，跳过脚本自身路径
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        # 检查是否是参数标识符（以 '--' 或 '-' 开头）
        if arg.startswith('--') or arg.startswith('-'):
            # 获取参数名（去掉开头的 '--' 或 '-'）
            key = arg.lstrip('-')
            # 确保后面还有一个值
            if i + 1 < len(sys.argv):
                args[key] = sys.argv[i + 1]
                i += 1 # 跳过值
        i += 1
    return args

params = parse_arguments()
target_path = params.get('p')

target_path = r(target_path)


# ====================== 配置项 ======================
export_folder = target_path  # 导出目录
# 贴图名称后缀筛选规则
texture_suffixes = ('_D', '_DA', '_M', '_MR', '_N', '_NR', '_H', '_B','_m')
# ====================================================

# 获取内容浏览器选中的静态网格体
selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
static_meshes = unreal.EditorFilterLibrary.by_class(selected_assets, unreal.StaticMesh)



def get_texture_suffix_key(texture_name):
    """匹配贴图后缀（保留你的筛选逻辑）"""
    for suffix in texture_suffixes:
        if texture_name.endswith(suffix):
            return suffix
    return None

def export_texture_to_tga(texture, output_dir):
    """导出贴图为TGA"""
    os.makedirs(output_dir, exist_ok=True)
    texture_name = texture.get_name()
    filename = os.path.join(output_dir, f"{texture_name}.tga")

    task = unreal.AssetExportTask()
    task.object = texture
    task.filename = filename
    task.automated = True
    task.prompt = False
    task.replace_identical = True

    try:
        if hasattr(unreal.Exporter, 'run_asset_export_task'):
            unreal.Exporter.run_asset_export_task(task)
        else:
            unreal.Exporter.run_asset_export_tasks([task])
        return filename
    except Exception as e:
        print(f"导出失败: {texture_name}，错误: {e}")
        return None

def get_static_mesh_materials(mesh):
    """获取模型的所有材质槽+材质"""
    materials = []
    try:
        static_materials = mesh.get_editor_property('static_materials')
        for idx, sm in enumerate(static_materials):
            mat = sm.get_editor_property('material_interface')
            if mat:
                materials.append((idx, mat))
    except:
        idx = 0
        while True:
            try:
                mat = mesh.get_material(idx)
                if mat:
                    materials.append((idx, mat))
                else:
                    break
                idx +=1
            except:
                break
    return materials

# 全局存储已导出的贴图，避免重复导出
exported_textures = {}

if not static_meshes:
    print("请在内容浏览器中选择静态网格体！")
else:
    # 遍历每个模型，单独生成JSON
    for mesh in static_meshes:
        mesh_name = mesh.get_name()
        print(f"\n========================================")
        print(f"开始处理模型：{mesh_name}")
        
        # 每个模型独立的JSON数据结构：材质名 → 参数名:路径
        current_model_data = {}
        materials = get_static_mesh_materials(mesh)

        for idx, material in materials:
            mat_name = material.get_name()
            
            # 只处理材质实例
            if not isinstance(material, (unreal.MaterialInstanceConstant, unreal.MaterialInstance)):
                continue

            try:
                texture_params = material.get_editor_property("texture_parameter_values")
            except:
                texture_params = []

            for param in texture_params:
                try:
                    # 修复参数名类型，转为字符串
                    param_info = param.get_editor_property("parameter_info")
                    param_name = str(param_info.get_editor_property("name"))
                    
                    # 获取贴图
                    texture = param.get_editor_property("parameter_value")
                    if not texture or not isinstance(texture, unreal.Texture):
                        continue

                    # 后缀筛选
                    if not get_texture_suffix_key(texture.get_name()):
                        continue

                    # 导出贴图（去重）
                    tex_path = texture.get_path_name()
                    if tex_path not in exported_textures:
                        local_path = export_texture_to_tga(texture, export_folder)
                        exported_textures[tex_path] = local_path
                    else:
                        local_path = exported_textures[tex_path]

                    if not local_path:
                        continue

                    # 填充当前模型的JSON数据
                    if mat_name not in current_model_data:
                        current_model_data[mat_name] = {}
                    current_model_data[mat_name][param_name] = local_path
                    print(f"├─ 材质：{mat_name} | 参数：{param_name}")

                except Exception as e:
                    continue

        # 为当前模型生成独立JSON文件（文件名=模型名.json）
        if current_model_data:
            json_filename = f"{mesh_name}.json"
            json_file_path = os.path.join(export_folder, json_filename)
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(current_model_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 模型 {mesh_name} JSON 已保存：{json_filename}")
        else:
            print(f"⚠️ 模型 {mesh_name} 未找到符合条件的贴图参数")

    print("\n========================================")
    print("所有模型处理完成！")