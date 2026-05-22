import os
import json
import sys
import unreal


def r(path):
    """就像Python的r字符串一样，返回原始路径"""
    return path.replace("\\", "/")  # 就这么简单！


def parse_arguments():
    """从 sys.argv 中解析命令行参数"""
    args = {}
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--") or arg.startswith("-"):
            key = arg.lstrip("-")
            if i + 1 < len(sys.argv):
                args[key] = sys.argv[i + 1]
                i += 1
        i += 1
    return args


# params = parse_arguments()
# target_path = params.get('p')
# target_path = r(target_path)

# 全局存储已导出的贴图，避免重复导出
exported_textures = {}

# ====================== 配置项 ======================
export_folder = r"E:\work\SM_Plant"  # 导出目录
fbxDir = os.path.join(export_folder, "original")
texDir = os.path.join(export_folder, "Tex")
# 贴图名称后缀筛选规则
texture_suffixes = ("_D", "_DA", "_M", "_MR", "_N", "_NR", "_H", "_B", "_m")
# ====================================================


def get_texture_suffix_key(texture_name):
    """匹配贴图后缀（保留你的筛选逻辑）"""
    for suffix in texture_suffixes:
        if texture_name.endswith(suffix):
            return suffix
    return None


def export_texture_to_tga(texture, output_dir):
    """先尝试导出TGA，如果失败则导出EXR（通过检查文件是否存在来确认成功）"""
    os.makedirs(output_dir, exist_ok=True)
    texture_name = texture.get_name()
    
    # 先尝试导出TGA
    tga_filename = os.path.join(output_dir, f"{texture_name}.tga")
    
    # 删除可能存在的旧文件（确保可以检测新文件是否被创建）
    if os.path.exists(tga_filename):
        os.remove(tga_filename)
    
    task = unreal.AssetExportTask()
    task.object = texture
    task.filename = tga_filename
    task.automated = True
    task.prompt = False
    task.replace_identical = True

    try:
        if hasattr(unreal.Exporter, "run_asset_export_task"):
            unreal.Exporter.run_asset_export_task(task)
        else:
            unreal.Exporter.run_asset_export_tasks([task])
        
        # 验证文件是否成功创建
        if os.path.exists(tga_filename) and os.path.getsize(tga_filename) > 0:
            print(f"✅ 贴图 {texture_name}.tga 已导出")
            return tga_filename
        else:
            print(f"⚠️ TGA导出后文件不存在或为空: {texture_name}")
    except Exception as e:
        print(f"⚠️ TGA导出失败: {texture_name}，错误: {e}")
    
    # TGA失败，尝试导出EXR
    exr_filename = os.path.join(output_dir, f"{texture_name}.exr")
    
    # 删除可能存在的旧文件
    if os.path.exists(exr_filename):
        os.remove(exr_filename)
    
    task.filename = exr_filename
    try:
        if hasattr(unreal.Exporter, "run_asset_export_task"):
            unreal.Exporter.run_asset_export_task(task)
        else:
            unreal.Exporter.run_asset_export_tasks([task])
        
        # 验证文件是否成功创建
        if os.path.exists(exr_filename) and os.path.getsize(exr_filename) > 0:
            print(f"✅ 贴图 {texture_name}.exr 已导出")
            return exr_filename
        else:
            print(f"❌ EXR导出后文件不存在或为空: {texture_name}")
    except Exception as exr_e:
        print(f"❌ EXR导出也失败: {texture_name}，错误: {exr_e}")
    
    return None


def export_static_mesh_to_fbx(mesh, output_dir):
    """导出静态网格体为FBX"""
    os.makedirs(output_dir, exist_ok=True)
    mesh_name = mesh.get_name()
    filename = os.path.join(output_dir, f"{mesh_name}.fbx")

    task = unreal.AssetExportTask()
    task.object = mesh
    task.filename = filename
    task.automated = True
    task.prompt = False
    task.replace_identical = True

    try:
        if hasattr(unreal.Exporter, "run_asset_export_task"):
            success = unreal.Exporter.run_asset_export_task(task)
        else:
            success = unreal.Exporter.run_asset_export_tasks([task])
        if success:
            print(f"✅ 模型 {mesh_name} 已导出至 {filename}")
            return filename
        else:
            print(f"❌ 模型 {mesh_name} 导出失败")
            return None
    except Exception as e:
        print(f"导出模型 {mesh_name} 时出错: {e}")
        return None


def get_static_mesh_materials(mesh):
    """获取模型的所有材质槽+材质"""
    materials = []
    try:
        static_materials = mesh.get_editor_property("static_materials")
        for idx, sm in enumerate(static_materials):
            mat = sm.get_editor_property("material_interface")
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
                idx += 1
            except:
                break
    return materials


def process_static_mesh(mesh):
    """处理单个静态网格体，导出模型和贴图"""
    mesh_name = mesh.get_name()
    print(f"\n========================================")
    print(f"开始处理模型：{mesh_name}")

    # 导出模型本身
    export_static_mesh_to_fbx(mesh, fbxDir)

    # 每个模型独立的JSON数据结构：材质名 → 参数名:路径
    current_model_data = {}
    materials = get_static_mesh_materials(mesh)

    for idx, material in materials:
        mat_name = material.get_name()

        # 只处理材质实例
        if not isinstance(
            material, (unreal.MaterialInstanceConstant, unreal.MaterialInstance)
        ):
            continue

        try:
            texture_params = material.get_editor_property(
                "texture_parameter_values"
            )
        except:
            texture_params = []

        for param in texture_params:
            try:
                param_info = param.get_editor_property("parameter_info")
                param_name = str(param_info.get_editor_property("name"))

                texture = param.get_editor_property("parameter_value")
                if not texture or not isinstance(texture, unreal.Texture):
                    continue

                if not get_texture_suffix_key(texture.get_name()):
                    continue

                tex_path = texture.get_path_name()
                if tex_path not in exported_textures or not os.path.exists(exported_textures[tex_path]):
                    # 如果缓存中没有，或者缓存的文件不存在，则重新导出
                    local_path = export_texture_to_tga(texture, texDir)
                    exported_textures[tex_path] = local_path
                else:
                    local_path = exported_textures[tex_path]

                if not local_path:
                    continue

                if mat_name not in current_model_data:
                    current_model_data[mat_name] = {}
                # 使用绝对路径存储到JSON
                current_model_data[mat_name][param_name] = local_path
                print(f"├─ 材质：{mat_name} | 参数：{param_name} | 路径：{local_path}")

            except Exception as e:
                continue

    # 生成JSON文件
    save_model_json(mesh_name, current_model_data)


def save_model_json(mesh_name, model_data):
    """保存模型的JSON配置文件"""
    if not model_data:
        print(f"⚠️ 模型 {mesh_name} 未找到符合条件的贴图参数")
        return

    json_filename = f"{mesh_name}.json"
    json_file_path = os.path.join(texDir, json_filename)
    
    # 先删除旧文件
    if os.path.exists(json_file_path):
        os.remove(json_file_path)
        print(f"已删除旧JSON文件: {json_filename}")
    
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(model_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 模型 {mesh_name} JSON 已保存：{json_filename}")


def main():
    """主函数：处理所有选中的静态网格体"""
    # 获取内容浏览器选中的静态网格体
    selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
    static_meshes = unreal.EditorFilterLibrary.by_class(selected_assets, unreal.StaticMesh)
    
    if not static_meshes:
        print("请在内容浏览器中选择静态网格体！")
        return
    
    # 遍历每个模型，单独生成JSON
    for mesh in static_meshes:
        process_static_mesh(mesh)

    print("\n========================================")
    print("所有模型处理完成！")


if __name__ == "__main__":
    main()